from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.config import Configuration, findability, load_config, read_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_configuration_and_unconfirmed_production_capacity():
    config = load_config(ROOT)
    assert config.build.profiles["dev"].usable_bytes() == 256 * 1024 * 1024
    assert config.build.profiles["sample"].usable_bytes() == 4096 * 1024 * 1024
    with pytest.raises(ValueError, match="unconfirmed"):
        config.build.profiles["full"].usable_bytes()


@pytest.mark.parametrize("mutation", ["category", "coverage", "collection", "unknown", "extra"])
def test_broken_invariants_rejected(mutation):
    data = deepcopy(load_config(ROOT).model_dump())
    variants = data["variants"]["variants"]
    if mutation == "category":
        variants[1]["topics"] = ["medical", "care", "convening"]
    elif mutation == "coverage":
        variants[1]["topics"][0] = "care"
    elif mutation == "collection":
        variants[2]["collection"] = variants[1]["collection"]
    elif mutation == "unknown":
        variants[1]["topics"][0] = "missing"
    else:
        data["defaults"]["radio"]["telemetry"] = True
    with pytest.raises(ValidationError):
        Configuration.model_validate(data)


def test_duplicate_yaml_keys_rejected(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("channel: 3\nchannel: 4\n")
    with pytest.raises(ValueError, match="Duplicate"):
        read_yaml(path)


@pytest.mark.parametrize(
    ("k", "n", "expected"),
    [
        (0, 5, 0),
        (8, 0, 0),
        (8, 1, 1),
        (2, 5, 1 - 0.75**5),
        (4, 5, 0.96875),
    ],
)
def test_findability(k, n, expected):
    assert findability(k, n) == pytest.approx(expected)


@pytest.mark.parametrize(("k", "n"), [(-1, 5), (9, 5), (1, -1), (True, 3), (1, 2.5)])
def test_findability_invalid_input(k, n):
    with pytest.raises(ValueError):
        findability(k, n)
