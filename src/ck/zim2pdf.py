"""Read pinned reference articles and regenerate offline, attributed phone PDFs."""

import hashlib
import json
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, date, datetime
from importlib.metadata import version
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pydantic import Field, model_validator
from weasyprint import HTML

from ck.catalog import Item
from ck.config import Configuration, Identifier, Model, Text, read_yaml
from ck.fetch import verify_zim
from ck.generated import cached_input, generation_manifest, verified_generated_files
from ck.reference_math import MathRenderer, math_source_id, prepare_equations, restore_equations
from ck.render import OfflineFetcher, pdf_timestamp


class Topic(Model):
    id: Identifier
    source: Identifier
    title: Text


class Topics(Model):
    status: str = Field(pattern="^(draft|reviewed)$")
    reviewer: str | None
    reviewed_on: str | None
    topics: list[Topic] = Field(min_length=1)

    @model_validator(mode="after")
    def named_review(self):
        if self.status == "reviewed" and not (self.reviewer and self.reviewed_on):
            raise ValueError("Reviewed medical selections need a named reviewer and date")
        if self.reviewed_on:
            date.fromisoformat(self.reviewed_on)
        return self


def article(html: str, expected_license: str, math_renderer=None) -> dict:
    source = BeautifulSoup(html, "html.parser")
    if source.select_one('meta[property="mw:PageProp/disambiguation"]'):
        raise ValueError("Reference selection resolves to a disambiguation page")
    if source.select_one('meta[name="ck-source-redirect"]'):
        raise ValueError(
            "Reference selection resolves to a source redirect; choose its canonical title"
        )
    footer = source.select_one(".zim-footer")
    if footer is None:
        raise ValueError("Article has no publisher source/date/license footer")
    origin = next(
        (
            link
            for link in footer.find_all("a", href=True)
            if re.search(r"\d{4}-\d{2}-\d{2}$", link.get("title", ""))
        ),
        None,
    )
    if origin is None or urlparse(origin["href"]).scheme != "https":
        raise ValueError("Article source URL or edit date is unconfirmed")
    revision = parse_qs(urlparse(origin["href"]).query).get("oldid", [])
    if len(revision) != 1 or not revision[0].isdigit():
        raise ValueError("Article source URL must identify an exact revision")
    modified = re.search(r"\d{4}-\d{2}-\d{2}$", origin["title"])[0]
    date.fromisoformat(modified)
    components = set(expected_license.split(" AND "))
    article_licenses = components - {"CC0-1.0"}
    version = (
        {"CC-BY-SA-4.0": "4.0", "CC-BY-SA-3.0": "3.0"}.get(next(iter(article_licenses)))
        if len(article_licenses) == 1
        else None
    )
    license_link = next(
        (
            link["href"]
            for link in footer.find_all("a", href=True)
            if link["href"].startswith("https://creativecommons.org/licenses/by-sa/")
            and f"/by-sa/{version}/" in link["href"]
        ),
        None,
    )
    if not version or not license_link:
        raise ValueError("Article license does not match the confirmed archive license")
    content = source.select_one("#mw-content-text > .mw-parser-output")
    if content is None:
        raise ValueError("Article main content is missing")
    for navigation in list(content.select(".navbox, .mw-editsection")):
        navigation.decompose()
    equations = prepare_equations(source, content, math_renderer)
    # The nopic archive replaces figures with empty SVG placeholders. Preserve
    # source alt text and captions; do not imply these are usable illustrations.
    media_count = 0
    for image in list(content.find_all(["img", "svg", "video", "audio"])):
        alternative = image.get("alt") or image.get("aria-label") or ""
        replacement = source.new_tag("span")
        replacement["class"] = "omitted-figure"
        replacement.string = (
            "[Source figure unavailable" + (": " + alternative if alternative else "") + "]"
        )
        image.replace_with(replacement)
        media_count += 1
    for element in list(
        content.select(
            "script, style, noscript, form, input, button, "
            "textarea, select, iframe, object, embed, base, link"
        )
    ):
        element.decompose()
    for element in content.find_all(True):
        element.attrs = {
            key: value
            for key, value in element.attrs.items()
            if key
            in {
                "id",
                "href",
                "class",
                "lang",
                "dir",
                "colspan",
                "rowspan",
                "scope",
                "headers",
                "title",
            }
        }
        if element.name == "a" and element.get("href"):
            href = element["href"]
            if not href.startswith("#") and urlparse(href).scheme != "https":
                # Preserve the words without making unsafe/unresolvable links.
                del element["href"]
    # An unbreakable source table cell can exceed a phone page vertically.
    # Keep cell coordinates and spans explicit while allowing prose to paginate.
    tables = list(enumerate(content.find_all("table"), 1))
    for table_number, table in reversed(tables):
        original_text = Counter(table.stripped_strings)
        section = source.new_tag("section", attrs={"class": "source-table"})
        if table.get("id"):
            section["id"] = table["id"]
        description = source.new_tag("p")
        description.string = (
            f"Source table {table_number}, reflowed row by row. "
            "Column numbers retain the original positions. "
            "Compare cells with the same column number."
        )
        section.append(description)
        caption = table.find("caption", recursive=False)
        if caption:
            caption.name = "p"
            section.append(caption.extract())
        occupied = {}
        rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
        for row_number, row in enumerate(rows, 1):
            if row.get("id"):
                section.append(source.new_tag("span", attrs={"id": row["id"]}))
            column = 1
            for cell in row.find_all(["td", "th"], recursive=False):
                while occupied.get(column, 0) >= row_number:
                    column += 1
                width = int(cell.get("colspan", 1))
                height = int(cell.get("rowspan", 1))
                if height == 0:
                    height = len(rows) - row_number + 1
                if width < 1 or height < 1:
                    raise ValueError("Source table has invalid cell spans")
                label = f"Row {row_number}, column {column}"
                if width > 1:
                    label += f" through {column + width - 1}"
                if height > 1:
                    label += f"; continues through row {row_number + height - 1}"
                label += " (header)" if cell.name == "th" else ""
                cell.name = "div"
                cell["class"] = ["source-cell"]
                marker = source.new_tag("p")
                emphasis = source.new_tag("strong")
                emphasis.string = label
                marker.append(emphasis)
                cell.insert(0, marker)
                section.append(cell.extract())
                for index in range(column, column + width):
                    occupied[index] = row_number + height - 1
                column += width
        if original_text - Counter(section.stripped_strings):
            raise ValueError("Source table contains text outside supported cells or captions")
        table.replace_with(section)
    headings = []
    for number, heading in enumerate(content.select("h2, h3, h4, h5, h6")):
        if not heading.get("id"):
            heading["id"] = f"ck-heading-{number}"
        headings.append({"id": heading["id"], "title": heading.get_text(" ", strip=True)})
    identifiers = {element["id"] for element in content.find_all(id=True)}
    broken_links = 0
    for link in content.find_all("a", href=True):
        if link["href"].startswith("#") and unquote(link["href"][1:]) not in identifiers:
            del link["href"]
            broken_links += 1
    converted, equation_audit = restore_equations(str(content), equations)
    return {
        "html": converted,
        "url": origin["href"],
        "modified": modified,
        "license_url": license_link,
        "omitted_media": media_count,
        "headings": headings,
        "omitted_broken_links": broken_links,
        "rendered_equations": equation_audit,
    }


