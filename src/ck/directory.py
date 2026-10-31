"""Public-place imports with an allowlist and explicit incomplete-build status."""

import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from ck.catalog import Item
from ck.config import Configuration, Model, Text
from ck.generated import cached_input, generation_manifest
from ck.render import render_pdf

Category = Literal[
    "public_school",
    "public_library",
    "hospital",
    "urgent_care",
    "pharmacy",
    "fire_station",
    "police",
    "post_office",
    "broadcast_station",
    "weather_radio",
]
AMENITIES = {
    "hospital": "hospital",
    "pharmacy": "pharmacy",
    "fire_station": "fire_station",
    "police": "police",
    "post_office": "post_office",
}
EXCLUDED = {
    "power": None,
    "pipeline": None,
    "telecom": None,
    "communication": None,
    "waterway": {"dam", "weir"},
    "man_made": {
        "water_works",
        "wastewater_plant",
        "water_tower",
        "reservoir_covered",
        "pipeline",
        "pumping_station",
        "communications_tower",
        "works",
    },
    "industrial": {"power", "oil", "gas", "water", "wastewater"},
    "office": {"telecommunication"},
}
REQUIRED_SOURCES = {
    "nces_schools",
    "imls_libraries",
    "osm",
    "fcc_stations",
    "noaa_transmitters",
    "fema_risk",
    "state_emergency_agencies",
}


def read_boundaries(path: Path):
    import geopandas as gpd

    from ck.catalog import safe_path

    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".shp")]
        if len(names) != 1:
            raise ValueError("Expected one county shapefile")
        safe_path(names[0])
    # GDAL's braces are required because the cache filename is a hash, not *.zip.
    return gpd.read_file(f"/vsizip/{{{path.resolve()}}}/{names[0]}").to_crs(4326)


def excluded(tags: dict[str, str]) -> bool:
    return any(
        key in tags and (values is None or tags[key] in values) for key, values in EXCLUDED.items()
    )


def osm_category(tags: dict[str, str]) -> str | None:
    if excluded(tags) or any(tags.get(key) in {"no", "private"} for key in ("access", "public")):
        return None
    if tags.get("healthcare") == "clinic" and tags.get("healthcare:speciality") == "emergency":
        return "urgent_care"
    return AMENITIES.get(tags.get("amenity"))


class Place(Model):
    id: Text
    category: Category
    name: Text
    address: str
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    source_id: Text
    as_of: Text
    tags: dict[str, str] = Field(default_factory=dict)
    county: str = ""
    county_name: str = ""
    details: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def no_sensitive_infrastructure(self):
        if excluded(self.tags):
            raise ValueError("Excluded infrastructure tag in directory")
        return self


def libraries(path: Path, item: Item):
    with zipfile.ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if "outlet" in name.lower() and name.endswith(".csv")
        ]
        if len(names) != 1:
            raise ValueError("Expected one IMLS outlet CSV")
        # FY2024's CSV contains Windows-1252 text, including curly apostrophes.
        rows = csv.DictReader(io.TextIOWrapper(archive.open(names[0]), encoding="cp1252"))
        for row in rows:
            # Mobile bookmobiles are not stable rally places.
            if row["C_OUT_TY"] not in {"CE", "BR"}:
                continue
            if not row["LATITUDE"] or not row["LONGITUD"]:
                continue
            yield Place(
                id="imls-" + row["FSCSKEY"] + "-" + row["FSCS_SEQ"],
                category="public_library",
                name=row["LIBNAME"],
                address=f"{row['ADDRESS']}, {row['CITY']}, {row['STABR']} {row['ZIP']}",
                latitude=float(row["LATITUDE"]),
                longitude=float(row["LONGITUD"]),
                source_id=item.id,
                as_of=item.version,
            )


