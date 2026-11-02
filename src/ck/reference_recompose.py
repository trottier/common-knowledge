"""Reframe authenticated generated medical HTML without opening source archives."""

import hashlib
import json
import re
import resource
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from multiprocessing import get_context
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pypdf import PdfReader

from ck.catalog import load_catalog, safe_path
from ck.config import read_yaml
from ck.generated import cached_input, generation_manifest, verified_generated_files
from ck.zim2pdf import render_article


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def contained_file(root: Path, relative: str) -> Path:
    path = root / safe_path(relative)
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Cached reference path is a symlink")
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Cached reference path escapes or is missing")
    return path


def exact_main(document: str) -> str:
    if document.count("<main>") != 1 or document.count("</main>") != 1:
        raise ValueError("Cached clinical main body is ambiguous")
    return document.split("<main>", 1)[1].split("</main>", 1)[0]


def exact_style(document: str) -> str:
    if document.count("<style>") != 1 or document.count("</style>") != 1:
        raise ValueError("Cached reference stylesheet is ambiguous")
    return document.split("<style>", 1)[1].split("</style>", 1)[0]


def admit_medical(root: Path, prepared: Path, cache: Path) -> tuple[dict, list, dict, dict]:
    """Authenticate generated payloads and HTML associations, not quarantined inputs."""
    catalog = load_catalog(root)
    item = catalog["medical_phone_pdfs"]
    metadata, payloads = verified_generated_files(item, prepared, catalog)
    for entry in metadata["intermediates"]:
        path = contained_file(prepared, entry["path"])
        if path.stat().st_size != entry["size_bytes"] or digest(path) != entry["sha256"]:
            raise ValueError("Historical reference intermediate changed")
    rows = json.loads(contained_file(prepared, "articles.json").read_text())
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Cached reference topic IDs repeat")
    font_ids = {key for key in metadata["inputs"] if catalog[key].family == "fonts"}
    documents, fonts = {}, {}
    for number, row in enumerate(rows, 1):
        name = f"{number:03d}_{row['id']}"
        if not re.fullmatch(r"[0-9]{3}_[a-z0-9_]+", name):
            raise ValueError("Unsafe cached reference topic ID")
        pdf = payloads.get(name + ".pdf")
        if pdf is None:
            raise ValueError("Cached topic is absent from the generated payload inventory")
        path = contained_file(prepared, "audit/" + name + ".html")
        document = path.read_bytes().decode("utf-8")
        identifiers = PdfReader(pdf).trailer.get("/ID")
        identifier = getattr(identifiers[0], "original_bytes", None) if identifiers else None
        if identifier != hashlib.sha256(document.encode()).hexdigest().encode("ascii"):
            raise ValueError("Cached reference HTML does not match its original PDF ID")
        exact_main(document)
        exact_style(document)
        aliases = list(dict.fromkeys(re.findall(r"ck-font:///([a-z0-9_]+)", document)))
        if set(aliases) != font_ids:
            raise ValueError("Cached font aliases differ from the original input pins")
        for key in aliases:
            if key not in fonts:
                fonts[key] = cached_input(catalog[key], cache)
        documents[row["id"]] = {"filename": name + ".pdf", "html": document, "aliases": aliases}
    expected = {record["filename"] for record in documents.values()}
    actual = {name for name in payloads if name.endswith(".pdf")}
    if expected != actual:
        raise ValueError("Cached article inventory does not cover every original PDF")
    provenance = {
        "source_item": item.id,
        "canonical_generation_sha256": item.sha256,
        "raw_generation_sha256": digest(prepared / "generation.json"),
        "historical_pipeline_version": metadata["pipeline_version"],
        "historical_inputs": metadata["inputs"],
        "historical_complete": metadata["complete"],
        "review_hold": item.review,
        "input_review_holds": {
            key: {
                "license": catalog[key].license,
                "license_proof_url": catalog[key].license_proof_url,
                "review": catalog[key].review,
                "requires_legal": catalog[key].requires_legal,
                "legal_reviewer": catalog[key].legal_reviewer,
                "legal_reviewed_on": catalog[key].legal_reviewed_on,
            }
            for key in sorted(metadata["inputs"])
        },
        "archive_accessed": False,
        "source_date_epoch": metadata["source_date_epoch"],
    }
    return metadata, rows, documents, {"fonts": fonts, "provenance": provenance}


