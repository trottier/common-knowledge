"""Pinned font coverage for geographic source names; never replace source text."""

import unicodedata
from pathlib import Path

from ck.catalog import Item
from ck.config import Identifier, Model, read_yaml
from ck.generated import cached_input


class Settings(Model):
    fonts: list[Identifier]


def font_ids(root: Path) -> list[str]:
    selected = Settings.model_validate(read_yaml(root / "pipelines/geodata-fonts.yaml")).fonts
    if not selected or selected[0] != "noto_sans" or len(set(selected)) != len(selected):
        raise ValueError("Geographic fonts need Noto Sans first and distinct catalog IDs")
    return selected


def font_records(root: Path, items: dict[str, Item], cache: Path) -> list[dict]:
    result = []
    for identifier in font_ids(root):
        item = items[identifier]
        if item.family != "fonts":
            raise ValueError("Geographic font policy references a non-font item")
        result.append(
            {
                "id": identifier,
                "path": str(cached_input(item, cache).resolve()),
                "sha256": item.sha256,
            }
        )
    return result


def require_glyphs(texts, paths: list[Path]) -> None:
    from fontTools.ttLib import TTFont

    supported = set()
    for path in paths:
        with TTFont(path) as font:
            supported.update(font.getBestCmap())
    missing = set()
    for text in texts:
        missing.update(
            ord(character)
            for character in text
            if not character.isspace()
            and unicodedata.category(character) not in {"Cc", "Cf"}
            and ord(character) not in supported
        )
    if missing:
        labels = [
            f"U+{value:04X} {unicodedata.name(chr(value), 'unnamed')}" for value in sorted(missing)
        ]
        raise ValueError(
            "Geographic source text needs additional pinned font coverage: " + ", ".join(labels)
        )