def schools(path: Path, item: Item):
    from openpyxl import load_workbook

    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".xlsx")]
        if len(names) != 1:
            raise ValueError("Expected one NCES school workbook")
        book = load_workbook(io.BytesIO(archive.read(names[0])), read_only=True, data_only=True)
        try:
            rows = iter(book.active.values)
            header = next(rows)
            for values in rows:
                row = dict(zip(header, values, strict=True))
                if row["LAT"] is None or row["LON"] is None:
                    continue
                yield Place(
                    id="nces-" + str(row["NCESSCH"]),
                    category="public_school",
                    name=row["NAME"],
                    address=f"{row['STREET']}, {row['CITY']}, {row['STATE']} {row['ZIP']}",
                    latitude=float(row["LAT"]),
                    longitude=float(row["LON"]),
                    source_id=item.id,
                    as_of=item.version,
                )
        finally:
            book.close()


def osm_places(path: Path, item: Item):
    import osmium
    from shapely import from_wkb

    places = {}
    factory = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def add(self, obj, identifier, latitude, longitude):
            tags = dict(obj.tags)
            category = osm_category(tags)
            if category is None:
                return
            address = " ".join(
                tags.get(key, "")
                for key in (
                    "addr:housenumber",
                    "addr:street",
                    "addr:city",
                    "addr:state",
                    "addr:postcode",
                )
            ).strip()
            places[identifier] = Place(
                id=identifier,
                category=category,
                name=tags.get("name", "[name missing in source]"),
                address=address,
                latitude=float(latitude),
                longitude=float(longitude),
                source_id=item.id,
                as_of=item.version,
                tags=tags,
            )

        def node(self, node):
            if node.location.valid() and osm_category(dict(node.tags)):
                self.add(node, f"osm-n{node.id}", node.location.lat, node.location.lon)

        def area(self, area):
            if osm_category(dict(area.tags)):
                point = from_wkb(factory.create_multipolygon(area)).representative_point()
                kind = "w" if area.from_way() else "r"
                self.add(area, f"osm-{kind}{area.orig_id()}", point.y, point.x)

    with tempfile.TemporaryDirectory(prefix="ck-osm-places-") as temporary:
        filtered = Path(temporary) / "places.osm.pbf"
        subprocess.run(
            [
                "osmium",
                "tags-filter",
                "-F",
                "pbf",
                str(path),
                "nwr/amenity=" + ",".join(sorted(AMENITIES)),
                "nwr/healthcare=clinic",
                "--output",
                str(filtered),
            ],
            check=True,
        )
        Handler().apply_file(str(filtered), locations=True, idx="flex_mem")
    return places.values()


def weather_radio(path: Path, item: Item, rejected: list | None = None):
    match = re.fullmatch(r"var cclData\s*=\s*(\[.*\]);\s*", path.read_text(), re.S)
    if not match:
        raise ValueError("NWR station data format changed; review the publisher's schema")
    for row in json.loads(match[1]):
        # The publisher includes one county-coverage sentinel, not a station.
        # Its empty coordinates are intentional; never turn it into a POI.
        if (
            not row["callsign"]
            and not row["freq"]
            and not row["lat"]
            and not row["lon"]
            and " ".join(row["sitename"].split()) == "---No NWR Coverage---"
        ):
            continue
        # Read only stable station facts. Outages/status and transmitter power
        # are deliberately not copied into any generated record.
        if not row["lat"] or not row["lon"]:
            if rejected is None:
                raise ValueError(f"NWR station has no source coordinates: {row['callsign']}")
            rejected.append({"id": row["callsign"], "reason": "NWR coordinates missing"})
            continue
        yield Place(
            id="nwr-" + row["callsign"],
            category="weather_radio",
            name=row["callsign"] + " — " + row["sitename"],
            address="",
            latitude=float(row["lat"]),
            longitude=float(row["lon"]),
            source_id=item.id,
            as_of=item.version,
            details={"Frequency MHz": row["freq"]},
        )