def font_glyphs(fonts: list[Path]) -> set[int]:
    covered = set()
    for path in fonts:
        with TTFont(path) as font:
            covered.update(font.getBestCmap())
    return covered


def ensure_glyphs(text: str, covered: set[int]) -> None:
    missing = {
        character
        for character in text
        if ord(character) not in covered
        and not unicodedata.category(character).startswith(("C", "Z"))
    }
    if missing:
        raise ValueError(
            "Missing reference font glyphs: "
            + ", ".join(f"U+{ord(character):04X}" for character in sorted(missing))
        )


class ReferenceFetcher(OfflineFetcher):
    def __init__(self, fonts: dict[str, Path]):
        super().__init__([path.parent for path in fonts.values()])
        self.fonts = {url: path.resolve() for url, path in fonts.items()}

    def fetch(self, url, headers=None):
        if url not in self.fonts:
            raise ValueError(f"Unexpected reference resource: {url}")
        return super().fetch(self.fonts[url].as_uri(), headers)


def ensure_page_bounds(document) -> None:
    """Do not silently clip a source table or unbreakable reference line."""
    for number, page in enumerate(document.pages, 1):
        for box in page._page_box.descendants():
            if getattr(box, "text", "").strip() and (
                box.position_x < -0.5
                or box.position_x + box.width > page.width + 0.5
                or box.position_y < -0.5
                or box.position_y + box.height > page.height + 0.5
            ):
                raise ValueError(f"Reference text exceeds page {number}: {box.text[:80]}")


