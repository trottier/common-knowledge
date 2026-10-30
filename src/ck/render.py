"""Offline Markdown → HTML → PDF with explicit fonts and deterministic dates."""

import hashlib
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markdown_it import MarkdownIt
from markupsafe import Markup
from pydantic import Field
from weasyprint import HTML
from weasyprint.urls import FatalURLFetchingError, URLFetcher, URLFetcherResponse

from ck.config import Configuration, Language, Model, read_yaml

_FONT_TIMESTAMP_LOCK = threading.RLock()


class Header(Model):
    title: str = Field(min_length=1)
    status: str = Field(pattern="^(draft|reviewed|machine)$")
    reviewer: str | None
    reviewed_on: str | None
    review_required: list[str] = Field(default_factory=list)


def content_file(path: Path) -> tuple[Header, str]:
    source = path.read_text(encoding="utf-8")
    if not source.startswith("---\n") or "\n---\n" not in source[4:]:
        raise ValueError(f"Missing content front matter: {path}")
    front, body = source[4:].split("\n---\n", 1)
    return Header.model_validate(yaml.safe_load(front)), body


class OfflineFetcher(URLFetcher):
    def __init__(self, roots: list[Path]):
        super().__init__(allowed_protocols={"data", "file"}, fail_on_errors=True)
        self.roots = [root.resolve() for root in roots]

    def fetch(self, url, headers=None):
        parsed = urlparse(url)
        if parsed.scheme == "data":
            return super().fetch(url, headers)
        if parsed.scheme == "file" and parsed.netloc in {"", "localhost"}:
            path = Path(unquote(parsed.path)).resolve()
            if any(path.is_relative_to(root) for root in self.roots):
                return URLFetcherResponse(url, body=path.read_bytes())
        raise FatalURLFetchingError(f"Resource outside offline build inputs: {url}")


def epoch_for(config: Configuration, explicit: int | None = None) -> int:
    value = explicit if explicit is not None else config.build.source_date_epoch
    if isinstance(value, str) and value.startswith("[[VERIFY"):
        value = os.environ.get("SOURCE_DATE_EPOCH", value)
    try:
        epoch = int(value)
        datetime.fromtimestamp(epoch, UTC)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            "Set a confirmed source_date_epoch or pass --epoch for development"
        ) from error
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH cannot be negative")
    return epoch


def font_files(root: Path, language: Language) -> list[Path]:
    cache = Path(os.environ.get("CK_FONT_CACHE", root / "cache"))
    catalog = {item["id"]: item for item in read_yaml(root / "catalog/fonts.yaml")}
    paths = []
    for identifier in dict.fromkeys([language.font, "noto_sans"]):
        if identifier not in catalog:
            raise ValueError(f"Missing font catalog entry: {identifier}")
        item = catalog[identifier]
        path = cache / item["sha256"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Fetch the verified build font {identifier} before rendering")
        paths.append(path.resolve())
    return paths


def render_html(
    root: Path,
    config: Configuration,
    source: Path,
    language: Language,
    page_format: str,
    epoch: int,
) -> str:
    header, body = content_file(source)
    content_env = Environment(undefined=StrictUndefined, autoescape=False)
    body = content_env.from_string(body).render(
        defaults=config.defaults.model_dump(), variants=config.variants.model_dump()
    )
    markdown = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = markdown.parse(body)
    headings = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            anchor = f"section-{len(headings) + 1}"
            token.attrSet("id", anchor)
            headings.append({"anchor": anchor, "title": tokens[index + 1].content})
    rendered = markdown.renderer.render(tokens, markdown.options, {})
    rendered = re.sub(
        r"\[\[VERIFY[^\]]*\]\]",
        lambda match: '<mark class="verify">' + match.group() + "</mark>",
        rendered,
    )
    source_file = root / "content/sources.yaml"
    sources = read_yaml(source_file) if source_file.exists() else {}
    citations = sorted(set(re.findall(r"\[@([a-z0-9_]+)\]", body)))
    missing = set(citations) - sources.keys()
    if missing:
        raise ValueError(f"Unknown citation ids: {', '.join(sorted(missing))}")
    for citation in citations:
        rendered = rendered.replace(
            f"[@{citation}]", f'<a href="#source-{citation}">[{citation}]</a>'
        )
    env = Environment(
        loader=FileSystemLoader(root / "templates"), undefined=StrictUndefined, autoescape=True
    )
    footer = ""
    if language.code == "es":
        footer = "Traducción automática sin revisar."
    elif language.status == "stub":
        footer = "[[VERIFY: localized unreviewed machine translation footer]]"
    fonts = font_files(root, language)
    return env.get_template("document.html.j2").render(
        title=header.title,
        language=language,
        body=Markup(rendered),
        headings=headings,
        sources={key: sources[key] for key in citations},
        page_format=page_format,
        timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
        footer=footer,
        fonts=[path.as_uri() for path in fonts],
        css=(root / "templates/document.css").read_text(),
        draft=header.status != "reviewed",
    )


def render_pdf(
    root: Path,
    config: Configuration,
    source: Path,
    language: Language,
    page_format: str,
    output: Path,
    epoch: int | None = None,
) -> Path:
    timestamp = epoch_for(config, epoch)
    document = render_html(root, config, source, language, page_format, timestamp)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".html").write_text(document, encoding="utf-8")
    fonts = font_files(root, language)
    fetcher = OfflineFetcher([root / "assets", *[path.parent for path in fonts]])
    identifier = hashlib.sha256(document.encode()).hexdigest().encode("ascii")
    # fontTools consults this environment variable when instantiating variable
    # fonts. Serialize this short environment override across renderer threads.
    with _FONT_TIMESTAMP_LOCK:
        previous_epoch = os.environ.get("SOURCE_DATE_EPOCH")
        os.environ["SOURCE_DATE_EPOCH"] = str(timestamp)
        try:
            HTML(string=document, url_fetcher=fetcher).write_pdf(
                output,
                pdf_identifier=identifier,
                pdf_tags=True,
            )
        finally:
            if previous_epoch is None:
                os.environ.pop("SOURCE_DATE_EPOCH", None)
            else:
                os.environ["SOURCE_DATE_EPOCH"] = previous_epoch
    return output
