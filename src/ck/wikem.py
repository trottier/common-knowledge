"""Regenerate a text WikEM archive from exact, catalog-pinned API responses.

Generated navigation, notices and the book icon are original CC0-1.0 content.
Publisher article content retains CC BY-SA 4.0.
"""

import hashlib
import html
import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from bs4 import BeautifulSoup, Comment
from PIL import Image, ImageDraw

from ck.catalog import Item
from ck.config import read_yaml
from ck.fetch import verify_zim
from ck.generated import cached_input, generation_manifest
from ck.zimclean import normalize_uuid


@dataclass
class Snapshot:
    pages: dict[str, dict]
    revisions: dict[int, dict]
    articles: dict[int, dict]
    inputs: dict[str, str]
    license_url: str
    origin: str
    exclusions: list[dict] = field(default_factory=list)


def title_key(title: str) -> str:
    title = html.unescape(title).replace("_", " ").strip()
    return title[:1].upper() + title[1:]


def load_snapshot(root: Path, items: dict[str, Item], cache: Path) -> Snapshot:
    settings = read_yaml(root / "pipelines/wikem/settings.yaml")
    api, license_url = settings["api_url"], settings["license_url"]
    prefixes = ("wikem_listing_", "wikem_revisions_", "wikem_article_")
    selected = [item for item in items.values() if item.id.startswith(prefixes)]
    evidence = items.get("wikem_license_snapshot")
    if evidence is None:
        raise ValueError(
            "Pin and fetch the WikEM publisher API snapshot before building its archive"
        )
    license_bytes = cached_input(evidence, cache).read_bytes()
    if (
        evidence.url != license_url
        or b"creativecommons.org/licenses/by-sa/4.0/" not in license_bytes
    ):
        raise ValueError("WikEM license snapshot does not match its catalog proof")
    pages, revisions, articles, inputs = {}, {}, {}, {evidence.id: evidence.sha256}
    continuation, listing_count = {}, 0
    for item in sorted(selected, key=lambda item: item.id):
        if item.license != "CC-BY-SA-4.0" or item.license_proof_url != license_url:
            raise ValueError("Unexpected WikEM source license")
        parsed_url = urlsplit(item.url)
        if parsed_url._replace(query="").geturl() != api:
            raise ValueError("Unexpected WikEM API origin")
        query = parse_qs(parsed_url.query)
        raw = json.loads(cached_input(item, cache).read_bytes())
        if "error" in raw:
            raise ValueError("A pinned WikEM source is an API error")
        inputs[item.id] = item.sha256
        if item.id.startswith("wikem_listing_"):
            if (
                item.id != f"wikem_listing_{listing_count:04d}"
                or query.get("generator") != ["allpages"]
                or query.get("gapnamespace") != ["0"]
                or {key: query.get(key) for key in ("gapcontinue", "continue") if key in query}
                != {key: [value] for key, value in continuation.items()}
            ):
                raise ValueError("Unexpected WikEM page listing")
            listing_count += 1
            continuation = raw.get("continue", {})
            for page in raw.get("query", {}).get("pages", {}).values():
                key = title_key(page["title"])
                if key in pages and pages[key] != page:
                    raise ValueError("Inconsistent WikEM source page listing")
                pages[key] = page
        elif item.id.startswith("wikem_revisions_"):
            requested = {int(value) for value in query.get("revids", [""])[0].split("|")}
            returned = set()
            for page in raw.get("query", {}).get("pages", {}).values():
                for revision in page.get("revisions", []):
                    if "texthidden" in revision or "suppressed" in revision:
                        raise ValueError("A selected WikEM revision is hidden or suppressed")
                    identifier = revision["revid"]
                    if identifier in revisions:
                        raise ValueError("Duplicate WikEM source revision")
                    revisions[identifier] = {"pageid": page["pageid"], **revision}
                    returned.add(identifier)
            if requested != returned:
                raise ValueError("WikEM revision response differs from its requested IDs")
        else:
            parsed = raw.get("parse", {})
            identifier = parsed.get("pageid")
            if query.get("oldid") != [str(parsed.get("revid"))] or not isinstance(identifier, int):
                raise ValueError("WikEM rendered the wrong article revision")
            if item.id != f"wikem_article_{identifier}" or identifier in articles:
                raise ValueError("Duplicate or mislabeled WikEM article source")
            articles[identifier] = {"revision": parsed["revid"], "html": parsed["text"]["*"]}
    suffixes = set(settings["translation_suffixes"])
    pages = {
        key: page
        for key, page in pages.items()
        if page["title"].rsplit("/", 1)[-1].lower() not in suffixes
    }
    exclusions = read_yaml(root / "config/wikem-scope.yaml")["pages"]
    excluded = {entry["pageid"] for entry in exclusions}
    page_ids = {page["pageid"]: page for page in pages.values()}
    if len(excluded) != len(exclusions) or any(
        entry["pageid"] not in page_ids
        or entry["title"] != page_ids[entry["pageid"]]["title"]
        or entry["reason"] != "Publisher denied anonymous access"
        for entry in exclusions
    ):
        raise ValueError("WikEM scope exclusions do not match publisher listing observations")
    pages = {key: page for key, page in pages.items() if page["pageid"] not in excluded}
    revisions = {
        key: revision for key, revision in revisions.items() if revision["pageid"] not in excluded
    }
    if continuation or not listing_count:
        raise ValueError("WikEM namespace listing stopped before the final publisher page")
    if not pages or set(revisions) != {page["lastrevid"] for page in pages.values()}:
        raise ValueError("WikEM revision metadata does not cover the selected source snapshot")
    expected = {page["pageid"] for page in pages.values() if "redirect" not in page}
    if articles.keys() != expected:
        raise ValueError("WikEM rendered articles do not cover every selected source page")
    for page in pages.values():
        revision = revisions[page["lastrevid"]]
        if revision["pageid"] != page["pageid"] or page["ns"] != 0:
            raise ValueError("WikEM source page and revision disagree")
        datetime.fromisoformat(revision["timestamp"].replace("Z", "+00:00"))
        if "redirect" not in page and articles[page["pageid"]]["revision"] != page["lastrevid"]:
            raise ValueError("WikEM article HTML and selected revision disagree")
    origin = urlsplit(api)._replace(path="", query="").geturl()
    return Snapshot(pages, revisions, articles, inputs, license_url, origin, exclusions)


