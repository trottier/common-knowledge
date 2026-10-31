import subprocess
from pathlib import Path

import osmium
import pytest

from ck.androidmaps import Settings, filter_roads, filtered_tags, unpack_tool
from ck.config import read_yaml
from ck.directory import excluded

ROOT = Path(__file__).resolve().parents[1]


def settings():
    return Settings.model_validate(read_yaml(ROOT / "pipelines/androidmaps/settings.yaml"))


@pytest.mark.parametrize(
    "tags",
    [
        {"amenity": "fire_station", "power": "substation", "name": "Synthetic excluded feature"},
        {"highway": "service", "man_made": "water_works"},
        {"place": "locality", "waterway": "dam"},
        {"amenity": "townhall", "office": "government", "highway": "pedestrian"},
        {"highway": "construction", "name": "Synthetic unfinished road"},
    ],
)
def test_map_policy_does_not_keep_excluded_or_unfinished_features(tags):
    assert filtered_tags("way", tags, settings()) == {}


def test_map_keeps_road_restrictions_and_only_approved_public_poi_tags():
    policy = settings()
    tags = {
        "highway": "service",
        "access": "private",
        "oneway": "yes",
        "amenity": "townhall",
        "name": "Synthetic road",
        "note": "Discard this note",
    }
    result = filtered_tags("way", tags, policy)
    assert result == {
        "highway": "service",
        "access": "private",
        "oneway": "yes",
        "name": "Synthetic road",
    }
    assert filtered_tags("node", {"amenity": "school"}, policy) == {}
    public = {"amenity": "school", "operator:type": "public", "name": "Synthetic school"}
    assert filtered_tags("node", public, policy)["amenity"] == "school"


def test_pbf_filter_removes_sensitive_tags_and_preserves_references(tmp_path):
    xml = tmp_path / "fixture.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" lat="1" lon="1"><tag k="power" v="substation"/></node>
      <node id="2" lat="1" lon="1.01"/>
      <node id="3" lat="1.01" lon="1"><tag k="amenity" v="hospital"/>
        <tag k="name" v="Synthetic hospital"/></node>
      <node id="4" lat="1.02" lon="1"><tag k="amenity" v="pharmacy"/>
        <tag k="telecom" v="exchange"/></node>
      <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>
        <tag k="name" v="Synthetic road"/><tag k="oneway" v="yes"/></way>
    </osm>""")
    original = tmp_path / "original.osm.pbf"
    subprocess.run(["osmium", "cat", str(xml), "-o", str(original)], check=True)
    target = tmp_path / "filtered.osm.pbf"
    counts = filter_roads(original, target, settings())
    result = {}

    class Reader(osmium.SimpleHandler):
        def node(self, node):
            result["n" + str(node.id)] = dict(node.tags)

        def way(self, way):
            result["w" + str(way.id)] = dict(way.tags)

    Reader().apply_file(str(target))
    assert result["n1"] == {} and "n2" in result
    assert result["n3"]["amenity"] == "hospital" and result["n4"] == {}
    assert result["w10"]["oneway"] == "yes"
    assert counts["way_tagged"] == 1
    assert all(not excluded(tags) for tags in result.values())


def test_map_creator_archive_cannot_escape_its_directory(tmp_path):
    import zipfile

    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../../outside.jar", b"Synthetic archive fixture")
    with pytest.raises(ValueError):
        unpack_tool(archive, tmp_path / "tool")


def test_source_supplement_repairs_restriction_without_changing_download(tmp_path):
    from ck.fetch import digest

    original = tmp_path / "original.osm"
    original.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="1" lon="1"/>
      <node id="2" version="1" lat="1" lon="1.01"/>
      <way id="10" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="residential"/></way>
      <relation id="20" version="1"><member type="way" ref="10" role="from"/>
        <member type="node" ref="2" role="via"/><member type="way" ref="11" role="to"/>
        <tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/>
      </relation></osm>""")
    source = tmp_path / "source.osm.pbf"
    subprocess.run(["osmium", "cat", str(original), "-o", str(source)], check=True)
    before = digest(source)
    supplement = tmp_path / "supplement.osm"
    supplement.write_text("""<osm version="0.6">
      <node id="3" version="1" lat="1.01" lon="1.01"/>
      <way id="11" version="1"><nd ref="2"/><nd ref="3"/>
        <tag k="highway" v="residential"/></way></osm>""")
    result = tmp_path / "result.osm.pbf"
    counts = filter_roads(source, result, settings(), (supplement,))
    assert counts["relation_tagged"] == 1 and counts["way_tagged"] == 2
    assert digest(source) == before
    subprocess.run(["osmium", "check-refs", "--check-relations", str(result)], check=True)


def test_map_howto_has_one_page_and_machine_translation_footer(tmp_path):
    from pypdf import PdfReader

    from ck.androidhowto import build_howto
    from ck.catalog import load_catalog
    from ck.config import load_config

    config = load_config(ROOT)
    output = tmp_path / "howto"
    build_howto(ROOT, config, load_catalog(ROOT, config), output, 946684800)
    for file in (output / "files").glob("*.pdf"):
        pdf = PdfReader(file)
        assert len(pdf.pages) == 1
        if file.name.startswith("COMO_USAR"):
            # PDF text extraction can infer a space before a kerned period.
            text = pdf.pages[0].extract_text().replace(" .", ".")
            assert "Traducción automática sin revisar." in text
            html = (output / "audit" / file.with_suffix(".html").name).read_text()
            assert 'content: "Traducción automática sin revisar."' in html
