"""Compose source editions, cards, tags and the variant guide."""

import json
from pathlib import Path

import yaml

from ck.config import Configuration
from ck.render import content_file, render_pdf


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
) -> list[Path]:
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
            files.append(render_pdf(root, config, bundle, language, page_format, target, epoch))
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
                    )
                )
    if not files:
        raise ValueError("No requested language edition exists")
    (output / "core-files.json").write_text(
        json.dumps([str(path.relative_to(output)) for path in files], indent=2) + "\n"
    )
    return files
