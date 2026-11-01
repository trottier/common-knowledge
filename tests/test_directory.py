import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely import box

from ck.directory import (
    EXCLUDED,
    Place,
    assign_counties,
    emergency_agencies,
    osm_category,
    osm_places,
    read_boundaries,
    weather_radio,
)
from ck.generated import generation_manifest


def place(**changes):
    values = dict(
        id="fixture",
        category="public_library",
        name="Synthetic library",
        address="",
        latitude=1.0,
        longitude=1.0,
        source_id="fixture",
        as_of="test-fixture",
    )
    return Place(**{**values, **changes})


@pytest.mark.parametrize(
    "key,value", [(k, next(iter(v)) if v else "test") for k, v in EXCLUDED.items()]
)
def test_exclusions_override_allowed_public_place(key, value):
    tags = {"amenity": "hospital", key: value}
    assert osm_category(tags) is None
    with pytest.raises(ValueError, match="Excluded"):
        place(tags=tags)


def test_county_assignment_handles_boundary_ties_and_outside_points():
    counties = gpd.GeoDataFrame(
        {
            "STATEFP": ["00", "00"],
            "GEOID": ["00002", "00001"],
            "NAMELSAD": ["Synthetic east", "Synthetic west"],
        },
        geometry=[box(1, 0, 2, 2), box(0, 0, 1, 2)],
        crs=4326,
    )
    result = assign_counties([place(), place(id="outside", longitude=3.0)], counties, "00")
    assert len(result) == 1
    assert result[0].county == "00001"


def test_osmium_real_filter_excludes_infrastructure_and_keeps_public_points(tmp_path):
    import subprocess

    from ck.catalog import Item

    xml = tmp_path / "fixture.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="1" lon="1">
        <tag k="amenity" v="hospital"/><tag k="name" v="Synthetic hospital"/>
      </node>
      <node id="2" version="1" lat="1" lon="1">
        <tag k="amenity" v="hospital"/><tag k="power" v="substation"/>
      </node>
      <node id="3" version="1" lat="1" lon="1">
        <tag k="office" v="government"/>
      </node>
    </osm>""")
    pbf = tmp_path / "fixture.pbf"
    subprocess.run(["osmium", "cat", str(xml), "-o", str(pbf)], check=True)
    item = Item(
        id="fixture",
        family="geodata",
        title="Synthetic source",
        url="https://example.org/fixture",
        version="test-fixture",
        size_bytes=1,
        sha256="0" * 64,
        license="CC0-1.0",
        attribution="Test fixture",
        license_proof_url="https://example.org/license",
        placement="hub_only",
        dest="build/inputs/",
        profiles=["sample"],
    )
    records = list(osm_places(pbf, item))
    assert [p.id for p in records] == ["osm-n1"]


def test_generated_manifest_records_incomplete_status_and_exact_files(tmp_path):
    files = tmp_path / "files"
    files.mkdir()
    (files / "fixture.txt").write_text("Synthetic fixture")
    result = generation_manifest(tmp_path, "test-v1", {"source": "0" * 64}, complete=False)
    metadata = json.loads((tmp_path / "generation.json").read_text())
    assert metadata["complete"] is False
    assert result["size_bytes"] == len(b"Synthetic fixture")
    assert metadata["inputs"] == {"source": "0" * 64}


def test_invalid_osm_area_requires_an_explicit_omission_audit(tmp_path, monkeypatch):
    import subprocess

    import osmium

    from ck.catalog import load_catalog

    xml = tmp_path / "area.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="1" lon="1"/>
      <node id="2" version="1" lat="1" lon="2"/>
      <node id="3" version="1" lat="2" lon="2"/>
      <way id="4" version="1">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/>
        <tag k="amenity" v="hospital"/><tag k="name" v="Synthetic hospital"/>
      </way>
    </osm>""")
    pbf = tmp_path / "area.pbf"
    subprocess.run(["osmium", "cat", str(xml), "-o", str(pbf)], check=True)
    item = load_catalog(Path(__file__).resolve().parents[1])["geofabrik_us"]
    assert [record.id for record in osm_places(pbf, item)] == ["osm-w4"]

    class InvalidAreaFactory:
        def create_multipolygon(self, area):
            raise RuntimeError("Synthetic incomplete area")

    monkeypatch.setattr(osmium.geom, "WKBFactory", InvalidAreaFactory)
    with pytest.raises(RuntimeError, match="Synthetic incomplete"):
        list(osm_places(pbf, item))
    rejected = []
    assert list(osm_places(pbf, item, rejected)) == []
    assert rejected == [
        {
            "id": "osm-w4",
            "source_id": item.id,
            "as_of": item.version,
            "name": "Synthetic hospital",
            "category": "hospital",
            "reason": "Invalid or incomplete OSM area geometry",
        }
    ]


def test_extensionless_checksum_cache_supports_county_zip(tmp_path):
    import zipfile

    source = tmp_path / "county.shp"
    gpd.GeoDataFrame({"GEOID": ["00001"]}, geometry=[box(0, 0, 1, 1)], crs=4326).to_file(source)
    archive = tmp_path / ("0" * 64)
    with zipfile.ZipFile(archive, "w") as output:
        for path in tmp_path.glob("county.*"):
            output.write(path, path.name)
    frame = read_boundaries(archive)
    assert list(frame.GEOID) == ["00001"]
    assert frame.crs.to_epsg() == 4326


def test_nwr_import_drops_event_status_and_reports_missing_coordinates(tmp_path):
    from ck.catalog import load_catalog

    item = load_catalog(Path(__file__).resolve().parents[1])["noaa_transmitters"]
    row = {
        "callsign": "FIXTURE",
        "sitename": "Synthetic station",
        "lat": "1",
        "lon": "1",
        "freq": "synthetic frequency",
        "status": "LIVE EVENT STATUS",
        "power": "synthetic",
    }
    source = tmp_path / "source.js"
    source.write_text("var cclData = " + json.dumps([row, {**row, "lat": ""}]) + ";")
    rejected = []
    records = list(weather_radio(source, item, rejected))
    assert len(records) == len(rejected) == 1
    assert "LIVE EVENT STATUS" not in records[0].model_dump_json()
    assert records[0].details == {"Frequency MHz": "synthetic frequency"}


def test_nwr_county_coverage_sentinel_is_not_a_missing_station(tmp_path):
    from ck.catalog import load_catalog

    item = load_catalog(Path(__file__).resolve().parents[1])["noaa_transmitters"]
    source = tmp_path / "source.js"
    source.write_text(
        "var cclData = "
        + json.dumps(
            [
                {
                    "callsign": "",
                    "freq": "",
                    "lat": "",
                    "lon": "",
                    "sitename": "---No  NWR Coverage---",
                }
            ]
        )
        + ";"
    )
    rejected = []
    assert list(weather_radio(source, item, rejected)) == []
    assert rejected == []


def test_agency_parser_accepts_only_named_state_https_links(tmp_path):
    source = tmp_path / "agencies.html"
    source.write_text(
        '<a href="https://example.test/agency">Synthetic state (RI)</a>'
        '<a href="javascript:alert(1)">Synthetic state (AL)</a>'
    )
    assert emergency_agencies(source) == {"RI": "https://example.test/agency"}
