import importlib.util
from pathlib import Path

import pytest

from ck.assemble import write_manifest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("copy_index", ROOT / "tools/build_copy_index.py")
index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(index)


def test_inventory_uses_actual_files_excludes_duplicates_and_rejects_changes(tmp_path):
    for name in [
        "1_START/English/01_START_phone.pdf",
        "4_PHONE_PACK/English/01_START_phone.pdf",
        "BACKUP/1_START/English/01_START_phone.pdf",
        "4_PHONE_PACK/0_WHAT_TO_COPY.pdf",
        "4_PHONE_PACK/LICENSE.TXT",
    ]:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"synthetic fixture")
    expected = write_manifest(tmp_path)
    rows = index.inventory(tmp_path, expected)
    assert [row["path"] for row in rows] == [
        "1_START/English/01_START_phone.pdf",
        "4_PHONE_PACK/English/01_START_phone.pdf",
    ]
    assert all((tmp_path / row["path"]).is_file() for row in rows)
    assert rows[0]["decimal_mb"] == "0.000017"
    (tmp_path / rows[0]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="Manifest checksum mismatch"):
        index.inventory(tmp_path, expected)
    with pytest.raises(ValueError, match="Original drive manifest"):
        index.inventory(tmp_path, "0" * 64)


def test_optional_formats_are_indexed_and_companion_source_stays_with_folders(
    tmp_path,
):
    for name in [
        "5_MEDICAL_REFERENCE/book.zim",
        "3_MAPS_AND_PLACES/map.obf",
        "3_MAPS_AND_PLACES/source.osm.pbf",
        "3_MAPS_AND_PLACES/SOURCE.TXT",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic")
    rows = index.inventory(tmp_path, write_manifest(tmp_path))
    assert {row["format"] for row in rows} == {"ZIM", "OBF"}
    assert all((tmp_path / row["path"]).is_file() for row in rows)
