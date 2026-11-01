import os
import subprocess
import time
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError

from ck.catalog import Collection, Item
from ck.config import LocalLLM, load_config
from ck.llm import model_metadata, settings_for, start_text, system_prompt
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
        dest="9_LOCAL_LLM/fixture",
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


def test_model_fallback_preserves_four_copies_and_every_other_item():
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
    assert [plan.variant for plan in plans if "base_model" in plan.items] == [1, 3, 5, 7]
    assert all(plan.llm_variants == [1, 3, 5, 7] for plan in plans)
    assert all(
        {"national_atlas", "national_directory", "android_roads_places"} <= set(plan.items)
        for plan in plans
    )
    # Larger capacity keeps eight copies. Unknown sizes cannot trigger omission.
    assert all(
        "base_model" in plan.items for plan in plan_variants(config, items, "full", 10, 2000)
    )
    items["depth_howto_2"].size_bytes = "[[VERIFY: fixture size]]"
    plans = plan_variants(config, items, "full", 10, 1000)
    assert all("base_model" in plan.items for plan in plans)
    assert not all(plan.fits for plan in plans)


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
