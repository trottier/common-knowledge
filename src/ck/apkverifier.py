"""Pinned modern APK verification without changing the frozen build container."""

import hashlib
import re
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from ck.catalog import Item
from ck.fetch import HttpsRedirects, digest


def build_tool_archive(item: Item, cache: Path, *, opener=None) -> Path:
    """Fetch an exact build-only SDK archive; never place or approve SDK payloads.

    This deliberately separate bootstrap is for the explicitly cataloged SDK
    verifier input, whose SDK terms differ from redistributable drive content.
    It does not relax normal content fetching or any release/license review.
    """
    if (
        item.family != "binaries"
        or item.placement != "hub_only"
        or item.dest != "build/apk-verifier/"
        or not str(item.url).startswith("https://dl.google.com/android/repository/build-tools_")
        or not isinstance(item.size_bytes, int)
        or not re.fullmatch(r"[0-9a-f]{64}", item.sha256)
    ):
        raise ValueError("Verifier bootstrap requires a pinned build-only Google SDK archive")
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / item.sha256
    if (
        target.is_file()
        and target.stat().st_size == item.size_bytes
        and digest(target) == item.sha256
    ):
        return target
    open_url = opener or urllib.request.build_opener(HttpsRedirects()).open
    request = urllib.request.Request(item.url, headers={"User-Agent": "CommonKnowledge-build"})
    with open_url(request, timeout=60) as response:
        if not response.url.startswith("https://"):
            raise ValueError("Verifier download left HTTPS")
        with tempfile.NamedTemporaryFile(dir=cache, prefix=".apk-tool-", delete=False) as stream:
            temporary = Path(stream.name)
            checksum, size = hashlib.sha256(), 0
            try:
                while chunk := response.read(min(1024 * 1024, item.size_bytes - size + 1)):
                    size += len(chunk)
                    if size > item.size_bytes:
                        raise ValueError("Verifier archive exceeds catalog size")
                    stream.write(chunk)
                    checksum.update(chunk)
                if size != item.size_bytes or checksum.hexdigest() != item.sha256:
                    raise ValueError("Verifier archive checksum or size mismatch")
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
    temporary.replace(target)
    return target


def verifier_jar(archive: Path, item: Item, spec: dict, tool_cache: Path) -> Path:
    """Copy one original ZIP member to a bounded, checksum-addressed tool cache."""
    if archive.stat().st_size != item.size_bytes or digest(archive) != item.sha256:
        raise ValueError("Unverified SDK archive")
    expected = spec["jar_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Unpinned apksigner JAR")
    tool_cache.mkdir(parents=True, exist_ok=True)
    target = tool_cache / (expected + ".jar")
    if target.is_file() and target.stat().st_size == spec["jar_size_bytes"]:
        if digest(target) == expected:
            return target
    with zipfile.ZipFile(archive) as bundle:
        entry = bundle.getinfo(spec["jar_member"])
        if entry.file_size != spec["jar_size_bytes"]:
            raise ValueError("SDK JAR member size mismatch")
        payload = bundle.read(entry)
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("SDK JAR member checksum mismatch")
    with tempfile.NamedTemporaryFile(dir=tool_cache, prefix=".apksigner-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    temporary.replace(target)
    return target


def verify_apk(item: Item, path: Path, jar: Path, spec: dict, *, java: str = "java") -> dict:
    """Use the modern tool's complete default SDK range, preserving hybrid checks."""
    policy = spec.get("apk_policies", {}).get(item.id)
    if (
        not isinstance(policy, dict)
        or not policy.get("certificate_roles")
        or not policy.get("required_schemes")
    ):
        raise ValueError("Modern APK verification requires an explicit signer/scheme policy")
    if digest(jar) != spec["jar_sha256"] or jar.stat().st_size != spec["jar_size_bytes"]:
        raise ValueError("Cached apksigner JAR changed")
    if (
        item.family != "apk"
        or digest(path) != item.sha256
        or path.stat().st_size != item.size_bytes
    ):
        raise ValueError("APK differs from its catalog pin")
    command = [java, "-jar", str(jar), "verify", "--verbose", "--print-certs", str(path)]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode or result.stderr.strip() or re.search(r"^WARNING:", result.stdout, re.M):
        raise ValueError("Modern APK verification failed: " + result.stderr + result.stdout)
    certificates = re.findall(
        r"^(.+?)\s*certificate SHA-256 digest:\s*([0-9a-fA-F]{64})\s*$",
        result.stdout,
        re.M,
    )
    found = {value.lower() for _, value in certificates}
    if item.signer_cert_sha256 not in found:
        raise ValueError("Modern APK signer does not match the catalog")
    for role, expected in policy.get("certificate_roles", {}).items():
        if not any(
            label.startswith(role) and value.lower() == expected for label, value in certificates
        ):
            raise ValueError("Required platform signer is absent: " + role)
    for scheme in policy.get("required_schemes", []):
        if not re.search(
            rf"^Verified using {re.escape(scheme)} scheme .*: true$", result.stdout, re.M
        ):
            raise ValueError("Required APK signing scheme was not verified: " + scheme)
    if not result.stdout.startswith("Verifies\n"):
        raise ValueError("Modern APK tool produced no verification result")
    return {
        "item_id": item.id,
        "apk_sha256": item.sha256,
        "verifier_jar_sha256": spec["jar_sha256"],
        "sdk_range_override": None,
        "certificates": [
            {"label": label.strip(), "sha256": value.lower()} for label, value in certificates
        ],
        "stdout": result.stdout,
        "stderr": result.stderr,
        "signature_verified": True,
        "source_completeness_or_release_approval": False,
    }
