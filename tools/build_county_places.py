"""A phone companion for the authenticated Bristol proof's historical public places."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from pypdf import PdfReader
from pyproj import Transformer
from weasyprint import HTML

from ck.assemble import copy_exact
from ck.config import load_config, read_yaml
from ck.directory import Place, plain
from ck.fetch import digest
from ck.geofonts import require_glyphs
from ck.render import OfflineFetcher, font_files, pdf_timestamp, render_html
from tools.assemble_inspection_preview import confined_file

TARGET = "3_MAPS_AND_PLACES/RI/Bristol County/Bristol County - Places.pdf"
SOURCE = "SOURCE/RI_SOURCE_DATA.json"


def selected_places(proof, public, original):
    """Retain the overview's exact numbering and the original exclusion-checked records."""
    ids = proof["overview"]["poi_ids"]
    if len(ids) != 33 or len(set(ids)) != len(ids):
        raise ValueError("The Bristol proof must retain its 33 unique overview points")
    county = proof["policy"]["county"]
    if county != "44001" or proof["policy"]["county_name"] != "Bristol County":
        raise ValueError("This bounded companion is only for the Bristol proof")
    public_rows = [row for row in public["places"] if row["county"] == county]
    private_rows = [row for row in original["places"] if row["county"] == county]
    if [row["id"] for row in public_rows] != ids or len(private_rows) != len(ids):
        raise ValueError("Historical point membership/order differs from the overview")
    original_by_id = {row["id"]: Place.model_validate(row) for row in private_rows}
    if len(original_by_id) != len(ids) or set(original_by_id) != set(ids):
        raise ValueError("Duplicate or mismatched original points")
    places = []
    for row in public_rows:
        place = original_by_id[row["id"]]
        if place.model_dump(exclude={"tags"}) != row:
            raise ValueError("Public and original place records differ")
        places.append(place)
    return places


def point_references(proof, places):
    """Use actual sheet bounds, page numbers, and the printed five-by-six grid."""
    transform = Transformer.from_crs(4326, proof["crs"], always_xy=True)
    sheets = [sheet for sheet in proof["sheets"] if not sheet.get("inset_depth", 0)]
    refs = {}
    for place in places:
        x, y = transform.transform(place.longitude, place.latitude)
        candidates = []
        for sheet in sheets:
            west, south, east, north = sheet["bounds"]
            if east <= west or north <= south:
                raise ValueError("Invalid actual sheet bounds")
            if sheet["grid_columns"] != "ABCDE" or sheet["grid_rows"] != list(range(1, 7)):
                raise ValueError("Unsupported actual printed grid")
            if sheet["pdf"] != proof["detail_pdf"] or sheet["page"] < 1:
                raise ValueError("Actual sheet file or page differs")
            if west <= x <= east and south <= y <= north:
                u, v = (x - west) / (east - west), (north - y) / (north - south)
                # Prefer a point away from an overlapping sheet's edge; page breaks ties.
                margin = min(u, 1 - u, v, 1 - v)
                grid = chr(65 + min(4, math.floor(u * 5))) + str(min(5, math.floor(v * 6)) + 1)
                candidates.append((-margin, sheet["page"], sheet["id"], grid))
        if not candidates:
            raise ValueError(f"Point lies outside actual detail sheets: {place.id}")
        _, page, sheet, grid = min(candidates)
        refs[place.id] = {"file": proof["detail_pdf"], "page": page, "sheet": sheet, "grid": grid}
    return refs


