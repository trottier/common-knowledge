import os
import subprocess
import time
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError

from ck.catalog import Collection, Item, load_catalog
from ck.config import LocalLLM, load_config
from ck.llm import android_prompt_settings, model_metadata, settings_for, start_text, system_prompt
from ck.planner import plan_variants

ROOT = Path(__file__).resolve().parents[1]


def fixture_item(identifier, size):
    return Item(
        id=identifier,
        family="llm" if identifier == "base_model" else "docs",
        title="Synthetic policy fixture, never shipped",
        version="fixture",
        url="https://example.invalid/fixture",
        size_bytes=size,
        sha256="0" * 64,
        license="Apache-2.0",
        attribution="Synthetic fixture",
        license_proof_url="https://example.invalid/license",
        placement="universal",
        dest="9_OFFLINE_AI/fixture" if identifier == "base_model" else "7_LAPTOP/" + identifier,
        profiles=["full"],
    )


@pytest.mark.parametrize(
    "change",
    [
        {"host": "0.0.0.0"},
        {"fallback_variants": [1, 1, 3, 4]},
        {"fallback_variants": [1, 3, 5, 9]},
        {"runner_filename": "runner$(command).exe"},
        {"context_reserve_tokens": 32768},
        {"context_tokens": 16384},
    ],
)
def test_settings_reject_unsafe_or_ambiguous_launches(change):
    with pytest.raises(ValidationError):
        LocalLLM.model_validate({**settings_for(ROOT).model_dump(), **change})


def test_model_size_limit_is_independent_of_parameter_basis(tmp_path):
    model = tmp_path / "oversized.gguf"
    with model.open("wb") as stream:
        stream.truncate(2_500_000_001)
    with pytest.raises(ValueError, match="file size"):
        model_metadata(model, fixture_item("base_model", 2_500_000_001), 32768)


def test_ai_deferral_preserves_other_items_and_future_allocation_never_expands():
    config = load_config(ROOT)
    config.build.android_maps = "roads_places"
    items = {
        key: fixture_item(key, size)
        for key, size in {
            "national_atlas": 100,
            "national_directory": 100,
            "android_roads_places": 100,
            "base_model": 300,
        }.items()
    }
    for collection in ("howto_2", "med_lib", "simplewiki", "morale"):
        item = fixture_item("depth_" + collection, 450)
        item.placement = Collection(collection=collection)
        items[item.id] = item
    plans = plan_variants(config, items, "full", 10, 1000)
    assert all(plan.fits for plan in plans)
    assert all("base_model" not in plan.items for plan in plans)
    assert all(plan.llm_variants == [] for plan in plans)
    assert all(
        {"national_atlas", "national_directory", "android_roads_places"} <= set(plan.items)
        for plan in plans
    )
    config.variants.offline_ai_enabled = True
    plans = plan_variants(config, items, "full", 10, 1000)
    assert [
        plan.variant for plan in plans if "base_model" in plan.items
    ] == config.variants.offline_ai
    assert all(plan.llm_variants == config.variants.offline_ai for plan in plans)
    # Overflow fails instead of moving, expanding, or silently dropping the model.
    assert not all(plan.fits for plan in plans)
    assert any("Overflow" in problem for problem in plans[7].blockers)
    assert [
        plan.variant
        for plan in plan_variants(config, items, "full", 10, 2000)
        if "base_model" in plan.items
    ] == config.variants.offline_ai


def test_start_grounding_uses_the_rendered_defaults_in_both_languages():
    config = load_config(ROOT)
    for language in ("en", "es"):
        text = start_text(ROOT, language, config, 946684800)
        assert config.defaults.mesh.channels.block in text
        if language == "en":
            assert config.defaults.radio.listen_window in text
        assert "12:00" in text


def test_prompt_preserves_complete_short_start_and_labels_oversized_start():
    settings = settings_for(ROOT)
    source = "# Medical basics\nComplete synthetic protocol.\n# Communications\nRead the card.\n"
    prompt, grounding = system_prompt(ROOT, settings, "en", source)
    assert source in prompt and grounding["mode"] == "full"
    assert settings.warning in prompt
    oversized = "# Medical basics\n" + "Do not truncate this protocol. " * 2000
    prompt, grounding = system_prompt(ROOT, settings, "es", oversized)
    assert grounding["mode"] == "section_index"
    assert "Medical basics" in prompt and "Do not truncate this protocol." not in prompt
    assert "NOT supplied" in prompt and "Do not reconstruct missing instructions" in prompt
    assert settings.warning_es in prompt and "solo los títulos" in grounding["notice"]
    assert (
        len(prompt.encode())
        + settings.max_output_tokens
        + settings.context_reserve_tokens
        + 2 * settings.message_reserve_tokens
        < settings.context_tokens
    )


def test_an_oversized_section_index_is_rejected_instead_of_truncated():
    settings = settings_for(ROOT)
    with pytest.raises(ValueError, match="section index exceeds"):
        system_prompt(ROOT, settings, "en", "# " + "Huge title " * 4000)