def render_article(task: tuple) -> int:
    document, target, fonts, epoch = task
    with pdf_timestamp(epoch):
        rendered = HTML(string=document, url_fetcher=ReferenceFetcher(fonts)).render(pdf_tags=True)
        ensure_page_bounds(rendered)
        rendered.write_pdf(
            target,
            pdf_tags=True,
            pdf_identifier=hashlib.sha256(document.encode()).hexdigest().encode(),
        )
    return len(rendered.pages)


def archive_source(
    item: Item, catalog: dict[str, Item], cache: Path, generated: Path, epoch: int
) -> tuple[Path, dict]:
    if item.family == "generated":
        manifest, payloads = verified_generated_files(item, generated / item.id, catalog)
        candidates = [path for name, path in payloads.items() if name.endswith(".zim")]
        if manifest["source_date_epoch"] != epoch or len(candidates) != 1:
            raise ValueError("Generated medical source needs one complete ZIM at this epoch")
        path = candidates[0]
        return path, verify_zim(path)
    if item.family != "zim":
        raise ValueError("Medical topics must refer to a pinned ZIM or generated ZIM edition")
    source_cache = cache if (cache / item.sha256).is_file() else cache / "quarantine"
    path = cached_input(item, source_cache)
    return path, verify_zim(path, regeneration_only=True, allow_broken_links=True)