def authenticate(proof_dir, proof_sha256, directory):
    manifest = confined_file(proof_dir, "prototype.json")
    if digest(manifest) != proof_sha256:
        raise ValueError("Map proof checksum differs")
    proof = json.loads(manifest.read_text())
    for row in proof["files"]:
        path = confined_file(proof_dir, row["path"])
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Actual map PDF differs from its proof")
    historical = json.loads(confined_file(directory, "generation.json").read_text())
    if historical != proof["historical_points"]["manifest"]:
        raise ValueError("Original directory generation differs from the historical proof")
    if (
        historical.get("complete") is not False
        or proof["historical_points"]["complete"] is not False
    ):
        raise ValueError("Retain the original incomplete-directory status")
    for row in historical["files"] + historical["intermediates"]:
        relative = "files/" + row["path"] if row in historical["files"] else row["path"]
        path = confined_file(directory, relative)
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Original directory payload or audit differs")
    source = confined_file(directory, "files/RI_SOURCE_DATA.json")
    if digest(source) != proof["historical_points"]["source_payload_sha256"]:
        raise ValueError("Original source data differs")
    public = json.loads(source.read_text())
    original = json.loads(confined_file(directory, "places.json").read_text())
    # The unchanged source JSON includes the whole historical state, so validate all
    # its original records before retaining that file as the public source offer.
    all_original = {row["id"]: Place.model_validate(row) for row in original["places"]}
    if len(all_original) != len(original["places"]) or len(public["places"]) != len(all_original):
        raise ValueError("Whole historical source membership differs")
    for row in public["places"]:
        if (
            row["id"] not in all_original
            or all_original[row["id"]].model_dump(exclude={"tags"}) != row
        ):
            raise ValueError("Whole historical source record differs")
    places = selected_places(proof, public, original)
    refs = point_references(proof, places)
    detail = next(row for row in proof["files"] if Path(row["path"]).name == proof["detail_pdf"])
    reader = PdfReader(confined_file(proof_dir, detail["path"]))
    for ref in refs.values():
        if (
            ref["page"] > len(reader.pages)
            or ref["sheet"] not in reader.pages[ref["page"] - 1].extract_text()
        ):
            raise ValueError("Sheet page does not resolve in the actual detail PDF")
    return proof, historical, source, places, refs


def body_text(proof, places, refs):
    body = [
        "---",
        "title: Bristol County — Places",
        "status: draft",
        "reviewer: null",
        "reviewed_on: null",
        "---",
        "",
        "May help; not confirmed open.",
        "",
        "Incomplete coverage. A listed place is not an event shelter or an assurance of service.",
        "",
        "Numbers match the red points in 0_OVERVIEW.pdf in this folder.",
        "",
        "Detail map in this folder:",
        "",
        plain(proof["detail_pdf"]),
        "",
        "Open its listed page. Grid columns A–E run left to right; rows 1–6 run top to bottom.",
        "",
    ]
    category = None
    for number, place in enumerate(places, 1):
        if place.category != category:
            category = place.category
            body += ["## " + plain(category.replace("_", " ").capitalize()), ""]
        ref = refs[place.id]
        body += [
            "::: place",
            "",
            f"**{number}. {plain(place.name)}**",
            "",
            plain(place.address) or "Address not supplied.",
            "",
            f"{place.latitude:.6f}, {place.longitude:.6f}",
            "",
            f"Detail map: page {ref['page']}, sheet {ref['sheet']}, grid {ref['grid']}.",
            "",
        ]
        if place.details.get("Access"):
            body += [plain(place.details["Access"]) + ".", ""]
        body += [f"> Source: {plain(place.source_id)}; as of {plain(place.as_of)}.", "", ":::", ""]
    body += [
        "## Source notes",
        "",
        "> Draft from the existing historical directory. Its incomplete status is retained. "
        "No new source records or live opening information were added. Source, safety, "
        "and physical-phone review remain open.",
        "",
        "> © OpenStreetMap contributors; NCES; IMLS; FCC. OpenStreetMap data: ODbL-1.0. "
        "Original source data and its license notice are in SOURCE/RI_SOURCE_DATA.json. "
        "Keep SOURCE and SOURCE.TXT with this PDF when sharing.",
        "",
    ]
    return "\n".join(body)


