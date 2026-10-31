import json
from collections import Counter
from pathlib import Path

import pytest
from pypdf import PdfReader

from ck.catalog import load_catalog
from ck.config import load_config
from ck.directory import Place, directory_text, pipeline_version
from ck.national import DirectoryData
from ck.nationaldirectory import (
    Inputs,
    Settings,
    build_all,
    build_state,
    collect,
    county_parts,
    prepare,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def context():
    items = load_catalog(ROOT)
    places = [
        Place(
            id=f"synthetic-{i}",
            category="public_library",
            name=f"Library {i}",
            address="Synthetic address",
            latitude=1,
            longitude=1,
            source_id="imls_libraries",
            as_of="synthetic snapshot",
            county=county,
            county_name="Alpha County" if county == "44001" else "Beta County",
        )
        for i, county in enumerate(["44001", "44001", "44001", "10001"])
    ]
    data = DirectoryData(
        ["directory_points"],
        {"RI": "44", "DE": "10"},
        {"44001": "Alpha County", "44003": "Empty County", "10001": "Beta County"},
        places,
        {
            "44001": {"county": "Alpha County", "risk_rating": "Synthetic", "hazards": {}},
            "10001": {"county": "Beta County", "risk_rating": "Synthetic", "hazards": {}},
        },
        ["44003"],
        [],
        {"RI": "https://example.invalid/agency", "DE": "https://example.invalid/agency"},
        {"imls_libraries": "synthetic snapshot"},
    )
    references = {place.id: "page 1, grid A1, point 1" for place in places}
    index = json.dumps(references).encode()
    ids = ["directory_points", "national_atlas"]
    pins = {
        identifier: items[identifier].sha256
        for identifier in [
            *ids,
            "noto_sans",
            "noto_sans_arabic",
            "noto_sans_sc",
            "noto_sans_cherokee",
        ]
    }
    return Inputs(
        ROOT,
        load_config(ROOT),
        items,
        data,
        references,
        index,
        946684800,
        Settings(
            max_places_per_part=2,
            default_jobs=1,
            index_link_prefix="https://ck-directory.invalid/county/",
        ),
        ids,
        pins,
        pipeline_version(ROOT, index),
    )


def test_directory_groups_entries_and_keeps_empty_counties(context):
    plans = list(county_parts(context.data, "RI", 2))
    assert [(county, number, len(places)) for county, number, places in plans] == [
        ("44001", 1, 2),
        ("44001", 2, 1),
        ("44003", 1, 0),
    ]
    assert Counter(place.id for _, _, entries in plans for place in entries) == Counter(
        {f"synthetic-{i}": 1 for i in range(3)}
    )
    body = directory_text(
        context.items,
        "RI",
        context.data.places[:3],
        {},
        [],
        {},
        context.references,
        context.ids,
        True,
        [],
        [],
    )
    assert body.count("## Alpha County") == 1
    assert body.count("### public library") == 1
    assert body.count("::: place") == 3


def test_directory_layout_markers_cannot_be_injected_by_imported_names(context, tmp_path):
    from bs4 import BeautifulSoup

    from ck.render import render_html

    place = context.data.places[0].model_copy(
        update={
            "name": '<script>alert("source")</script>{{ defaults }}',
            "address": "::: place",
        }
    )
    body = directory_text(
        context.items, "RI", [place], {}, [], {}, context.references, context.ids, True, [], []
    )
    source = tmp_path / "imported.md"
    source.write_text(body)
    document = render_html(
        ROOT,
        context.config,
        source,
        context.config.languages[0],
        "phone",
        context.epoch,
        template="directory-part.html.j2",
    )
    soup = BeautifulSoup(document, "html.parser")
    assert len(soup.select("main div.place")) == 1
    assert not soup.select("main script")
    assert soup.select_one("main div.place").get_text().count("::: place") == 1


def test_bounded_pdfs_reproduce_and_local_contents_survive_merge(context, tmp_path):
    first = build_state(context, "RI", tmp_path / "a")
    second = build_state(context, "RI", tmp_path / "b")
    assert first == second and first["places"] == 3 and first["counties"] == 2
    for page_format in ("phone", "print"):
        path = tmp_path / "a/files" / f"RI_{page_format}.pdf"
        assert path.read_bytes() == (tmp_path / "b/files" / path.name).read_bytes()
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() for page in reader.pages)
        for name in (
            "Library 0",
            "Library 1",
            "Library 2",
            "Empty County",
            "No public place in this snapshot.",
        ):
            assert name in text
        assert "page 1, grid A1, point 1" in text
        assert '<section class="place">' not in text and ":::" not in text
        for page in reader.pages:
            assert "May help; not confirmed open." in page.extract_text()
        actions = [
            ref.get_object().get("/A", {})
            for page in reader.pages
            for ref in page.get("/Annots", [])
        ]
        assert sum(action.get("/S") == "/GoTo" for action in actions) >= 2
        assert not any(
            str(action.get("/URI", "")).startswith(context.settings.index_link_prefix)
            for action in actions
        )
        assert str(reader.metadata.creation_date.year) == "2000"
    audit = json.loads((tmp_path / "a/state.json").read_text())
    assert all(len(part["place_ids"]) <= 2 for part in audit["parts"])
    for html in (tmp_path / "a/parts").glob("*.html"):
        document = html.read_text()
        assert '<nav aria-label="Contents">' not in document
        if html.name.startswith("44001"):
            assert '<div class="place">' in document