def test_android_context_is_distinct_and_preserves_the_complete_index():
    laptop = settings_for(ROOT)
    android = android_prompt_settings(laptop)
    assert laptop.context_tokens == 32768
    assert android.context_tokens == laptop.android.context_tokens == 16384
    assert android.warning == laptop.warning and android.warning_es == laptop.warning_es
    config = load_config(ROOT)
    for language in ("en", "es"):
        source = start_text(ROOT, language, config, 946684800)
        prompt, grounding = system_prompt(ROOT, android, language, source, section_index_only=True)
        assert grounding["mode"] == "section_index"
        assert grounding["start_bytes"] == len(source.encode())
        assert grounding["prompt_bytes"] == len(prompt.encode())
        assert grounding["prompt_bytes"] <= grounding["prompt_byte_budget"]
        assert all(line[2:] in prompt for line in source.splitlines() if line.startswith("# "))
        assert "NOT supplied" in prompt and "Do not reconstruct missing instructions" in prompt
        assert (android.warning if language == "en" else android.warning_es) in prompt
    with pytest.raises(ValidationError):
        LocalLLM.model_validate({**laptop.model_dump(), "context_tokens": android.context_tokens})


def test_development_android_selection_preserves_historical_sources_and_bundle_linkage():
    items = load_catalog(ROOT)
    settings = settings_for(ROOT)
    selected = items[settings.android.apk_id]
    assert selected.placement == "hub_only"
    assert not load_config(ROOT).variants.offline_ai_enabled
    assert selected.dest == f"9_LOCAL_LLM/android/{settings.android.apk_filename}"
    assert selected.source_id == "offlinellm_android_candidate_source"
    assert "[[VERIFY:" in selected.review
    historical = items["pocketpal_android"]
    assert historical.placement == "hub_only"
    assert historical.source_id == "pocketpal_android_source"
    assert items[historical.source_id].inputs
    for identifier in ("local_llm_full", "local_llm_sample"):
        item = items[identifier]
        assert settings.android.apk_id in item.inputs
        assert {"offlinellm_app_license", "offlinellm_native_license"} <= set(item.inputs)
        assert "pocketpal_license" not in item.inputs


def test_android_howtos_reference_the_android_prompts_and_exact_controls():
    from ck.render import render_html

    config = load_config(ROOT)
    for code in ("en", "es"):
        edition = next(item for item in config.languages if item.code == code)
        html = render_html(
            ROOT, config, ROOT / f"content/{code}/local-llm.md", edition, "phone", 946684800
        )
        assert "PocketPal" not in html
        for label in (
            "Import GGUF Model",
            "GPU Acceleration (Vulkan)",
            "CPU Threads",
            "Context Size",
            "Max Tokens",
            "Custom System Prompt",
            "New Chat",
        ):
            assert label in html
        assert str(config.local_llm.android.context_tokens) in html
        assert config.local_llm.android.apk_filename in html
        assert "android → system-en.txt" in html
        assert (config.local_llm.warning if code == "en" else config.local_llm.warning_es) in html
        if code == "es":
            assert "Traducción automática sin revisar." in html


def make_launcher(drive: Path, settings):
    drive.mkdir()
    (drive / "WARNING.TXT").write_text(settings.warning)
    script = (
        Environment(loader=FileSystemLoader(ROOT / "pipelines/llm"))
        .get_template("launch.sh.j2")
        .render(**settings.model_dump())
    )
    (drive / "launch.sh").write_text(script)


def test_launcher_uses_writable_temp_and_preserves_a_read_only_drive(tmp_path):
    settings = settings_for(ROOT)
    drive = tmp_path / "test drive café"
    make_launcher(drive, settings)
    (drive / settings.model_filename).write_bytes(b"Synthetic model, never shipped")
    runner = drive / settings.runner_filename
    raw = (
        '#!/bin/sh\nprintf "%s\\0" "$@" > "$CK_TEST_CAPTURE.tmp"\n'
        'mv "$CK_TEST_CAPTURE.tmp" "$CK_TEST_CAPTURE"\n'
        f'printf "listening on http://{settings.host}:{settings.port}\\n"\n'
        "trap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n"
    ).encode()
    runner.write_bytes(raw)
    runner.chmod(0o444)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    capture = tmp_path / "arguments"
    process = subprocess.Popen(
        ["/bin/sh", str(drive / "launch.sh")],
        cwd=tmp_path,
        env={
            **os.environ,
            "CK_NO_BROWSER": "1",
            "CK_TEST_CAPTURE": str(capture),
            "TMPDIR": str(runtime),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while not capture.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(0.05)
        assert capture.exists(), process.communicate(timeout=5)
        arguments = capture.read_bytes().decode().split("\0")
        assert arguments[arguments.index("--host") + 1] == "127.0.0.1"
        assert arguments[arguments.index("--model") + 1] == str(drive / settings.model_filename)
        assert "--offline" in arguments and "--no-context-shift" in arguments
    finally:
        process.terminate()
        process.communicate(timeout=10)
    assert runner.read_bytes() == raw and runner.stat().st_mode & 0o777 == 0o444
    assert list(runtime.iterdir()) == []


def test_missing_model_does_not_start_a_runner_or_browser(tmp_path):
    drive = tmp_path / "drive"
    make_launcher(drive, settings_for(ROOT))
    result = subprocess.run(["/bin/sh", str(drive / "launch.sh")], capture_output=True, text=True)
    assert result.returncode == 1 and "model is not on this drive" in result.stdout
