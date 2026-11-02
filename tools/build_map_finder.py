"""Make a small phone navigation PDF from the county maps actually present."""

import argparse
import json
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

TARGET = "3_MAPS_AND_PLACES/0_FIND_A_MAP.pdf"


def build(
    root: Path,
    drive: Path,
    cache: Path,
    output: Path,
    manifest_sha256: str,
    epoch: int,
    tool_image: str,
):
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a fresh map-finder output")
    if drive.is_symlink() or digest(drive / "MANIFEST.SHA256") != manifest_sha256:
        raise ValueError("Map finder needs the exact actual-tree manifest")
    check_manifest(drive)
    config = load_config(root)
    records = []
    for path in validate_tree(drive):
        relative = path.relative_to(drive).as_posix()
        parts = Path(relative).parts
        if (
            len(parts) != 4
            or parts[0] != "3_MAPS_AND_PLACES"
            or parts[1].casefold() == "android"
            or path.suffix.lower() != ".pdf"
        ):
            continue
        records.append(
            {
                "path": relative,
                "state": parts[1],
                "county": parts[2],
                "name": path.name,
                "sha256": digest(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if not records:
        raise ValueError("No actual county-map PDFs to index")
    groups = {}
    for row in records:
        groups.setdefault((row["state"], row["county"]), []).append(row)
    font = next(row for row in read_yaml(root / "catalog/fonts.yaml") if row["id"] == "noto_sans")
    font_path = cache / font["sha256"]
    if font_path.is_symlink() or digest(font_path) != font["sha256"]:
        raise ValueError("Pinned map-finder font changed")
    require_glyphs([row["path"] for row in records], [font_path])
    template = root / "pipelines/copy_index/map-finder.html.j2"
    document = (
        Environment(
            loader=FileSystemLoader(template.parent), autoescape=True, undefined=StrictUndefined
        )
        .get_template(template.name)
        .render(
            groups=groups,
            font_uri=font_path.as_uri(),
            timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
        )
    )
    output.mkdir(parents=True)
    html = output / "map-finder.html"
    html.write_text(document)
    pdf = output / "0_FIND_A_MAP.pdf"
    with pdf_timestamp(epoch):
        HTML(string=document, url_fetcher=OfflineFetcher([cache])).write_pdf(
            pdf, pdf_tags=True, pdf_identifier=digest(html).encode()
        )
    if pdf.stat().st_size > config.build.pdf.max_file_bytes:
        raise ValueError("Map finder exceeds the shared PDF budget")
    reader = PdfReader(pdf)
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    for row in records:
        if "".join(row["name"].split()) not in "".join(text.split()):
            raise ValueError("Map filename did not survive the rendered index")
    receipt = {
        "status": "Draft navigation; not physical-phone acceptance",
        "target_path": TARGET,
        "epoch": epoch,
        "source_manifest_sha256": manifest_sha256,
        "indexed_maps": records,
        "pages": len(reader.pages),
        "pdf": {"sha256": digest(pdf), "size_bytes": pdf.stat().st_size},
        "producer_files": {
            str(p.relative_to(root)): digest(p)
            for p in [
                root / "tools/build_map_finder.py",
                template,
                root / "src/ck/render.py",
                root / "pyproject.toml",
                root / "uv.lock",
                root / "Dockerfile.build",
            ]
        },
        "font": {"id": font["id"], "sha256": font["sha256"]},
        "html_sha256": digest(html),
        "tool_image": tool_image,
        "pdf_max_bytes": config.build.pdf.max_file_bytes,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["root", "drive", "cache", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--tool-image", required=True)
    args = parser.parse_args()
    print(json.dumps(build(**vars(args)), ensure_ascii=False, indent=2))
