"""Capture exact publisher API responses for a proposed WikEM catalog.

Run with Python 3.12. This acquisition tool writes a proposal; it does not approve
pins, place content on a drive or contact people. Never commit captured responses.
"""

import argparse
import hashlib
import html
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

SETTINGS = json.loads(
    (Path(__file__).resolve().parents[1] / "pipelines/wikem/settings.yaml").read_text()
)
API = SETTINGS["api_url"]
LICENSE = SETTINGS["license_url"]
LANGUAGES = set(SETTINGS["translation_suffixes"])
USER_AGENT = "CommonKnowledge/0.1 (https://github.com/trottier/common-knowledge)"


class AccessDenied(ValueError):
    def __init__(self, url, raw):
        self.url, self.raw = url, raw
        self.info = json.loads(raw)["error"]["info"]
        super().__init__(self.info)


def record_denial(error, candidates, exclusions, path, phase="revisions"):
    matches = [
        page
        for page in candidates
        if html.unescape(error.info) == f"You are not allowed to view {page['title']}."
    ]
    if len(matches) != 1:
        raise ValueError("Publisher denial does not identify one selected page; stop acquisition")
    page = matches[0]
    exclusions[page["pageid"]] = {
        "pageid": page["pageid"],
        "title": page["title"],
        "reason": "Publisher denied anonymous access",
        "phase": phase,
        "request_url": error.url,
        "response_sha256": checksum(error.raw),
    }
    path.write_text(json.dumps(list(exclusions.values()), ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps({"excluded_restricted_page": page["pageid"], "title": page["title"]}), flush=True
    )


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def request_url(parameters):
    return API + "?" + urllib.parse.urlencode({**parameters, "format": "json", "maxlag": "5"})


def capture(url, target, delay):
    record = target.with_suffix(target.suffix + ".request.json")
    if target.is_file():
        raw = target.read_bytes()
        if not record.is_file() or json.loads(record.read_text()) != {
            "url": url,
            "sha256": checksum(raw),
        }:
            raise ValueError("Cached response belongs to a different request")
        return raw
    for attempt in range(8):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response:
                if urllib.parse.urlsplit(response.url).scheme != "https":
                    raise ValueError("Publisher redirected outside HTTPS")
                data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ValueError("Unexpectedly large publisher response")
            if url != LICENSE:
                result = json.loads(data)
                if "error" in result:
                    if result["error"].get("code") == "maxlag":
                        time.sleep(5)
                        continue
                    if result["error"].get("code") == "accessdenied":
                        time.sleep(delay)
                        raise AccessDenied(url, data)
                    raise ValueError(str(result["error"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".part")
            temporary.write_bytes(data)
            temporary.replace(target)
            record.write_text(json.dumps({"url": url, "sha256": checksum(data)}) + "\n")
            time.sleep(delay)
            return data
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            time.sleep(min(60, int(error.headers.get("Retry-After", 5))))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 7:
                raise
            time.sleep(5)
    raise ValueError("Publisher stayed unavailable; retain the partial acquisition for a retry")


def item(identifier, title, url, raw, version):
    return {
        "id": identifier,
        "family": "docs",
        "title": title,
        "url": url,
        "version": version,
        "size_bytes": len(raw),
        "sha256": checksum(raw),
        "license": "CC-BY-SA-4.0",
        "attribution": "WikEM contributors",
        "license_proof_url": LICENSE,
        "placement": "hub_only",
        "dest": "build/wikem-inputs/",
        "profiles": ["sample", "full"],
        "review": (
            "[[VERIFY: independently review this computed publisher API snapshot pin "
            "and preserve its exact bytes at an immutable URL before release]]"
        ),
    }


def collect_listings(directory, delay):
    directory.mkdir(parents=True, exist_ok=True)
    continuation, records = {}, []
    for number in range(1000):
        url = request_url(
            {
                "action": "query",
                "generator": "allpages",
                "gapnamespace": "0",
                "gaplimit": "500",
                "prop": "info",
                "inprop": "url",
                **continuation,
            }
        )
        target = directory / f"{number:04d}.json"
        raw = capture(url, target, delay)
        records.append(
            {"url": url, "file": target.name, "size_bytes": len(raw), "sha256": checksum(raw)}
        )
        continuation = json.loads(raw).get("continue")
        if not continuation:
            (directory / "pins.json").write_text(json.dumps(records, indent=2) + "\n")
            return
    raise ValueError("Publisher listing exceeded its safety bound without completing")


def snapshot(listings, output, cache, delay, captured_on):
    date.fromisoformat(captured_on)
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    entries, pages = [], {}
    denial_path = output / "denials.json"
    exclusions = {
        entry["pageid"]: entry
        for entry in (json.loads(denial_path.read_text()) if denial_path.exists() else [])
    }
    for number, record in enumerate(json.loads((listings / "pins.json").read_text())):
        raw = (listings / Path(record["file"]).name).read_bytes()
        if len(raw) != record["size_bytes"] or checksum(raw) != record["sha256"]:
            raise ValueError("Source listing checksum changed")
        if not record["url"].startswith(API + "?"):
            raise ValueError("Unexpected publisher listing origin")
        entries.append(
            item(
                f"wikem_listing_{number:04d}",
                "WikEM namespace-zero page listing",
                record["url"],
                raw,
                "API listing snapshot " + captured_on,
            )
        )
        (cache / checksum(raw)).write_bytes(raw)
        for key, page in json.loads(raw).get("query", {}).get("pages", {}).items():
            if key in pages and pages[key] != page:
                raise ValueError("Inconsistent source listing")
            pages[key] = page
    selected = sorted(
        (p for p in pages.values() if p["title"].rsplit("/", 1)[-1].lower() not in LANGUAGES),
        key=lambda p: p["pageid"],
    )
    if not selected or any(p["ns"] != 0 or p["contentmodel"] != "wikitext" for p in selected):
        raise ValueError("Unsupported source selection")
    license_raw = capture(LICENSE, output / "license.html", delay)
    if b"creativecommons.org/licenses/by-sa/4.0/" not in license_raw:
        raise ValueError("Publisher license evidence changed")
    entries.append(
        item(
            "wikem_license_snapshot",
            "WikEM license evidence",
            LICENSE,
            license_raw,
            "Publisher license snapshot " + captured_on,
        )
    )
    (cache / checksum(license_raw)).write_bytes(license_raw)
    revisions = {}
    for number, start in enumerate(range(0, len(selected), 50)):
        batch = [
            p
            for p in selected[start : start + 50]
            if exclusions.get(p["pageid"], {}).get("phase") != "revisions"
        ]
        while batch:
            url = request_url(
                {
                    "action": "query",
                    "revids": "|".join(str(p["lastrevid"]) for p in batch),
                    "prop": "revisions",
                    "rvprop": "ids|timestamp|content",
                    "rvslots": "main",
                }
            )
            try:
                raw = capture(url, output / "revisions" / f"{number:04d}.json", delay)
                break
            except AccessDenied as error:
                record_denial(error, batch, exclusions, denial_path)
                batch = [
                    p for p in batch if exclusions.get(p["pageid"], {}).get("phase") != "revisions"
                ]
        if not batch:
            continue
        result = json.loads(raw)
        if "badrevids" in result.get("query", {}):
            raise ValueError("A selected source revision is not public")
        for page in result.get("query", {}).get("pages", {}).values():
            for revision in page.get("revisions", []):
                revisions[revision["revid"]] = {"pageid": page["pageid"], **revision}
        entries.append(
            item(
                f"wikem_revisions_{number:04d}",
                "WikEM exact revision metadata and source",
                url,
                raw,
                "Exact revision IDs listed in the query",
            )
        )
        (cache / checksum(raw)).write_bytes(raw)
        if number % 20 == 0:
            print(json.dumps({"revision_batches": number + 1}), flush=True)
    metadata_pages = [
        p for p in selected if exclusions.get(p["pageid"], {}).get("phase") != "revisions"
    ]
    if set(revisions) != {p["lastrevid"] for p in metadata_pages}:
        raise ValueError("Revision responses do not cover the selected source snapshot")
    if any(revisions[p["lastrevid"]]["pageid"] != p["pageid"] for p in metadata_pages):
        raise ValueError("A selected revision belongs to another source page")
    articles = [p for p in selected if p["pageid"] not in exclusions and "redirect" not in p]
    for number, page in enumerate(articles):
        revision = page["lastrevid"]
        url = request_url(
            {"action": "parse", "oldid": str(revision), "prop": "text|revid|displaytitle"}
        )
        try:
            raw = capture(url, output / "articles" / f"{revision}.json", delay)
        except AccessDenied as error:
            record_denial(error, [page], exclusions, denial_path, "article")
            continue
        parsed = json.loads(raw).get("parse", {})
        if (
            parsed.get("pageid") != page["pageid"]
            or parsed.get("revid") != revision
            or not parsed.get("text", {}).get("*")
        ):
            raise ValueError("Publisher rendered the wrong source revision")
        entries.append(
            item(
                f"wikem_article_{page['pageid']}",
                "WikEM article: " + page["title"],
                url,
                raw,
                "Revision " + str(revision),
            )
        )
        (cache / checksum(raw)).write_bytes(raw)
        if number % 100 == 0:
            print(json.dumps({"articles": number + 1, "total": len(articles)}), flush=True)
    proposal = output / "catalog.json"
    proposal.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    public = [p for p in selected if p["pageid"] not in exclusions]
    report = {
        "listing_batches": sum(e["id"].startswith("wikem_listing_") for e in entries),
        "selected_pages": len(public),
        "articles": sum(e["id"].startswith("wikem_article_") for e in entries),
        "redirects": sum("redirect" in p for p in public),
        "excluded_restricted_pages": len(exclusions),
        "catalog_entries": len(entries),
        "payload_bytes": sum(e["size_bytes"] for e in entries),
    }
    (output / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    (output / "scope.json").write_text(
        json.dumps(
            {
                "review": "[[VERIFY: review publisher access-denial scope exclusions]]",
                "pages": sorted(exclusions.values(), key=lambda entry: entry["pageid"]),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--captured-on", required=True, help="ISO date of source acquisition")
    args = parser.parse_args()
    if args.delay < 1:
        parser.error("Use at least one second between fresh publisher requests")
    if not (args.listings / "pins.json").is_file():
        collect_listings(args.listings, args.delay)
    snapshot(args.listings, args.output, args.cache, args.delay, args.captured_on)


if __name__ == "__main__":
    main()
