"""Input generation preserves dependency order, review gates and offline boundaries."""

import importlib.util
from pathlib import Path

import pytest

from ck.catalog import load_catalog
from ck.config import load_config
from ck.preparation import fetch_build_inputs, preparation_plan

ROOT = Path(__file__).resolve().parents[1]


def test_complete_catalog_has_handlers_and_dependencies_precede_consumers():
    items = load_catalog(ROOT, load_config(ROOT))
    assert preparation_plan(ROOT, "dev")["tasks"] == []
    for profile in ("sample", "full"):
        # The nominal user-supplied label is an inspection assumption, never a build capacity.
        plan = preparation_plan(ROOT, profile, capacity_override=32_000_000_000)
        assert plan["capacity_assumed"] is True
        ordered = [task["id"] for task in plan["tasks"]]
        for index, identifier in enumerate(ordered):
            assert all(
                dependency in ordered[:index] or dependency in plan["downloads"]
                for dependency in items[identifier].inputs
            )
        assert "wikem_en_nopic" in ordered
        assert "osmand_prebuilt" not in plan["selected"]
    assert {"national_atlas", "national_directory", "android_roads_places"} <= set(ordered)
    assert len([key for key in ordered if key.startswith("android_extract_")]) == 56


def test_unknown_generator_and_cycles_fail_instead_of_dropping_content(monkeypatch):
    items = load_catalog(ROOT, load_config(ROOT))
    source = items["wikimed_en_nopic"]
    unknown = items["wikimed_en_offline"].model_copy(
        update={"id": "unregistered", "profiles": ["sample"], "placement": "universal"}
    )
    monkeypatch.setattr(
        "ck.preparation.load_catalog", lambda *args: {source.id: source, unknown.id: unknown}
    )
    with pytest.raises(ValueError, match="No input-generation pipeline"):
        preparation_plan(ROOT, "sample")
    unknown.inputs = [unknown.id]
    with pytest.raises(ValueError, match="Cyclic"):
        preparation_plan(ROOT, "sample")


def test_only_unplaced_zim_inputs_receive_the_repairable_source_audit(tmp_path, monkeypatch):
    items = load_catalog(ROOT, load_config(ROOT))
    source = items["wikimed_en_nopic"]
    placed = source.model_copy(update={"id": "placed", "placement": "universal"})
    monkeypatch.setattr(
        "ck.preparation.load_catalog", lambda *args: {source.id: source, placed.id: placed}
    )
    calls = []

    def fetch(item, cache, **kwargs):
        calls.append((item.id, bool(kwargs)))
        if kwargs:
            kwargs["format_check"](item, tmp_path / "fixture")
        return tmp_path / item.sha256

    audits = []
    monkeypatch.setattr("ck.preparation.fetch", fetch)
    monkeypatch.setattr(
        "ck.preparation.verify_zim", lambda path, **flags: audits.append(flags) or {"status": False}
    )
    fetch_build_inputs(ROOT, [source.id, placed.id], tmp_path)
    assert calls == [(source.id, True), (placed.id, False)]
    assert audits == [{"regeneration_only": True, "allow_broken_links": True}]
    assert (tmp_path / "audits" / (source.sha256 + "-regeneration.json")).exists()


def test_source_audit_does_not_bypass_legal_holds(tmp_path, monkeypatch):
    items = load_catalog(ROOT, load_config(ROOT))
    held = items["wikimed_en_nopic"].model_copy(update={"requires_legal": True})
    monkeypatch.setattr("ck.preparation.load_catalog", lambda *args: {held.id: held})
    monkeypatch.setattr(
        "ck.preparation.verify_zim",
        lambda *args, **kwargs: pytest.fail("No audit or network before legal gate"),
    )
    with pytest.raises(ValueError, match="Cannot fetch unconfirmed"):
        fetch_build_inputs(ROOT, [held.id], tmp_path)


def driver(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "prepare_profile_driver", ROOT / "tools/prepare_profile.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.Driver.__new__(module.Driver)
    result.root, result.work, result.cache, result.generated = [
        tmp_path / name for name in ("root", "work", "cache", "generated")
    ]
    for folder in (result.root, result.work, result.cache, result.generated):
        folder.mkdir()
    result.images = {"build": "sha256:fixture-build", "atlas": "sha256:fixture-atlas"}
    result.epoch, result.produced = 946684800, set()
    return result, module


def test_native_failure_prevents_composition_and_paths_cannot_escape(tmp_path, monkeypatch):
    build, _ = driver(tmp_path)
    folder = build.work / "final" / "RI"
    folder.mkdir(parents=True)
    (folder / "jobs.json").write_text("{}")
    calls = []

    def fail(*args, **kwargs):
        raise RuntimeError("native render failed")

    monkeypatch.setattr(build, "run", fail)
    monkeypatch.setattr(build, "ck", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(RuntimeError, match="native render failed"):
        build.action(
            {
                "kind": "render-compose",
                "jobs": "/work/final",
                "national": True,
                "output": "/work/composed",
            }
        )
    assert not calls
    with pytest.raises(ValueError, match="escapes"):
        build.path("/work/../../outside")


def test_only_explicit_fetch_containers_have_network_and_source_is_read_only(tmp_path, monkeypatch):
    build, module = driver(tmp_path)
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda command, **kwargs: calls.append(command))
    build.run(["national-points"])
    build.run(["fetch-build-inputs", "fixture"], network=True)
    assert "--network=none" in calls[0] and "--network=none" not in calls[1]
    assert str(build.root) + ":/source:ro" in calls[0]
    assert str(build.cache) + ":/cache:ro" in calls[0]
    assert str(build.cache) + ":/cache" in calls[1]
    assert "sha256:fixture-build" in calls[0]


def test_preflight_failure_never_starts_fetching_or_generation(tmp_path, monkeypatch):
    build, _ = driver(tmp_path)
    calls = []

    def blocked(*arguments, **kwargs):
        calls.append(arguments)
        raise ValueError("Review gates remain")

    monkeypatch.setattr(build, "ck", blocked)
    with pytest.raises(ValueError, match="Review gates remain"):
        build.prepare("full")
    assert calls == [("check-profile", "--profile", "full")]
    assert not (build.work / "preparation.json").exists()


@pytest.mark.parametrize("jobs", [0, 9])
def test_workflow_worker_settings_match_the_pipeline_bounds(jobs):
    from pydantic import ValidationError
    from ck.config import read_yaml
    from ck.preparation import BuildSettings

    values = read_yaml(ROOT / "pipelines/build.yaml")
    values["medical_pdf_jobs"] = jobs
    with pytest.raises(ValidationError):
        BuildSettings.model_validate(values)