def render_cached_task(task: tuple) -> dict:
    """One isolated renderer owns one unique output and its timestamp scope."""
    pages = render_article(task[:4])
    if task[1].stat().st_size > task[4]:
        raise ValueError("Reframed reference exceeds the shared PDF byte budget")
    return {"pages": pages, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def recompose_medical(
    root: Path, prepared: Path, cache: Path, output: Path, topics: list[str] | None, jobs: int = 1
) -> dict:
    started = time.monotonic()
    if type(jobs) is not int or jobs not in (1, 2):
        raise ValueError("Cached medical framing permits one or two workers")
    if output.exists():
        raise ValueError("Choose a fresh cached-reference output; no overwrite")
    if output.resolve().is_relative_to(prepared.resolve()) or prepared.resolve().is_relative_to(
        output.resolve()
    ):
        raise ValueError("Cached source and output must not contain one another")
    original, rows, documents, admitted = admit_medical(root, prepared, cache)
    requested = {row["id"] for row in rows} if topics is None else set(topics)
    if not requested or (topics is not None and len(requested) != len(topics)):
        raise ValueError("Select nonempty, unique cached topics")
    if requested - documents.keys():
        raise ValueError("Requested topics are not in the authenticated cache")
    policy = read_yaml(root / "config/build.yaml")["pdf"]
    maximum = Decimal(str(policy["max_file_mb"])) * 1_000_000
    if not maximum.is_finite() or maximum <= 0 or maximum != int(maximum):
        raise ValueError("Shared PDF budget must be positive whole bytes")
    env = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    sources = {
        name: digest(root / name)
        for name in [
            "src/ck/reference_recompose.py",
            "src/ck/zim2pdf.py",
            "src/ck/render.py",
            "src/ck/catalog.py",
            "src/ck/config.py",
            "src/ck/generated.py",
            "templates/reference.html.j2",
            "templates/reference-notes.css",
            "templates/source-math.css",
            "tools/recompose_medical_references.py",
            "Dockerfile.build",
            "config/debian.sources",
            "pyproject.toml",
            "uv.lock",
        ]
    }
    recipe = {
        "source_files": sources,
        "original": {
            key: value
            for key, value in admitted["provenance"].items()
            if key not in {"review_hold", "input_review_holds"}
        },
        "selected_topics": sorted(requested),
        "pdf_budget": policy,
        "tools": {name: version(name) for name in ["weasyprint", "pypdf"]},
    }
    fingerprint = hashlib.sha256(
        json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    files, audit = output / "files", output / "audit"
    files.mkdir(parents=True)
    audit.mkdir()
    rendered_rows, render_audits, tasks = [], [], []
    epoch = original["source_date_epoch"]
    for row in rows:
        if row["id"] not in requested:
            continue
        cached = documents[row["id"]]
        body = exact_main(cached["html"])
        # Keep the authenticated body styles; do not inherit unrelated core CSS changes.
        document = env.get_template("reference.html.j2").render(
            **row,
            body=Markup(body),
            fonts=["ck-font:///" + key for key in cached["aliases"]],
            timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
            reviewed=False,
            css=exact_style(cached["html"]),
        )
        if exact_main(document) != body:
            raise ValueError("Clinical main-body bytes changed during reframing")
        target = files / cached["filename"]
        aliases = {"ck-font:///" + key: admitted["fonts"][key] for key in cached["aliases"]}
        tasks.append((document, target, aliases, epoch, int(maximum)))
        (audit / target.with_suffix(".html").name).write_text(document)
        rendered_rows.append(dict(row))
        render_audits.append(
            {
                "id": row["id"],
                "filename": target.name,
                "original_pages": row["pages"],
                "original_html_sha256": hashlib.sha256(cached["html"].encode()).hexdigest(),
                "clinical_main_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "new_clinical_main_sha256": hashlib.sha256(
                    exact_main(document).encode()
                ).hexdigest(),
                "clinical_main_bytes_unchanged": True,
            }
        )
    if jobs == 1:
        results = list(map(render_cached_task, tasks))
    else:
        with ProcessPoolExecutor(
            max_workers=jobs, mp_context=get_context("spawn"), max_tasks_per_child=1
        ) as pool:
            try:
                results = list(pool.map(render_cached_task, tasks, chunksize=1))
            except BaseException:
                pool.shutdown(wait=True, cancel_futures=True)
                raise
    for row, audit_row, result in zip(rendered_rows, render_audits, results, strict=True):
        row["pages"] = audit_row["pages"] = result["pages"]
    for name in ("README.TXT", "00_Equation_Renderer_LICENSE.TXT"):
        shutil.copyfile(contained_file(prepared, "files/" + name), files / name)
    shutil.copyfile(contained_file(prepared, "archive-audits.json"), output / "archive-audits.json")
    (output / "articles.json").write_text(
        json.dumps(rendered_rows, indent=2, ensure_ascii=False) + "\n"
    )
    report = {
        **recipe,
        "original": admitted["provenance"],
        "articles": render_audits,
        "scope": "Cached framing only; original archives were not opened or restored.",
        "medical_review_status": "Unreviewed; all original human, rights, and source holds remain.",
        "original_pack_unchanged": True,
        "elapsed_seconds": time.monotonic() - started,
        "jobs": jobs,
        "worker_max_tasks": 1 if jobs == 2 else None,
        "parent_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "worker_peak_rss_kib": max(result["peak_rss_kib"] for result in results),
        "peak_rss_kib": max(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            max(result["peak_rss_kib"] for result in results),
        ),
        "cgroup": {
            name: Path("/sys/fs/cgroup", name).read_text()
            for name in ["memory.peak", "memory.events"]
            if Path("/sys/fs/cgroup", name).exists()
        },
    }
    (output / "recomposition.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    result = generation_manifest(
        output,
        "medical-cache-reframe-v1-" + fingerprint,
        {
            "medical_phone_pdfs": admitted["provenance"]["canonical_generation_sha256"],
            **{key: original["inputs"][key] for key in admitted["fonts"]},
        },
        complete=requested == set(documents) and original["complete"],
        epoch=epoch,
        intermediates=["articles.json", "recomposition.json", "archive-audits.json"],
        tool_versions="\n".join(f"{name}: {value}" for name, value in recipe["tools"].items()),
    )
    return {**result, "articles": len(rendered_rows), "recomposition": report}
