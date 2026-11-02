import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject

from ck.config import read_yaml
from ck.map_recompose import (
    artifact_path,
    authenticated_html,
    places_from_html,
    prepared_data,
    recompose,
    require_pdf_layout,
)

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_pdf(path, html):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    identity = hashlib.sha256(html.encode()).hexdigest().encode()
    writer._ID = ArrayObject([ByteStringObject(identity), ByteStringObject(b"fixture")])
    writer.write(path)


@pytest.fixture
def pinned_font():
    item = next(
        item for item in read_yaml(ROOT / "catalog/fonts.yaml") if item["id"] == "noto_sans"
    )
    path = Path(os.environ.get("CK_FONT_CACHE", ROOT / "cache")) / item["sha256"]
    if not path.is_file():
        if "CK_FONT_CACHE" in os.environ:
            pytest.fail("Authoritative font cache lacks pinned Noto Sans")
        pytest.skip("Requires the existing pinned font cache")
    assert digest(path) == item["sha256"]
    return {"id": item["id"], "path": str(path), "sha256": item["sha256"]}


@pytest.fixture
def fixture_proof(tmp_path, pinned_font):
    root, prepared = tmp_path / "root", tmp_path / "prepared"
    for name in [
        "src/ck/map_recompose.py",
        "src/ck/countyproof.py",
        "src/ck/render.py",
        "src/ck/catalog.py",
        "src/ck/config.py",
        "tools/recompose_county_map.py",
        "templates/county-proof.html.j2",
        "config/build.yaml",
        "pyproject.toml",
        "uv.lock",
        "Dockerfile.build",
        "config/debian.sources",
    ]:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (root / "pipelines/atlas").mkdir(parents=True)
    audit = prepared / "audit"
    audit.mkdir(parents=True)
    leaf = "Bristol County fixture.pdf"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="190mm" height="230mm" '
        'viewBox="0 0 190 230"><text x="20" y="40">Fixture Street</text></svg>'
    )
    locator = '<svg xmlns="http://www.w3.org/2000/svg"><text>R1C1</text></svg>'
    overview = '<svg xmlns="http://www.w3.org/2000/svg"><text>Fixture overview</text></svg>'
    table = (
        "<table><tbody><tr><td>1</td><td>Fixture &amp; Library</td>"
        "<td>public library<br>Address not supplied</td></tr></tbody></table>"
    )
    documents = {leaf: locator + svg, "0_OVERVIEW.pdf": overview + table}
    for identifier, source in [("R1C1", svg), ("locator", locator), ("overview", overview)]:
        (audit / (identifier + ".svg")).write_text(source)
    records = []
    for name, html in documents.items():
        (audit / (name + ".html")).write_text(html)
        target = prepared / "3_MAPS_AND_PLACES/RI/Bristol County" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        original_pdf(target, html)
        records.append(
            {
                "path": str(target.relative_to(prepared)),
                "sha256": digest(target),
                "size_bytes": target.stat().st_size,
            }
        )
    metadata = {
        "status": "Unreviewed fixture",
        "detail_pdf": leaf,
        "producer": {"version": "fixture", "source_files": {}},
        "policy": {"epoch": 1793404800, "scale_denominator": 25000, "max_pages": 64},
        "fonts": [pinned_font],
        "zctas": ["fixture"],
        "sheets": [
            {
                "id": "R1C1",
                "page": 2,
                "neighbors": {},
                "bounds": [0, 0, 1, 1],
                "effective_scale_denominator": 25000,
            }
        ],
        "overview": {"poi_ids": ["fixture-library"]},
        "street_name_coverage": {
            "expected_way_ids": [7],
            "labeled_way_ids": [7],
            "missing_way_ids": [],
            "source_names": ["Fixture Street"],
        },
        "historical_points": {"complete": False},
        "inputs": {},
        "files": records,
    }
    save_proof(root, prepared, metadata)
    return root, prepared, metadata


def save_proof(root, prepared, metadata):
    path = prepared / "prototype.json"
    path.write_text(json.dumps(metadata))
    (root / "pipelines/atlas/bristol-recompose.json").write_text(
        json.dumps(
            {
                "source_commit": "f" * 40,
                "prototype_sha256": digest(path),
            }
        )
    )


def test_html_authentication_rejects_stale_html_even_with_valid_pdf(tmp_path):
    pdf, cached = tmp_path / "original.pdf", tmp_path / "cached.html"
    original_pdf(pdf, "Original markup")
    cached.write_text("Original markup")
    assert authenticated_html(pdf, cached) == "Original markup"
    cached.write_text("Changed markup")
    with pytest.raises(ValueError, match="identifier"):
        authenticated_html(pdf, cached)


def test_cached_paths_reject_escape_and_symlink(tmp_path):
    (tmp_path / "a").write_text("fixture")
    (tmp_path / "link").symlink_to(tmp_path / "a")
    with pytest.raises(ValueError, match="Unsafe"):
        artifact_path(tmp_path, "../a")
    with pytest.raises(ValueError, match="Unsafe"):
        artifact_path(tmp_path, "link")


