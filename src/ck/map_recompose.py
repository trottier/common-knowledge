"""Recompose an authenticated county proof without reading or changing geodata."""

import hashlib
import json
import os
import re
import resource
import time
from copy import deepcopy
from decimal import Decimal
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path
from xml.etree import ElementTree

from markupsafe import Markup
from pypdf import PdfReader
from weasyprint import HTML

from ck.catalog import safe_path
from ck.config import read_yaml
from ck.countyproof import horizontal_layout, html_document, sha
from ck.render import OfflineFetcher, pdf_timestamp


def artifact_path(folder: Path, name: str) -> Path:
    """Reject path escapes and symlinks before opening a cached artifact."""
    safe_path(name)
    path = folder / name
    current = folder
    parts = []
    for part in path.relative_to(folder).parts:
        current = current / part
        parts.append(current)
    if not path.resolve().is_relative_to(folder.resolve()) or any(p.is_symlink() for p in parts):
        raise ValueError(f"Unsafe cached artifact: {name}")
    if not path.is_file():
        raise ValueError(f"Missing cached artifact: {name}")
    return path


def authenticated_html(pdf: Path, cached: Path) -> str:
    """The original producer binds the exact HTML SHA to the PDF's first ID."""
    source = cached.read_bytes()
    reader = PdfReader(pdf)
    identifiers = reader.trailer.get("/ID")
    identifier = getattr(identifiers[0], "original_bytes", None) if identifiers else None
    if identifier != hashlib.sha256(source).hexdigest().encode("ascii"):
        raise ValueError("Cached HTML does not match the original PDF identifier")
    return source.decode("utf-8")


