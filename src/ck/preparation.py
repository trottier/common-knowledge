"""Describe the pinned input graph and existing pipeline commands for a host driver."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import Field, StringConstraints

from ck.catalog import Item, load_catalog
from ck.config import Identifier, Model, load_config, read_yaml
from ck.fetch import fetch, verify_zim
from ck.generated import verified_generated_files
from ck.planner import plan_variants


class SampleSettings(Model):
    state: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    state_fips: Annotated[str, StringConstraints(pattern=r"^[0-9]{2}$")]
    osm_id: Identifier


class BuildSettings(Model):
    sample: SampleSettings
    medical_pdf_jobs: int = Field(ge=1, le=8)


def generated_actions(root: Path, items: dict[str, Item], identifier: str) -> list[dict]:
    """Every command runs in a pinned container; paths are shared between stages."""
    item = items[identifier]
    output = "/generated/" + identifier
    workflow = BuildSettings.model_validate(read_yaml(root / "pipelines/build.yaml"))
    sample = workflow.sample.model_dump()

    def ck(*arguments):
        return {"kind": "ck", "args": [str(value) for value in arguments]}

    def build(*arguments, cache=True):
        return ck(*arguments, *(["--cache", "/cache"] if cache else []), "--output", output)

    if identifier == "directory_points":
        return [build("national-points")]
    if identifier == "directory_seed_ri":
        return [
            build(
                "directory",
                "--seed",
                "--state",
                sample["state"],
                "--state-fips",
                sample["state_fips"],
                "--osm-id",
                sample["osm_id"],
            )
        ]
    if identifier in {"protomaps_us", "protomaps_ri"}:
        national = identifier == "protomaps_us"
        seed = "directory_points" if national else "directory_seed_ri"
        prefix = "/work/preliminary-" + identifier
        if seed not in item.inputs:
            raise ValueError(f"Undeclared preparation dependency: {identifier} needs {seed}")
        prepare = (
            ["atlas", "prepare-all"]
            if national
            else [
                "atlas",
                "prepare",
                "--state",
                sample["state"],
                "--state-fips",
                sample["state_fips"],
                "--places-id",
                "census_places_" + sample["state"].lower(),
            ]
        )
        return [
            ck(
                *prepare,
                "--directory",
                "/generated/" + seed,
                "--directory-id",
                seed,
                "--cache",
                "/cache",
                "--generated",
                "/generated",
                "--output",
                prefix,
            ),
            {
                "kind": "extract",
                "jobs": prefix,
                "national": national,
                "planet_sha256": items["protomaps_planet"].sha256,
                "output": output,
            },
        ]
    if identifier in {"national_atlas", "atlas_ri"}:
        national = identifier == "national_atlas"
        seed = "directory_points" if national else "directory_seed_ri"
        basemap = "protomaps_us" if national else "protomaps_ri"
        prefix = "/work/final-" + identifier
        prepare = (
            ["atlas", "prepare-all"]
            if national
            else [
                "atlas",
                "prepare",
                "--state",
                sample["state"],
                "--state-fips",
                sample["state_fips"],
                "--places-id",
                "census_places_" + sample["state"].lower(),
            ]
        )
        actions = [
            ck(
                *prepare,
                "--directory",
                "/generated/" + seed,
                "--directory-id",
                seed,
                "--basemap-id",
                basemap,
                "--cache",
                "/cache",
                "--generated",
                "/generated",
                "--output",
                prefix,
            ),
            {
                "kind": "render-compose",
                "jobs": prefix,
                "national": national,
                "output": "/work/composed" if national else output,
            },
        ]
        if national:
            actions.append(
                {
                    "kind": "collect",
                    "command": ["atlas", "collect"],
                    "folder": "/work/composed",
                    "output": output,
                    "args": ["--directory", "/generated/" + seed],
                }
            )
        return actions
    if identifier == "national_directory":
        return [
            ck(
                "directory-all",
                "--points",
                "/generated/directory_points",
                "--atlas",
                "/generated/national_atlas",
                "--jobs",
                str(read_yaml(root / "pipelines/directory/settings.yaml")["default_jobs"]),
                "--output",
                "/work/directories",
            ),
            {
                "kind": "collect",
                "command": ["directory-collect"],
                "folder": "/work/directories",
                "output": output,
                "args": [
                    "--points",
                    "/generated/directory_points",
                    "--atlas",
                    "/generated/national_atlas",
                ],
            },
        ]
    if identifier == "directory_ri":
        return [
            build(
                "directory",
                "--state",
                sample["state"],
                "--state-fips",
                sample["state_fips"],
                "--osm-id",
                sample["osm_id"],
                "--atlas-index",
                "/generated/atlas_ri/place-index.json",
                "--atlas-id",
                "atlas_ri",
            )
        ]
    if identifier.startswith("android_source_"):
        parent = identifier.removeprefix("android_source_")
        policy = read_yaml(root / "pipelines/androidmaps/national.yaml")
        return [build("android-source", "--osm-id", policy["source_inputs"][parent])]
    if identifier.startswith("android_extract_"):
        parent = next(key for key in item.inputs if key.startswith("android_source_"))
        state = identifier.removeprefix("android_extract_").upper()
        return [
            build(
                "android-extract",
                "--prepared",
                "/generated/" + parent,
                "--prepared-id",
                parent,
                "--states",
                state,
            )
        ]
    if identifier == "android_map_howto":
        return [build("android-howto", cache=False)]
    if identifier.startswith("android_map_"):
        state = identifier.removeprefix("android_map_").upper()
        prepared = next(key for key in item.inputs if key.startswith("android_extract_"))
        source = next(key for key in item.inputs if key.startswith("geofabrik_"))
        return [
            build(
                "android-map",
                "--state",
                state,
                "--osm-id",
                source,
                "--prepared",
                "/generated/" + prepared,
                "--prepared-id",
                prepared,
            )
        ]
    if identifier == "android_roads_places_ri":
        return [build("android-map", "--state", sample["state"], "--osm-id", sample["osm_id"])]
    if identifier == "android_roads_places":
        maps = sorted(key for key in item.inputs if key.startswith("android_map_"))
        if not maps:
            raise ValueError("National Android collection has no map inputs")
        return [build("android-collect", "--outputs", *["/generated/" + key for key in maps])]
    if identifier == "laptop_roads_places":
        return [build("laptop-tiles", "--generated", "/generated", cache=False)]
    if identifier == "laptop_map_viewer":
        return [build("laptop-viewer", "--generated", "/generated")]
    if identifier.startswith("local_llm_"):
        return [build("local-llm", "--profile", identifier.removeprefix("local_llm_"))]
    if identifier == "wikem_en_nopic":
        return [build("wikem")]
    if identifier.endswith("_offline") and len(item.inputs) == 1:
        source = items[item.inputs[0]]
        if source.family == "zim":
            return [build("offline-zim", "--item", source.id)]
    if identifier == "medical_phone_pdfs":
        return [
            build(
                "medpdf",
                "--generated",
                "/generated",
                "--jobs",
                str(workflow.medical_pdf_jobs),
            )
        ]
    if identifier.startswith("phrasebook_"):
        return [{"kind": "phrasebooks", "output": "/work/phrasebooks"}]
    if identifier.startswith("reference_"):
        from ck.referencepacks import selections

        if identifier in selections(root):
            return [build("reference-pack", "--pack", identifier)]
    clips = read_yaml(root / "pipelines/video/clips.yaml")
    matches = [key for key, clip in clips.items() if clip["source_id"] in item.inputs]
    if len(matches) == 1:
        return [build("video", "--clip", matches[0])]
    raise ValueError(f"No input-generation pipeline registered for {identifier}")


def preparation_plan(
    root: Path, profile: str, core_bytes: int = 0, capacity_override: int | None = None
) -> dict:
    config = load_config(root)
    if profile not in config.build.profiles:
        raise ValueError("Unknown build profile")
    items = load_catalog(root, config)
    plans = plan_variants(config, items, profile, core_bytes, capacity_override)
    selected = sorted({identifier for plan in plans for identifier in plan.items})
    ordered, visiting, done = [], set(), set()

    def visit(identifier):
        if identifier in visiting or identifier not in items:
            raise ValueError(f"Cyclic or missing preparation input: {identifier}")
        if identifier in done:
            return
        visiting.add(identifier)
        for dependency in sorted(items[identifier].inputs):
            visit(dependency)
        visiting.remove(identifier)
        done.add(identifier)
        ordered.append(identifier)

    for identifier in selected:
        visit(identifier)
    return {
        "profile": profile,
        "version": config.build.version,
        "capacity_assumed": capacity_override is not None,
        "selected": selected,
        "downloads": [key for key in ordered if items[key].family != "generated"],
        "tasks": [
            {"id": key, "actions": generated_actions(root, items, key)}
            for key in ordered
            if items[key].family == "generated"
        ],
    }


def fetch_build_inputs(root: Path, identifiers: list[str], cache: Path) -> list[str]:
    """Unplaced source ZIMs may have audited repairable content-link defects."""
    items = load_catalog(root, load_config(root))
    paths = []
    for identifier in identifiers:
        item = items[identifier]
        if item.family == "zim" and item.placement == "hub_only":

            def check(_item, path):
                report = verify_zim(path, regeneration_only=True, allow_broken_links=True)
                audit = cache / "audits" / (_item.sha256 + "-regeneration.json")
                audit.parent.mkdir(parents=True, exist_ok=True)
                audit.write_text(json.dumps(report, sort_keys=True) + "\n")

            path = fetch(item, cache, format_check=check)
        else:
            path = fetch(item, cache)
        paths.append(str(path))
    return paths


def verify_prepared(root: Path, identifiers: list[str], generated: Path, epoch: int) -> None:
    items = load_catalog(root, load_config(root))
    for identifier in identifiers:
        item = items[identifier]
        seed = identifier == "directory_seed_ri" and item.placement == "hub_only"
        metadata, _ = verified_generated_files(
            item, generated / identifier, items, allow_incomplete=seed
        )
        if metadata["source_date_epoch"] != epoch:
            raise ValueError(f"Prepared input epoch changed: {identifier}")
