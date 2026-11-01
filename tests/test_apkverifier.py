"""Preserve modern hybrid checks while using an immutable extracted tool."""

import hashlib
import io
import json
import subprocess
import zipfile

import pytest

from ck.apkverifier import build_tool_archive, fetch_catalog_apk, verifier_jar, verify_apk
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


@pytest.mark.parametrize("missing", ["candidate", "certificate_roles", "required_schemes"])
def test_missing_hybrid_policy_cannot_silently_downgrade_verification(inputs, monkeypatch, missing):
    _, _, _, spec = inputs
    if missing == "candidate":
        del spec["apk_policies"][missing]
    else:
        del spec["apk_policies"]["candidate"][missing]
    monkeypatch.setattr(
        "ck.apkverifier.subprocess.run", lambda *args, **kwargs: pytest.fail("executed")
    )
    with pytest.raises(ValueError, match="explicit signer/scheme policy"):
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


def test_selected_apk_fetch_uses_modern_verification_and_an_offline_tool_cache(
    tmp_path, inputs, monkeypatch
):
    item, apk, jar, spec = inputs
    settings = tmp_path / "pipelines/apk_verifier/settings.yaml"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({**spec, "archive_id": "sdk_tool", "jar_id": "jar"}))
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as bundle:
        bundle.writestr(spec["jar_member"], jar.read_bytes())
    archive = fixture_item(payload.getvalue())
    jar_item = fixture_item(jar.read_bytes()).model_copy(update={"id": "jar"})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / archive.sha256).write_bytes(payload.getvalue())
    (cache / item.sha256).write_bytes(apk.read_bytes())
    seen = []

    def verified(apk_item, path, verifier, policy):
        seen.append((apk_item.id, path.read_bytes(), verifier.read_bytes(), policy))
        return {"signature_verified": True, "sdk_range_override": None}

    monkeypatch.setattr("ck.apkverifier.verify_apk", verified)
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open", lambda *a, **k: pytest.fail("network")
    )
    result = fetch_catalog_apk(
        tmp_path, {archive.id: archive, jar_item.id: jar_item}, item, cache, allow_download=False
    )
    assert result.read_bytes() == apk.read_bytes()
    assert seen[0][:3] == (item.id, apk.read_bytes(), jar.read_bytes())
    assert seen[0][3]["apk_policies"][item.id]["required_schemes"] == ["v3", "v3.2"]
    assert json.loads((cache / "audits" / (item.sha256 + "-apksigner.json")).read_text())[
        "signature_verified"
    ]
    (cache / archive.sha256).unlink()
    with pytest.raises(ValueError, match="Missing cached modern"):
        fetch_catalog_apk(
            tmp_path, {archive.id: archive, "jar": jar_item}, item, cache, allow_download=False
        )


def test_license_hold_is_enforced_before_modern_tool_bootstrap(tmp_path, inputs, monkeypatch):
    item, _, _, spec = inputs
    settings = tmp_path / "pipelines/apk_verifier/settings.yaml"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps(spec))
    monkeypatch.setattr(
        "ck.apkverifier.build_tool_archive", lambda *a, **k: pytest.fail("tool fetch")
    )
    held = item.model_copy(update={"requires_legal": True})
    with pytest.raises(ValueError, match="Cannot fetch unconfirmed"):
        fetch_catalog_apk(tmp_path, {}, held, tmp_path / "cache")


def test_selected_app_rename_cannot_fall_back_to_the_older_path_verifier(
    tmp_path, inputs, monkeypatch
):
    item, _, _, _ = inputs
    verifier_settings = tmp_path / "pipelines/apk_verifier/settings.yaml"
    verifier_settings.parent.mkdir(parents=True)
    verifier_settings.write_text(json.dumps({"apk_policies": {}}))
    selected_settings = tmp_path / "pipelines/llm/settings.yaml"
    selected_settings.parent.mkdir(parents=True)
    selected_settings.write_text(json.dumps({"android": {"apk_id": item.id}}))
    monkeypatch.setattr("ck.fetch.fetch", lambda *a, **k: pytest.fail("old verifier fallback"))
    with pytest.raises(ValueError, match="lacks its modern verifier policy"):
        fetch_catalog_apk(tmp_path, {}, item, tmp_path / "cache")
