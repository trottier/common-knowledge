"""Current drives exclude deferred research while preserving future allocation."""

from pathlib import Path

from ck.catalog import load_catalog
from ck.config import load_config
from ck.core import bundle_sections
from ck.planner import plan_variants
from ck.preparation import preparation_plan
from ck.render import content_file, render_html, verify_translation_inputs

ROOT = Path(__file__).resolve().parents[1]


def test_current_sample_and_full_variants_have_no_ai_items_or_folders():
    config = load_config(ROOT)
    items = load_catalog(ROOT, config)
    deferred = {
        identifier
        for identifier, item in items.items()
        if item.family == "llm" or item.dest.startswith(("9_LOCAL_LLM/", "9_OFFLINE_AI/"))
    }
    assert deferred == {
        "base_model",
        "sample_model",
        "local_llm_full",
        "local_llm_sample",
        "offlinellm_android_candidate",
    }
    assert all(items[identifier].placement == "hub_only" for identifier in deferred)
    for profile in ("sample", "full"):
        for plan in plan_variants(config, items, profile, 0, 32_000_000_000):
            assert not deferred.intersection(plan.items)
            assert "llm_variants" not in plan.as_dict()
            assert "llm_reason" not in plan.as_dict()
            assert not any(
                items[key].dest.startswith(("9_LOCAL_LLM/", "9_OFFLINE_AI/")) for key in plan.items
            )
    plan = preparation_plan(ROOT, "sample", variants=[1])
    closure = (
        set(plan["selected"]) | set(plan["downloads"]) | {task["id"] for task in plan["tasks"]}
    )
    assert not closure.intersection(
        deferred
        | {
            "llamafile_runner",
            "llamafile_license",
            "llamafile_llama_notices",
            "offlinellm_app_license",
            "offlinellm_native_license",
            "qwen_sample_license",
            "qwen_full_license",
        }
    )
    assert "wikem_en_nopic" in plan["selected"]


def test_current_core_omits_future_section_and_absent_feature_notices(monkeypatch, tmp_path):
    # HTML generation needs font URLs, but this text-only check reads no font bytes.
    monkeypatch.setattr("ck.render.font_files", lambda *args: [Path("/synthetic-font")])
    config = load_config(ROOT)
    for code in ("en", "es"):
        edition = next(edition for edition in config.languages if edition.code == code)
        source_dir = ROOT / "content" / code
        bundle = tmp_path / code / "START.md"
        sections = sorted((source_dir / "start").glob("*.md"))
        assert len(sections) == 12
        assert not any(path.name.startswith("10-") for path in sections)
        bundle_sections(sections, bundle)
        for source in (bundle, source_dir / "start/11-variants.md", source_dir / "card.md"):
            html = render_html(
                ROOT,
                config,
                source,
                edition,
                "phone",
                946684800,
                template="card.html.j2" if source.name == "card.md" else "document.html.j2",
                profile="sample",
            )
            for forbidden in (
                "Offline AI",
                "offline AI",
                "local LLM",
                "language model",
                "IA sin conexión",
                "9_LOCAL_LLM",
                "9_OFFLINE_AI",
                "Model.gguf",
            ):
                assert forbidden not in html
        future = source_dir / "future/10-offline-ai.md"
        assert future.exists()
        header, _ = content_file(future)
        verify_translation_inputs(ROOT, header)
