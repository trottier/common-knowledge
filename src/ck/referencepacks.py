"""Curated, attributed phone references from an unchanged publisher ZIM."""

import hashlib
import json
import re
import tempfile
from datetime import UTC, date, datetime
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Literal

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pydantic import Field, model_validator

from ck.catalog import Collection, Item
from ck.config import Identifier, Model, Text, read_yaml
from ck.generated import cached_input, generation_manifest
from ck.reference_math import MathRenderer, math_source_id
from ck.zim2pdf import archive_source, article, ensure_glyphs, font_glyphs, render_article


class Pack(Model):
    title: Text
    source: Identifier
    collection: Identifier
    status: Literal["draft", "reviewed"]
    reviewer: Text | None
    reviewed_on: Text | None
    paths: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def selection(self):
        if len(set(self.paths)) != len(self.paths):
            raise ValueError("Reference paths must be unique")
        if any(
            path.startswith("/") or ".." in PurePosixPath(path).parts or "\x00" in path
            for path in self.paths
        ):
            raise ValueError("Reference paths must be archive-relative")
        if self.status == "reviewed" and not (self.reviewer and self.reviewed_on):
            raise ValueError("Reviewed references need a named reviewer and date")
        if self.reviewed_on:
            date.fromisoformat(self.reviewed_on)
        return self


def selections(root: Path) -> dict[str, Pack]:
    return {
        key: Pack.model_validate(value)
        for key, value in read_yaml(root / "pipelines/referencepacks/selection.yaml").items()
    }


def filename(number: int, path: str) -> str:
    # Source paths may contain colons, quotes or long titles. Never copy them
    # directly into a FAT path, and retain a digest to disambiguate truncation.
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")[:60] or "article"
    return f"{number:03d}_{slug}_{hashlib.sha256(path.encode()).hexdigest()[:12]}.pdf"


def build_reference_pack(
    root: Path, catalog: dict[str, Item], cache: Path, output: Path, epoch: int, pack_id: str
) -> dict:
    from libzim.reader import Archive

    pack = selections(root)[pack_id]
    target = catalog[pack_id]
    if (
        not isinstance(target.placement, Collection)
        or target.placement.collection != pack.collection
        or set(target.license.split(" AND ")) != {catalog[pack.source].license, "CC0-1.0"}
    ):
        raise ValueError("Reference placement or license differs from its source selection")
    font_ids = read_yaml(root / "pipelines/referencepacks/settings.yaml")["fonts"]
    input_ids = {pack.source, *font_ids, math_source_id(root)}
    if set(target.inputs) != input_ids:
        raise ValueError("Reference catalog inputs differ from the selection and fonts")
    if output.exists():
        raise ValueError("Reference output must be new")
    path, audit = archive_source(
        catalog[pack.source], catalog, cache, root / "build/generated", epoch
    )
    archive = Archive(path)
    fonts = {
        f"ck-font:///{identifier}": cached_input(catalog[identifier], cache)
        for identifier in font_ids
    }
    covered = font_glyphs(list(fonts.values()))
    env = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-reference-") as temporary,
        MathRenderer(root, catalog, cache) as math_renderer,
    ):
        stage = Path(temporary)
        files = stage / "files"
        files.mkdir()
        index = []
        for number, entry_path in enumerate(pack.paths, 1):
            entry = archive.get_entry_by_path(entry_path)
            if entry.is_redirect:
                raise ValueError(f"Select a canonical reference article: {entry_path}")
            source = entry.get_item()
            if source.mimetype != "text/html":
                raise ValueError(f"Reference article is not HTML: {entry_path}")
            raw = bytes(source.content)
            data = article(raw.decode("utf-8"), catalog[pack.source].license, math_renderer)
            ensure_glyphs(BeautifulSoup(data["html"], "html.parser").get_text(), covered)
            document = env.get_template("collection-reference.html.j2").render(
                **data,
                title=source.title,
                body=Markup(data["html"]),
                pack=pack,
                fonts=list(fonts),
                timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
                source_version=catalog[pack.source].version,
                css=(root / "templates/document.css").read_text(),
            )
            name = filename(number, entry_path)
            pages = render_article((document, files / name, fonts, epoch))
            index.append(
                {
                    **{key: value for key, value in data.items() if key != "html"},
                    "title": source.title,
                    "entry_path": entry_path,
                    "source_html_sha256": hashlib.sha256(raw).hexdigest(),
                    "file": name,
                    "pages": pages,
                }
            )
        notice = (
            f"{pack.title}\nSource: {catalog[pack.source].title}, {catalog[pack.source].version}\n"
            f"{catalog[pack.source].attribution}\n{catalog[pack.source].license_proof_url}\n"
            "Draft reference selection; source accuracy and suitability need human review.\n"
            "Text-only conversion: source figures are unavailable. This can omit essential\n"
            "information. Do not use it as a substitute for training or illustrated instructions.\n"
            "Follow START and the printed cards when guidance differs.\n"
            "Article text, source revision links and license notices are retained.\n"
            "Navigation and table layout are adapted for phones.\n\n"
            "Source MathML equations are rendered as vector graphics by the pinned MathJax tool.\n"
        )
        (files / "00_README.TXT").write_text(
            notice + "\n".join(f"{row['file']} — {row['title']}" for row in index) + "\n"
        )
        (files / f"00_{pack_id}_LICENSE.TXT").write_text(math_renderer.notice)
        (stage / "articles.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
        (stage / "archive-audit.json").write_text(
            json.dumps(audit, sort_keys=True, indent=2) + "\n"
        )
        recipe = hashlib.sha256()
        for relative in (
            "src/ck/referencepacks.py",
            "src/ck/reference_math.py",
            "src/ck/zim2pdf.py",
            "src/ck/catalog.py",
            "src/ck/config.py",
            "src/ck/fetch.py",
            "src/ck/render.py",
            "src/ck/generated.py",
            "templates/collection-reference.html.j2",
            "templates/source-math.css",
            "pipelines/math/render.mjs",
            "pipelines/math/settings.yaml",
            "templates/document.css",
            "pipelines/referencepacks/selection.yaml",
            "pipelines/referencepacks/settings.yaml",
            "Dockerfile.build",
            "catalog/buildtools.yaml",
            "tools/bootstrap_zim.py",
            "config/debian.sources",
            "pyproject.toml",
            "uv.lock",
        ):
            recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
        manifest = generation_manifest(
            stage,
            "reference-pack-v1-" + recipe.hexdigest(),
            {key: catalog[key].sha256 for key in sorted(input_ids)},
            complete=True,
            epoch=epoch,
            intermediates=["articles.json", "archive-audit.json"],
            tool_versions=Path("/opt/ck-tool-versions.txt").read_text()
            + "\nlibzim: "
            + version("libzim")
            + math_renderer.versions,
        )
        stage.rename(output)
    return {**manifest, "articles": len(index)}