def test_collection_requires_all_places_states_and_bound_audits(context, tmp_path):
    ri, de = tmp_path / "RI", tmp_path / "DE"
    build_state(context, "RI", ri)
    build_state(context, "DE", de)
    result = collect(context, [ri, de], tmp_path / "national")
    assert result["places"] == 4 and result["counties"] == 3 and result["jurisdictions"] == 2
    assert len(list((tmp_path / "national/files").iterdir())) == 6
    with pytest.raises(ValueError, match="every jurisdiction"):
        collect(context, [ri], tmp_path / "missing")
    with pytest.raises(ValueError, match="jurisdiction changed"):
        collect(context, [ri, ri], tmp_path / "duplicate")
    (ri / "state.json").write_text("{}")
    with pytest.raises(ValueError, match="audit or payload"):
        collect(context, [ri, de], tmp_path / "changed")


def test_preparation_checks_the_bound_atlas_epoch_and_reference_inventory(
    context, tmp_path, monkeypatch
):
    from ck.generated import generation_manifest

    monkeypatch.setattr("ck.nationaldirectory.load_national_points", lambda *args: context.data)
    atlas = tmp_path / "atlas"
    (atlas / "files").mkdir(parents=True)
    (atlas / "files/test.txt").write_text("Synthetic checked payload")
    index = atlas / "place-index.json"
    index.write_bytes(context.index_bytes)

    def pin():
        measured = generation_manifest(
            atlas,
            "synthetic-atlas",
            {"directory_points": context.items["directory_points"].sha256},
            complete=True,
            epoch=context.epoch,
            intermediates=["place-index.json"],
        )
        context.items["national_atlas"] = context.items["national_atlas"].model_copy(
            update={**measured, "inputs": ["directory_points"]}
        )

    pin()
    result = prepare(ROOT, context.config, context.items, tmp_path, atlas, context.epoch)
    assert result.references == context.references
    with pytest.raises(ValueError, match="epoch"):
        prepare(ROOT, context.config, context.items, tmp_path, atlas, context.epoch + 1)
    index.write_text(json.dumps(dict(list(context.references.items())[1:])))
    pin()
    with pytest.raises(ValueError, match="every distinct"):
        prepare(ROOT, context.config, context.items, tmp_path, atlas, context.epoch)
    index.write_text("{}")
    with pytest.raises(ValueError, match="bound complete atlas"):
        prepare(ROOT, context.config, context.items, tmp_path, atlas, context.epoch)


def test_batch_uses_isolated_pdf_workers_and_rejects_zero_jobs(context, tmp_path):
    with pytest.raises(ValueError, match="one to four"):
        build_all(context, tmp_path / "invalid", ["DE"], 0)
    result = build_all(context, tmp_path / "workers", ["DE"], 1)
    assert result["states"] == ["DE"] and result["places"] == 1
    assert (tmp_path / "workers/DE/generation.json").is_file()