class PlaceRows(HTMLParser):
    """Recover only the authenticated generated table, never execute its HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.cell = None
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self.in_body = True
        elif self.in_body and tag == "tr":
            self.row = []
        elif self.in_body and tag == "td":
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append("\x1e")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append("".join(self.cell))
            self.cell = None
        elif self.in_body and tag == "tr":
            self.rows.append(self.row)
        elif tag == "tbody":
            self.in_body = False


def places_from_html(source: str, identifiers: list[str]) -> list[dict]:
    parser = PlaceRows()
    parser.feed(source)
    if len(parser.rows) != len(identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Cached places do not match the original point inventory")
    result = []
    for number, (row, identifier) in enumerate(zip(parser.rows, identifiers, strict=True), 1):
        if len(row) != 3 or row[0].strip() != str(number) or "\x1e" not in row[2]:
            raise ValueError("Cached place row has unexpected fields or numbering")
        category, address = row[2].split("\x1e", 1)
        address = " ".join(address.split())
        result.append(
            {
                "id": identifier,
                "number": number,
                "name": " ".join(row[1].split()),
                "category": " ".join(category.split()),
                "address": "" if address == "Address not supplied" else address,
            }
        )
    return result


def require_svg(source: str, document: str) -> set[str]:
    if document.count(source) != 1:
        raise ValueError("Cached SVG is not an exact unique substring of original HTML")
    root = ElementTree.fromstring(source)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Cached map is not SVG")
    return {
        " ".join("".join(node.itertext()).split())
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "text"
    }


def prepared_data(root: Path, prepared: Path) -> tuple[dict, dict, dict]:
    """Authenticate original PDFs, HTML, SVGs, and fonts before any new output."""
    pin = json.loads((root / "pipelines/atlas/bristol-recompose.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", pin["source_commit"]):
        raise ValueError("Original source commit must be pinned")
    manifest = artifact_path(prepared, "prototype.json")
    if sha(manifest) != pin["prototype_sha256"]:
        raise ValueError("Original prototype does not match the pinned recomposition input")
    original = json.loads(manifest.read_text())
    leaf = original["detail_pdf"]
    if safe_path(leaf).name != leaf:
        raise ValueError("Detailed PDF must have a single safe leaf name")
    documents, receipts = {}, {}
    for entry in original["files"]:
        pdf = artifact_path(prepared, entry["path"])
        if pdf.name in documents or pdf.name not in {leaf, "0_OVERVIEW.pdf"}:
            raise ValueError("Unexpected or duplicate original PDF")
        if sha(pdf) != entry["sha256"] or pdf.stat().st_size != entry["size_bytes"]:
            raise ValueError("Original PDF does not match its manifest")
        cached = artifact_path(prepared, "audit/" + pdf.name + ".html")
        documents[pdf.name] = authenticated_html(pdf, cached)
        receipts["audit/" + cached.name] = sha(cached)
    if set(documents) != {leaf, "0_OVERVIEW.pdf"}:
        raise ValueError("Both original county PDFs are required")
    svgs, names = {}, set()
    for sheet in original["sheets"]:
        identifier = sheet["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier) or identifier in svgs:
            raise ValueError("Unsafe or duplicate map sheet ID")
        path = artifact_path(prepared, f"audit/{identifier}.svg")
        source = path.read_text()
        names.update(require_svg(source, documents[leaf]))
        svgs[identifier] = source
        receipts[f"audit/{identifier}.svg"] = sha(path)
    for identifier, filename in [("overview", "0_OVERVIEW.pdf"), ("locator", leaf)]:
        path = artifact_path(prepared, f"audit/{identifier}.svg")
        source = path.read_text()
        require_svg(source, documents[filename])
        svgs[identifier] = source
        receipts[f"audit/{identifier}.svg"] = sha(path)
    coverage = original["street_name_coverage"]
    if coverage["missing_way_ids"] or set(coverage["expected_way_ids"]) != set(
        coverage["labeled_way_ids"]
    ):
        raise ValueError("Original source-way coverage is incomplete")
    if any(" ".join(name.split()) not in names for name in coverage["source_names"]):
        raise ValueError("Original map SVGs omit a source street name")
    data = deepcopy(original)
    data["pois"] = places_from_html(documents["0_OVERVIEW.pdf"], original["overview"]["poi_ids"])
    for font in data["fonts"]:
        candidates = [Path(font["path"])]
        if os.environ.get("CK_FONT_CACHE"):
            candidates.append(Path(os.environ["CK_FONT_CACHE"]) / font["sha256"])
        candidates.append(root / "cache" / font["sha256"])
        match = next(
            (path for path in candidates if path.is_file() and sha(path) == font["sha256"]), None
        )
        if match is None:
            raise ValueError("Original pinned font is unavailable or changed: " + font["id"])
        font["path"] = str(match.resolve())
    return (
        data,
        svgs,
        {
            "source_commit": pin["source_commit"],
            "prototype_sha256": sha(manifest),
            "original_producer": original["producer"],
            "cached_files": receipts,
            "original_files": original["files"],
        },
    )


def pages_from_metadata(data: dict, svgs: dict) -> list[dict]:
    by_id = {sheet["id"]: sheet for sheet in data["sheets"]}
    pages = []
    for sheet in data["sheets"]:
        neighbors = "; ".join(
            f"{direction}: {identifier}, page {by_id[identifier]['page']}"
            for direction, identifier in sheet["neighbors"].items()
        )
        children = [child for child in data["sheets"] if child.get("parent") == sheet["id"]]
        if children:
            neighbors += "; enlarged streets: " + (
                ", ".join(f"{child['id']} p{child['page']}" for child in children)
                if len(children) <= 5
                else "see the index at the end"
            )
        target_name = ""
        if "target_way_id" in sheet:
            targets = {
                placement["name"]
                for placement in sheet["street_name_coverage"]["placed_labels"]
                if sheet["target_way_id"] in placement["source_ways"]
            }
            if len(targets) != 1:
                raise ValueError("Inset target does not match exactly one cached street label")
            target_name = targets.pop()
            neighbors = f"Enlarged streets near {target_name}; " + neighbors
        pages.append(
            {
                **sheet,
                "svg": Markup(svgs[sheet["id"]]),
                "continuation": neighbors or "County edge: use the locator",
                "target_name": target_name,
            }
        )
    return pages


def require_pdf_layout(reader: PdfReader, sheets: list[dict], maximum: int) -> None:
    destinations = {}

    def collect(items):
        for item in items:
            if isinstance(item, list):
                collect(item)
            else:
                destinations[item.title] = reader.get_destination_page_number(item) + 1

    collect(reader.outline)
    if len(reader.pages) > maximum or any(
        destinations.get("Bristol County · " + sheet["id"]) != sheet["page"] for sheet in sheets
    ):
        raise ValueError("Recomposed PDF page/outline targets changed or exceed the page budget")


def recompose(root: Path, prepared: Path, output: Path) -> dict:
    started = time.monotonic()
    if output.exists():
        raise ValueError("Choose a fresh recomposition output; no overwrite")
    data, svgs, provenance = prepared_data(root, prepared)
    budget_path = root / "config/build.yaml"
    budget = read_yaml(budget_path)["pdf"]
    maximum = Decimal(str(budget["max_file_mb"])) * 1_000_000
    if not maximum.is_finite() or maximum <= 0 or maximum != int(maximum):
        raise ValueError("Shared PDF budget must resolve to a positive whole byte count")
    data["policy"]["pdf_max_bytes"] = int(maximum)
    data["policy"]["pdf_budget"] = budget
    data["policy"]["pdf_budget_source_sha256"] = sha(budget_path)
    source_files = {
        name: sha(root / name)
        for name in [
            "src/ck/map_recompose.py",
            "src/ck/countyproof.py",
            "src/ck/render.py",
            "src/ck/catalog.py",
            "src/ck/config.py",
            "tools/recompose_county_map.py",
            "templates/county-proof.html.j2",
            "pipelines/atlas/bristol-recompose.json",
            "pyproject.toml",
            "uv.lock",
            "Dockerfile.build",
            "config/debian.sources",
        ]
    }
    recipe = {
        "source_files": source_files,
        "input": provenance,
        "pdf_budget": budget,
        "fonts": [
            {"id": font["id"], "sha256": font["sha256"], "render_uri": Path(font["path"]).as_uri()}
            for font in data["fonts"]
        ],
        "tools": {name: version(name) for name in ["weasyprint", "pypdf"]},
    }
    digest = hashlib.sha256(
        json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    pages = pages_from_metadata(data, svgs)
    leaf = data["detail_pdf"]
    parent = Path(data["files"][0]["path"]).parent
    if any(Path(entry["path"]).parent != parent for entry in data["files"]):
        raise ValueError("Original county PDFs must share their folder")
    files = output / parent
    files.mkdir(parents=True)
    audit = output / "audit"
    audit.mkdir()
    layout = {}
    for filename, title, kind in [
        (leaf, "Bristol County road maps", "detail"),
        ("0_OVERVIEW.pdf", "Bristol County overview and public places", "overview"),
    ]:
        document = html_document(
            root, title, kind, pages, svgs["overview"], svgs["locator"], leaf, data
        )
        (audit / (filename + ".html")).write_text(document)
        with pdf_timestamp(data["policy"]["epoch"]):
            rendered = HTML(
                string=document,
                url_fetcher=OfflineFetcher([Path(font["path"]).parent for font in data["fonts"]]),
            ).render()
            layout[filename] = horizontal_layout(rendered)
            rendered.write_pdf(
                files / filename,
                pdf_identifier=hashlib.sha256(document.encode()).hexdigest().encode(),
                pdf_tags=True,
            )
        if (files / filename).stat().st_size > int(maximum):
            raise ValueError("Recomposed PDF exceeds the configured byte budget")
        if kind == "detail":
            require_pdf_layout(
                PdfReader(files / filename), data["sheets"], data["policy"]["max_pages"]
            )
    for identifier, svg in svgs.items():
        (audit / (identifier + ".svg")).write_text(svg)
    result = {
        **data,
        "producer": {"version": "county-map-recompose-v1-" + digest, **recipe},
        "recomposition": provenance,
        "horizontal_layout": layout,
        "files": [
            {
                "path": str(path.relative_to(output)),
                "size_bytes": path.stat().st_size,
                "sha256": sha(path),
            }
            for path in sorted(files.glob("*.pdf"))
        ],
        "elapsed_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "cgroup": {
            name: Path("/sys/fs/cgroup", name).read_text()
            for name in ["memory.peak", "memory.events"]
            if Path("/sys/fs/cgroup", name).exists()
        },
    }
    # Runtime font paths and recovered point rows are not new source pins.
    result.pop("pois")
    (output / "prototype.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result
