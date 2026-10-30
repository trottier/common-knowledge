"""Bounded HTTPS downloads, content-addressed caching and format verification."""

import hashlib
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ck.catalog import Item


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
        subprocess.run(["zimcheck", "--all", str(path)], check=True, capture_output=True, text=True)
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
        format_check(item, temporary)
        temporary.replace(target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
