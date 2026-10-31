"""Catalog validation, explicit readiness checks and attribution generation."""

import re
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from ck.config import Configuration, Identifier, Marker, Model, Text, read_yaml

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Https = Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$")]
ProfileName = Literal["dev", "sample", "full"]


def safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(part in {".", ".."} for part in value.split("/")):
        raise ValueError(f"Unsafe relative path: {value!r}")
    if len(value.encode("utf-16-le")) // 2 >= 200 or re.search(r'[\\:*?"<>|\x00-\x1f]', value):
        raise ValueError(f"Path is not FAT-safe: {value!r}")
    for part in path.parts:
        if part.endswith((".", " ")) or part.split(".")[0].upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            raise ValueError(f"Reserved FAT/Windows name: {part!r}")
        if part.casefold() == "autorun.inf":
            raise ValueError("autorun.inf is forbidden")
    return path


class Topics(Model):
    topics: list[Identifier] = Field(min_length=1)


class Collection(Model):
    collection: Identifier


class Item(Model):
    id: Identifier
    family: Literal[
        "zim",
        "apk",
        "binaries",
        "fonts",
        "maps",
        "geodata",
        "llm",
        "video",
        "docs",
        "phrasebooks",
        "generated",
    ]
    title: Text
    url: Https | Marker | None = None
    version: Text
    size_bytes: Annotated[int, Field(gt=0)] | Marker
    sha256: Sha256 | Marker
    license: Text
    attribution: Text
    license_proof_url: Https | Marker
    placement: Literal["universal", "hub_only"] | Topics | Collection
    dest: Text
    profiles: list[ProfileName] = Field(min_length=1)
    inputs: list[Identifier] = Field(default_factory=list)
    pipeline_version: Text | None = None
    signer_cert_sha256: Sha256 | Marker | None = None
    source_url: Https | Marker | None = None
    source_id: Identifier | None = None
    source_for: Identifier | None = None
    checksum_source_url: Https | Marker | None = None
    publisher_blake3: Sha256 | Marker | None = None
    review: Text | None = None
    requires_legal: bool = False
    permission_proof_url: Https | Marker | None = None
    legal_reviewer: Text | None = None
    legal_reviewed_on: Text | None = None

    @model_validator(mode="after")
    def structure(self) -> Self:
        safe_path(self.dest.rstrip("/"))
        if self.family == "generated":
            if self.url is not None or not self.inputs or self.pipeline_version is None:
                raise ValueError("Generated items need inputs and pipeline_version, not a URL")
        elif self.url is None:
            raise ValueError("Downloaded items need a URL or an explicit VERIFY marker")
        if self.family == "apk" and (self.signer_cert_sha256 is None or self.source_url is None):
            raise ValueError("APK entries need signer_cert_sha256 and source_url")
        if len(set(self.profiles)) != len(self.profiles):
            raise ValueError("Duplicate catalog profiles")
        return self

    def blockers(self, *, release: bool = False) -> list[str]:
        problems = []
        for key, value in self.model_dump().items():
            if isinstance(value, str) and "[[VERIFY" in value:
                problems.append(f"{self.id}.{key}: {value}")
        licenses = self.license.split(" AND ")
        if not set(licenses) <= {
            "CC-BY-4.0",
            "CC-BY-SA-4.0",
            "CC-BY-SA-3.0",
            "CC0-1.0",
            "OFL-1.1",
            "MIT",
            "ISC",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "GPL-3.0-only",
            "GPL-3.0-or-later",
            "GPL-2.0-only",
            "ODbL-1.0",
            "US-PD",
            "Public-domain-US",
            "CC-BY-NC-SA-3.0",
        }:
            problems.append(f"{self.id}: license needs redistribution review: {self.license}")
        if "-NC-" in self.license and (
            not self.permission_proof_url or "[[VERIFY" in self.permission_proof_url
        ):
            problems.append(
                f"{self.id}: noncommercial material requires a written emergency-use license"
            )
        if "-NC-" in self.license and not self.requires_legal:
            problems.append(f"{self.id}: a named human must review the written license grant")
        if self.requires_legal and not (self.legal_reviewer and self.legal_reviewed_on):
            problems.append(f"{self.id}: named legal sign-off is missing")
        if self.family == "apk" and self.signer_cert_sha256 is None:
            problems.append(f"{self.id}: APK signer is missing")
        if (
            release
            and any(license.startswith("GPL-") for license in licenses)
            and self.family in {"apk", "binaries"}
            and self.placement != "hub_only"
        ):
            if not self.source_id:
                problems.append(f"{self.id}: corresponding source archive catalog entry is missing")
        return problems


def load_catalog(root: Path, config: Configuration | None = None) -> dict[str, Item]:
    result = {}
    for path in sorted((root / "catalog").glob("*.yaml")):
        if path.name == "medpdf_topics.yaml":
            continue
        data = read_yaml(path)
        if not isinstance(data, list):
            raise ValueError(f"Catalog family must be a list: {path}")
        for raw in data:
            item = Item.model_validate(raw)
            if item.id in result:
                raise ValueError(f"Duplicate catalog id: {item.id}")
            result[item.id] = item
    for item in result.values():
        if any(identifier not in result for identifier in item.inputs):
            raise ValueError(f"{item.id}: unknown generated-item input")
        if item.source_id and item.source_id not in result:
            raise ValueError(f"{item.id}: corresponding source id does not exist")
        if item.source_id:
            source = result[item.source_id]
            if source.source_for != item.id or source.url != item.source_url:
                raise ValueError(f"{item.id}: source archive is not explicitly tied to this app")
        if config:
            if isinstance(item.placement, Topics):
                if not set(item.placement.topics) <= config.variants.topics.keys():
                    raise ValueError(f"{item.id}: unknown topic placement")
            elif (
                isinstance(item.placement, Collection)
                and item.placement.collection not in config.variants.collections
            ):
                raise ValueError(f"{item.id}: unknown collection placement")
    if config and config.local_llm:
        for profile, identifier in config.local_llm.models.items():
            if identifier not in result or profile not in result[identifier].profiles:
                raise ValueError(f"Missing local LLM model selection for {profile}: {identifier}")
    # Input graphs must be acyclic, including references that are not yet fetched.
    active, visited = set(), set()

    def visit(identifier):
        if identifier in active:
            raise ValueError(f"Catalog input cycle at {identifier}")
        if identifier in visited:
            return
        active.add(identifier)
        for dependency in result[identifier].inputs:
            visit(dependency)
        active.remove(identifier)
        visited.add(identifier)

    for identifier in result:
        visit(identifier)
    return result


def attributions(items: dict[str, Item], target: Path) -> None:
    lines = [
        "# Third-party materials",
        "",
        "Generated from catalog/; do not edit by hand.",
        "",
        "VERIFY entries are candidates and cannot be placed until confirmed.",
        "",
    ]
    for item in sorted(items.values(), key=lambda item: item.id):
        lines += [
            f"## {item.title}",
            "",
            f"- Catalog id: `{item.id}`",
            f"- Version: {item.version}",
            f"- License: {item.license}",
            f"- Attribution: {item.attribution}",
            f"- License proof: {item.license_proof_url}",
            f"- Size: {item.size_bytes} bytes",
            f"- SHA-256: `{item.sha256}`",
        ]
        if item.url:
            lines.append(f"- Publisher file: {item.url}")
        else:
            lines.append(f"- Pipeline: {item.pipeline_version}; inputs: {', '.join(item.inputs)}")
        lines.append("")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
