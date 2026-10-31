"""Generate short Android-map instructions with explicit device-test gaps."""

import hashlib
import subprocess
from pathlib import Path

from ck.catalog import Item
from ck.config import Configuration
from ck.generated import generation_manifest
from ck.render import render_pdf


def build_howto(
    root: Path, config: Configuration, catalog: dict[str, Item], output: Path, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("Map how-to output must be new")
    files = output / "files"
    files.mkdir(parents=True)
    for code, basename in (("en", "HOW_TO"), ("es", "COMO_USAR")):
        language = next(language for language in config.languages if language.code == code)
        for page_format in ("phone", "print"):
            suffix = "" if page_format == "phone" else "_print"
            target = files / (basename + suffix + ".pdf")
            render_pdf(
                root,
                config,
                root / "content" / code / "android-maps.md",
                language,
                page_format,
                target,
                epoch,
                template="map-howto.html.j2",
            )
            audit = output / "audit"
            audit.mkdir(exist_ok=True)
            target.with_suffix(".html").rename(audit / target.with_suffix(".html").name)
            info = subprocess.run(
                ["pdfinfo", str(target)], check=True, capture_output=True, text=True
            )
            if not any(line.split() == ["Pages:", "1"] for line in info.stdout.splitlines()):
                raise ValueError("Map instructions must fit one page")
    recipe = hashlib.sha256()
    for relative in (
        "src/ck/androidhowto.py",
        "src/ck/render.py",
        "src/ck/locales.py",
        "templates/map-howto.html.j2",
        "templates/document.html.j2",
        "templates/document.css",
        "content/en/android-maps.md",
        "content/es/android-maps.md",
        "content/sources.yaml",
        "Dockerfile.build",
        "config/debian.sources",
        "uv.lock",
    ):
        recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
    return generation_manifest(
        output,
        "android-howto-v1-" + recipe.hexdigest(),
        {key: catalog[key].sha256 for key in ("noto_sans", "osmand_android")},
        complete=False,
        epoch=epoch,
    )