def emergency_agencies(path: Path) -> dict[str, str]:
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.url = None
            self.label = []
            self.agencies = {}

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.url = dict(attrs).get("href")
                self.label = []

        def handle_data(self, data):
            if self.url:
                self.label.append(data)

        def handle_endtag(self, tag):
            if tag == "a" and self.url:
                match = re.search(r"\(([A-Z]{2})\)$", "".join(self.label).strip())
                if match and self.url.startswith("https://"):
                    self.agencies[match[1]] = self.url
                self.url = None

    parser = Parser()
    parser.feed(path.read_text())
    if not parser.agencies:
        raise ValueError("No state agency links in the pinned USAGov page")
    return parser.agencies


def assign_counties(places, boundaries, state_fips: str):
    from shapely import Point

    boundaries = (
        boundaries[boundaries.STATEFP == state_fips].sort_values("GEOID").reset_index(drop=True)
    )
    if boundaries.empty:
        raise ValueError(f"No Census counties for state FIPS {state_fips}")
    result = []
    for place in places:
        hits = boundaries.sindex.query(
            Point(place.longitude, place.latitude), predicate="intersects"
        )
        if len(hits):
            county = boundaries.iloc[min(hits)]
            place.county, place.county_name = county.GEOID, county.NAMELSAD
            result.append(place)
    # Stable IDs deduplicate repeat extracts, without guessing that nearby places are identical.
    unique = {place.id: place for place in result}
    return sorted(
        unique.values(),
        key=lambda p: (p.county_name.casefold(), p.category, p.name.casefold(), p.id),
    )


