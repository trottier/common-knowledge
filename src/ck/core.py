"""Compose source editions, cards, tags and the variant guide."""

import hashlib
import json
from pathlib import Path

import yaml

from ck.config import Configuration
from ck.render import content_file, epoch_for, render_pdf


def recipe_fingerprint(root: Path, epoch: int, languages: list[str], profile: str) -> str:
    checksum = hashlib.sha256()
    for directory in ("content", "templates", "config", "catalog", "src/ck"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.suffix in {
                ".md",
                ".yaml",
                ".yml",
                ".j2",
                ".css",
                ".py",
                ".sources",
            }:
                checksum.update(path.relative_to(root).as_posix().encode() + b"\0")
                checksum.update(path.read_bytes())
    for name in ("Dockerfile.build", "pyproject.toml", "uv.lock"):
        checksum.update(name.encode() + b"\0" + (root / name).read_bytes())
    checksum.update(json.dumps([epoch, sorted(languages), profile]).encode())
    return checksum.hexdigest()


def write_core_manifest(
    root: Path, output: Path, epoch: int, languages: list[str], profile: str
) -> None:
    records = []
    for path in sorted(output.glob("*/*")):
        if path.suffix in {".pdf", ".html"}:
            records.append(
                {
                    "path": path.relative_to(output).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    data = {
        "epoch": epoch,
        "languages": sorted(languages),
        "profile": profile,
        "recipe_sha256": recipe_fingerprint(root, epoch, languages, profile),
        "files": records,
    }
    (output / "core-manifest.json").write_text(json.dumps(data, indent=2) + "\n")


def verify_core(root: Path, output: Path, epoch: int, profile: str) -> None:
    from ck.catalog import safe_path

    data = json.loads((output / "core-manifest.json").read_text())
    if data["epoch"] != epoch or data["profile"] != profile:
        raise ValueError("Core epoch or profile differs; rebuild the core")
    if data["recipe_sha256"] != recipe_fingerprint(root, epoch, data["languages"], profile):
        raise ValueError("Core inputs changed; rebuild the core")
    expected = set()
    for entry in data["files"]:
        relative = str(safe_path(entry["path"]))
        if relative in expected:
            raise ValueError("Duplicate core manifest path")
        expected.add(relative)
        path = output / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"Core output changed: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Core output changed: {relative}")
    actual = {
        path.relative_to(output).as_posix()
        for path in output.glob("*/*")
        if path.suffix in {".pdf", ".html"}
    }
    if actual != expected:
        raise ValueError("Core manifest does not cover the rendered outputs")


def bundle_sections(sources: list[Path], target: Path) -> None:
    if not sources:
        raise ValueError("No START sections found")
    headers, bodies = zip(*(content_file(path) for path in sources), strict=True)
    # Preserve approval only when every input records a human approval.
    approved = all(h.status == "reviewed" and h.reviewer and h.reviewed_on for h in headers)
    status = (
        "reviewed"
        if approved
        else ("machine" if all(h.status == "machine" for h in headers) else "draft")
    )
    metadata = {
        "title": "START — Common Knowledge",
        "status": status,
        "reviewer": "; ".join(sorted({h.reviewer for h in headers})) if approved else None,
        "reviewed_on": min(h.reviewed_on for h in headers) if approved else None,
        "review_required": sorted({tag for h in headers for tag in h.review_required}),
    }
    text = "---\n" + yaml.safe_dump(metadata, allow_unicode=True) + "---\n\n"
    for header, body in zip(headers, bodies, strict=True):
        text += f"# {header.title}\n\n{body}\n\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build_core(
    root: Path,
    config: Configuration,
    output: Path,
    epoch: int | None = None,
    languages: list[str] | None = None,
    profile: str = "dev",
) -> list[Path]:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Core output must be empty; choose a clean build directory")
    files = []
    unknown = set(languages or ["en"]) - {item.code for item in config.languages}
    if unknown:
        raise ValueError(f"Unknown requested editions: {sorted(unknown)}")
    for language in config.languages:
        if language.code not in (languages or ["en"]):
            continue
        destination = output / language.code
        source_dir = root / "content" / language.code
        bundle = destination / "START.md"
        sources = sorted((source_dir / "start").glob("*.md"))
        bundle_sections(sources, bundle)
        for page_format in ("phone", "print"):
            target = destination / f"01_START_{page_format}.pdf"
            files.append(
                render_pdf(
                    root, config, bundle, language, page_format, target, epoch, profile=profile
                )
            )
        for source_name, target_name, template in (
            ("card.md", "02_CARD.pdf", "card.html.j2"),
            ("tags.md", "03_TAGS.pdf", "tags.html.j2"),
        ):
            files.append(
                render_pdf(
                    root,
                    config,
                    source_dir / source_name,
                    language,
                    "print",
                    destination / target_name,
                    epoch,
                    template,
                    profile,
                )
            )
        why = source_dir / "start/11-variants.md"
        if why.exists():
            for page_format in ("phone", "print"):
                files.append(
                    render_pdf(
                        root,
                        config,
                        why,
                        language,
                        page_format,
                        destination / f"04_VARIANTS_{page_format}.pdf",
                        epoch,
                        profile=profile,
                    )
                )
    if not files:
        raise ValueError("No requested language edition exists")
    (output / "core-files.json").write_text(
        json.dumps([str(path.relative_to(output)) for path in files], indent=2) + "\n"
    )
    write_core_manifest(
        root,
        output,
        epoch_for(config, epoch),
        sorted({path.parent.name for path in files}),
        profile,
    )
    return files
