import json
from pathlib import Path

import pytest

from ck.atlas import directory_points
from ck.catalog import Item
from ck.directory import Place
from ck.national import COMMON_INPUTS, DirectoryData, build_national_points, load_national_points

ROOT = Path(__file__).resolve().parents[1]


def test_national_snapshot_preserves_omissions_and_rejects_changed_points_or_epoch(
    tmp_path, monkeypatch
):
    identifiers = [*COMMON_INPUTS, "geofabrik_us", "geofabrik_oceania"]
    common = dict(
        family="geodata",
        title="Synthetic source",
        url="https://example.invalid/source",
        version="fixture",
        size_bytes=1,
        sha256="0" * 64,
        license="CC0-1.0",
        attribution="Synthetic test fixture",
        license_proof_url="https://example.invalid/license",
        placement="hub_only",
        dest="build/inputs/",
        profiles=["full"],
    )
    items = {identifier: Item(id=identifier, **common) for identifier in identifiers}
    place = Place(
        id="synthetic-place",
        category="public_library",
        name="Synthetic library",
        address="",
        latitude=1,
        longitude=1,
        source_id="imls_libraries",
        as_of="fixture",
        county="00001",
        county_name="Synthetic county",
        tags={"build_only": "do not publish tags"},
    )
    data = DirectoryData(
        identifiers,
        {"XX": "00"},
        {"00001": "Synthetic county"},
        [place],
        {},
        ["00001"],
        [{"id": "synthetic-omission", "reason": "No source coordinates"}],
        {"XX": "https://example.invalid/agency"},
        {identifier: "fixture" for identifier in identifiers},
    )
    monkeypatch.setattr("ck.national.prepare_data", lambda *args: data)
    output = tmp_path / "points"
    result = build_national_points(ROOT, items, tmp_path, output, 946684800)
    item = Item(
        id="directory_points",
        family="generated",
        title="Synthetic national points",
        version="fixture",
        size_bytes=result["size_bytes"],
        sha256=result["sha256"],
        license="CC0-1.0",
        attribution="Synthetic test fixture",
        license_proof_url="https://example.invalid/license",
        placement="hub_only",
        dest="build/inputs/",
        profiles=["full"],
        inputs=identifiers,
        pipeline_version=result["pipeline_version"],
    )
    restored = load_national_points(item, output, items, 946684800)
    assert restored.places[0].id == place.id
    assert restored.rejected == data.rejected and restored.missing_profiles == ["00001"]
    public = json.loads((output / "files/NATIONAL_SOURCE_DATA.json").read_text())
    assert "tags" not in public["places"][0]
    assert public["omitted_records"] == data.rejected
    _, selected = directory_points(output, "XX", "00")
    assert [entry.id for entry in selected] == [place.id]
    with pytest.raises(ValueError, match="jurisdiction"):
        directory_points(output, "XX", "01")
    with pytest.raises(ValueError, match="epoch"):
        load_national_points(item, output, items, 946684802)
    (output / "places.json").write_text("{}")
    with pytest.raises(ValueError, match="pinned content"):
        load_national_points(item, output, items, 946684800)
