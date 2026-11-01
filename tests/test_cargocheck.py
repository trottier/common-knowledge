import hashlib
import io
import tarfile

import pytest

from ck.cargocheck import archive_text, audit_cargo_sources
from ck.catalog import Item


def archive_item(cache, identifier, files, *, version="1.0.0", inputs=()):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as archive:
        for name, text in files.items():
            payload = text.encode()
            member = tarfile.TarInfo("source/" + name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    payload = data.getvalue()
    sha = hashlib.sha256(payload).hexdigest()
    (cache / sha).write_bytes(payload)
    return Item(
        id=identifier,
        family="docs",
        title="Synthetic source fixture",
        url="https://example.org/source.tar.gz",
        version=version,
        size_bytes=len(payload),
        sha256=sha,
        license="MIT",
        attribution="Synthetic test fixture",
        license_proof_url="https://example.org/license",
        placement="hub_only",
        dest="build/sources/",
        profiles=["sample"],
        inputs=list(inputs),
    )


def source_set(cache, *, crate_name="dependency", upstream_version="1.0.0"):
    crate = archive_item(
        cache,
        "dependency_source",
        {"Cargo.toml": f'[package]\nname="{crate_name}"\nversion="1.0.0"\nlicense="MIT"'},
    )
    upstream = archive_item(
        cache,
        "upstream_source",
        {"crates/local/Cargo.toml": f'[package]\nname="local"\nversion="{upstream_version}"'},
    )
    lock = (
        'version=4\n[[package]]\nname="dependency"\nversion="1.0.0"\n'
        'source="registry+https://github.com/rust-lang/crates.io-index"\n'
        f'checksum="{crate.sha256}"\n'
        '[[package]]\nname="wrapper"\nversion="1.0.0"\n'
        '[[package]]\nname="local"\nversion="1.0.0"\n'
    )
    app = archive_item(
        cache,
        "app_source",
        {
            "tools/Cargo.lock": lock,
            "tools/Cargo.toml": '[package]\nname="wrapper"\nversion="1.0.0"',
        },
        inputs=[crate.id, upstream.id],
    )
    return {item.id: item for item in [app, crate, upstream]}


def test_complete_locked_sources_never_grant_application_or_human_approval(tmp_path):
    items = source_set(tmp_path)
    result = audit_cargo_sources(items, "app_source", "tools/Cargo.lock", tmp_path)
    assert result["complete_cargo_lock_sources"] is True
    assert len(result["registry_packages"]) == 1
    assert {package["name"] for package in result["local_packages"]} == {"local", "wrapper"}
    assert result["complete_application_source_closure"] is False
    assert result["human_license_or_pin_approval"] is False


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing", "Missing or ambiguous registry source"),
        ("identity", "package identity mismatch"),
        ("local_version", "Missing or ambiguous local package source"),
        ("license", "license metadata mismatch"),
        ("tamper", "checksum mismatch"),
    ],
)
def test_incomplete_or_changed_source_set_is_rejected(tmp_path, change, message):
    items = source_set(
        tmp_path,
        crate_name="different" if change == "identity" else "dependency",
        upstream_version="2.0.0" if change == "local_version" else "1.0.0",
    )
    crate = items["dependency_source"]
    if change == "missing":
        items["app_source"].inputs.remove(crate.id)
    elif change == "license":
        crate.license = "Apache-2.0"
    elif change == "tamper":
        path = tmp_path / crate.sha256
        payload = path.read_bytes()
        path.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
    with pytest.raises(ValueError, match=message):
        audit_cargo_sources(items, "app_source", "tools/Cargo.lock", tmp_path)


def test_lockfile_symlink_cannot_stand_in_for_original_source():
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        member = tarfile.TarInfo("source/Cargo.lock")
        member.type = tarfile.SYMTYPE
        member.linkname = "/outside/Cargo.lock"
        archive.addfile(member)
    data.seek(0)
    with tarfile.open(fileobj=data) as archive:
        with pytest.raises(ValueError, match="one regular source file"):
            archive_text(archive, "Cargo.lock")


@pytest.mark.parametrize("name", ["../Cargo.lock", "/Cargo.lock"])
def test_lockfile_cannot_use_an_unsafe_archive_path(name):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.size = 1
        archive.addfile(member, io.BytesIO(b"x"))
    data.seek(0)
    with tarfile.open(fileobj=data) as archive:
        with pytest.raises(ValueError, match="Unsafe source archive path"):
            archive_text(archive, "Cargo.lock")