def build(*, root, cache, proof_dir, proof_sha256, directory, output, tool_image):
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("Choose a fresh output; no overwrite or symlinks")
    for source in (root, cache, proof_dir, directory):
        if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(
            output.resolve()
        ):
            raise ValueError("Output overlaps an input")
    proof, historical, source, places, refs = authenticate(proof_dir, proof_sha256, directory)
    epoch = historical["source_date_epoch"]
    if epoch != proof["policy"]["epoch"]:
        raise ValueError("Historical epochs differ")
    config = load_config(root)
    language = config.languages[0]
    os.environ["CK_FONT_CACHE"] = str(cache)
    fonts = font_files(root, language)
    font_catalog = {r["id"]: r for r in read_yaml(root / "catalog/fonts.yaml")}
    for path in fonts:
        pin = font_catalog[language.font]
        if path.stat().st_size != pin["size_bytes"] or digest(path) != pin["sha256"]:
            raise ValueError("Pinned font differs")
    output.mkdir(parents=True)
    text = output / "places.md"
    text.write_text(body_text(proof, places, refs))
    require_glyphs([text.read_text()], fonts)
    document = render_html(
        root,
        config,
        text,
        language,
        "phone",
        epoch,
        template="directory-part.html.j2",
        profile="sample",
    )
    # Reuse the existing directory renderer and grouping; only source notes are quiet.
    css = """@page { margin-top: 18mm; @top-center { font-size: 12pt; } }
    .place blockquote, main > blockquote { font-size: 8pt; color: #666; margin: 1mm 0; }
    .place p { line-height: 1.25; } .place { break-inside: avoid; }
    h1 { font-size: 19pt; } main h2 { break-before: auto; }
    """
    document = document.replace("</style>", css + "</style>", 1)
    html = output / "places.html"
    html.write_text(document)
    files = output / "files"
    pdf = files / TARGET
    pdf.parent.mkdir(parents=True)
    with pdf_timestamp(epoch):
        HTML(string=document, url_fetcher=OfflineFetcher([cache])).write_pdf(
            pdf, pdf_tags=True, pdf_identifier=digest(html).encode()
        )
    if pdf.stat().st_size > config.build.pdf.max_file_bytes:
        raise ValueError("Companion exceeds the shared PDF budget")
    reader = PdfReader(pdf)
    extracted = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
    if any(
        " ".join(f"{n}. {place.name}".split()) not in extracted for n, place in enumerate(places, 1)
    ):
        raise ValueError("A numbered place did not survive rendering")
    source_target = pdf.parent / SOURCE
    copy_exact(source, source_target, digest(source))
    notice = pdf.parent / "SOURCE.TXT"
    original_attribution = json.loads(source.read_text())["attribution"]
    notice.write_text(
        "Bristol County public places — incomplete local draft\n" + original_attribution + ".\n"
        "OpenStreetMap data: Open Database License 1.0 (ODbL-1.0).\n"
        "https://opendatacommons.org/licenses/odbl/1-0/\n"
        "Original historical public data, including its source versions and license notice:\n"
        "SOURCE/RI_SOURCE_DATA.json (unchanged original bytes).\n"
        "Only the 33 Bristol County records are presented in the companion PDF.\n"
        "Their numbers match 0_OVERVIEW.pdf. No new source records were added.\n"
        "Map references are calculated from the authenticated current detail sheet bounds.\n"
        "Source, safety, completeness, and physical-phone review remain open.\n"
    )
    producer_files = [
        root / "tools/build_county_places.py",
        *[
            root / p
            for p in (
                "src/ck/directory.py",
                "src/ck/render.py",
                "templates/directory-part.html.j2",
                "templates/directory.html.j2",
                "templates/document.html.j2",
                "templates/document.css",
                "config/build.yaml",
                "config/languages.yaml",
                "content/en/edition.yaml",
                "catalog/fonts.yaml",
                "pyproject.toml",
                "uv.lock",
                "Dockerfile.build",
            )
        ],
    ]
    receipt = {
        "status": "Draft/incomplete; no new records or human approval",
        "complete": False,
        "epoch": epoch,
        "target_path": TARGET,
        "map_proof_sha256": proof_sha256,
        "historical_directory_generation": historical,
        "historical_generation_file_sha256": digest(directory / "generation.json"),
        "source_payload_sha256": digest(source),
        "original_source_versions": json.loads(source.read_text())["source_versions"],
        "places": [
            {"number": n, "record": p.model_dump(), "map_reference": refs[p.id]}
            for n, p in enumerate(places, 1)
        ],
        "map_files": proof["files"],
        "pages": len(reader.pages),
        "html_sha256": digest(html),
        "producer_files": {str(p.relative_to(root)): digest(p) for p in producer_files},
        "font_pins": [
            {"sha256": digest(path), "size_bytes": path.stat().st_size} for path in fonts
        ],
        "tool_image": tool_image,
        "pdf_max_bytes": config.build.pdf.max_file_bytes,
        "files": [
            {
                "path": p.relative_to(files).as_posix(),
                "sha256": digest(p),
                "size_bytes": p.stat().st_size,
            }
            for p in sorted(files.rglob("*"))
            if p.is_file()
        ],
    }
    receipt["recipe"] = (
        "county-places-proof-v1-"
        + hashlib.sha256(json.dumps(receipt["producer_files"], sort_keys=True).encode()).hexdigest()
    )
    for path in [*output.rglob("*"), output]:
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "cache", "proof-dir", "directory", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("proof-sha256", "tool-image"):
        parser.add_argument("--" + name, required=True)
    result = build(**vars(parser.parse_args()))
    print(json.dumps({"pages": result["pages"], "files": result["files"]}, indent=2))
