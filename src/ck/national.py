"""Prepare national directory points once for all Census county jurisdictions."""

import csv
import hashlib
import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ck.catalog import Item
from ck.directory import (
    Place,
    assign_counties,
    emergency_agencies,
    libraries,
    osm_places,
    read_boundaries,
    schools,
    weather_radio,
)
from ck.directory_sources import broadcast_stations, county_profiles
from ck.generated import cached_input, generation_manifest, verified_generated_files
from ck.mapextract import policy

COMMON_INPUTS = [
    "census_county_analysis",
    "census_states",
    "nces_schools",
    "imls_libraries",
    "noaa_transmitters",
    "state_emergency_agencies",
    "fcc_stations",
    "fcc_locations",
    "fcc_license_versions",
    "fcc_service_codes",
    "fcc_facility_statuses",
    "fema_risk",
]


@dataclass
class DirectoryData:
    source_ids: list[str]
    states: dict[str, str]
    counties: dict[str, str]
    places: list[Place]
    profiles: dict
    missing_profiles: list[str]
    rejected: list[dict]
    agencies: dict[str, str]
    source_versions: dict[str, str]


def prepare_data(items: dict[str, Item], cache: Path, osm_ids: list[str]) -> DirectoryData:
    if not osm_ids or len(osm_ids) != len(set(osm_ids)):
        raise ValueError("Choose distinct OSM source inputs")
    ids = [*COMMON_INPUTS, *osm_ids]
    paths = {identifier: cached_input(items[identifier], cache) for identifier in ids}
    boundaries = read_boundaries(paths["census_county_analysis"])
    with paths["census_states"].open() as stream:
        states = {row["STUSAB"]: row["STATE"] for row in csv.DictReader(stream, delimiter="|")}
    profiles, missing = county_profiles(paths["fema_risk"], set(boundaries.GEOID))
    rejected = []
    records = [
        *schools(paths["nces_schools"], items["nces_schools"]),
        *libraries(paths["imls_libraries"], items["imls_libraries"]),
        *weather_radio(paths["noaa_transmitters"], items["noaa_transmitters"], rejected),
        *broadcast_stations(paths, items, None, rejected),
    ]
    for identifier in osm_ids:
        records.extend(osm_places(paths[identifier], items[identifier], rejected))
    places = assign_counties(records, boundaries, None)
    return DirectoryData(
        ids,
        states,
        dict(zip(boundaries.GEOID, boundaries.NAMELSAD, strict=True)),
        places,
        profiles,
        missing,
        rejected,
        emergency_agencies(paths["state_emergency_agencies"]),
        {identifier: items[identifier].version for identifier in ids},
    )


def build_national_points(
    root: Path, items: dict[str, Item], cache: Path, output: Path, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("National point output must be new")
    sources = policy(root)
    data = prepare_data(items, cache, sorted(set(sources.source_inputs.values())))
    if (
        not data.places
        or not data.counties
        or not {code[:2] for code in data.counties} <= set(data.states.values())
    ):
        raise ValueError("National points need places and a Census jurisdiction for every county")
    jurisdictions = {
        code: fips
        for code, fips in data.states.items()
        if any(county.startswith(fips) for county in data.counties)
    }
    counts = Counter((place.county[:2], place.source_id) for place in data.places)
    coverage = {
        state: {
            "source_id": sources.source_for(state),
            "places": counts[fips, sources.source_for(state)],
        }
        for state, fips in sorted(jurisdictions.items())
    }
    missing = [state for state, entry in coverage.items() if not entry["places"]]
    if missing:
        raise ValueError(
            "No places from the configured OSM source in jurisdictions: " + ", ".join(missing)
        )
    metadata = {
        "purpose": "national-atlas-points",
        "states": jurisdictions,
        "counties": data.counties,
        "places": [place.model_dump() for place in data.places],
        "county_profiles": data.profiles,
        "missing_county_profiles": data.missing_profiles,
        "rejected_records": data.rejected,
        "agencies": data.agencies,
        "source_versions": data.source_versions,
        "source_ids": data.source_ids,
        "osm_source_coverage": coverage,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-national-points-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        (stage / "places.json").write_text(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        )
        public = {
            "attribution": "OpenStreetMap contributors; NCES; IMLS; FCC; FEMA; NWS; "
            "USAGov; U.S. Census Bureau",
            "license": "OpenStreetMap data: ODbL-1.0; federal source data: public domain",
            "source_versions": data.source_versions,
            "osm_source_coverage": coverage,
            "places": [place.model_dump(exclude={"tags"}) for place in data.places],
            "omitted_records": data.rejected,
            "missing_county_profiles": data.missing_profiles,
            "county_profiles": data.profiles,
        }
        (stage / "files/NATIONAL_SOURCE_DATA.json").write_text(
            json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        )
        recipe = hashlib.sha256()
        for name in [
            "src/ck/national.py",
            "src/ck/directory.py",
            "src/ck/directory_sources.py",
            "src/ck/generated.py",
            "src/ck/mapextract.py",
            "pipelines/androidmaps/national.yaml",
            "pyproject.toml",
            "uv.lock",
            "Dockerfile.build",
        ]:
            recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
        # Completeness records a finished import, including disclosed omissions
        # in publisher data. It does not grant catalog pin or release approval.
        measured = generation_manifest(
            stage,
            "national-points-v1-" + recipe.hexdigest(),
            {identifier: items[identifier].sha256 for identifier in data.source_ids},
            complete=True,
            epoch=epoch,
            intermediates=["places.json"],
        )
        stage.rename(output)
    return {
        **measured,
        "places": len(data.places),
        "counties": len(data.counties),
        "jurisdictions": jurisdictions,
        "omitted_records": len(data.rejected),
        "missing_county_profiles": data.missing_profiles,
    }


def load_national_points(
    item: Item, directory: Path, items: dict[str, Item], epoch: int
) -> DirectoryData:
    from ck.fetch import digest

    manifest, _ = verified_generated_files(item, directory, items)
    binding = next(
        (entry for entry in manifest["intermediates"] if entry["path"] == "places.json"), None
    )
    source = directory / "places.json"
    if (
        source.is_symlink()
        or not source.is_file()
        or not binding
        or digest(source) != binding["sha256"]
        or manifest["source_date_epoch"] != epoch
    ):
        raise ValueError("National points differ from their pinned content or epoch")
    data = json.loads(source.read_text())
    if data["purpose"] != "national-atlas-points":
        raise ValueError("Expected a national atlas point set")
    return DirectoryData(
        [item.id],
        data["states"],
        data["counties"],
        [Place.model_validate(row) for row in data["places"]],
        data["county_profiles"],
        data["missing_county_profiles"],
        data["rejected_records"],
        data["agencies"],
        data["source_versions"],
    )