def test_place_recovery_preserves_visible_text_and_missing_address():
    html = (
        "<tbody><tr><td>1</td><td>A &amp; B</td>"
        "<td>fire station<br>Address not supplied</td></tr></tbody>"
    )
    assert places_from_html(html, ["p1"]) == [
        {
            "id": "p1",
            "number": 1,
            "name": "A & B",
            "category": "fire station",
            "address": "",
        }
    ]
    with pytest.raises(ValueError, match="inventory"):
        places_from_html(html, [])


@pytest.mark.parametrize("kind", ["manifest", "pdf", "svg", "coverage", "font"])
def test_cached_proof_rejects_tampering_before_output(fixture_proof, kind):
    root, prepared, metadata = fixture_proof
    if kind == "manifest":
        (prepared / "prototype.json").write_text("{}")
    elif kind == "pdf":
        with (prepared / metadata["files"][0]["path"]).open("ab") as stream:
            stream.write(b"changed")
    elif kind == "svg":
        (prepared / "audit/R1C1.svg").write_text("<svg>Changed</svg>")
    elif kind == "coverage":
        metadata["street_name_coverage"]["missing_way_ids"] = [7]
        save_proof(root, prepared, metadata)
    else:
        metadata["fonts"][0]["sha256"] = "0" * 64
        save_proof(root, prepared, metadata)
    with pytest.raises(ValueError):
        recompose(root, prepared, root / "output")
    assert not (root / "output").exists()


def test_pinned_proof_preserves_points_and_incomplete_parent(fixture_proof):
    root, prepared, _ = fixture_proof
    data, svgs, provenance = prepared_data(root, prepared)
    assert data["historical_points"]["complete"] is False
    assert data["pois"][0]["name"] == "Fixture & Library"
    assert svgs["R1C1"] == (prepared / "audit/R1C1.svg").read_text()
    assert provenance["prototype_sha256"] == digest(prepared / "prototype.json")


def test_recomposition_renders_cached_vectors_without_geodata(fixture_proof, monkeypatch):
    root, prepared, original = fixture_proof

    def no_geodata(*args, **kwargs):
        pytest.fail("Recomposition must not rerun geodata, sheet planning, or labeling")

    for name in ["prepare", "sheet_plan", "read_roads", "svg_map"]:
        monkeypatch.setattr("ck.countyproof." + name, no_geodata)
    result = recompose(root, prepared, root / "output")
    assert result["historical_points"]["complete"] is False
    assert result["street_name_coverage"] == original["street_name_coverage"]
    assert (root / "output/audit/R1C1.svg").read_bytes() == (
        prepared / "audit/R1C1.svg"
    ).read_bytes()
    detail = (
        root / "output" / next(f["path"] for f in result["files"] if "fixture.pdf" in f["path"])
    )
    reader = PdfReader(detail)
    assert "Fixture Street" in reader.pages[1].extract_text()
    assert str(reader.metadata["/CreationDate"]).startswith("D:20261031000000")
    overview = (root / "output/audit/0_OVERVIEW.pdf.html").read_text()
    assert "<h2>Public places</h2>" in overview
    assert "All 1 source places" not in overview
    assert '<aside class="source-notes">' in overview
    assert overview.index("parent directory remains incomplete") > overview.index(
        '<aside class="source-notes">'
    )
    assert "font-size: 8pt" in overview and 'content: "Preview · page "' in overview
    assert "May help; not confirmed open." in overview


def test_layout_guard_rejects_shifted_bookmark(tmp_path):
    path = tmp_path / "shifted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_outline_item("Bristol County · R1C1", 0)
    writer.write(path)
    with pytest.raises(ValueError, match="page/outline"):
        require_pdf_layout(PdfReader(path), [{"id": "R1C1", "page": 2}], 64)


def test_existing_output_is_never_overwritten(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    marker = output / "keep"
    marker.write_text("existing proof")
    with pytest.raises(ValueError, match="no overwrite"):
        recompose(tmp_path, tmp_path, output)
    assert marker.read_text() == "existing proof"


def test_actual_recomposition_obeys_shared_pdf_byte_cap(fixture_proof):
    root, prepared, _ = fixture_proof
    config = read_yaml(root / "config/build.yaml")
    config["pdf"]["max_file_mb"] = "0.000001"
    (root / "config/build.yaml").write_text(json.dumps(config))
    with pytest.raises(ValueError, match="byte budget"):
        recompose(root, prepared, root / "output")
    assert not (root / "output/prototype.json").exists()


def test_unrelated_build_config_does_not_invalidate_recomposition(fixture_proof):
    root, prepared, _ = fixture_proof
    first = recompose(root, prepared, root / "first")
    config = read_yaml(root / "config/build.yaml")
    config["unused_fixture_note"] = "Unrelated to map typography or policy"
    (root / "config/build.yaml").write_text(json.dumps(config))
    second = recompose(root, prepared, root / "second")
    assert first["producer"]["version"] == second["producer"]["version"]
    assert first["files"] == second["files"]


def test_recomposition_uses_the_explicit_roots_template(fixture_proof):
    root, prepared, _ = fixture_proof
    template = root / "templates/county-proof.html.j2"
    template.write_text(template.read_text() + "\n<!-- explicit build-root template -->\n")
    output = root / "output"
    recompose(root, prepared, output)
    document = (output / "audit/0_OVERVIEW.pdf.html").read_text()
    assert "<!-- explicit build-root template -->" in document