def build_medpdf(
    root: Path,
    config: Configuration,
    catalog: dict[str, Item],
    cache: Path,
    output: Path,
    epoch: int,
    limit: int | None = None,
    jobs: int = 1,
    generated: Path | None = None,
) -> dict:
    from libzim.reader import Archive

    selection = Topics.model_validate(read_yaml(root / "catalog/medpdf_topics.yaml"))
    if len({topic.id for topic in selection.topics}) != len(selection.topics):
        raise ValueError("Medical topic IDs must be unique")
    if output.exists():
        raise ValueError("Medical PDF output must be new")
    if limit is not None and limit <= 0:
        raise ValueError("Development topic limit must be positive")
    if not 1 <= jobs <= 8:
        raise ValueError("Medical PDF worker count must be between one and eight")
    topics = selection.topics[:limit] if limit else selection.topics
    font_ids = set(read_yaml(root / "pipelines/zim2pdf/settings.yaml")["fonts"])
    math_id = math_source_id(root)
    inputs = {topic.source for topic in topics} | font_ids | {math_id}
    archives, audits = {}, {}
    for identifier in sorted(inputs - font_ids - {math_id}):
        path, audits[identifier] = archive_source(
            catalog[identifier], catalog, cache, generated or root / "build/generated", epoch
        )
        archives[identifier] = Archive(path)
    fonts = {
        f"ck-font:///{identifier}": cached_input(catalog[identifier], cache)
        for identifier in ["noto_sans", *sorted(font_ids - {"noto_sans"})]
    }
    coverage = font_glyphs(list(fonts.values()))
    env = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-medpdf-") as temporary,
        MathRenderer(root, catalog, cache) as math_renderer,
    ):
        stage = Path(temporary)
        files = stage / "files"
        files.mkdir()
        audit = stage / "audit"
        audit.mkdir()
        index = []
        tasks = []
        for number, topic in enumerate(topics, 1):
            archive = archives[topic.source]
            entry = archive.get_entry_by_title(topic.title)
            item = entry.get_item()
            if item.mimetype != "text/html":
                raise ValueError(f"Medical article is not HTML: {topic.id}")
            raw = bytes(item.content)
            data = article(raw.decode("utf-8"), catalog[topic.source].license, math_renderer)
            ensure_glyphs(BeautifulSoup(data["html"], "html.parser").get_text(), coverage)
            data.update(
                id=topic.id,
                title=item.title,
                entry_path=item.path,
                source_id=topic.source,
                source_version=catalog[topic.source].version,
                source_html_sha256=hashlib.sha256(raw).hexdigest(),
            )
            document = env.get_template("reference.html.j2").render(
                **data,
                body=Markup(data["html"]),
                fonts=list(fonts),
                timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
                reviewed=selection.status == "reviewed",
                css=(root / "templates/document.css").read_text(),
            )
            target = files / f"{number:03d}_{topic.id}.pdf"
            (audit / target.with_suffix(".html").name).write_text(document)
            tasks.append((document, target, fonts, epoch))
            index.append({key: value for key, value in data.items() if key != "html"})
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            for number, pages in enumerate(pool.map(render_article, tasks), 1):
                index[number - 1]["pages"] = pages
                print(
                    f"Rendered {number}/{len(topics)}: {topics[number - 1].id} ({pages} pages)",
                    file=sys.stderr,
                    flush=True,
                )
        (files / "README.TXT").write_text(
            "Medical reference PDFs — development conversion\n"
            "These articles still need named human medical review.\n"
            "Open START for the emergency instructions. Follow the printed cards.\n"
            "Source text and numbers are preserved; navigation and layout are adapted.\n"
            "Source figures are unavailable. Each PDF gives its source revision and license.\n"
            "The numbered files follow the draft selection in catalog/medpdf_topics.yaml.\n"
        )
        (files / "00_Equation_Renderer_LICENSE.TXT").write_text(math_renderer.notice)
        (stage / "articles.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
        (stage / "archive-audits.json").write_text(
            json.dumps(audits, sort_keys=True, indent=2) + "\n"
        )
        recipe = hashlib.sha256()
        for relative in (
            "src/ck/zim2pdf.py",
            "src/ck/reference_math.py",
            "src/ck/catalog.py",
            "src/ck/config.py",
            "src/ck/fetch.py",
            "src/ck/render.py",
            "src/ck/generated.py",
            "templates/reference.html.j2",
            "templates/source-math.css",
            "pipelines/math/render.mjs",
            "pipelines/math/settings.yaml",
            "templates/document.css",
            "catalog/medpdf_topics.yaml",
            "pipelines/zim2pdf/settings.yaml",
            "Dockerfile.build",
            "catalog/buildtools.yaml",
            "tools/bootstrap_zim.py",
            "config/debian.sources",
            "pyproject.toml",
            "uv.lock",
        ):
            recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
        result = generation_manifest(
            stage,
            "medpdf-v1-" + recipe.hexdigest(),
            {key: catalog[key].sha256 for key in sorted(inputs)},
            complete=limit is None,
            epoch=epoch,
            intermediates=["articles.json", "archive-audits.json"],
            tool_versions=(
                Path("/opt/ck-tool-versions.txt").read_text()
                + "\nlibzim: "
                + version("libzim")
                + math_renderer.versions
            ),
        )
        stage.rename(output)
    return {**result, "articles": len(index)}