def local_link(href: str, pages: dict[str, dict], origin: str) -> str | None:
    if href.startswith("#"):
        return href
    parsed = urlsplit(href)
    if parsed.scheme and parsed.scheme not in {"https", "http"}:
        return None
    if parsed.netloc and parsed.netloc != urlsplit(origin).netloc:
        return href if parsed.scheme == "https" else None
    if parsed.path.startswith("/wiki/"):
        title = unquote(parsed.path.removeprefix("/wiki/"))
    elif parsed.path == "/w/index.php":
        query = parse_qs(parsed.query)
        if set(query) != {"title"}:
            return None
        title = query["title"][0]
    else:
        return None
    target = pages.get(title_key(title))
    if target is None:
        return None
    return (
        str(target["pageid"])
        + ".html"
        + ("#" + quote(unquote(parsed.fragment)) if parsed.fragment else "")
    )


def clean_html(raw: str, pages: dict[str, dict], origin: str) -> tuple[str, dict]:
    soup = BeautifulSoup(raw, "html.parser")
    content = soup.select_one(".mw-parser-output")
    if content is None:
        raise ValueError("WikEM article main content is missing")
    for comment in content.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    counts = {"omitted_media": 0, "disabled_controls": 0, "unavailable_links": 0}
    for element in list(content.find_all("script")):
        if str(element.get("type", "")).lower().startswith("math/tex"):
            replacement = soup.new_tag("span")
            replacement.string = "[Source formula: " + element.get_text() + "]"
            element.replace_with(replacement)
    for element in list(content.select("script, style, link, meta, base, .mw-editsection")):
        element.decompose()
    for element in list(content.select("img, svg, video, audio, iframe, object, embed, canvas")):
        if element.attrs is None:
            continue
        alternative = (
            element.get("alt") or element.get("aria-label") or element.get_text(" ", strip=True)
        )
        replacement = soup.new_tag("span")
        replacement.string = (
            "[Source figure or media omitted" + (": " + alternative if alternative else "") + "]"
        )
        element.replace_with(replacement)
        counts["omitted_media"] += 1
    for element in list(content.select("form, input, button, textarea, select")):
        if element.attrs is None:
            continue
        if element.name == "form":
            element.unwrap()
        else:
            replacement = soup.new_tag("span")
            replacement.string = "[Interactive control unavailable offline.] " + element.get_text(
                " ", strip=True
            )
            element.replace_with(replacement)
        counts["disabled_controls"] += 1
    for element in [content, *content.find_all(True)]:
        attributes = {
            key: value
            for key, value in element.attrs.items()
            if key in {"id", "lang", "dir", "colspan", "rowspan", "scope", "headers", "title"}
        }
        if element.name == "a" and element.get("href"):
            target = local_link(element["href"], pages, origin)
            if target:
                attributes["href"] = target
            else:
                counts["unavailable_links"] += 1
        element.attrs = attributes
    content["class"] = ["mw-parser-output"]
    identifiers = {element["id"] for element in content.find_all(id=True)}
    for link in content.find_all("a", href=True):
        if link["href"].startswith("#") and unquote(link["href"][1:]) not in identifiers:
            del link["href"]
            counts["unavailable_links"] += 1
    return str(content), counts


