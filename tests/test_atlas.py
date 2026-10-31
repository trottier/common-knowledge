import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader
from shapely import Point, box

from ck.atlas import (
    atlas_budget,
    compose_atlas,
    detail_regions,
    page_data,
    pipeline_version,
    place_labels,
    region_for,
    state_basemap,
)
from ck.config import load_config
from ck.fetch import digest
from ck.geo import Frame
from ck.render import font_files

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = dict(width=1500, height=1800, columns=6, rows=8, padding=0.08, maxzoom=14)


def test_batch_basemap_selection_never_uses_another_state():
    files = {"RI.pmtiles": Path("ri"), "DE.pmtiles": Path("de")}
    assert state_basemap(files, "DE") == Path("de")
    with pytest.raises(ValueError, match="exactly one"):
        state_basemap(files, "AS")
    with pytest.raises(ValueError, match="exactly one"):
        state_basemap({**files, "extra/RI.pmtiles": Path("other-ri")}, "RI")


@pytest.mark.parametrize("coincident,dateline", [(False, False), (True, False), (False, True)])
def test_dense_details_keep_every_point_and_handle_coincident_or_dateline_locations(
    coincident, dateline
):
    from shapely import MultiPolygon
    from shapely.geometry import shape

    from ck.directory import Place

    geometry = (
        MultiPolygon([box(177, 0, 180, 3), box(-180, 0, -177, 3)]) if dateline else box(0, 0, 3, 3)
    )
    places = [
        Place(
            id=f"fixture-{index}",
            category="public_library",
            name="Synthetic library",
            address="",
            latitude=1 if coincident else 0.5 + index / 100,
            longitude=(179 if index % 2 else -179)
            if dateline
            else (1 if coincident else 0.5 + index % 8 / 10),
            source_id="fixture",
            as_of="fixture",
        )
        for index in range(80)
    ]
    parts = list(detail_regions(geometry, places, 25))
    assert sorted(record.id for _, records in parts for record in records) == sorted(
        p.id for p in places
    )
    for region, records in parts:
        assert 1 <= len(records) <= 25
        frame = Frame.fit(region, **SETTINGS)
        coverage = shape(region_for([{"frame": frame.as_dict()}]))
        for place in records:
            assert frame.grid(place.longitude, place.latitude)
            assert coverage.covers(Point(place.longitude, place.latitude))


