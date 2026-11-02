import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from ck.assemble import write_manifest
from ck.catalog import load_catalog
from ck.fetch import digest
from tools.attach_map_proofs import admit_map, lineage, payloads, source_pins

ROOT = Path(__file__).resolve().parents[1]


def test_local_date_hold_is_preserved_while_unknown_rights_and_changed_pins_fail():
    item = load_catalog(ROOT)["census_zcta_ri_2020"]
    admitted = source_pins({item.id: item}, {item.id: item.sha256})
    assert admitted[item.id]["release_date"] == item.release_date
    assert "[[VERIFY:" in admitted[item.id]["release_date"]
    with pytest.raises(ValueError, match="pin changed"):
        source_pins({item.id: item}, {item.id: "0" * 64})
    for change in (
        {"license": "[[VERIFY: unknown rights]]"},
        {"review": "[[VERIFY: redistribution permission is unknown]]"},
        {"requires_legal": True},
    ):
        with pytest.raises(ValueError, match="rights or pins"):
            source_pins({item.id: item.model_copy(update=change)}, {item.id: item.sha256})


def test_actual_ancestor_manifest_and_link_are_checked(tmp_path):
    old, base = tmp_path / "old", tmp_path / "base"
    old.mkdir()
    base.mkdir()
    (old / "README.TXT").write_text("Synthetic old draft")
    (base / "README.TXT").write_text("Synthetic current draft")
    prior = {"manifest_sha256": write_manifest(old)}
    current = {
        "manifest_sha256": write_manifest(base),
        "base_manifest_sha256": prior["manifest_sha256"],
        "base_provenance": prior,
    }
    assert len(lineage(base, current)) == 2
    with pytest.raises(ValueError, match="link differs"):
        lineage(base, {**current, "base_manifest_sha256": "0" * 64})
    (old / "README.TXT").write_text("Mutated ancestor")
    with pytest.raises(ValueError):
        lineage(base, current)


@pytest.mark.parametrize("kind", ["county_overview", "nested_area"])
def test_partial_area_cannot_use_county_overview_or_extra_area_folder(tmp_path, kind):
    folder = tmp_path / "proof"
    folder.mkdir()
    overview = "0_OVERVIEW.pdf" if kind == "county_overview" else "Area - Overview.pdf"
    prefix = "3_MAPS_AND_PLACES/RI/Kent County/"
    if kind == "nested_area":
        prefix += "extra/"
    proof = {
        "policy": {
            "state": "RI",
            "epoch": 1793404800,
            "county_name": "Kent County",
            "overview_filename": overview,
        },
        "coverage_scope": {"whole_county": False},
        "detail_pdf": "Area.pdf",
        "files": [{"path": prefix + "Area.pdf"}, {"path": prefix + overview}],
    }
    path = folder / "prototype.json"
    path.write_text(json.dumps(proof))
    wrapper = tmp_path / "receipt.json"
    wrapper.write_text(json.dumps({"prototype": proof, "prototype_sha256": digest(path)}))
    with pytest.raises(ValueError, match="named overview|directly in their county"):
        admit_map(folder, digest(path), digest(wrapper), {}, 10000000, 1793404800)


def test_pdf_budget_and_hidden_extra_payload_are_not_omitted_from_admission(tmp_path):
    path = tmp_path / "map.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.write(path)
    row = {"path": path.name, "size_bytes": path.stat().st_size, "sha256": digest(path)}
    with pytest.raises(ValueError, match="PDF cap"):
        payloads(tmp_path, [row], 1)
    (tmp_path / "unlisted.txt").write_text("Synthetic unlisted payload")
    with pytest.raises(ValueError, match="missing or extra"):
        payloads(tmp_path, [row], 10000000)
