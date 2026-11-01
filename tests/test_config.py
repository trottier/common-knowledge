from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.config import Configuration, PDFBudget, findability, load_config, read_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_configuration_and_unconfirmed_production_capacity():
    config = load_config(ROOT)
    assert config.build.profiles["dev"].usable_bytes() == 256 * 1024 * 1024
    assert config.build.profiles["sample"].usable_bytes() == 4096 * 1024 * 1024
    with pytest.raises(ValueError, match="unconfirmed"):
        config.build.profiles["full"].usable_bytes()


def test_pdf_budget_uses_decimal_megabytes_and_has_no_model_defaults():
    budget = load_config(ROOT).build.pdf
    assert budget.max_file_bytes == budget.max_file_mb * 1_000_000
    assert PDFBudget(max_file_mb=3, target_phone_coverage=1).max_file_bytes == 3_000_000
    with pytest.raises(ValidationError):
        PDFBudget.model_validate({})


@pytest.mark.parametrize(
    "budget",
    [
        {"max_file_mb": 0, "target_phone_coverage": 0.5},
        {"max_file_mb": -1, "target_phone_coverage": 0.5},
        {"max_file_mb": 1.5, "target_phone_coverage": 0.5},
        {"max_file_mb": True, "target_phone_coverage": 0.5},
        {"max_file_mb": 1, "target_phone_coverage": 0},
        {"max_file_mb": 1, "target_phone_coverage": 1.01},
        {"max_file_mb": 1, "target_phone_coverage": float("nan")},
    ],
)
def test_invalid_pdf_budget_is_rejected(budget):
    data = deepcopy(load_config(ROOT).model_dump())
    data["build"]["pdf"] = budget
    with pytest.raises(ValidationError):
        Configuration.model_validate(data)


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


def test_offline_ai_is_explicitly_deferred_with_a_configured_future_allocation():
    config = load_config(ROOT)
    assert config.variants.offline_ai == [7, 8]
    assert config.variants.offline_ai_enabled is False


@pytest.mark.parametrize("allocation", [[], [7], [7, 7], [0, 8], [7, 9], [True, 8]])
def test_invalid_future_ai_allocation_is_rejected(allocation):
    data = deepcopy(load_config(ROOT).model_dump())
    data["variants"]["offline_ai"] = allocation
    with pytest.raises(ValidationError):
        Configuration.model_validate(data)


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
