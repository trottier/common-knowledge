"""Exercise the installed CLI from outside the source tree."""

import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest


@pytest.fixture(params=["script", "module"])
def command(request: pytest.FixtureRequest) -> list[str]:
    if request.param == "module":
        return [sys.executable, "-m", "ck"]
    return [str(Path(sys.executable).with_name("ck"))]


@pytest.mark.parametrize("args", [[], ["--help"]])
def test_help(command: list[str], args: list[str], tmp_path: Path) -> None:
    result = subprocess.run(
        command + args, cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert "usage: ck" in result.stdout
    assert "--version" in result.stdout
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_version(command: list[str], tmp_path: Path) -> None:
    result = subprocess.run(
        command + ["--version"], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert result.stdout == f"ck {version('common-knowledge')}\n"
    assert result.stderr == ""


@pytest.mark.parametrize("args", [["--unknown"], ["not-a-command"]])
def test_unsupported_arguments_fail(command: list[str], args: list[str], tmp_path: Path) -> None:
    result = subprocess.run(
        command + args, cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode == 2
    assert "error:" in result.stderr
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []
