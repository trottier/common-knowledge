import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject

from ck.catalog import Item, load_catalog
from ck.generated import generation_manifest
from ck.reference_recompose import admit_medical, digest, exact_main, recompose_medical

ROOT = Path(__file__).resolve().parents[1]


def test_reference_framing_separates_source_notes_without_altering_body():
    body = '<h2 id="fixture">Synthetic, never guidance</h2><p>Fixture: 2.5; 12–18.</p>'
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined
    )
    for template in ("reference.html.j2", "collection-reference.html.j2"):
        document = env.get_template(template).render(
            title="Synthetic reference",
            modified="2000-01-01",
            source_version="fixture",
            url="https://example.invalid/revision?oldid=1",
            license_url="https://example.invalid/license",
            body=Markup(body),
            headings=[],
            fonts=[],
            timestamp="2000-01-01T00:00:00+00:00",
            css="",
            reviewed=False,
            pack={"status": "draft", "title": "Fixture pack", "collection": "med_lib"},
        )
        assert exact_main(document) == body
        soup = BeautifulSoup(document, "html.parser")
        assert (
            soup.select_one(".review-notice").get_text(strip=True)
            == "Unreviewed medical reference."
        )
        assert "DEVELOPMENT CONVERSION" not in soup.get_text()
        notes = soup.select_one("aside.publication-notes")
        assert "Article last edited: 2000-01-01" in notes.get_text()
        assert "Formatting and offline navigation" in notes.get_text()
        assert notes.find("a", href="https://example.invalid/revision?oldid=1")
        assert notes.find("a", href="https://example.invalid/license")
        assert "If 911 does not answer" in soup.get_text()
        assert "font-size: 8pt" in soup.style.string


@pytest.mark.parametrize("body", ["<main>A</main><main>B</main>", "No body", "<main>Open"])
def test_ambiguous_cached_clinical_body_is_rejected(body):
    with pytest.raises(ValueError, match="ambiguous"):
        exact_main(body)


@pytest.fixture
def cached_fixture(tmp_path, monkeypatch):
    source_font = load_catalog(ROOT)["noto_sans"]
    cache = Path(os.environ.get("CK_FONT_CACHE", ROOT / "cache"))
    if not (cache / source_font.sha256).is_file():
        if "CK_FONT_CACHE" in os.environ:
            pytest.fail("Authoritative font cache lacks pinned Noto Sans")
        pytest.skip("Requires the existing pinned font cache")
    assert digest(cache / source_font.sha256) == source_font.sha256
    root, prepared = tmp_path / "root", tmp_path / "prepared"
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
        "config/build.yaml",
        "pyproject.toml",
        "uv.lock",
    ]:
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (prepared / "files").mkdir(parents=True)
    (prepared / "audit").mkdir()
    rows = []
    for index, identifier in enumerate(["fixture_a", "fixture_b"], 1):
        body = f'<h2 id="topic">Synthetic {identifier}</h2><p>Fixture numbers: 2.5; 12–18.</p>'
        document = (
            "<html><head><style>@font-face {font-family:CK; "
            'src:url("ck-font:///noto_sans")} body{font-size:12pt}</style></head>'
            "<body><main>" + body + "</main></body></html>"
        )
        (prepared / "audit" / f"{index:03d}_{identifier}.html").write_text(document)
        writer = PdfWriter()
        writer.add_blank_page(width=255, height=454)
        writer._ID = ArrayObject(
            [
                ByteStringObject(hashlib.sha256(document.encode()).hexdigest().encode()),
                ByteStringObject(b"fixture"),
            ]
        )
        writer.write(prepared / "files" / f"{index:03d}_{identifier}.pdf")
        rows.append(
            {
                "id": identifier,
                "title": "Synthetic, never guidance",
                "url": "https://example.invalid/revision?oldid=1",
                "license_url": "https://example.invalid/license",
                "modified": "2000-01-01",
                "source_version": "fixture",
                "headings": [{"id": "topic", "title": f"Synthetic {identifier}"}],
                "pages": 1,
            }
        )
    (prepared / "files/README.TXT").write_text("Synthetic selection; unreviewed")
    (prepared / "files/00_Equation_Renderer_LICENSE.TXT").write_text(
        "Synthetic notice; never shipped"
    )
    (prepared / "articles.json").write_text(json.dumps(rows))
    (prepared / "archive-audits.json").write_text('{"historical_fixture":true}')
    summary = generation_manifest(
        prepared,
        "synthetic-v1",
        {"noto_sans": source_font.sha256},
        complete=True,
        epoch=1793404800,
        intermediates=["articles.json", "archive-audits.json"],
    )
    item = Item(
        id="medical_phone_pdfs",
        family="generated",
        title="Synthetic fixture",
        version="fixture",
        size_bytes=summary["size_bytes"],
        sha256=summary["sha256"],
        license="CC-BY-SA-4.0",
        attribution="Synthetic fixture",
        license_proof_url="https://example.invalid/license",
        placement="universal",
        dest="5_MEDICAL_REFERENCE/pdf/",
        profiles=["full"],
        inputs=["noto_sans"],
        pipeline_version="synthetic-v1",
        review="[[VERIFY: fixture review]]",
    )
    monkeypatch.setattr(
        "ck.reference_recompose.load_catalog",
        lambda _: {"medical_phone_pdfs": item, "noto_sans": source_font},
    )
    return root, prepared, cache, rows


