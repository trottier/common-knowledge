"""The example builder must not overwrite cargo or bypass its input pins."""

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/prepare_mobile_examples.py"


def arguments(tmp_path, receipt_name):
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    prototype = prepared / "prototype.json"
    prototype.write_text(json.dumps({"recomposition": {}, "fonts": [], "files": []}))
    output = tmp_path / "examples"
    return [
        str(SCRIPT),
        "--prepared",
        str(prepared),
        "--prototype-sha256",
        hashlib.sha256(prototype.read_bytes()).hexdigest(),
        "--cache",
        str(tmp_path),
        "--output",
        str(output),
        "--receipt",
        str(output / receipt_name),
    ], output


@pytest.mark.parametrize("receipt_name", ["README.TXT", "receipt.json", "maps/sample.pdf"])
def test_receipts_cannot_overwrite_an_example_file(tmp_path, monkeypatch, receipt_name):
    argv, output = arguments(tmp_path, receipt_name)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="outside the prepared maps and examples"):
        runpy.run_path(str(SCRIPT))["main"]()
    assert not output.exists()


def test_input_pins_remain_enforced_when_python_optimization_is_enabled(tmp_path):
    argv, output = arguments(tmp_path, "unused")
    argv[-1] = str(tmp_path / "receipt.json")
    prepared = tmp_path / "prepared"
    source = prepared / "0_OVERVIEW.pdf"
    source.write_bytes(b"Changed synthetic source")
    prototype = prepared / "prototype.json"
    prototype.write_text(
        json.dumps(
            {
                "recomposition": {},
                "fonts": [],
                "files": [
                    {
                        "path": source.name,
                        "size_bytes": source.stat().st_size,
                        "sha256": "a" * 64,
                    }
                ],
            }
        )
    )
    argv[argv.index("--prototype-sha256") + 1] = hashlib.sha256(prototype.read_bytes()).hexdigest()
    result = subprocess.run([sys.executable, "-O", *argv], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Prepared map bytes differ" in result.stderr
    assert not output.exists() and not (tmp_path / "receipt.json").exists()
