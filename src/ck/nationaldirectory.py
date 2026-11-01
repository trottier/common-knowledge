"""Bounded directory rendering, local contents links and national coverage checks."""

import hashlib
import json
import multiprocessing
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    ByteStringObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

from ck import geofonts
from ck.catalog import Item
from ck.config import Configuration, Model, read_yaml
from ck.directory import directory_text, pipeline_version, plain, public_source_data
from ck.fetch import digest
from ck.generated import generation_manifest, verified_generated_files
from ck.national import DirectoryData, load_national_points
from ck.render import font_files, render_pdf


class Settings(Model):
    max_places_per_part: int = Field(ge=1, le=1000)
    default_jobs: int = Field(ge=1, le=4)
    index_link_prefix: str


@dataclass
class Inputs:
    root: Path
    config: Configuration
    items: dict[str, Item]
    data: DirectoryData
    references: dict[str, str]
    index_bytes: bytes
    epoch: int
    settings: Settings
    ids: list[str]
    pins: dict[str, str]
    recipe: str


def prepare(
    root,
    config,
    items,
    points,
    atlas,
    epoch,
    points_id="directory_points",
    atlas_id="national_atlas",
):
    data = load_national_points(items[points_id], points, items, epoch)
    manifest, _ = verified_generated_files(items[atlas_id], atlas, items)
    index = atlas / "place-index.json"
    binding = next(
        (entry for entry in manifest["intermediates"] if entry["path"] == "place-index.json"), None
    )
    if (
        manifest["source_date_epoch"] != epoch
        or manifest["inputs"].get(points_id) != items[points_id].sha256
        or index.is_symlink()
        or not binding
        or digest(index) != binding["sha256"]
    ):
        raise ValueError("National directory requires this epoch's bound complete atlas index")
    index_bytes = index.read_bytes()
    references = json.loads(index_bytes)
    identifiers = [place.id for place in data.places]
    if (
        not isinstance(references, dict)
        or len(identifiers) != len(set(identifiers))
        or references.keys() != set(identifiers)
        or any(
            not isinstance(value, str)
            or not re.fullmatch(r"page [1-9]\d*, grid [A-Z][1-9]\d*, point [1-9]\d*", value)
            for value in references.values()
        )
    ):
        raise ValueError("National atlas references must cover every distinct source place")
    settings = Settings.model_validate(read_yaml(root / "pipelines/directory/settings.yaml"))
    namespace = urlsplit(settings.index_link_prefix)
    if (
        namespace.scheme != "https"
        or not namespace.netloc.endswith(".invalid")
        or not namespace.path.endswith("/")
        or namespace.query
        or namespace.fragment
    ):
        raise ValueError("The temporary contents-link namespace must remain reserved and offline")
    ids = [points_id, atlas_id]
    pins = {identifier: items[identifier].sha256 for identifier in [*ids, *geofonts.font_ids(root)]}
    return Inputs(
        root,
        config,
        items,
        data,
        references,
        index_bytes,
        epoch,
        settings,
        ids,
        pins,
        pipeline_version(root, index_bytes),
    )


def county_parts(data: DirectoryData, state: str, maximum: int):
    fips = data.states[state]
    grouped = defaultdict(list)
    for place in data.places:
        if place.county.startswith(fips):
            if place.county not in data.counties:
                raise ValueError("Directory place has an unknown Census county")
            grouped[place.county].append(place)
    counties = sorted(
        (code for code in data.counties if code.startswith(fips)),
        key=lambda code: (data.counties[code].casefold(), code),
    )
    for code in counties:
        places = sorted(
            grouped[code], key=lambda place: (place.category, place.name.casefold(), place.id)
        )
        for offset in range(0, max(1, len(places)), maximum):
            yield code, offset // maximum + 1, places[offset : offset + maximum]