def test_batch_preparation_reuses_shared_sources_and_keeps_jurisdictions_separate(
    tmp_path, monkeypatch
):
    import hashlib
    import zipfile
    from collections import Counter

    import geopandas as gpd

    from ck.atlas import collect_atlases, prepare_atlases, read_boundaries
    from ck.catalog import Item
    from ck.directory import Place
    from ck.generated import generation_manifest

    cache = tmp_path / "cache"
    cache.mkdir()
    items = {}

    def pin(identifier, payload):
        sha = hashlib.sha256(payload).hexdigest()
        (cache / sha).write_bytes(payload)
        item = Item(
            id=identifier,
            family="geodata",
            title="Synthetic fixture",
            url="https://example.invalid/fixture",
            version="fixture",
            size_bytes=len(payload),
            sha256=sha,
            license="CC0-1.0",
            attribution="Synthetic fixture",
            license_proof_url="https://example.invalid/license",
            placement="hub_only",
            dest="build/inputs/",
            profiles=["full"],
        )
        items[identifier] = item
        return item

    def shape_zip(identifier, frame):
        folder = tmp_path / identifier
        folder.mkdir()
        frame.to_file(folder / "fixture.shp")
        target = folder / "fixture.zip"
        with zipfile.ZipFile(target, "w") as archive:
            for path in sorted(folder.glob("fixture.*")):
                if path != target:
                    archive.write(path, path.name)
        return pin(identifier, target.read_bytes())

    counties = gpd.GeoDataFrame(
        {
            "STATEFP": ["00", "01"],
            "GEOID": ["00001", "01001"],
            "NAMELSAD": ["Synthetic west", "Synthetic east"],
        },
        geometry=[box(0, 0, 1, 1), box(2, 0, 3, 1)],
        crs=4326,
    )
    county_item = shape_zip("census_county_analysis", counties)
    for state, geometry in [("xx", box(0, 0, 1, 1)), ("yy", box(2, 0, 3, 1))]:
        shape_zip(
            "census_places_" + state,
            gpd.GeoDataFrame(
                {"GEOID": [state], "NAME": ["Synthetic city"]}, geometry=[geometry], crs=4326
            ),
        )
    pin("noto_sans", b"Build-only synthetic font placeholder; no PDF is rendered")
    points = tmp_path / "points"
    (points / "files").mkdir(parents=True)
    (points / "files/source.txt").write_text("Synthetic source")
    records = [
        Place(
            id=state,
            category="public_library",
            name="Synthetic library " + state,
            address="",
            latitude=0.5,
            longitude=longitude,
            source_id="fixture",
            as_of="fixture",
            county=county,
            county_name=county,
        ).model_dump()
        for state, longitude, county in [("XX", 0.5, "00001"), ("YY", 2.5, "01001")]
    ]
    (points / "places.json").write_text(
        json.dumps(
            {
                "purpose": "national-atlas-points",
                "states": {"XX": "00", "YY": "01"},
                "counties": {"00001": "Synthetic west", "01001": "Synthetic east"},
                "places": records,
            }
        )
    )
    measured = generation_manifest(
        points,
        "fixture",
        {county_item.id: county_item.sha256},
        complete=True,
        epoch=946684800,
        intermediates=["places.json"],
    )
    items["directory_points"] = county_item.model_copy(
        update={
            "id": "directory_points",
            "family": "generated",
            "url": None,
            "inputs": [county_item.id],
            **measured,
        }
    )
    reads = Counter()

    def read_once(path):
        reads[path.name] += 1
        return read_boundaries(path)

    monkeypatch.setattr("ck.atlas.read_boundaries", read_once)
    output = tmp_path / "atlas"
    jobs = prepare_atlases(ROOT, load_config(ROOT), items, cache, points, output, 946684800)
    assert set(jobs) == {"XX", "YY"}
    assert reads[county_item.sha256] == 1
    for state, path in jobs.items():
        data = json.loads((output / path).read_text())
        assert data["county_count"] == 1
        assert [place["id"] for page in data["pages"] for place in page["places"]] == [state]
        assert data["complete"] is False  # No basemap was supplied.
    with pytest.raises(ValueError, match="epoch"):
        prepare_atlases(
            ROOT, load_config(ROOT), items, cache, points, tmp_path / "wrong-epoch", 946684802
        )

    # Synthetic PDFs exercise collection integrity; native maps are tested separately.
    from pypdf import PdfWriter

    pin("protomaps_us", b"Synthetic basemap placeholder")
    outputs = []
    for state, county in [("XX", "Synthetic west"), ("YY", "Synthetic east")]:
        folder = tmp_path / ("composed-" + state)
        (folder / "files").mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_outline_item(county, 0)
        writer.write(folder / "files" / f"{state}.pdf")
        (folder / "place-index.json").write_text(json.dumps({state: "page 1, grid A1, point 1"}))
        generation_manifest(
            folder,
            pipeline_version(ROOT),
            {
                identifier: items[identifier].sha256
                for identifier in [
                    "census_county_analysis",
                    "noto_sans",
                    "directory_points",
                    "protomaps_us",
                    "census_places_" + state.lower(),
                ]
            },
            complete=True,
            epoch=946684800,
            intermediates=["place-index.json"],
        )
        outputs.append(folder)
    collected = tmp_path / "collected"
    result = collect_atlases(ROOT, items, points, outputs, collected, 946684800)
    assert result["jurisdictions"] == result["counties"] == result["places"] == 2
    assert set(json.loads((collected / "place-index.json").read_text())) == {"XX", "YY"}
    with pytest.raises(ValueError, match="Missing atlas"):
        collect_atlases(ROOT, items, points, outputs[:1], tmp_path / "missing", 946684800)
    (outputs[0] / "place-index.json").write_text("{}")
    with pytest.raises(ValueError, match="index is missing or changed"):
        collect_atlases(ROOT, items, points, outputs, tmp_path / "changed", 946684800)


