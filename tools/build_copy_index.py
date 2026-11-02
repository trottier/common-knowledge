"""Build a draft navigation index from a verified actual drive tree, without changing it."""

import argparse
import hashlib
import importlib.metadata
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pypdf import PdfReader
from weasyprint import HTML

from ck.assemble import check_manifest
from ck.config import load_config, read_yaml
from ck.drive_safety import validate_tree
from ck.fetch import digest
from ck.geofonts import require_glyphs
from ck.render import OfflineFetcher, pdf_timestamp

INDEX_PATH = "4_PHONE_PACK/0_WHAT_TO_COPY.pdf"
FORMAT_SUFFIXES = {".pdf", ".mp4", ".apk", ".zim", ".obf"}


def inventory(drive: Path, manifest_sha256: str) -> list[dict]:
    manifest = drive / "MANIFEST.SHA256"
    if drive.is_symlink() or manifest.is_symlink() or digest(manifest) != manifest_sha256:
        raise ValueError("Original drive manifest checksum differs")
    check_manifest(drive)
    records = []
    for path in validate_tree(drive):
        relative = path.relative_to(drive).as_posix()
        if (
            relative == INDEX_PATH
            or relative.split("/")[0].casefold() == "backup"
            or path.suffix.casefold() not in FORMAT_SUFFIXES
        ):
            continue
        size = path.stat().st_size
        records.append(
            {
                "path": relative,
                "name": path.name,
                "folder": str(Path(relative).parent),
                "size_bytes": size,
                "decimal_mb": f"{size / 1_000_000:.6f}",
                "sha256": digest(path),
                "format": path.suffix[1:].upper(),
            }
        )
    if not records:
        raise ValueError("Actual tree contains no eligible copy-index files")
    return records


def build_index(
    root: Path,
    drive: Path,
    cache: Path,
    output: Path,
    manifest_sha256: str,
    epoch: int,
    tool_image: str,
) -> dict:
    if output.exists():
        raise ValueError("Choose a fresh output directory; no overwrite")
    config = load_config(root)
    records = inventory(drive, manifest_sha256)
    languages = [lang for lang in config.languages if (drive / "1_START" / lang.name).is_dir()]
    if {p.name for p in (drive / "1_START").iterdir() if p.is_dir()} != {
        lang.name for lang in languages
    }:
        raise ValueError("Actual edition folders differ from configured readable names")
    font_catalog = {row["id"]: row for row in read_yaml(root / "catalog/fonts.yaml")}
    font_ids = list(dict.fromkeys(["noto_sans", *[lang.font for lang in languages]]))
    fonts = []
    for key in font_ids:
        item = font_catalog[key]
        path = cache / item["sha256"]
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != item["size_bytes"]
            or digest(path) != item["sha256"]
        ):
            raise ValueError(f"Missing or changed pinned font: {key}")
        fonts.append({"id": key, "path": path, "sha256": item["sha256"]})
    require_glyphs(
        [entry["path"] for entry in records] + [lang.name for lang in languages],
        [font["path"] for font in fonts],
    )
    groups = []
    for folder in dict.fromkeys(row["folder"] for row in records):
        groups.append(
            {
                "folder": folder,
                "id": "group-" + str(len(groups) + 1),
                "files": [row for row in records if row["folder"] == folder],
            }
        )
    template = root / "pipelines/copy_index/index.html.j2"
    source_files = [
        root / "tools/build_copy_index.py",
        template,
        *[
            root / "src/ck" / name
            for name in [
                "assemble.py",
                "catalog.py",
                "config.py",
                "drive_safety.py",
                "fetch.py",
                "geofonts.py",
                "render.py",
            ]
        ],
        *[root / name for name in ["Dockerfile.build", "pyproject.toml", "uv.lock"]],
    ]
    producer_inputs = {str(p.relative_to(root)): digest(p) for p in source_files}
    producer = (
        "copy-index-v1-"
        + hashlib.sha256(json.dumps(producer_inputs, sort_keys=True).encode()).hexdigest()
    )
    timestamp = datetime.fromtimestamp(epoch, UTC).isoformat()
    env = Environment(
        loader=FileSystemLoader(template.parent), autoescape=True, undefined=StrictUndefined
    )
    document = env.get_template(template.name).render(
        groups=groups,
        languages=languages,
        fonts=fonts,
        font_families={font["id"]: f"CopyFont{n}" for n, font in enumerate(fonts, 1)},
        timestamp=timestamp,
        file_count=len(records),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-copy-index-", dir=output.parent) as temporary:
        stage = Path(temporary)
        pdf = stage / "0_WHAT_TO_COPY.pdf"
        (stage / "index.html").write_text(document)
        identifier = hashlib.sha256(document.encode()).hexdigest().encode()
        with pdf_timestamp(epoch):
            HTML(string=document, url_fetcher=OfflineFetcher([cache])).write_pdf(
                pdf, pdf_identifier=identifier, pdf_tags=True
            )
        if pdf.stat().st_size > config.build.pdf.max_file_bytes:
            raise ValueError("Copy index exceeds the configured PDF byte budget")
        reader = PdfReader(pdf)
        for page in reader.pages:
            if (
                abs(float(page.mediabox.width) - 90 * 72 / 25.4) > 0.1
                or abs(float(page.mediabox.height) - 160 * 72 / 25.4) > 0.1
            ):
                raise ValueError("Copy index page is not phone size")
        if not reader.outline:
            raise ValueError("Copy index has no heading bookmarks")
        if inventory(drive, manifest_sha256) != records:
            raise ValueError("Original drive changed during index generation")
        result = {
            "status": "Draft navigation index; no content approval or phone acceptance",
            "target_path": INDEX_PATH,
            "source_manifest_sha256": manifest_sha256,
            "epoch": epoch,
            "producer": producer,
            "producer_inputs": producer_inputs,
            "requested_tool_image": tool_image,
            "pdf_budget": config.build.pdf.model_dump(),
            "system_tool_versions": Path("/opt/ck-tool-versions.txt").read_text(),
            "fonts": [{**font, "path": str(font["path"])} for font in fonts],
            "tool_versions": {
                "weasyprint": importlib.metadata.version("weasyprint"),
                "pypdf": importlib.metadata.version("pypdf"),
            },
            "editions": [lang.name for lang in languages],
            "indexed_files": records,
            "indexed_file_count": len(records),
            "pages": len(reader.pages),
            "pdf": {"path": pdf.name, "sha256": digest(pdf), "size_bytes": pdf.stat().st_size},
            "exclusions": [
                "BACKUP duplicates",
                "copy index itself",
                "formats other than PDF/MP4/APK/ZIM/OBF",
            ],
            "limitations": (
                "Actual partial-tree inventory only; not all formats, a complete sample, "
                "release, or device acceptance. Keep required notices when sharing folders."
            ),
        }
        (stage / "receipt.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        if output.exists():
            raise ValueError("Output appeared during generation; no overwrite")
        stage.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["root", "drive", "cache", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--tool-image", required=True)
    result = build_index(**vars(parser.parse_args()))
    print(
        json.dumps(
            {key: result[key] for key in ["indexed_file_count", "pages", "pdf", "producer"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
