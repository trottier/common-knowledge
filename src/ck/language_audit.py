"""Audit edition ordering against pinned ACS limited-English-proficiency estimates."""

import csv
import json
import re
from pathlib import Path

from ck.catalog import load_catalog
from ck.config import Model, load_config, read_yaml
from ck.generated import cached_input


class Settings(Model):
    data_id: str
    labels_id: str
    language_variables: dict[str, str]


def lep_groups(data: Path, labels: Path) -> list[dict]:
    groups = []
    current_language = None
    universe = None
    with labels.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream, delimiter="|"):
            if row["Table ID"] != "B16001":
                continue
            universe = row["Universe"]
            if row["Indent"] == "1":
                current_language = row["Label"].removesuffix(":")
            if row["Label"] == 'Speak English less than "very well"':
                if not current_language or row["Indent"] != "2":
                    raise ValueError("ACS language hierarchy changed")
                identifier = row["Unique ID"]
                if not re.fullmatch(r"B16001_\d{3}", identifier):
                    raise ValueError("Unexpected ACS language variable")
                groups.append(
                    {"variable": identifier, "language": current_language, "universe": universe}
                )
    if not groups or len({group["variable"] for group in groups}) != len(groups):
        raise ValueError("ACS language labels are missing or duplicated")
    with data.open(encoding="utf-8-sig") as stream:
        rows = [
            row for row in csv.DictReader(stream, delimiter="|") if row["GEO_ID"] == "0100000US"
        ]
    if len(rows) != 1:
        raise ValueError("Expected exactly one United States ACS estimate row")
    for group in groups:
        suffix = group["variable"].split("_")[1]
        value = rows[0]["B16001_E" + suffix]
        margin = rows[0]["B16001_M" + suffix]
        if not value.isdigit() or not margin.isdigit():
            raise ValueError("ACS estimates or margins are missing, suppressed or invalid")
        group.update(estimate=int(value), margin_of_error=int(margin))
    return sorted(groups, key=lambda group: (-group["estimate"], group["variable"]))


def audit_languages(root: Path, cache: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Language audit output must be new")
    config = load_config(root)
    items = load_catalog(root, config)
    settings = Settings.model_validate(read_yaml(root / "pipelines/languages/settings.yaml"))
    groups = lep_groups(
        cached_input(items[settings.data_id], cache), cached_input(items[settings.labels_id], cache)
    )
    variables = {group["variable"]: group for group in groups}
    codes = [language.code for language in config.languages]
    if set(settings.language_variables) != set(codes) - {"en"}:
        raise ValueError("Every non-English edition needs an explicit ACS language-group mapping")
    if not set(settings.language_variables.values()) <= variables.keys():
        raise ValueError("An edition mapping is not a limited-English-proficiency variable")
    selected = [
        {"code": code, **variables[settings.language_variables[code]]}
        for code in codes
        if code != "en"
    ]
    expected = ["en", *[row["code"] for row in sorted(selected, key=lambda row: -row["estimate"])]]
    result = {
        "inputs": {
            identifier: items[identifier].sha256
            for identifier in (settings.data_id, settings.labels_id)
        },
        "groups": groups,
        "selected_editions": selected,
        "current_order": codes,
        "selected_editions_in_estimate_order": expected,
        "order_matches": codes == expected,
        "limitation": (
            "ACS B16001 combines some languages. It cannot establish a complete "
            "individual-language ranking or a separate count for Chinese writing systems. "
            "Estimates have sampling margins of error. This report does not approve the "
            "edition selection."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return result