def build_directory(
    root: Path,
    config: Configuration,
    items: dict[str, Item],
    cache: Path,
    output: Path,
    state: str,
    state_fips: str,
    epoch: int,
    osm_id: str = "geofabrik_ri",
    atlas_index: Path | None = None,
    atlas_id: str | None = None,
    seed: bool = False,
) -> dict:
    if output.exists():
        raise ValueError("Directory output must be new")
    if len(state) != 2 or not state.isascii() or not state.isalpha():
        raise ValueError("State must be a two-letter code")
    if bool(atlas_index) != bool(atlas_id) or (seed and atlas_index):
        raise ValueError(
            "Final atlas references need both an index and catalog ID; seeds have neither"
        )
    ids = [
        "census_county_analysis",
        "census_states",
        "nces_schools",
        "imls_libraries",
        osm_id,
        "noaa_transmitters",
        "state_emergency_agencies",
        "fcc_stations",
        "fcc_locations",
        "fcc_license_versions",
        "fcc_service_codes",
        "fcc_facility_statuses",
        "fema_risk",
    ]
    paths = {identifier: cached_input(items[identifier], cache) for identifier in ids}
    atlas_complete = False
    if atlas_index:
        from ck.fetch import digest
        from ck.generated import verified_generated_files

        atlas_manifest, _ = verified_generated_files(
            items[atlas_id], atlas_index.parent, items, allow_incomplete=True
        )
        index_pin = next(
            (
                entry
                for entry in atlas_manifest["intermediates"]
                if entry["path"] == "place-index.json"
            ),
            None,
        )
        if (
            not index_pin
            or digest(atlas_index) != index_pin["sha256"]
            or atlas_manifest["source_date_epoch"] != epoch
        ):
            raise ValueError("Atlas index differs from its pinned source or epoch")
        atlas_complete = atlas_manifest["complete"]
        ids.append(atlas_id)
    with paths["census_states"].open() as stream:
        states = {row["STUSAB"]: row["STATE"] for row in csv.DictReader(stream, delimiter="|")}
    if states.get(state.upper()) != state_fips:
        raise ValueError("State code and FIPS disagree with Census reference data")
    boundaries = read_boundaries(paths["census_county_analysis"])
    rejected = []
    from ck.directory_sources import broadcast_stations, county_profiles

    counties = boundaries[boundaries.STATEFP == state_fips]
    profiles, missing_profiles = county_profiles(paths["fema_risk"], set(counties.GEOID))
    records = [
        *schools(paths["nces_schools"], items["nces_schools"]),
        *libraries(paths["imls_libraries"], items["imls_libraries"]),
        *osm_places(paths[osm_id], items[osm_id]),
        *weather_radio(paths["noaa_transmitters"], items["noaa_transmitters"], rejected),
        *broadcast_stations(paths, items, None, rejected),
    ]
    places = assign_counties(records, boundaries, state_fips)
    if not places:
        raise ValueError("No public places matched the requested state")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-directory-") as temporary:
        stage = Path(temporary)
        files = stage / "files"
        files.mkdir()
        # The atlas index supplies exact PDF page and grid labels. Until it exists,
        # directory PDFs remain explicitly incomplete and cannot enter a release.
        references = json.loads(atlas_index.read_text()) if atlas_index else {}
        if not isinstance(references, dict) or any(
            not isinstance(value, str)
            or not re.fullmatch(r"page [1-9]\d*, grid [A-Z]+[1-9]\d*, point [1-9]\d*", value)
            for value in references.values()
        ):
            raise ValueError(
                "Atlas references must contain checked PDF page, grid and point labels"
            )
        if atlas_index:
            (stage / "atlas-index.json").write_bytes(atlas_index.read_bytes())
        agencies = emergency_agencies(paths["state_emergency_agencies"])
        present = {
            "nces_schools",
            "imls_libraries",
            "osm",
            "noaa_transmitters",
            "fcc_stations",
            "fema_risk",
        }
        if state.upper() in agencies:
            present.add("state_emergency_agencies")
        missing = sorted(REQUIRED_SOURCES - present)
        missing_references = sorted(place.id for place in places if place.id not in references)
        source_complete = not (missing or rejected or missing_profiles)
        complete = source_complete and (seed or (atlas_complete and not missing_references))
        metadata = {
            "state": state.upper(),
            "state_fips": state_fips,
            "purpose": "atlas-points" if seed else "directory",
            "missing_sources": missing,
            "places": [p.model_dump() for p in places],
            "counts": dict(sorted(Counter(p.category for p in places).items())),
            "rejected_records": rejected,
            "county_profiles": profiles,
            "missing_county_profiles": missing_profiles,
            "missing_atlas_references": missing_references,
        }
        (stage / "places.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        )
        public_data = {
            "attribution": (
                "© OpenStreetMap contributors; NCES; IMLS; NWS; FCC; FEMA; USAGov; "
                "U.S. Census Bureau"
            ),
            "license_notice": "OpenStreetMap data: ODbL-1.0. Federal source data: public domain.",
            "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
            "source_versions": {identifier: items[identifier].version for identifier in ids},
            "places": [place.model_dump(exclude={"tags"}) for place in places],
            "county_profiles": profiles,
        }
        (files / f"{state.upper()}_SOURCE_DATA.json").write_text(
            json.dumps(public_data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        body = [
            "---",
            f"title: {state.upper()} public places",
            "status: draft",
            "reviewer: null",
            "reviewed_on: null",
            "---",
            "",
            "PUBLIC PLACES DIRECTORY" if complete else "DEVELOPMENT DIRECTORY — INCOMPLETE",
            "",
            f"Missing source families: {', '.join(missing)}.",
            "",
            "May help; not confirmed open. "
            "No entry is an event shelter or an assurance of service.",
            "",
            "Geographic assignments use Census TIGER/Line® statistical boundaries, "
            "not legal land descriptions. TIGER/Line® is a registered trademark "
            "of the U.S. Census Bureau.",
            "",
        ]
        if rejected:
            body += [
                f"[[VERIFY: {len(rejected)} source records lack confirmed geographic references; "
                "review the build rejection report before publication.]]",
                "",
            ]
        for place in places:
            # Escape Markdown control characters in imported fields.
            def plain(value):
                import html
                import re

                text = html.escape(value).replace("\n", " ")
                text = re.sub(r"([\\`*_\[\]#<>])", r"\\\1", text)
                return text.replace("{", "&#123;").replace("}", "&#125;")

            body += [
                f"## {plain(place.county_name)} · {place.category}",
                "",
                f"**{plain(place.name)}**",
                "",
                plain(place.address) or "Address not supplied.",
                "",
                f"{place.latitude:.6f}, {place.longitude:.6f}",
                "",
                f"Atlas: {references.get(place.id, '[[VERIFY: atlas page and grid]]')}",
                "",
                f"Source: {place.source_id}; as of {plain(place.as_of)}.",
                "",
            ]
            for label, value in sorted(place.details.items()):
                body += [f"{plain(label)}: {plain(value)}.", ""]
        for identifier in ids:
            body += [
                f"Source {identifier}: {items[identifier].attribution}; "
                f"{items[identifier].version}.",
                "",
            ]
        body += [
            "## County hazard profiles",
            "",
            "FEMA National Risk Index ratings describe historical relative risk. "
            "They are not current emergency warnings or forecasts.",
            "",
        ]
        for code, profile in sorted(profiles.items()):
            body += [
                f"### {plain(profile['county'])} · {code}",
                "",
                f"Overall risk rating: {plain(profile['risk_rating']) or 'Not supplied'}.",
                "",
            ]
            for hazard, rating in sorted(profile["hazards"].items()):
                body += [f"{plain(hazard)}: {plain(rating) or 'Not supplied'}.", ""]
            body += [f"Source: fema_risk; as of {plain(items['fema_risk'].version)}.", ""]
        if missing_profiles:
            body += [
                "[[VERIFY: FEMA has no county profile for Census codes "
                + ", ".join(missing_profiles)
                + "; review source coverage.]]",
                "",
            ]
        if state.upper() in agencies:
            body += [
                "## State emergency agency",
                "",
                "USAGov lists this agency website. It requires internet to visit:",
                "",
                agencies[state.upper()],
                "",
            ]
        body += [
            "## Data and license",
            "",
            "OpenStreetMap data: © OpenStreetMap contributors, under the Open Database License.",
            "",
            "https://opendatacommons.org/licenses/odbl/1-0/",
            "",
            f"The companion {state.upper()}_SOURCE_DATA.json provides the public data used here.",
            "",
        ]
        source = stage / "directory.md"
        source.write_text("\n".join(body), encoding="utf-8")
        for page_format in () if seed else ("phone", "print"):
            render_pdf(
                root,
                config,
                source,
                config.languages[0],
                page_format,
                files / f"{state.upper()}_{page_format}.pdf",
                epoch,
                template="directory.html.j2",
            )
            audit = stage / "audit"
            audit.mkdir(exist_ok=True)
            (files / f"{state.upper()}_{page_format}.html").rename(
                audit / f"{state.upper()}_{page_format}.html"
            )
        recipe = hashlib.sha256()
        recipe.update(b"atlas-index\0" + (atlas_index.read_bytes() if atlas_index else b"none"))
        for relative in (
            "src/ck/directory.py",
            "src/ck/directory_sources.py",
            "src/ck/generated.py",
            "src/ck/render.py",
            "src/ck/locales.py",
            "config/defaults.yaml",
            "config/languages.yaml",
            "content/en/edition.yaml",
            "templates/document.html.j2",
            "templates/document.css",
            "templates/directory.html.j2",
            "pyproject.toml",
            "uv.lock",
            "Dockerfile.build",
        ):
            recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
        measurements = generation_manifest(
            stage,
            ("directory-seed-v1-" if seed else "directory-v1-") + recipe.hexdigest(),
            {
                **{i: items[i].sha256 for i in ids},
                **({} if seed else {"noto_sans": items["noto_sans"].sha256}),
            },
            complete=complete,
            epoch=epoch,
            intermediates=["places.json", *(["atlas-index.json"] if atlas_index else [])],
        )
        stage.rename(output)
    return {**measurements, "counts": metadata["counts"], "missing_sources": missing}
