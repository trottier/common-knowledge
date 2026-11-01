"""Absent features stay out of the plain-text development inventory too."""

from pathlib import Path

from ck.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_plain_text_plan_does_not_advertise_deferred_ai(tmp_path, monkeypatch, capsys):
    (tmp_path / "core-manifest.json").write_text('{"epoch": 946684800}')
    monkeypatch.setattr("ck.core.verify_core", lambda *args: None)
    monkeypatch.setattr("ck.assemble.core_size", lambda *args: 100)
    monkeypatch.setattr("ck.catalog.load_catalog", lambda *args: {})
    assert main(["--root", str(ROOT), "plan", "--profile", "sample", "--core", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "VARIANT" in output and "FITS" in output
    assert "LLM" not in output and "AI" not in output