def test_atlas_uses_bound_point_seeds_without_a_final_directory_cycle(tmp_path):
    from ck.atlas import directory_points
    from ck.fetch import digest

    source = tmp_path / "places.json"
    source.write_text(json.dumps({"purpose": "atlas-points", "places": []}))
    manifest = {"intermediates": [{"path": "places.json", "sha256": digest(source)}]}
    (tmp_path / "generation.json").write_text(json.dumps(manifest))
    assert directory_points(tmp_path)[1] == []
    source.write_text(json.dumps({"purpose": "directory", "places": []}))
    manifest["intermediates"][0]["sha256"] = digest(source)
    (tmp_path / "generation.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="point seed"):
        directory_points(tmp_path)


def test_dense_and_coincident_labels_keep_locations_and_do_not_overlap():
    page = {
        "width": 1500,
        "height": 1800,
        "places": [{"x": 750 + i % 3, "y": 900, "number": i + 1} for i in range(80)],
    }
    original = [(p["x"], p["y"]) for p in page["places"]]
    place_labels(page)
    assert [(p["x"], p["y"]) for p in page["places"]] == original
    boxes = [
        (
            p["label_x"] - 2,
            p["label_y"] - 23,
            p["label_x"] + 14 * len(str(p["number"])) + 4,
            p["label_y"] + 5,
        )
        for p in page["places"]
    ]
    for i, (left, top, right, bottom) in enumerate(boxes):
        assert 0 <= left < right <= page["width"]
        assert 0 <= top < bottom <= page["height"]
        for a, b, c, d in boxes[:i]:
            assert not (left < c and right > a and top < d and bottom > b)


def test_region_covers_all_viewports():
    from shapely.geometry import shape

    frame = Frame.fit(box(-72, 41, -71, 42), **SETTINGS)
    region = shape(region_for([{"frame": frame.as_dict()}]))
    assert region.covers(Point(-71.5, 41.5))
    dateline = Frame.fit(box(178, 51, 179, 52), **SETTINGS)
    assert shape(region_for([{"frame": dateline.as_dict()}])).covers(Point(178.5, 51.5))


def test_atlas_composition_bookmarks_integrity_and_reproducibility(tmp_path):
    from PIL import Image

    class Settings:
        def viewport(self):
            return SETTINGS

    config = load_config(ROOT)
    font = font_files(ROOT, config.languages[0])[0]
    page = page_data("county", "Synthetic county", "test", box(-72, 41, -71, 42), [], Settings())
    place_labels(page)
    jobs = {
        "state": "TEST",
        "schema": 1,
        "epoch": 946684800,
        "pipeline_version": pipeline_version(ROOT),
        "pages": [page],
        "county_count": 1,
        "complete": False,
        "inputs": {},
        "font": {"sha256": digest(font)},
    }
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps(jobs))
    raster = tmp_path / "rasters/county.png"
    raster.parent.mkdir()
    Image.new("RGB", (100, 100), "white").save(raster)
    rendered = {
        "jobs_sha256": digest(jobs_path),
        "system_tools": "Synthetic fixture\n",
        "files": [{"id": "county", "path": "rasters/county.png", "sha256": digest(raster)}],
    }
    (tmp_path / "rendered.json").write_text(json.dumps(rendered))
    for name in ("first", "second"):
        compose_atlas(ROOT, config, jobs_path, tmp_path / name)
    first = tmp_path / "first/files/TEST.pdf"
    assert digest(first) == digest(tmp_path / "second/files/TEST.pdf")
    elsewhere = tmp_path / "different-input-directory"
    elsewhere.mkdir()
    for name in ("jobs.json", "rendered.json"):
        shutil.copyfile(tmp_path / name, elsewhere / name)
    shutil.copytree(tmp_path / "rasters", elsewhere / "rasters")
    compose_atlas(ROOT, config, elsewhere / "jobs.json", tmp_path / "third")
    assert digest(first) == digest(tmp_path / "third/files/TEST.pdf")
    pdf = PdfReader(first)
    assert any(page.images for page in pdf.pages)
    assert [entry["/Title"] for entry in pdf.outline] == ["Synthetic county"]
    assert "DEVELOPMENT ATLAS" in pdf.pages[0].extract_text()
    assert pdf.metadata.creation_date.year == 2000
    size = first.stat().st_size
    assert atlas_budget([tmp_path / "first"], ["TEST"], size)["total_bytes"] == size
    with pytest.raises(ValueError, match="budget exceeded"):
        atlas_budget([tmp_path / "first"], ["TEST"], size - 1)
    with pytest.raises(ValueError, match="Missing atlas"):
        atlas_budget([tmp_path / "first"], ["TEST", "OTHER"], size * 2)
    with pytest.raises(ValueError, match="Duplicate"):
        atlas_budget([tmp_path / "first", tmp_path / "second"], ["TEST"], size * 2)
    raster.write_bytes(b"Changed after rendering")
    with pytest.raises(ValueError, match="checksum mismatch"):
        compose_atlas(ROOT, config, jobs_path, tmp_path / "tampered")
