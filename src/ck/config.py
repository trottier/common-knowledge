"""Strict, shared configuration and YAML loading."""

import math
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(min_length=1)]
Marker = Annotated[str, StringConstraints(pattern=r"^\[\[VERIFY(?::[^\n]+)?\]\]$")]
ClockTime = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject ambiguous YAML instead of silently accepting the last key."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"Duplicate YAML key {key!r} at {key_node.start_mark}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def read_yaml(path: Path):
    with path.open(encoding="utf-8") as stream:
        try:
            return yaml.load(stream, Loader=UniqueKeyLoader)
        except (yaml.YAMLError, TypeError) as error:
            raise ValueError(f"Invalid YAML in {path}: {error}") from error


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class RallyPoint(Model):
    rule: list[Text] = Field(min_length=1)


class Meetings(Model):
    times_local: list[ClockTime] = Field(min_length=2, max_length=2)
    if_nobody_there: Text


class Convener(Model):
    rule: Text
    rotation: Text
    role_fallback: Text


class Radio(Model):
    service: Literal["FRS"]
    channel: int = Field(ge=1, le=22)
    frequency_mhz: float = Field(gt=0)
    privacy_code: Literal["none"]
    listen_window: Text


class MeshChannels(Model):
    block: Text
    help: Text


class MeshFormats(Model):
    help: Text
    ok: Text


class Mesh(Model):
    app: Text
    channels: MeshChannels
    formats: MeshFormats
    schedule: Text


class BlockDay(Model):
    date: Text
    time_local: ClockTime


class Defaults(Model):
    rally_point: RallyPoint
    meetings: Meetings
    convener: Convener
    radio: Radio
    mesh: Mesh
    block_day: BlockDay


class Module(Model):
    category: Literal["body", "infra", "civic"]
    title: Text


class Variant(Model):
    modules: list[Identifier] = Field(min_length=3, max_length=3)
    shelf: Identifier


class Variants(Model):
    modules: dict[Identifier, Module]
    shelves: dict[Identifier, Text]
    variants: dict[int, Variant]

    @model_validator(mode="after")
    def check_coverage(self) -> Self:
        if set(self.variants) != set(range(1, 9)):
            raise ValueError("Exactly variants 1 through 8 are required")
        if len(self.modules) != 12 or len(self.shelves) != 8:
            raise ValueError("Exactly 12 modules and 8 shelves are required")
        module_counts: Counter = Counter()
        shelf_counts: Counter = Counter()
        for number, variant in self.variants.items():
            if len(set(variant.modules)) != 3 or not set(variant.modules) <= self.modules.keys():
                raise ValueError(f"Variant {number} has duplicate or unknown modules")
            categories = Counter(self.modules[m].category for m in variant.modules)
            if categories != Counter(body=1, infra=1, civic=1):
                raise ValueError(f"Variant {number} must have one module from each category")
            if variant.shelf not in self.shelves:
                raise ValueError(f"Variant {number} has an unknown shelf")
            module_counts.update(variant.modules)
            shelf_counts.update([variant.shelf])
        if module_counts != Counter({key: 2 for key in self.modules}):
            raise ValueError("Each module must appear on exactly two variants")
        if shelf_counts != Counter({key: 1 for key in self.shelves}):
            raise ValueError("Each shelf must appear on exactly one variant")
        return self


class Language(Model):
    code: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}(?:-[A-Za-z]+)?$")]
    name: Text
    script: Annotated[str, StringConstraints(pattern=r"^[A-Z][a-z]{3}$")]
    dir: Literal["ltr", "rtl"]
    font: Identifier
    status: Literal["full", "machine", "stub"]


class Profile(Model):
    third_party: Literal["none", "sample", "all"]
    image_size_mib: int | None = Field(default=None, ge=1)
    capacity_bytes: Annotated[int, Field(gt=0)] | Marker | None = None
    reserve_fraction: float = Field(default=0.0, ge=0, lt=1)

    @model_validator(mode="after")
    def check_capacity(self) -> Self:
        if (self.image_size_mib is None) == (self.capacity_bytes is None):
            raise ValueError("Specify exactly one of image_size_mib or capacity_bytes")
        return self

    def usable_bytes(self) -> int:
        capacity = self.capacity_bytes
        if self.image_size_mib is not None:
            capacity = self.image_size_mib * 1024 * 1024
        if not isinstance(capacity, int):
            raise ValueError(f"Production capacity is unconfirmed: {capacity}")
        return math.floor(capacity * (1 - self.reserve_fraction))


class Build(Model):
    version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
    volume_label: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]{1,11}$")]
    volume_id: Annotated[str, StringConstraints(pattern=r"^[0-9A-F]{8}$")]
    site_base_url: Text
    source_date_epoch: Annotated[int, Field(ge=315532800)] | Marker
    profiles: dict[Literal["dev", "sample", "full"], Profile]

    @model_validator(mode="after")
    def all_profiles(self) -> Self:
        if set(self.profiles) != {"dev", "sample", "full"}:
            raise ValueError("dev, sample and full profiles are required")
        return self


class Configuration(Model):
    defaults: Defaults
    variants: Variants
    languages: list[Language]
    build: Build

    @model_validator(mode="after")
    def editions(self) -> Self:
        codes = [language.code for language in self.languages]
        if len(codes) != 15 or len(set(codes)) != 15:
            raise ValueError("Exactly 15 unique language editions are required")
        statuses = {language.code: language.status for language in self.languages}
        if statuses.get("en") != "full" or statuses.get("es") != "machine":
            raise ValueError("English must be full and Spanish must be machine-translated")
        if any(status != "stub" for code, status in statuses.items() if code not in {"en", "es"}):
            raise ValueError("The other thirteen editions must be stubs in v0.1")
        return self


def load_config(root: Path) -> Configuration:
    data = {
        name: read_yaml(root / "config" / f"{name}.yaml")
        for name in ("defaults", "variants", "languages", "build")
    }
    return Configuration.model_validate(data)


def findability(carriers: int, homes: int) -> float:
    """Chance at least one of n independent shuffled drives carries an item."""
    if type(carriers) is not int or not 0 <= carriers <= 8:
        raise ValueError("carriers must be an integer from 0 through 8")
    if type(homes) is not int or homes < 0:
        raise ValueError("homes must be a nonnegative integer")
    if homes == 0 or carriers == 0:
        return 0.0
    if carriers == 8:
        return 1.0
    return -math.expm1(homes * math.log1p(-carriers / 8))
