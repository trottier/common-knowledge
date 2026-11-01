"""The preview reads its shared label without preparing or building cargo."""

from pathlib import Path

from ck.cli import main
from ck.config import read_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_explorer_uses_the_configured_label_and_selected_tree(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ck.drive_preview.serve", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    assert main(["--root", str(ROOT), "explore", "--drive", str(tmp_path)]) == 0
    args, kwargs = calls[0]
    assert args == (tmp_path, ROOT / "pipelines/drive_preview")
    assert kwargs["label"] == read_yaml(ROOT / "config/build.yaml")["volume_label"]
