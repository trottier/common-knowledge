"""Actual offline restoration rejects changed bytes and changed catalog claims."""

import hashlib
import io
import tarfile

import pytest

from ck.catalog import Item
from ck.sourcebundle import pack_sources, restore_sources, source_records


def fixture(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    raw = b"Original synthetic fixture; not third-party content.\n"
    checksum = hashlib.sha256(raw).hexdigest()
    (cache / checksum).write_bytes(raw)
    item = Item(
        id="source",
        family="docs",
        title="Original fixture",
        url="https://example.invalid/fixture",
        version="1",
        size_bytes=len(raw),
        sha256=checksum,
        license="CC0-1.0",
        attribution="Original test fixture",
        license_proof_url="https://example.invalid/license",
        placement="hub_only",
        dest="build/input.txt",
        profiles=["sample"],
    )
    generated = Item(
        id="generated",
        family="generated",
        title="Generated fixture",
        version="1",
        size_bytes=1,
        sha256="a" * 64,
        license="CC0-1.0",
        attribution="Fixture",
        license_proof_url="https://example.invalid/license",
        placement="universal",
        dest="fixture.txt",
        profiles=["sample"],
        inputs=["source"],
        pipeline_version="fixture-1",
    )
    return cache, {"source": item, "generated": generated}


def test_pack_repeat_and_restore_without_network(tmp_path):
    cache, items = fixture(tmp_path)
    a, b = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    first = pack_sources(items, ["generated"], cache, a, 946684800)
    assert first == pack_sources(items, ["generated"], cache, b, 946684800)
    assert a.read_bytes() == b.read_bytes()
    restored = tmp_path / "restored"
    result = restore_sources(items, ["generated"], a, restored, first["sha256"])
    assert result["source_items"] == 1
    assert (restored / items["source"].sha256).read_bytes() == (
        cache / items["source"].sha256
    ).read_bytes()
    assert restore_sources(items, ["generated"], a, restored, first["sha256"]) == result
    with tarfile.open(a) as archive:
        assert all(
            member.mtime == 946684800 and member.uid == member.gid == 0 for member in archive
        )


def test_bundle_and_catalog_changes_are_rejected(tmp_path):
    cache, items = fixture(tmp_path)
    output = tmp_path / "sources.tar.gz"
    record = pack_sources(items, ["generated"], cache, output, 946684800)
    with pytest.raises(ValueError, match="checksum mismatch"):
        restore_sources(items, ["generated"], output, tmp_path / "restore", "0" * 64)
    items["source"].attribution = "Changed attribution"
    with pytest.raises(ValueError, match="catalog records changed"):
        restore_sources(items, ["generated"], output, tmp_path / "restore", record["sha256"])
    assert not list((tmp_path / "restore").iterdir())


@pytest.mark.parametrize("defect", ["missing", "unexpected", "duplicate", "symlink", "payload"])
def test_member_audit_finishes_before_cache_publication(tmp_path, defect):
    cache, items = fixture(tmp_path)
    original = tmp_path / "original.tar.gz"
    pack_sources(items, ["generated"], cache, original, 946684800)
    broken = tmp_path / "broken.tar.gz"
    with tarfile.open(original) as source, tarfile.open(broken, "w:gz") as target:
        for member in source:
            raw = source.extractfile(member).read()
            if member.name.startswith("cache/"):
                if defect == "missing":
                    continue
                if defect == "unexpected":
                    member.name = "../../escape"
                if defect == "payload":
                    raw = b"!" * len(raw)
                if defect == "symlink":
                    member.type, member.linkname, member.size = tarfile.SYMTYPE, "/tmp/escape", 0
            target.addfile(member, io.BytesIO(raw))
            if defect == "duplicate" and member.name.startswith("cache/"):
                target.addfile(member, io.BytesIO(raw))
    restored = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_sources(
            items, ["generated"], broken, restored, hashlib.sha256(broken.read_bytes()).hexdigest()
        )
    assert not list(restored.iterdir())


def test_cycles_and_corrupt_existing_cache_fail(tmp_path):
    cache, items = fixture(tmp_path)
    bundle = tmp_path / "sources.tar.gz"
    record = pack_sources(items, ["generated"], cache, bundle, 946684800)
    restored = tmp_path / "restored"
    restored.mkdir()
    (restored / items["source"].sha256).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="refusing to replace"):
        restore_sources(items, ["generated"], bundle, restored, record["sha256"])
    assert (restored / items["source"].sha256).read_bytes() == b"corrupt"
    items["generated"].inputs = ["generated"]
    with pytest.raises(ValueError, match="cyclic"):
        source_records(items, ["generated"])