def page_document(page: dict, revision: dict, body: str, origin: str) -> bytes:
    title = html.escape(page["title"])
    date = revision["timestamp"][:10]
    redirect = '<meta name="ck-source-redirect" content="1">' if "redirect" in page else ""
    source = origin + "/w/index.php?oldid=" + str(revision["revid"])
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' "
        "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
        "<title>"
        + title
        + "</title>"
        + redirect
        + "<style>body{font:1rem/1.5 sans-serif;margin:1rem}"
        "table{border-collapse:collapse}td,th{border:1px solid #888;padding:.3rem}"
        ".notice,footer{border:1px solid #888;padding:.5rem}a{overflow-wrap:anywhere}</style>"
        "</head><body><p><a href='../index.html'>Article index</a></p><h1>" + title + "</h1>"
        "<p class='notice'>Common Knowledge offline text adaptation. Figures and active widgets "
        "are omitted. Original article text and tables remain. "
        "Unavailable links have no target.</p>"
        "<div id='mw-content-text'>" + body + "</div><footer class='zim-footer'>"
        "WikEM contributors. <a href='"
        + html.escape(source, quote=True)
        + "' title='Modified "
        + date
        + "'>"
        "Original revision " + str(revision["revid"]) + " · " + date + "</a>. "
        "<a href='https://creativecommons.org/licenses/by-sa/4.0/'>CC BY-SA 4.0</a>. "
        "Regenerated by Common Knowledge; the source download is unchanged.</footer></body></html>"
    ).encode("utf-8")


def pipeline_version(root: Path) -> str:
    recipe = hashlib.sha256()
    for name in (
        "src/ck/wikem.py",
        "src/ck/catalog.py",
        "src/ck/config.py",
        "src/ck/zimclean.py",
        "src/ck/generated.py",
        "src/ck/fetch.py",
        "pipelines/wikem/settings.yaml",
        "config/wikem-scope.yaml",
        "pyproject.toml",
        "uv.lock",
        "Dockerfile.build",
        "catalog/buildtools.yaml",
        "tools/bootstrap_zim.py",
        "config/debian.sources",
    ):
        recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
    return "wikem-api-v1-" + recipe.hexdigest()