def join_parts(
    index: Path,
    parts: list[dict],
    output: Path,
    prefix: str,
    state: str,
    page_format: str,
    epoch: int,
) -> tuple[int, dict]:
    writer = PdfWriter()
    writer.append(index)
    targets = {}
    for part in parts:
        targets.setdefault(part["county"], len(writer.pages))
        continuation = f" · part {part['part']}" if part["part"] > 1 else ""
        writer.append(part["pdf"], outline_item=part["county_name"] + continuation)
    links = Counter()
    for page in writer.pages:
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            action = annotation.get("/A", {})
            uri = str(action.get("/URI", ""))
            if uri.startswith(prefix):
                county = uri[len(prefix) :]
                if county not in targets:
                    raise ValueError("Unknown county in directory contents")
                annotation[NameObject("/A")] = DictionaryObject(
                    {
                        NameObject("/S"): NameObject("/GoTo"),
                        NameObject("/D"): ArrayObject(
                            [writer.pages[targets[county]].indirect_reference, NameObject("/Fit")]
                        ),
                    }
                )
                links[county] += 1
    # A wrapped county name produces one PDF annotation per line. Every
    # clickable region must target that county; annotation count is not a
    # count of distinct contents entries.
    if links.keys() != targets.keys():
        raise ValueError("Directory contents must link to every county")
    timestamp = datetime.fromtimestamp(epoch, UTC).strftime("D:%Y%m%d%H%M%SZ")
    writer.add_metadata(
        {
            "/Title": f"{state} public places · {page_format}",
            "/Author": "Common Knowledge",
            "/CreationDate": timestamp,
            "/ModDate": timestamp,
        }
    )
    writer._root_object[NameObject("/Lang")] = TextStringObject("en")
    identity = hashlib.sha256(
        (
            state
            + page_format
            + str(epoch)
            + digest(index)
            + "".join(part["sha256"] for part in parts)
        ).encode()
    ).digest()[:16]
    writer._ID = ArrayObject([ByteStringObject(identity), ByteStringObject(identity)])
    with output.open("wb") as stream:
        writer.write(stream)
    count = len(writer.pages)
    writer.close()
    return count, targets


def build_state(context: Inputs, state: str, output: Path) -> dict:
    if output.exists() or state not in context.data.states:
        raise ValueError("Directory state output must be new and present in Census")
    data, root, settings = context.data, context.root, context.settings
    fips = data.states[state]
    county_ids = sorted(code for code in data.counties if code.startswith(fips))
    if not county_ids:
        raise ValueError("Directory state has no Census counties")
    plans = list(county_parts(data, state, settings.max_places_per_part))
    places = [place for _, _, entries in plans for place in entries]
    profiles = {code: value for code, value in data.profiles.items() if code.startswith(fips)}
    missing_profiles = [code for code in data.missing_profiles if code.startswith(fips)]
    fallback = tuple(geofonts.font_ids(root))
    fonts = font_files(root, context.config.languages[0], fallback)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-directory-state-") as temporary:
        stage = Path(temporary)
        files, audit = stage / "files", stage / "parts"
        files.mkdir()
        audit.mkdir()
        rendered = {"phone": [], "print": []}
        for county, number, entries in plans:
            body = directory_text(
                context.items,
                state,
                entries,
                {county: profiles[county]} if number == 1 and county in profiles else {},
                [county] if number == 1 and county in missing_profiles else [],
                data.agencies,
                context.references,
                context.ids,
                True,
                [],
                data.rejected,
            )
            body = body.replace(
                f"title: {state} public places", "title: " + json.dumps(data.counties[county])
            )
            if not entries:
                body += (
                    f"\n## {plain(data.counties[county])}\n\nNo public place in this snapshot.\n"
                )
            geofonts.require_glyphs([body], fonts)
            source = audit / f"{county}-{number}.md"
            source.write_text(body)
            for page_format in rendered:
                target = audit / f"{county}-{number}-{page_format}.pdf"
                render_pdf(
                    root,
                    context.config,
                    source,
                    context.config.languages[0],
                    page_format,
                    target,
                    context.epoch,
                    template="directory-part.html.j2",
                    fallback_ids=fallback,
                )
                rendered[page_format].append(
                    {
                        "county": county,
                        "county_name": data.counties[county],
                        "part": number,
                        "place_ids": [place.id for place in entries],
                        "pdf": target,
                        "sha256": digest(target),
                    }
                )
        index = [
            "---",
            f"title: {state} public places",
            "status: draft",
            "reviewer: null",
            "reviewed_on: null",
            "---",
            "",
            "May help; not confirmed open.",
            "",
            "Choose a county below. The atlas reference at each place "
            "gives its map page and grid square.",
            "",
            "No entry confirms that a place is open or serves as an event shelter.",
            "",
            "## Counties",
            "",
        ]
        counts = Counter(place.county for place in places)
        for county in sorted(county_ids, key=lambda code: (data.counties[code].casefold(), code)):
            index += [
                f"- [{plain(data.counties[county])}]({settings.index_link_prefix}{county}) "
                f"· {counts[county]} public places"
            ]
        index_source = audit / "index.md"
        index_source.write_text("\n".join(index) + "\n")
        geofonts.require_glyphs([index_source.read_text()], fonts)
        page_counts, starts = {}, {}
        for page_format, parts in rendered.items():
            index_pdf = audit / f"index-{page_format}.pdf"
            render_pdf(
                root,
                context.config,
                index_source,
                context.config.languages[0],
                page_format,
                index_pdf,
                context.epoch,
                template="directory-part.html.j2",
                fallback_ids=fallback,
            )
            page_counts[page_format], starts[page_format] = join_parts(
                index_pdf,
                parts,
                files / f"{state}_{page_format}.pdf",
                settings.index_link_prefix,
                state,
                page_format,
                context.epoch,
            )
        public = public_source_data(
            data, places, profiles, missing_profiles, context.items, context.ids
        )
        (files / f"{state}_SOURCE_DATA.json").write_text(
            json.dumps(public, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        state_audit = {
            "state": state,
            "state_fips": fips,
            "county_ids": county_ids,
            "place_ids": [place.id for place in places],
            "pages": page_counts,
            "county_start_pages_zero_based": starts,
            "parts": [
                {key: value for key, value in part.items() if key not in {"pdf", "county_name"}}
                for part in rendered["phone"]
            ],
        }
        (stage / "state.json").write_text(
            json.dumps(state_audit, ensure_ascii=False, sort_keys=True) + "\n"
        )
        if pipeline_version(root, context.index_bytes) != context.recipe:
            raise ValueError("Directory recipe changed during rendering")
        measured = generation_manifest(
            stage,
            context.recipe,
            context.pins,
            complete=True,
            epoch=context.epoch,
            intermediates=["state.json"],
        )
        stage.rename(output)
    return {
        **measured,
        "state": state,
        "places": len(places),
        "counties": len(county_ids),
        "pages": page_counts,
    }


_CONTEXT = None


def _initialize(context):
    global _CONTEXT
    _CONTEXT = context


def _worker(task):
    state, output = task
    result = build_state(_CONTEXT, state, output)
    print(json.dumps(result), file=sys.stderr, flush=True)
    return result


def build_all(
    context: Inputs, output: Path, states: list[str] | None = None, jobs: int | None = None
) -> dict:
    selected = sorted(
        states
        or {
            code
            for code, fips in context.data.states.items()
            if any(county.startswith(fips) for county in context.data.counties)
        }
    )
    jobs = context.settings.default_jobs if jobs is None else jobs
    if (
        output.exists()
        or not 1 <= jobs <= 4
        or len(selected) != len(set(selected))
        or not set(selected) <= context.data.states.keys()
    ):
        raise ValueError("Choose new output, distinct known states and one to four workers")
    output.mkdir(parents=True)
    # Builds run on Linux. Fork shares the checked national snapshot read-only,
    # while separate PDF processes bound memory and isolate font configuration.
    results = []
    with ProcessPoolExecutor(
        max_workers=jobs,
        mp_context=multiprocessing.get_context("fork"),
        initializer=_initialize,
        initargs=(context,),
    ) as pool:
        pending = [pool.submit(_worker, (state, output / state)) for state in selected]
        try:
            for future in as_completed(pending):
                results.append(future.result())
        except BaseException:
            for future in pending:
                future.cancel()
            raise
    return {
        "states": sorted(result["state"] for result in results),
        "places": sum(result["places"] for result in results),
        "size_bytes": sum(result["size_bytes"] for result in results),
    }


def collect(context: Inputs, outputs: list[Path], output: Path) -> dict:
    states = {
        code
        for code, fips in context.data.states.items()
        if any(county.startswith(fips) for county in context.data.counties)
    }
    if output.exists() or len(outputs) != len(states):
        raise ValueError("National directory collection needs a new output and every jurisdiction")
    verified, seen, total = [], set(), set()
    for folder in outputs:
        manifest = json.loads((folder / "generation.json").read_text())
        state = Path(manifest["files"][0]["path"]).name[:2]
        if (
            state not in states
            or state in seen
            or manifest["pipeline_version"] != context.recipe
            or manifest["inputs"] != context.pins
            or manifest["source_date_epoch"] != context.epoch
        ):
            raise ValueError("Directory state recipe, source pins, epoch or jurisdiction changed")
        item = Item(
            id="directory_" + state.lower(),
            family="generated",
            title="Measured state directory",
            version="development",
            size_bytes=sum(entry["size_bytes"] for entry in manifest["files"]),
            sha256=hashlib.sha256(
                json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            license="ODbL-1.0 AND US-PD",
            attribution="OpenStreetMap contributors; U.S. federal sources",
            license_proof_url="https://www.openstreetmap.org/copyright",
            placement="hub_only",
            dest="build/inputs/",
            profiles=["full"],
            inputs=list(context.pins),
            pipeline_version=context.recipe,
        )
        _, payloads = verified_generated_files(item, folder, context.items)
        expected_files = {f"{state}_phone.pdf", f"{state}_print.pdf", f"{state}_SOURCE_DATA.json"}
        binding = next(
            (entry for entry in manifest["intermediates"] if entry["path"] == "state.json"), None
        )
        if (
            payloads.keys() != expected_files
            or (folder / "state.json").is_symlink()
            or not binding
            or digest(folder / "state.json") != binding["sha256"]
        ):
            raise ValueError("Directory state audit or payload set changed")
        audit = json.loads((folder / "state.json").read_text())
        fips = context.data.states[state]
        expected_places = {
            place.id for place in context.data.places if place.county.startswith(fips)
        }
        expected_counties = sorted(code for code in context.data.counties if code.startswith(fips))
        part_ids = [identifier for part in audit["parts"] for identifier in part["place_ids"]]
        place_counties = {
            place.id: place.county for place in context.data.places if place.county.startswith(fips)
        }
        sequences = Counter()
        for part in audit["parts"]:
            county = part["county"]
            sequences[county] += 1
            if (
                county not in expected_counties
                or part["part"] != sequences[county]
                or len(part["place_ids"]) > context.settings.max_places_per_part
                or any(place_counties.get(identifier) != county for identifier in part["place_ids"])
            ):
                raise ValueError("Directory part bounds or county assignments changed")
        if (
            audit["state"] != state
            or audit["state_fips"] != fips
            or audit["county_ids"] != expected_counties
            or Counter(audit["place_ids"])
            != Counter({identifier: 1 for identifier in expected_places})
            or Counter(part_ids) != Counter({identifier: 1 for identifier in expected_places})
            or total & expected_places
            or set(sequences) != set(expected_counties)
        ):
            raise ValueError("Directory place or county coverage is missing or duplicated")
        canonical = [
            place
            for _, _, entries in county_parts(
                context.data, state, context.settings.max_places_per_part
            )
            for place in entries
        ]
        profiles = {
            code: value for code, value in context.data.profiles.items() if code.startswith(fips)
        }
        missing = [code for code in context.data.missing_profiles if code.startswith(fips)]
        if json.loads(payloads[f"{state}_SOURCE_DATA.json"].read_text()) != public_source_data(
            context.data, canonical, profiles, missing, context.items, context.ids
        ):
            raise ValueError(
                "Directory public source data differs from its checked national snapshot"
            )
        for page_format in ("phone", "print"):
            reader = PdfReader(payloads[f"{state}_{page_format}.pdf"])
            starts = audit["county_start_pages_zero_based"][page_format]
            if (
                len(reader.pages) != audit["pages"][page_format]
                or set(starts) != set(expected_counties)
                or any(
                    type(page) is not int or not 0 <= page < len(reader.pages)
                    for page in starts.values()
                )
            ):
                raise ValueError("Directory contents page references are invalid")
            target_pages = {
                reader.pages[number].indirect_reference.idnum for number in starts.values()
            }
            linked_pages = set()
            for number in range(min(starts.values())):
                page = reader.pages[number]
                for reference in page.get("/Annots", []):
                    action = reference.get_object().get("/A", {})
                    destination = action.get("/D", [])
                    if (
                        action.get("/S") != "/GoTo"
                        or not isinstance(destination, list)
                        or not destination
                        or getattr(destination[0], "idnum", None) not in target_pages
                    ):
                        raise ValueError("Directory contents link has an invalid county target")
                    linked_pages.add(destination[0].idnum)
            if linked_pages != target_pages:
                raise ValueError("Directory contents does not link to every county start")
            for page in reader.pages:
                for reference in page.get("/Annots", []):
                    action = reference.get_object().get("/A", {})
                    if str(action.get("/URI", "")).startswith(context.settings.index_link_prefix):
                        raise ValueError("An internal directory contents link was not rewritten")
        verified.append((state, folder, payloads))
        seen.add(state)
        total.update(expected_places)
    if seen != states or total != set(context.references):
        raise ValueError("National directory does not cover every source jurisdiction and place")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-directory-set-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        (stage / "states").mkdir()
        bindings = []
        for state, folder, payloads in sorted(verified):
            for name, path in payloads.items():
                shutil.copyfile(path, stage / "files" / name)
            for name in ("state.json", "generation.json"):
                target = f"states/{state}.{name}"
                shutil.copyfile(folder / name, stage / target)
                bindings.append(target)
        result = generation_manifest(
            stage,
            "directory-set-v1-" + context.recipe.removeprefix("directory-v1-"),
            context.pins,
            complete=True,
            epoch=context.epoch,
            intermediates=bindings,
        )
        stage.rename(output)
    return {
        **result,
        "jurisdictions": len(seen),
        "counties": len(context.data.counties),
        "places": len(total),
    }
