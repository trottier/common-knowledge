"""Render unchanged original START sections as local draft quick-guide PDFs."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from pypdf import PdfReader

from ck.catalog import safe_path
from ck.config import load_config, read_yaml
from ck.core import recipe_fingerprint
from ck.fetch import digest
from ck.locales import edition_for
from ck.render import content_file, font_files, render_pdf

SECTIONS = (
    "02-first-hour.md",
    "03-shutoffs.md",
    "04-water.md",
    "05-neighbors.md",
    "09-medical.md",
    "10-computer-systems.md",
)
FOLDERS = {"en": "00_Quick guides", "es": "00_Guías rápidas"}


def filename(number: int, title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " - ", title)
    name = f"{number:02d}_" + " ".join(cleaned.split()).strip(" .") + ".pdf"
    safe_path(name)
    return name


def build_guides(root: Path, cache: Path, output: Path, epoch: int, source_commit: str) -> dict:
    if output.exists():
        raise ValueError("Choose a fresh quick-guide output; no overwrite")
    if Path(os.environ.get("CK_FONT_CACHE", root / "cache")).resolve() != cache.resolve():
        raise ValueError("CK_FONT_CACHE must identify the explicit verified cache")
    config = load_config(root)
    languages = [lang for lang in config.languages if lang.code in FOLDERS]
    fonts = {row["sha256"]: row for row in read_yaml(root / "catalog/fonts.yaml")}
    source_snapshot = recipe_fingerprint(root, epoch, [lang.code for lang in languages], "sample")
    helper = Path(__file__)
    result = {
        "status": "Draft quick guides from unchanged original sections; no content approval",
        "profile": "local-inspection",
        "source_commit": source_commit,
        "epoch": epoch,
        "render_source_snapshot_sha256": source_snapshot,
        "helper_sha256": digest(helper),
        "sections": [],
        "files": [],
        "tool_versions": {
            "weasyprint": importlib.metadata.version("weasyprint"),
            "pypdf": importlib.metadata.version("pypdf"),
        },
        "system_tool_versions": Path("/opt/ck-tool-versions.txt").read_text(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-quick-guides-", dir=output.parent) as temporary:
        stage = Path(temporary)
        for language in languages:
            footer = edition_for(root, language, config).translation_footer
            font_pins = []
            for font in font_files(root, language):
                pin = digest(font)
                item = fonts[pin]
                if font.is_symlink() or font.stat().st_size != item["size_bytes"]:
                    raise ValueError("Pinned font size changed")
                font_pins.append(
                    {"id": item["id"], "sha256": pin, "size_bytes": item["size_bytes"]}
                )
            for number, section in enumerate(SECTIONS, 1):
                source = root / "content" / language.code / "start" / section
                if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Unsafe original section path")
                header, body = content_file(source)
                name = filename(number, header.title)
                pdf = stage / "rendered" / language.code / name
                render_pdf(root, config, source, language, "phone", pdf, epoch, profile="sample")
                if pdf.stat().st_size > config.build.pdf.max_file_bytes:
                    raise ValueError("Quick guide exceeds shared PDF byte budget")
                reader = PdfReader(pdf)
                pages = []
                for n, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if footer and "".join(footer.split()) not in "".join(text.split()):
                        raise ValueError(
                            f"Translation footer missing: {language.code}/{section} page{n}"
                        )
                    pages.append(
                        {
                            "page": n,
                            "width_pt": float(page.mediabox.width),
                            "height_pt": float(page.mediabox.height),
                            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                            "opening_line": text.splitlines()[0] if text.splitlines() else "",
                        }
                    )
                entry = {
                    "language": language.code,
                    "title": header.title,
                    "status": header.status,
                    "reviewer": header.reviewer,
                    "reviewed_on": header.reviewed_on,
                    "translation_footer": footer,
                    "source_path": str(source.relative_to(root)),
                    "source_file_sha256": digest(source),
                    "source_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                    "source_input_bindings": header.source_inputs,
                    "fonts": font_pins,
                    "pdf_sha256": digest(pdf),
                    "size_bytes": pdf.stat().st_size,
                    "rendered_path": pdf.relative_to(stage).as_posix(),
                    "html_sha256": digest(pdf.with_suffix(".html")),
                    "pages": pages,
                    "destinations": [],
                }
                destinations = [
                    f"{prefix}/{language.name}/{FOLDERS[language.code]}/{name}"
                    for prefix in ("1_START", "4_PHONE_PACK")
                ]
                if section == "09-medical.md":
                    destinations.append(
                        "5_MEDICAL_REFERENCE/" + filename(0, header.title + " - " + language.name)
                    )
                for relative in destinations:
                    safe_path(relative)
                    target = stage / "files" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(pdf, target)
                    assert digest(target) == entry["pdf_sha256"]
                    result["files"].append(
                        {
                            "path": relative,
                            "sha256": digest(target),
                            "size_bytes": target.stat().st_size,
                        }
                    )
                    entry["destinations"].append(relative)
                result["sections"].append(entry)
        if (
            recipe_fingerprint(root, epoch, [lang.code for lang in languages], "sample")
            != source_snapshot
        ):
            raise ValueError("Frozen original source changed during rendering")
        result["unique_pdf_count"] = len(result["sections"])
        result["placed_pdf_copies"] = len(result["files"])
        result["pdf_max_bytes"] = config.build.pdf.max_file_bytes
        result["placed_bytes"] = sum(row["size_bytes"] for row in result["files"])
        (stage / "receipt.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        if output.exists():
            raise ValueError("Output appeared during rendering; no overwrite")
        stage.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "cache", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--source-commit", required=True)
    result = build_guides(**vars(parser.parse_args()))
    print(
        json.dumps(
            {key: result[key] for key in ("unique_pdf_count", "placed_pdf_copies", "placed_bytes")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
