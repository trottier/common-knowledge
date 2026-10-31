"""Edition labels and translations tied to the canonical default's hash."""

import copy
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field

from ck.config import Configuration, Identifier, Language, Model, Text, read_yaml


class Edition(Model):
    status: Literal["draft", "machine", "reviewed"]
    reviewer: Text | None
    reviewed_on: Text | None
    translation_footer: str
    contents_label: Text
    sources_label: Text
    draft_label: Text
    readme: Text
    rally_labels: dict[Identifier, Text]
    qr_labels: list[Text] = Field(
        default_factory=lambda: ["Videos", "State agencies", "Verify drive"],
        min_length=3,
        max_length=3,
    )


def edition_for(root: Path, language: Language, config: Configuration) -> Edition:
    edition = Edition.model_validate(read_yaml(root / "content" / language.code / "edition.yaml"))
    if language.code != "en" and not edition.translation_footer:
        raise ValueError(f"Missing unreviewed-translation footer: {language.code}")
    if set(edition.rally_labels) != set(config.defaults.rally_point.rule):
        raise ValueError(f"Rally labels do not match the canonical rules: {language.code}")
    if any(character in edition.translation_footer for character in "<>\r\n"):
        raise ValueError("Translation footer must be plain single-line text")
    return edition


class Translation(Model):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: Text


class DefaultTranslations(Model):
    status: Literal["draft", "machine", "reviewed"]
    reviewer: Text | None
    reviewed_on: Text | None
    translations: dict[Text, Translation]


def display_defaults(root: Path, language: Language, config: Configuration) -> dict:
    result = copy.deepcopy(config.defaults.model_dump())
    path = root / "content" / language.code / "defaults.yaml"
    if path.exists():
        translations = DefaultTranslations.model_validate(read_yaml(path))
        for key, translation in translations.translations.items():
            parts = key.split(".")
            node = result
            for part in parts[:-1]:
                node = node[part]
            source = node[parts[-1]]
            if not isinstance(source, str):
                raise ValueError(f"Only text defaults may be translated: {key}")
            if hashlib.sha256(source.encode()).hexdigest() != translation.source_sha256:
                raise ValueError(f"Retranslate changed default {key} in {language.code}")
            node[parts[-1]] = translation.text
    if language.dir == "rtl":
        # Keep times, radio settings and channel names in their intended order.
        def isolate(value):
            return "\u2066" + str(value) + "\u2069"

        result["meetings"]["times_local"] = [
            isolate(value) for value in result["meetings"]["times_local"]
        ]
        for key in ("service", "channel", "frequency_mhz"):
            result["radio"][key] = isolate(result["radio"][key])
        result["mesh"]["app"] = isolate(result["mesh"]["app"])
        result["mesh"]["channels"] = {
            key: isolate(value) for key, value in result["mesh"]["channels"].items()
        }
    return result
