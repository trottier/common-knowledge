"""Prepare offline native-render jobs and compose their checked county atlas PDFs."""

import hashlib
import json
import math
from pathlib import Path

from pydantic import Field
from shapely import Point, box

from ck.catalog import Item, safe_path
from ck.config import Configuration, Model, read_yaml
from ck.directory import Place, read_boundaries
from ck.fetch import digest
from ck.generated import cached_input, verified_generated_files
from ck.geo import Frame, shifted_geometry, unproject


def pipeline_version(root: Path) -> str:
    recipe = hashlib.sha256()
    paths = [
        root / relative
        for relative in (
            "templates/atlas.html.j2",
            "pyproject.toml",
            "uv.lock",
            "Dockerfile.build",
            "config/ubuntu.sources",
            "catalog/buildtools.yaml",
            "tools/bootstrap_atlas.py",
            "tools/extract_atlas.py",
        )
    ]
    for directory in ("pipelines/atlas", "src/ck"):
        paths.extend(
            path
            for path in (root / directory).rglob("*")
            if "node_modules" not in path.parts
            and path.suffix in {".py", ".mjs", ".yaml", ".json", ".lock"}
        )
    for path in sorted(paths):
        recipe.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return "atlas-v1-" + recipe.hexdigest()


def place_labels(page: dict) -> None:
    """Place every point number without overlapping other numbers or points.

    Coordinates and grid squares stay attached to the dots. A leader connects
    a displaced label to its dot, including entries sharing source coordinates.
    """
    occupied = {}

    def cells(rect):
        left, top, right, bottom = rect
        return [
            (x, y)
            for x in range(int(left // 64), int(right // 64) + 1)
            for y in range(int(top // 64), int(bottom // 64) + 1)
        ]

    def reserve(rect):
        for cell in cells(rect):
            occupied.setdefault(cell, []).append(rect)

    def clear(rect):
        left, top, right, bottom = rect
        if left < 4 or top < 4 or right > page["width"] - 4 or bottom > page["height"] - 4:
            return False
        for cell in cells(rect):
            for a, b, c, d in occupied.get(cell, []):
                if left < c and right > a and top < d and bottom > b:
                    return False
        return True

    reserve((page["width"] - 95, 8, page["width"] - 10, 115))
    reserve((15, page["height"] - 85, page["width"] * 0.2 + 75, page["height"] - 10))
    for place in page["places"]:
        x, y = place["x"], place["y"]
        reserve((x - 5, y - 5, x + 5, y + 5))
    for place in sorted(page["places"], key=lambda item: item["number"]):
        width = 14 * len(str(place["number"])) + 4
        maximum = math.ceil(math.hypot(page["width"], page["height"]))
        placed = False
        for radius in range(12, maximum, 16):
            for step in range(max(8, math.ceil(2 * math.pi * radius / 24))):
                count = max(8, math.ceil(2 * math.pi * radius / 24))
                angle = -math.pi / 4 + step * 2 * math.pi / count
                x = place["x"] + radius * math.cos(angle)
                y = place["y"] + radius * math.sin(angle)
                rect = (x - 2, y - 23, x + width, y + 5)
                if clear(rect):
                    place["label_x"], place["label_y"] = x, y
                    place["leader"] = radius > 12
                    reserve(rect)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            raise ValueError("Atlas point numbers do not fit; add a more detailed inset")


class Settings(Model):
    width: int = Field(ge=100, le=1920)
    height: int = Field(ge=100, le=2400)
    columns: int = Field(ge=1, le=26)
    rows: int = Field(ge=1, le=30)
    padding: float = Field(ge=0, le=0.5)
    maxzoom: int = Field(ge=1, le=15)
    inset_min_points: int = Field(ge=1)
    max_total_bytes: int = Field(gt=0)

    def viewport(self):
        return self.model_dump(exclude={"inset_min_points", "max_total_bytes"})


def atlas_budget(outputs: list[Path], states: list[str], maximum: int) -> dict:
    """Measure the whole requested atlas set; missing states are not zero bytes."""
    if not states or len(set(states)) != len(states):
        raise ValueError("Supply a unique, nonempty list of atlas jurisdictions")
    sizes = {}
    for output in outputs:
        manifest = json.loads((output / "generation.json").read_text())
        entries = [entry for entry in manifest["files"] if entry["path"].endswith(".pdf")]
        if len(entries) != 1:
            raise ValueError("Expected one state PDF per atlas output")
        entry = entries[0]
        relative = safe_path(entry["path"])
        state = relative.stem
        if state in sizes or state not in states:
            raise ValueError(f"Duplicate or unexpected atlas jurisdiction: {state}")
        pdf = output / "files" / relative
        if (
            pdf.is_symlink()
            or pdf.stat().st_size != entry["size_bytes"]
            or digest(pdf) != entry["sha256"]
        ):
            raise ValueError(f"Atlas payload changed: {state}")
        sizes[state] = entry["size_bytes"]
    if set(sizes) != set(states):
        raise ValueError(
            "Missing atlas jurisdictions: " + ", ".join(sorted(set(states) - sizes.keys()))
        )
    total = sum(sizes.values())
    if total > maximum:
        raise ValueError(
            f"Atlas budget exceeded: {total:,} > {maximum:,} bytes; reduce raster quality"
        )
    return {"total_bytes": total, "maximum_bytes": maximum, "states": dict(sorted(sizes.items()))}


def directory_points(directory: Path) -> tuple[dict, list[Place]]:
    manifest = json.loads((directory / "generation.json").read_text())
    binding = next(
        (item for item in manifest.get("intermediates", []) if item["path"] == "places.json"), None
    )
    source = directory / "places.json"
    if binding is None or binding["sha256"] != digest(source):
        raise ValueError("Directory points are unbound or changed; regenerate the directory")
    data = json.loads(source.read_text())
    return manifest, [Place.model_validate(raw) for raw in data["places"]]


def outline(geometry, frame: Frame) -> list[str]:
    from shapely import LineString

    geometry, _ = shifted_geometry(geometry)
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    paths = []
    for polygon in polygons:
        for ring in [polygon.exterior, *polygon.interiors]:
            points = [frame.pixel(x, y) for x, y, *_ in ring.coords]
            points = LineString(points).simplify(0.5).coords
            paths.append(" ".join(f"{x:.3f},{y:.3f}" for x, y in points))
    return paths


def page_data(identifier, title, county, geometry, places, settings, *, inset=False):
    frame = Frame.fit(geometry, **settings.viewport())
    shifted, wraps = shifted_geometry(geometry)
    included = []
    for place in places:
        longitude = place.longitude + (360 if wraps and place.longitude < 0 else 0)
        if shifted.intersects(Point(longitude, place.latitude)):
            x, y = frame.pixel(place.longitude, place.latitude)
            included.append(
                {
                    **place.model_dump(),
                    "x": x,
                    "y": y,
                    "grid": frame.grid(place.longitude, place.latitude),
                }
            )
    return {
        "id": identifier,
        "title": title,
        "county": county,
        "inset": inset,
        "width": frame.width,
        "height": frame.height,
        "center": frame.center,
        "zoom": frame.zoom,
        "frame": frame.as_dict(),
        "labels": frame.labels(),
        "outline": outline(geometry, frame),
        "places": included,
    }


def region_for(pages: list[dict]) -> dict:
    from shapely.geometry import mapping
    from shapely.ops import unary_union

    rectangles = []
    for page in pages:
        frame = Frame(**page["frame"])
        west, north = unproject(frame.west, frame.north)
        east, south = unproject(frame.east, frame.south)
        if east > 180:
            rectangles.extend([box(west, south, 180, north), box(-180, south, east - 360, north)])
        elif west < -180:
            rectangles.extend([box(west + 360, south, 180, north), box(-180, south, east, north)])
        else:
            rectangles.append(box(west, south, east, north))
    return {"type": "Feature", "properties": {}, "geometry": mapping(unary_union(rectangles))}


def prepare_atlas(
    root: Path,
    config: Configuration,
    catalog: dict[str, Item],
    cache: Path,
    directory: Path,
    output: Path,
    state: str,
    state_fips: str,
    epoch: int,
    *,
    basemap_id: str | None = None,
    generated: Path = Path("build/generated"),
    places_id: str | None = None,
    directory_id: str = "national_directory",
) -> Path:
    settings = Settings.model_validate(read_yaml(root / "pipelines/atlas/settings.yaml"))
    directory_manifest, places = directory_points(directory)
    verified_generated_files(catalog[directory_id], directory, catalog, allow_incomplete=True)
    directory_data = json.loads((directory / "places.json").read_text())
    if directory_data["state"] != state or directory_data["state_fips"] != state_fips:
        raise ValueError("Directory and atlas state disagree")
    if (output / "rendered.json").exists():
        raise ValueError("Atlas already rendered; choose a clean preparation directory")
    county_item = catalog["census_county_analysis"]
    counties = read_boundaries(cached_input(county_item, cache))
    counties = counties[counties.STATEFP == state_fips].sort_values(["NAMELSAD", "GEOID"])
    if counties.empty:
        raise ValueError("No source counties for this state")
    cities = read_boundaries(cached_input(catalog[places_id], cache)) if places_id else None
    pages = []
    for county in counties.itertuples():
        county_places = [place for place in places if place.county == county.GEOID]
        base = page_data(
            "c" + county.GEOID,
            county.NAMELSAD,
            county.GEOID,
            county.geometry,
            county_places,
            settings,
        )
        numbers = {place["id"]: index + 1 for index, place in enumerate(base["places"])}
        for place in base["places"]:
            place["number"] = numbers[place["id"]]
        pages.append(base)
        if cities is not None:
            hits = cities.sindex.query(county.geometry, predicate="intersects")
            for city in cities.iloc[hits].sort_values("GEOID").itertuples():
                if not county.geometry.intersects(city.geometry):
                    continue
                geometry = county.geometry.intersection(city.geometry)
                if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                    continue
                inset = page_data(
                    "c" + county.GEOID + "_p" + city.GEOID,
                    city.NAME,
                    county.GEOID,
                    geometry,
                    county_places,
                    settings,
                    inset=True,
                )
                if (
                    len(inset["places"]) < settings.inset_min_points
                    or inset["zoom"] <= base["zoom"]
                ):
                    continue
                for place in inset["places"]:
                    place["number"] = numbers[place["id"]]
                pages.append(inset)
    source = {
        "path": str(cached_input(catalog["noto_sans"], cache).resolve()),
        "sha256": catalog["noto_sans"].sha256,
    }
    basemap, basemap_complete = None, False
    if basemap_id:
        item = catalog[basemap_id]
        if item.family == "generated":
            manifest, payloads = verified_generated_files(
                item, generated / item.id, catalog, allow_incomplete=True
            )
            candidates = [path for name, path in payloads.items() if name.endswith(".pmtiles")]
            if len(candidates) != 1:
                raise ValueError("Expected one generated basemap")
            path = candidates[0]
            basemap_complete = manifest["complete"]
        else:
            path = cached_input(item, cache)
            basemap_complete = not item.blockers()
        basemap = {"path": str(path.resolve()), "sha256": digest(path)}
    for page in pages:
        place_labels(page)
    data = {
        "schema": 1,
        "state": state,
        "state_fips": state_fips,
        "epoch": epoch,
        "pipeline_version": pipeline_version(root),
        "pages": pages,
        "county_count": len(counties),
        "basemap": basemap,
        "font": source,
        "insets_configured": places_id is not None,
        "complete": bool(directory_manifest["complete"] and basemap_complete and places_id),
        "inputs": {
            "census_county_analysis": county_item.sha256,
            "noto_sans": catalog["noto_sans"].sha256,
            directory_id: hashlib.sha256(
                json.dumps(directory_manifest, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            **({basemap_id: catalog[basemap_id].sha256} if basemap_id else {}),
            **({places_id: catalog[places_id].sha256} if places_id else {}),
        },
        "directory_sha256": digest(directory / "generation.json"),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "region.geojson").write_text(json.dumps(region_for(pages), sort_keys=True) + "\n")
    target = output / "jobs.json"
    target.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    return target


def compose_atlas(root: Path, config: Configuration, jobs_path: Path, output: Path) -> dict:
    from datetime import UTC, datetime

    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from pyproj import Geod
    from weasyprint import HTML
    from weasyprint.urls import URLFetcherResponse

    from ck.catalog import safe_path
    from ck.generated import generation_manifest
    from ck.render import OfflineFetcher, font_files, pdf_timestamp

    jobs = json.loads(jobs_path.read_text())
    if jobs["pipeline_version"] != pipeline_version(root):
        raise ValueError("Atlas recipe changed; prepare and render again")
    identity = {
        **jobs,
        "font": jobs["font"]["sha256"],
        "basemap": (jobs.get("basemap") or {}).get("sha256"),
    }
    identifier = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest().encode()
    rendered = json.loads((jobs_path.parent / "rendered.json").read_text())
    if rendered["jobs_sha256"] != digest(jobs_path):
        raise ValueError("Atlas jobs changed after rendering; prepare and render again")
    if output.exists():
        raise ValueError("Composed atlas output must be new")
    records = {entry["id"]: entry for entry in rendered["files"]}
    if len(records) != len(rendered["files"]) or set(records) != {
        page["id"] for page in jobs["pages"]
    }:
        raise ValueError("Rendered atlas is missing or has duplicate pages")
    references = {}
    resources = {}
    pages = []
    geod = Geod(ellps="WGS84")
    for page in jobs["pages"]:
        entry = records[page["id"]]
        raster = jobs_path.parent / str(safe_path(entry["path"]))
        if raster.is_symlink() or digest(raster) != entry["sha256"]:
            raise ValueError("Atlas raster checksum mismatch")
        page["image"] = f"ck-atlas://raster/{page['id']}.png"
        resources[page["image"]] = raster
        frame = Frame(**page["frame"])
        center_lon, center_lat = frame.center
        end_lon, _ = unproject(frame.west + (frame.east - frame.west) * 0.2, frame.north)
        start_lon, _ = unproject(frame.west, frame.north)
        distance = abs(geod.inv(start_lon, center_lat, end_lon, center_lat)[2])
        # The bar measures local east-west distance at the frame's center latitude.
        page["scale"] = {"pixels": frame.width * 0.2, "km": f"{distance / 1000:.2f}"}
        pages.append(page)
        for place in page["places"]:
            if place["id"] in references and references[place["id"]]["zoom"] >= page["zoom"]:
                continue
            references[place["id"]] = {
                "anchor": page["id"],
                "grid": place["grid"],
                "name": place["name"],
                "number": place["number"],
                "zoom": page["zoom"],
            }
    fonts = font_files(root, config.languages[0])
    if len(fonts) != 1 or digest(fonts[0]) != jobs["font"]["sha256"]:
        raise ValueError("Atlas font changed; prepare and render again")
    env = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    document = env.get_template("atlas.html.j2").render(
        state=jobs["state"],
        pages=pages,
        index=sorted(references.items(), key=lambda pair: (pair[1]["name"].casefold(), pair[0])),
        fonts=[font.as_uri() for font in fonts],
        timestamp=datetime.fromtimestamp(jobs["epoch"], UTC).isoformat(),
        draft=not jobs["complete"],
    )
    output.mkdir(parents=True)
    (output / "files").mkdir()
    (output / "atlas.html").write_text(document)
    target = output / "files" / f"{jobs['state']}.pdf"

    class AtlasFetcher(OfflineFetcher):
        def fetch(self, url, headers=None):
            if url in resources:
                return URLFetcherResponse(url, body=resources[url].read_bytes())
            return super().fetch(url, headers)

    fetcher = AtlasFetcher([font.parent for font in fonts])
    with pdf_timestamp(jobs["epoch"]):
        pdf = HTML(string=document, url_fetcher=fetcher).render(pdf_tags=True)
        pdf.write_pdf(
            target,
            pdf_tags=True,
            pdf_identifier=identifier,
        )
    anchors = {name: number for number, page in enumerate(pdf.pages, 1) for name in page.anchors}
    expected_counties = {page["id"] for page in jobs["pages"] if not page["inset"]}
    if not expected_counties <= anchors.keys() or len(expected_counties) != jobs["county_count"]:
        raise ValueError("Atlas does not contain every source county")
    reference_text = {
        identifier: f"page {anchors[data['anchor']]}, grid {data['grid']}, point {data['number']}"
        for identifier, data in references.items()
    }
    (output / "place-index.json").write_text(
        json.dumps(reference_text, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    settings = Settings.model_validate(read_yaml(root / "pipelines/atlas/settings.yaml"))
    if target.stat().st_size > settings.max_total_bytes:
        raise ValueError("Atlas exceeds the national atlas budget")
    (output / "renderer-tools.txt").write_text(rendered["system_tools"])
    return generation_manifest(
        output,
        jobs["pipeline_version"],
        jobs["inputs"],
        complete=jobs["complete"],
        epoch=jobs["epoch"],
        intermediates=["place-index.json", "renderer-tools.txt"],
        tool_versions=rendered["system_tools"],
    )
