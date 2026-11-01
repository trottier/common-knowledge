"""Current drives exclude deferred research while preserving future allocation."""

from pathlib import Path

from ck.catalog import load_catalog
from ck.config import load_config
from ck.planner import plan_variants
from ck.preparation import preparation_plan
from ck.render import render_html

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


def test_future_notes_read_configuration_without_launch_or_folder_claims(monkeypatch):
    # HTML generation needs font URLs, but this text-only check reads no font bytes.
    monkeypatch.setattr("ck.render.font_files", lambda *args: [Path("/synthetic-font")])
    config = load_config(ROOT)
    for code, conjunction in (("en", " and "), ("es", " y ")):
        edition = next(edition for edition in config.languages if edition.code == code)
        allocation = conjunction.join(map(str, config.variants.offline_ai))
        for relative in ("start/10-local-llm.md", "start/11-variants.md", "card.md"):
            html = render_html(
                ROOT,
                config,
                ROOT / "content" / code / relative,
                edition,
                "phone",
                946684800,
                template="card.html.j2" if relative == "card.md" else "document.html.j2",
            )
            assert allocation in html
            assert "deferred" in html if code == "en" else "aplazada" in html
            if relative == "start/10-local-llm.md":
                assert "9_LOCAL_LLM" not in html and "9_OFFLINE_AI" not in html
                assert "Model.gguf" not in html and "Start Local LLM" not in html
                assert "LLM" not in html and "language model" not in html