def build_archive(
    root: Path, items: dict[str, Item], cache: Path, output: Path, epoch: int
) -> dict:
    from libzim.writer import Creator, Hint, StringProvider
    from libzim.writer import Item as WriterItem

    if output.exists():
        raise ValueError("WikEM output must be new")
    snapshot = load_snapshot(root, items, cache)
    recipe = pipeline_version(root)
    pages = sorted(snapshot.pages.values(), key=lambda page: page["pageid"])

    class Entry(WriterItem):
        def __init__(self, path, title, data):
            self.path, self.title, self.data = path, title, data

        def get_path(self):
            return self.path

        def get_title(self):
            return self.title

        def get_mimetype(self):
            return "text/html"

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: 1}

        def get_contentprovider(self):
            return StringProvider(self.data)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-wikem-", dir=output.parent) as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        target = stage / "files/WikEM-offline.zim"
        creator = Creator(target).config_nbworkers(1).config_indexing(False, "eng")
        audit = {
            "articles": [],
            "redirects": [],
            "title_search": True,
            "full_text_index": False,
            "scope_exclusions": snapshot.exclusions,
        }
        with creator:
            for key, value in {
                "Name": "wikem_en_nopic",
                "Title": "WikEM — offline text edition",
                "Creator": "WikEM contributors",
                "Publisher": "Common Knowledge",
                "Date": datetime.fromtimestamp(epoch, UTC).date().isoformat(),
                "Language": "eng",
                "Description": "Clinical reference from pinned WikEM revisions",
                "License": "CC-BY-SA-4.0",
                "Flavour": "nopic",
            }.items():
                creator.add_metadata(key, value)
            image = Image.new("RGB", (48, 48), "white")
            drawing = ImageDraw.Draw(image)
            drawing.rectangle((9, 7, 38, 40), outline="black", width=3)
            for y in (16, 24, 32):
                drawing.line((16, y, 31, y), fill="black", width=2)
            icon = BytesIO()
            image.save(icon, format="PNG")
            creator.add_illustration(icon.getvalue(), 48)
            creator.set_mainpath("index.html")
            links = "".join(
                "<li><a href='A/"
                + str(page["pageid"])
                + ".html'>"
                + html.escape(page["title"])
                + "</a></li>"
                for page in sorted(pages, key=lambda page: page["title"].casefold())
            )
            index = (
                "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>WikEM</title>"
                "</head><body><h1>WikEM offline text edition</h1>"
                "<p>Regenerated from pinned publisher revisions. "
                "Figures and active widgets are omitted. "
                "Read START for the drive's first actions. Original content: WikEM contributors, "
                "CC BY-SA 4.0.</p><ul>" + links + "</ul></body></html>"
            )
            creator.add_item(Entry("index.html", "WikEM article index", index.encode()))
            for page in pages:
                revision = snapshot.revisions[page["lastrevid"]]
                if "redirect" in page:
                    source = revision["slots"]["main"]["*"]
                    match = re.match(r"\s*#redirect\s*\[\[([^\]]+)\]\]", source, re.I)
                    if not match:
                        raise ValueError("Unsupported WikEM redirect source syntax")
                    destination = match[1].split("|", 1)[0]
                    title, _, fragment = destination.partition("#")
                    link = local_link(
                        "/wiki/"
                        + quote(title.replace(" ", "_"))
                        + ("#" + quote(fragment) if fragment else ""),
                        snapshot.pages,
                        snapshot.origin,
                    )
                    body = (
                        "<div class='mw-parser-output'><p>Source redirect: "
                        + (
                            "<a href='"
                            + html.escape(link, quote=True)
                            + "'>"
                            + html.escape(destination)
                            + "</a>"
                            if link
                            else html.escape(destination)
                            + " [Target unavailable in this offline edition.]"
                        )
                        + "</p></div>"
                    )
                    audit["redirects"].append(
                        {
                            "pageid": page["pageid"],
                            "target": destination,
                            "available": link is not None,
                        }
                    )
                else:
                    body, counts = clean_html(
                        snapshot.articles[page["pageid"]]["html"], snapshot.pages, snapshot.origin
                    )
                    audit["articles"].append(
                        {"pageid": page["pageid"], "revision": page["lastrevid"], **counts}
                    )
                creator.add_item(
                    Entry(
                        "A/" + str(page["pageid"]) + ".html",
                        page["title"],
                        page_document(page, revision, body, snapshot.origin),
                    )
                )
        normalize_uuid(
            target, json.dumps([recipe, snapshot.inputs, epoch], sort_keys=True).encode()
        )
        audit["zimcheck"] = verify_zim(target)
        (stage / "audit.json").write_text(json.dumps(audit, sort_keys=True) + "\n")
        measured = generation_manifest(
            stage, recipe, snapshot.inputs, complete=True, epoch=epoch, intermediates=["audit.json"]
        )
        stage.rename(output)
    return {**measured, "articles": len(audit["articles"]), "redirects": len(audit["redirects"])}
