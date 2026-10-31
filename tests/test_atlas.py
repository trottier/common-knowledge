import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader
from shapely import Point, box

from ck.atlas import (
    atlas_budget,
    compose_atlas,
    page_data,
    pipeline_version,
    place_labels,
    region_for,
)
from ck.config import load_config
from ck.fetch import digest
from ck.geo import Frame
from ck.render import font_files

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = dict(width=1500, height=1800, columns=6, rows=8, padding=0.08, maxzoom=14)


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
