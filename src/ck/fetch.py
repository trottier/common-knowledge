"""Bounded HTTPS downloads, content-addressed caching and format verification."""

import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ck.catalog import Item

ZIM_CHECKS = {
    "checksum",
    "integrity",
    "empty",
    "metadata",
    "favicon",
    "main_page",
    "redundant",
    "url_internal",
    "url_external",
    "redirect",
}


def zim_report(path: Path, flags: list[str], required: set[str]) -> dict:
    result = subprocess.run(
        ["zimcheck", *flags, "--json", "--threads", "4", str(path)],
        capture_output=True,
        text=True,
    )
    if result.stderr.strip():
        raise ValueError("ZIM checker emitted an unexpected diagnostic: " + result.stderr[-1000:])
    try:
        report = json.loads(result.stdout)
    except (ValueError, TypeError) as error:
        raise ValueError(f"ZIM audit produced no valid report: {result.stderr[-1000:]}") from error
    if not required <= set(report.get("checks", [])) or result.returncode not in {0, 1}:
        raise ValueError("ZIM audit did not complete every required check")
    errors = [entry for entry in report.get("logs", []) if entry.get("level") == "ERROR"]
    if not isinstance(report.get("status"), bool) or (not report["status"] and not errors):
        raise ValueError("ZIM audit failed without a classified diagnostic")
    if report.get("status") is True and (errors or result.returncode):
        raise ValueError("ZIM audit returned an inconsistent success report")
    report.pop("file_name", None)
    report["logs"] = sorted(
        report.get("logs", []), key=lambda value: json.dumps(value, sort_keys=True)
    )
    return report


def verify_zim(
    path: Path, *, regeneration_only: bool = False, allow_broken_links: bool = False
) -> dict:
    """Only regenerated outputs may repair audited content-link defects."""
    if allow_broken_links and not regeneration_only:
        raise ValueError("Broken-link allowance is restricted to regeneration inputs")
    report = zim_report(path, ["--all"], ZIM_CHECKS)
    errors = [entry for entry in report["logs"] if entry.get("level") == "ERROR"]
    allowed = {"url_external"} if regeneration_only else set()
    if allow_broken_links:
        allowed.add("url_internal")
    if any(entry.get("check") not in allowed for entry in errors) or (
        not report.get("status") and not errors
    ):
        details = "; ".join(entry.get("message", "") for entry in errors[:5])
        raise ValueError("ZIM audit failed: " + details)
    if errors and regeneration_only:
        # A failing link phase can prevent later phases from running. Establish
        # structural validity separately, then collect both content audits.
        structural = zim_report(
            path,
            [
                "--checksum",
                "--integrity",
                "--empty",
                "--metadata",
                "--favicon",
                "--main",
                "--redundant",
                "--redirect_loop",
            ],
            ZIM_CHECKS - {"url_internal", "url_external"},
        )
        if structural["status"] is not True:
            raise ValueError("ZIM structural checks failed before regeneration")
        external = zim_report(path, ["--url_external"], {"url_external"})
        internal = zim_report(path, ["--url_internal"], {"url_internal"})
        combined = {
            json.dumps(entry, sort_keys=True): entry
            for entry in [*report["logs"], *external["logs"], *internal["logs"]]
        }
        report["logs"] = [combined[key] for key in sorted(combined)]
        if any(
            entry.get("level") == "ERROR" and entry.get("check") not in allowed
            for entry in report["logs"]
        ):
            raise ValueError("ZIM has additional unrepairable content errors")
        report["supplementary_audits"] = {
            "structure": structural,
            "external": external,
            "internal": internal,
        }
    report["regeneration_only"] = regeneration_only
    report["repairable_internal_links"] = allow_broken_links
    return report


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class HttpsRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValueError("Refusing a download redirect outside HTTPS")
        return super().redirect_request(request, fp, code, message, headers, newurl)


def verify_format(item: Item, path: Path) -> None:
    if item.family == "zim":
        verify_zim(path)
    elif item.family == "apk":
        result = subprocess.run(
            ["apksigner", "verify", "--print-certs", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        signers = re.findall(r"certificate SHA-256 digest:\s*([a-fA-F0-9:]+)", result.stdout)
        if item.signer_cert_sha256 not in {value.replace(":", "").lower() for value in signers}:
            raise ValueError(f"APK signer does not match catalog: {item.id}")


def fetch(item: Item, cache: Path, *, opener=None, format_check=verify_format) -> Path:
    # Human pin review does not prevent quarantine downloads. Placement and
    # releases enforce every review blocker separately.
    problems = [
        problem for problem in item.blockers() if not problem.startswith(f"{item.id}.review:")
    ]
    if problems or item.family == "generated":
        raise ValueError("Cannot fetch unconfirmed input: " + "; ".join(problems or [item.id]))
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / item.sha256
    quarantine = cache / "quarantine" / item.sha256
    if (
        quarantine.is_file()
        and quarantine.stat().st_size == item.size_bytes
        and digest(quarantine) == item.sha256
    ):
        format_check(item, quarantine)
        quarantine.replace(target)
        return target
    if (
        target.is_file()
        and target.stat().st_size == item.size_bytes
        and digest(target) == item.sha256
    ):
        format_check(item, target)
        return target
    temporary = None
    try:
        open_url = opener or urllib.request.build_opener(HttpsRedirects()).open
        request = urllib.request.Request(item.url, headers={"User-Agent": "CommonKnowledge-build"})
        with open_url(request, timeout=60) as response:
            if urlparse(response.url).scheme != "https":
                raise ValueError("Refusing non-HTTPS download")
            with tempfile.NamedTemporaryFile(dir=cache, prefix=".fetch-", delete=False) as stream:
                temporary = Path(stream.name)
                size = 0
                checksum = hashlib.sha256()
                while chunk := response.read(min(1024 * 1024, item.size_bytes - size + 1)):
                    size += len(chunk)
                    if size > item.size_bytes:
                        raise ValueError(f"Download exceeds catalog size: {item.id}")
                    stream.write(chunk)
                    checksum.update(chunk)
        if size != item.size_bytes or checksum.hexdigest() != item.sha256:
            raise ValueError(f"Download size or checksum mismatch: {item.id}")
        try:
            format_check(item, temporary)
        except (ValueError, subprocess.CalledProcessError) as error:
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            temporary.replace(quarantine)
            raise ValueError(
                f"Format verification failed for {item.id}; verified bytes retained "
                f"at {quarantine}: {error}"
            ) from error
        temporary.replace(target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
