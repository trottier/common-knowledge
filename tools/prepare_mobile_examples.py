"""Render a few representative pages from this project's generated county proof."""

import argparse
import hashlib
import io
import json
import re
from pathlib import Path

import pypdf
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML

from ck.catalog import safe_path
from ck.render import OfflineFetcher, pdf_timestamp


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--prototype-sha256", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    prepared = args.prepared.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(prepared) or prepared.is_relative_to(output):
        raise ValueError("Source and output must not contain one another")
    if sha(prepared / "prototype.json") != args.prototype_sha256:
        raise ValueError("Prepared map receipt checksum mismatch")
    if output.exists():
        raise ValueError("Use a fresh examples folder")
    if args.receipt.exists() or args.receipt.resolve().is_relative_to(prepared):
        raise ValueError("Choose a new receipt outside the prepared maps")
    receipt = json.loads((prepared / "prototype.json").read_text())
    if "recomposition" not in receipt:
        raise ValueError("Expected this project's recomposed Bristol County map proof")
    for font in receipt["fonts"]:
        path = args.cache / font["sha256"]
        if path.is_symlink() or sha(path) != font["sha256"]:
            raise ValueError("Pinned map font changed")
    sources = {Path(entry["path"]).name: entry for entry in receipt["files"]}
    directory = "3_MAPS_AND_PLACES/RI/Bristol County/"
    plan = [
        ("0_OVERVIEW.pdf", [1], "0_ZIP overview sample 02806,02809,02885.pdf"),
        ("Bristol County 02806,02809,02885.pdf", [14, 34], "Street samples 02806,02809,02885.pdf"),
    ]
    records = []
    for filename, pages, name in plan:
        original = sources[filename]
        source = prepared / safe_path(original["path"])
        if source.is_symlink() or not source.resolve().is_relative_to(prepared):
            raise ValueError("Map source must stay inside the prepared proof")
        assert source.stat().st_size == original["size_bytes"]
        assert sha(source) == original["sha256"]
        reader = PdfReader(source)
        html_path = prepared / "audit" / (filename + ".html")
        html = html_path.read_text()
        assert reader.trailer["/ID"][0].original_bytes.decode() == sha(html_path)
        sections = re.findall(r"<section\b[^>]*>[\s\S]*?</section>", html)
        selected = []
        extra_styles = []
        for number in pages:
            page_name = f"sample{number}"
            section = sections[number - 1]
            section = section.replace("<section", f'<section style="page:{page_name}"', 1)
            section = re.sub(r"<a\b[^>]*>([\s\S]*?)</a>", r"\1", section)
            if filename == "0_OVERVIEW.pdf":
                section = (
                    section.replace(
                        "Colored boundaries: 2020 Census ZIP areas 02806, 02809, 02885.",
                        "Colored boundaries: 2020 Census ZIP areas 02806, 02809, 02885. "
                        "Approximate areas, not a current USPS delivery directory.",
                    )
                    .replace(
                        "Detailed maps: Bristol County 02806,02809,02885.pdf.",
                        "Selected map samples; the full county atlas is kept in the local build.",
                    )
                    .replace(
                        "Places are numbered; see Public places.",
                        "Numbered place listings are in the full local atlas.",
                    )
                )
            selected.append(section)
            extra_styles.append(
                f"@page {page_name} {{ @bottom-center {{ "
                f'content: "Sample · original atlas page {number}\\A'
                'Continuations are in the full atlas"; white-space: pre; font-size: 7pt; } }'
            )
        html = html[: html.index("<body>")] + "<body>" + "\n".join(selected) + "</body></html>"
        html = html.replace("</head>", "<style>" + "\n".join(extra_styles) + "</style></head>")
        with pdf_timestamp(receipt["policy"]["epoch"]):
            rendered = HTML(string=html, url_fetcher=OfflineFetcher([args.cache])).write_pdf(
                pdf_identifier=hashlib.sha256(html.encode()).hexdigest().encode(), pdf_tags=True
            )
        excerpt = PdfReader(io.BytesIO(rendered))
        assert len(excerpt.pages) == len(pages)
        writer = PdfWriter()
        for index, number in enumerate(pages):
            writer.add_page(excerpt.pages[index], excluded_keys=["/Annots"])
            writer.add_outline_item(f"Sample — original atlas page {number}", len(writer.pages) - 1)
        writer.add_metadata(
            {
                **{key: str(value) for key, value in (reader.metadata or {}).items()},
                "/Title": name.removesuffix(".pdf"),
                "/Subject": "Selected map pages only. Continuations refer to the full local atlas.",
            }
        )
        writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
        writer.generate_file_identifiers()
        destination = output / directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        writer.write(destination)
        if destination.stat().st_size > receipt["policy"]["pdf_max_bytes"]:
            raise ValueError("Map sample exceeds the prepared proof's PDF budget")
        result = PdfReader(destination)
        assert len(result.pages) == len(pages)
        assert all("/Annots" not in page for page in result.pages)
        text = "\n".join(page.extract_text() for page in result.pages)
        assert "OpenStreetMap" in text
        if len(pages) == 2:
            assert "Woburn Street" in text and "Sloop Lane" in text
        else:
            assert all(code in text for code in ["02806", "02809", "02885"])
        records.append(
            {
                "path": directory + name,
                "size_bytes": destination.stat().st_size,
                "sha256": sha(destination),
                "original": original,
                "original_pages_one_based": pages,
                "annotation_links_removed": True,
                "generated_from_authenticated_html_sha256": sha(html_path),
                "rendered_from_unchanged_map_vectors": True,
            }
        )
    (output / "README.TXT").write_text(
        "Common Knowledge — mobile map examples\n\n"
        "This small online preview contains selected Bristol County map pages.\n"
        "Download a PDF, open it from your phone's Files app, and try zooming and panning.\n"
        "The ZIP overview shows the three Census ZIP areas.\n"
        "The street sample contains sheets I04 and I24 (original atlas pages 14 and 34).\n"
        "Continuation references use the original 46-page atlas's page numbers.\n"
        "Other sheets and the complete county atlas are kept in the local build.\n\n"
        "These are unreviewed development examples, not a complete drive.\n"
        "ZIP areas are Census 2020 approximations, not a current USPS delivery directory.\n"
        "See each map for data dates, attribution, and source notes.\n"
    )
    (output / "VERIFY.TXT").write_text(
        "Variant: 1\nProfile: representative examples\n"
        "Source: map recomposition 80bb900; original county map 39868af\n"
        "Status: selected map pages only; unreviewed; not a complete sample\n"
    )
    audit = {
        "scope": "representative generated-map excerpts only; full local tree unchanged",
        "producer_script_sha256": sha(Path(__file__)),
        "pypdf_version": pypdf.__version__,
        "map_prototype_sha256": sha(prepared / "prototype.json"),
        "map_source_commit": "80bb9009039cb3741c3938bc609bcdc19d9c3ff0",
        "files": records,
        "physical_phone_acceptance": False,
        "complete_sample": False,
    }
    args.receipt.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