def test_cache_admission_rejects_changed_html(cached_fixture):
    root, prepared, cache, _ = cached_fixture
    with (prepared / "audit/001_fixture_a.html").open("a") as stream:
        stream.write("Changed")
    with pytest.raises(ValueError, match="original PDF ID"):
        admit_medical(root, prepared, cache)


def test_cache_reframe_never_opens_archives_or_changes_clinical_body(cached_fixture, monkeypatch):
    root, prepared, cache, _ = cached_fixture
    original_manifest = (prepared / "generation.json").read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("Cached framing must not open archives or run MathJax")

    monkeypatch.setattr("ck.zim2pdf.archive_source", forbidden)
    monkeypatch.setattr("ck.zim2pdf.MathRenderer", forbidden)
    output = root / "new-proof"
    result = recompose_medical(root, prepared, cache, output, ["fixture_a"])
    assert result["articles"] == 1
    metadata = json.loads((output / "generation.json").read_text())
    assert metadata["complete"] is False
    assert metadata["source_date_epoch"] == 1793404800
    report = result["recomposition"]
    assert report["original"]["review_hold"] == "[[VERIFY: fixture review]]"
    assert report["original"]["archive_accessed"] is False
    assert (
        report["articles"][0]["clinical_main_sha256"]
        == report["articles"][0]["new_clinical_main_sha256"]
    )
    assert (prepared / "generation.json").read_bytes() == original_manifest
    old = (prepared / "audit/001_fixture_a.html").read_text()
    new = (output / "audit/001_fixture_a.html").read_text()
    assert exact_main(new) == exact_main(old)
    pdf = PdfReader(output / "files/001_fixture_a.pdf")
    text = " ".join(" ".join(page.extract_text() for page in pdf.pages).split())
    assert "Unreviewed medical reference." in text and "2.5; 12–18." in text
    assert str(pdf.metadata["/CreationDate"]).startswith("D:20261031000000")
    assert (output / "files/00_Equation_Renderer_LICENSE.TXT").read_bytes() == (
        prepared / "files/00_Equation_Renderer_LICENSE.TXT"
    ).read_bytes()


def test_cache_reframe_rejects_output_containment(cached_fixture):
    root, prepared, cache, _ = cached_fixture
    with pytest.raises(ValueError, match="contain"):
        recompose_medical(root, prepared, cache, prepared / "child", ["fixture_a"])


@pytest.mark.parametrize("jobs", [0, 3, True])
def test_cached_worker_budget_rejects_invalid_counts(tmp_path, jobs):
    with pytest.raises(ValueError, match="one or two"):
        recompose_medical(tmp_path, tmp_path, tmp_path, tmp_path / "output", None, jobs=jobs)


def test_two_spawn_workers_preserve_pdf_bytes_and_receipt_order(cached_fixture):
    root, prepared, cache, _ = cached_fixture
    first = recompose_medical(root, prepared, cache, root / "serial", None, jobs=1)
    second = recompose_medical(root, prepared, cache, root / "parallel", None, jobs=2)
    assert first["pipeline_version"] == second["pipeline_version"]
    assert [row["id"] for row in second["recomposition"]["articles"]] == ["fixture_a", "fixture_b"]
    assert second["recomposition"]["jobs"] == 2
    for name in ("001_fixture_a.pdf", "002_fixture_b.pdf"):
        assert (root / "serial/files" / name).read_bytes() == (
            root / "parallel/files" / name
        ).read_bytes()
    assert json.loads((root / "parallel/generation.json").read_text())["complete"] is True
