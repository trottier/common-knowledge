"""Preserve modern hybrid checks while using an immutable extracted tool."""

import hashlib
import io
import subprocess
import zipfile

import pytest

from ck.apkverifier import build_tool_archive, verifier_jar, verify_apk
from ck.catalog import Item


def fixture_item(payload, *, apk=False):
    item = {
        "id": "candidate" if apk else "sdk_tool",
        "family": "apk" if apk else "binaries",
        "title": "Unit test payload",
        "url": "https://dl.google.com/android/repository/build-tools_r37_linux.zip",
        "version": "fixture",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "license": "Apache-2.0" if apk else "LicenseRef-Android-SDK",
        "attribution": "Fixture",
        "license_proof_url": "https://developer.android.com/studio/terms",
        "placement": "hub_only",
        "dest": "build/apk-verifier/",
        "profiles": ["sample"],
    }
    if apk:
        item.update(signer_cert_sha256="1" * 64, source_url="https://example.invalid/source")
    return Item.model_validate(item)


@pytest.fixture
def inputs(tmp_path):
    jar_bytes, apk_bytes = b"fixture verifier jar", b"fixture APK"
    jar, apk = tmp_path / "tool.jar", tmp_path / "app.apk"
    jar.write_bytes(jar_bytes)
    apk.write_bytes(apk_bytes)
    spec = {
        "jar_member": "sdk/lib/apksigner.jar",
        "jar_sha256": hashlib.sha256(jar_bytes).hexdigest(),
        "jar_size_bytes": len(jar_bytes),
        "apk_policies": {
            "candidate": {
                "required_schemes": ["v3", "v3.2"],
                "certificate_roles": {"V3.2 Hybrid PQC Signer": "2" * 64},
            }
        },
    }
    return fixture_item(apk_bytes, apk=True), apk, jar, spec


def output(*, hybrid=True):
    return (
        "Verifies\nVerified using v3 scheme (APK Signature Scheme v3): true\n"
        f"Verified using v3.2 scheme (APK Signature Scheme v3.2): {str(hybrid).lower()}\n"
        f"V3.0 Signer: certificate SHA-256 digest: {'1' * 64}\n"
        f"V3.2 Hybrid PQC Signer: (minSdkVersion=36) certificate SHA-256 digest: {'2' * 64}\n"
    )


def test_modern_verification_keeps_the_full_default_sdk_range(inputs, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, output(), "")

    monkeypatch.setattr("ck.apkverifier.subprocess.run", run)
    result = verify_apk(*inputs)
    assert result["signature_verified"]
    assert result["sdk_range_override"] is None
    assert not result["source_completeness_or_release_approval"]
    assert "--max-sdk-version" not in calls[0]
    assert "--min-sdk-version" not in calls[0]
    assert "sign" not in calls[0]


@pytest.mark.parametrize(
    "status,stdout,stderr",
    [
        (1, "", "Hybrid signature block missing"),
        (0, output(hybrid=False), ""),
        (0, output() + "WARNING: Unknown additional attribute\n", ""),
        (0, output().replace("1" * 64, "3" * 64), ""),
        (0, output().replace("2" * 64, "3" * 64), ""),
    ],
)
def test_stripping_unknown_attribute_or_signer_mismatch_is_not_approval(
    inputs, monkeypatch, status, stdout, stderr
):
    monkeypatch.setattr(
        "ck.apkverifier.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, status, stdout, stderr),
    )
    with pytest.raises(ValueError):
        verify_apk(*inputs)


def test_changed_tool_is_rejected_before_execution(inputs, monkeypatch):
    _, _, jar, _ = inputs
    jar.write_bytes(b"changed")
    monkeypatch.setattr(
        "ck.apkverifier.subprocess.run", lambda *args, **kwargs: pytest.fail("executed")
    )
    with pytest.raises(ValueError, match="JAR changed"):
        verify_apk(*inputs)


def test_original_member_is_bounded_and_restores_a_corrupt_tool_cache(tmp_path, inputs):
    _, _, jar, spec = inputs
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(spec["jar_member"], jar.read_bytes())
        archive.writestr("../../unused", b"never extracted")
    original = payload.getvalue()
    item = fixture_item(original)
    archive = tmp_path / "sdk.zip"
    archive.write_bytes(original)
    tools = tmp_path / "tools"
    extracted = verifier_jar(archive, item, spec, tools)
    assert extracted.read_bytes() == jar.read_bytes()
    extracted.write_bytes(b"corrupt cache")
    assert verifier_jar(archive, item, spec, tools).read_bytes() == jar.read_bytes()
    assert archive.read_bytes() == original
    assert not (tmp_path / "unused").exists()
    with pytest.raises(ValueError, match="size"):
        verifier_jar(archive, item, {**spec, "jar_size_bytes": 1}, tmp_path / "different")


def test_sdk_bootstrap_is_build_only_and_size_bounded(tmp_path):
    class Response(io.BytesIO):
        url = "https://dl.google.com/android/repository/build-tools_r37_linux.zip"

    payload = b"fixture SDK archive"
    item = fixture_item(payload)
    result = build_tool_archive(
        item, tmp_path / "cache", opener=lambda *args, **kwargs: Response(payload)
    )
    assert result.read_bytes() == payload
    with pytest.raises(ValueError, match="build-only"):
        build_tool_archive(item.model_copy(update={"placement": "universal"}), tmp_path)
    with pytest.raises(ValueError, match="exceeds"):
        build_tool_archive(
            item, tmp_path / "overflow", opener=lambda *args, **kwargs: Response(payload + b"extra")
        )
    assert not list((tmp_path / "overflow").iterdir())
