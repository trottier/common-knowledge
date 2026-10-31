"""Convert pinned Wikivoyage phrasebooks with original article provenance."""

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from ck.catalog import Item
from ck.config import Configuration, Identifier, Model, Text, read_yaml
from ck.fetch import verify_zim
from ck.generated import cached_input, generation_manifest
from ck.zim2pdf import article, ensure_glyphs, font_glyphs, render_article


class Selection(Model):
    source: Identifier
    title: Text
    source_language: Literal["en", "es"]


def build_phrasebooks(
    root: Path,
    config: Configuration,
    catalog: dict[str, Item],
    cache: Path,
    output: Path,
    epoch: int,
) -> dict:
    from libzim.reader import Archive

    if output.exists():
        raise ValueError("Phrasebook output must be new")
    selection = {
        code: Selection.model_validate(value)
        for code, value in read_yaml(root / "pipelines/phrasebooks/selection.yaml").items()
    }
    if set(selection) != {edition.code for edition in config.languages}:
        raise ValueError("Every edition needs exactly one phrasebook selection")
    font_ids = set(read_yaml(root / "pipelines/phrasebooks/settings.yaml")["fonts"])
    fonts = {
        f"ck-font:///{key}": cached_input(catalog[key], cache)
        for key in ["noto_sans", *sorted(font_ids - {"noto_sans"})]
    }
    covered = font_glyphs(list(fonts.values()))
    archives, audits = {}, {}
    for key in sorted({value.source for value in selection.values()}):
        item = catalog[key]
        if item.family != "zim" or item.license != "CC-BY-SA-4.0":
            raise ValueError("Phrasebook input must be a confirmed CC BY-SA 4.0 ZIM")
        source_cache = cache if (cache / item.sha256).is_file() else cache / "quarantine"
        source = cached_input(item, source_cache)
        audits[key] = verify_zim(source, regeneration_only=True, allow_broken_links=True)
        archives[key] = Archive(source)
    templates = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    recipe = hashlib.sha256()
    for name in (
        "src/ck/phrasebooks.py",
        "src/ck/zim2pdf.py",
        "src/ck/generated.py",
        "src/ck/fetch.py",
        "templates/phrasebook.html.j2",
        "templates/document.css",
        "pipelines/phrasebooks/selection.yaml",
        "pipelines/phrasebooks/settings.yaml",
        "config/languages.yaml",
        "Dockerfile.build",
        "pyproject.toml",
        "uv.lock",
    ):
        recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
    pipeline = "phrasebooks-v1-" + recipe.hexdigest()
    results = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-phrasebooks-") as temporary:
        stage = Path(temporary)
        for number, edition in enumerate(config.languages, 1):
            chosen = selection[edition.code]
            entry = archives[chosen.source].get_entry_by_title(chosen.title).get_item()
            if entry.mimetype != "text/html":
                raise ValueError("Phrasebook selection did not resolve to HTML")
            raw = bytes(entry.content)
            data = article(raw.decode("utf-8"), catalog[chosen.source].license)
            ensure_glyphs(BeautifulSoup(data["html"], "html.parser").get_text(), covered)
            directory = stage / edition.code
            files = directory / "files"
            files.mkdir(parents=True)
            document = templates.get_template("phrasebook.html.j2").render(
                **data,
                body=Markup(data["html"]),
                title=entry.title,
                edition_name=edition.name,
                source_language=chosen.source_language,
                source_language_name={"en": "English", "es": "Español"}[chosen.source_language],
                fonts=list(fonts),
                timestamp=datetime.fromtimestamp(epoch, UTC).isoformat(),
                source_version=catalog[chosen.source].version,
                css=(root / "templates/document.css").read_text(),
            )
            filename = f"{number:02d}_{edition.code}_phrasebook.pdf"
            pages = render_article((document, files / filename, fonts, epoch))
            (directory / "article.html").write_text(document)
            audit = {key: value for key, value in data.items() if key != "html"}
            audit.update(
                source_html_sha256=hashlib.sha256(raw).hexdigest(),
                source_id=chosen.source,
                entry_path=entry.path,
                title=entry.title,
                pages=pages,
                target_language=edition.code,
                source_language=chosen.source_language,
                archive_audit=audits[chosen.source],
            )
            (directory / "audit.json").write_text(
                json.dumps(audit, sort_keys=True, indent=2) + "\n"
            )
            inputs = font_ids | {chosen.source}
            results[edition.code] = generation_manifest(
                directory,
                pipeline,
                {key: catalog[key].sha256 for key in sorted(inputs)},
                complete=True,
                epoch=epoch,
                intermediates=["audit.json"],
                tool_versions=Path("/opt/ck-tool-versions.txt").read_text(),
            )
            print(f"Rendered phrasebook {edition.code}: {pages} pages", flush=True)
        stage.rename(output)
    return results
