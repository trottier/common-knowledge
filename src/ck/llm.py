"""Pinned base-model checks and offline local LLM launch materials."""

import hashlib
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ck.catalog import Item
from ck.config import Configuration, LocalLLM, read_yaml
from ck.generated import cached_input, generation_manifest
from ck.render import content_file, render_pdf


def settings_for(root: Path) -> LocalLLM:
    return LocalLLM.model_validate(read_yaml(root / "pipelines/llm/settings.yaml"))


def model_metadata(path: Path, item: Item, context_tokens: int) -> dict:
    from gguf import GGUFReader, LlamaFileType

    if item.license not in {"Apache-2.0", "MIT"} or path.stat().st_size > 2_500_000_000:
        raise ValueError("Model license or file size fails the v0.1 selection rules")
    reader = GGUFReader(path)
    fields = {
        key: value.contents()
        for key, value in reader.fields.items()
        if key.startswith("general.") or key.endswith("context_length")
    }
    architecture = fields.get("general.architecture")
    if fields.get("general.license", "").casefold() != item.license.casefold():
        raise ValueError("GGUF license metadata disagrees with the catalog")
    context = fields.get(f"{architecture}.context_length", 0)
    quantization = fields.get("general.file_type")
    if quantization not in {
        int(LlamaFileType.MOSTLY_Q4_0),
        int(LlamaFileType.MOSTLY_Q4_1),
        int(LlamaFileType.MOSTLY_Q4_K_S),
        int(LlamaFileType.MOSTLY_Q4_K_M),
    }:
        raise ValueError("Selected model must be a supported four-bit GGUF")
    if fields.get("general.finetune") != "Base" and "Base" not in fields.get("general.name", ""):
        raise ValueError("Untuned base-model provenance is missing from the selected GGUF")
    parameters = sum(int(tensor.n_elements) for tensor in reader.tensors)
    if not 0 < parameters <= 4_000_000_000 or context < max(32768, context_tokens):
        raise ValueError("Model parameter count or context fails the v0.1 selection rules")
    return {
        "fields": fields,
        "parameters_in_file": parameters,
        "native_context_tokens": context,
        "source_id": item.id,
        "sha256": item.sha256,
    }


def start_text(
    root: Path, language: str, config: Configuration, epoch: int, profile: str = "full"
) -> str:
    from bs4 import BeautifulSoup

    from ck.render import render_html

    edition = next(edition for edition in config.languages if edition.code == language)
    sections = []
    for path in sorted((root / f"content/{language}/start").glob("*.md")):
        header, _ = content_file(path)
        soup = BeautifulSoup(
            render_html(root, config, path, edition, "phone", epoch, profile=profile), "html.parser"
        )
        body = soup.select_one("main").get_text("\n", strip=True)
        sources = soup.select_one("section.sources")
        sections.append(
            f"# {header.title}\n{body}\n" + (sources.get_text("\n", strip=True) if sources else "")
        )
    return "\n\n".join(sections)


def system_prompt(root: Path, settings: LocalLLM, language: str, source: str) -> tuple[str, dict]:
    if language not in {"en", "es"}:
        raise ValueError("A local LLM bundle needs an English or Spanish START edition")
    template = Environment(
        loader=FileSystemLoader(root / "pipelines/llm"), autoescape=False, undefined=StrictUndefined
    ).get_template("system_prompt.md")
    titles = [line[2:] for line in source.splitlines() if line.startswith("# ")]

    def render(text):
        return template.render(
            warning=settings.warning if language == "en" else settings.warning_es,
            language_name="English" if language == "en" else "Español",
            start_text=text,
            section_titles=titles,
        )

    budget = (
        settings.context_tokens
        - settings.max_output_tokens
        - settings.context_reserve_tokens
        - 2 * settings.message_reserve_tokens
        - 1
    )
    prompt = render(source)
    mode = "full"
    if len(prompt.encode()) > budget:
        prompt, mode = render(""), "section_index"
    if len(prompt.encode()) > budget:
        raise ValueError("START section index exceeds the conservative context budget")
    notices = {
        "full": {
            "en": "The local LLM is supplied the full START text. Read START before acting.",
            "es": "El LLM local recibe el texto completo de START. Lea START antes de actuar.",
        },
        "section_index": {
            "en": (
                "The local LLM is supplied only START section titles. Read START for instructions."
            ),
            "es": (
                "El LLM local recibe solo los títulos de START. Lea START para las instrucciones."
            ),
        },
    }
    return prompt, {
        "mode": mode,
        "notice": notices[mode][language],
        "start_bytes": len(source.encode()),
        "prompt_bytes": len(prompt.encode()),
        "prompt_byte_budget": budget,
    }


def build_bundle(
    root: Path,
    config: Configuration,
    catalog: dict[str, Item],
    cache: Path,
    output: Path,
    profile: str,
    epoch: int,
) -> dict:
    if output.exists():
        raise ValueError("Local LLM bundle output must be new")
    settings = settings_for(root)
    if profile not in settings.models:
        raise ValueError("Local LLM bundles are built for sample or full profiles")
    model_id = settings.models[profile]
    license_id = "qwen_sample_license" if profile == "sample" else "qwen_full_license"
    inputs = {
        model_id,
        "llamafile_runner",
        "llamafile_license",
        license_id,
        "pocketpal_license",
        "noto_sans",
        "noto_sans_license",
        "llamafile_llama_notices",
    }
    paths = {identifier: cached_input(catalog[identifier], cache) for identifier in sorted(inputs)}
    metadata = model_metadata(paths[model_id], catalog[model_id], settings.context_tokens)
    templates = Environment(
        loader=FileSystemLoader(root / "pipelines/llm"), autoescape=False, undefined=StrictUndefined
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-local-llm-") as temporary:
        stage = Path(temporary)
        files = stage / "files"
        ui = files / "ui"
        ui.mkdir(parents=True)
        shutil.copyfile(paths["llamafile_runner"], files / settings.runner_filename)
        (files / "WARNING.TXT").write_text(settings.warning + "\n\n" + settings.warning_es + "\n")
        licenses = files / "LICENSES"
        licenses.mkdir()
        for identifier in (
            "llamafile_license",
            license_id,
            "pocketpal_license",
            "noto_sans_license",
            "llamafile_llama_notices",
        ):
            shutil.copyfile(paths[identifier], licenses / f"{identifier}.txt")
        shutil.copyfile(root / "LICENSE", licenses / "Apache-2.0.txt")
        shutil.copyfile(root / "LICENSE-CONTENT", licenses / "Original-content-CC0.txt")
        context = {
            **settings.model_dump(),
            "timestamp": datetime.fromtimestamp(epoch, UTC).isoformat(),
        }
        for source, target in (
            ("launch.sh.j2", "launch.sh"),
            ("launch.ps1.j2", "launch.ps1"),
            ("windows.bat.j2", "Start Local LLM - Windows.bat"),
        ):
            text = templates.get_template(source).render(**context)
            if target.endswith((".bat", ".ps1")):
                text = text.replace("\n", "\r\n")
            (files / target).write_bytes(text.encode("utf-8"))
        for name in ("Start Local LLM - Mac.command", "Start Local LLM - Linux.sh"):
            (files / name).write_text('#!/bin/sh\nexec /bin/sh "$(dirname "$0")/launch.sh"\n')
        for name in ("index.html", "app.js", "style.css"):
            shutil.copyfile(root / "pipelines/llm/ui" / name, ui / name)
        grounding = {}
        for language in ("en", "es"):
            source = start_text(root, language, config, epoch, profile)
            prompt, grounding[language] = system_prompt(root, settings, language, source)
            (ui / f"start-{language}.txt").write_text(source)
            (ui / f"system-{language}.txt").write_text(prompt)
        (ui / "settings.json").write_text(
            json.dumps(
                {
                    "model": settings.model_alias,
                    "warning": settings.warning,
                    "warning_es": settings.warning_es,
                    "max_output_tokens": settings.max_output_tokens,
                    "max_question_chars": settings.max_question_chars,
                    "temperature": settings.temperature,
                    "grounding": grounding,
                    "context_tokens": settings.context_tokens,
                    "context_reserve_tokens": settings.context_reserve_tokens,
                    "message_reserve_tokens": settings.message_reserve_tokens,
                }
            )
            + "\n"
        )
        (stage / "model.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
        audit = stage / "audit"
        audit.mkdir()
        for code, name in (("en", "HOW_TO"), ("es", "COMO_USAR")):
            edition = next(edition for edition in config.languages if edition.code == code)
            for page_format in ("phone", "print"):
                suffix = "" if page_format == "phone" else "_print"
                target = files / f"{name}{suffix}.pdf"
                render_pdf(
                    root,
                    config,
                    root / f"content/{code}/local-llm.md",
                    edition,
                    page_format,
                    target,
                    epoch,
                )
                target.with_suffix(".html").rename(audit / target.with_suffix(".html").name)
        (files / "SOURCE.TXT").write_text(
            f"Model: {catalog[model_id].title}\n{catalog[model_id].url}\n"
            f"SHA-256: {catalog[model_id].sha256}\n{catalog[model_id].attribution}\n"
            "Untuned base model; no project tuning or evaluation claim.\n"
            "The model is placed separately as Model.gguf when included by the plan.\n"
        )
        recipe = hashlib.sha256()
        for directory in (root / "pipelines/llm", root / "content/en", root / "content/es"):
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    recipe.update(
                        path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes()
                    )
        for name in (
            "src/ck/llm.py",
            "src/ck/render.py",
            "src/ck/locales.py",
            "src/ck/generated.py",
            "config/defaults.yaml",
            "config/languages.yaml",
            "content/sources.yaml",
            "templates/document.html.j2",
            "templates/document.css",
            "Dockerfile.build",
            "pyproject.toml",
            "uv.lock",
            "LICENSE",
            "LICENSE-CONTENT",
        ):
            recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
        result = generation_manifest(
            stage,
            "local-llm-v1-" + recipe.hexdigest(),
            {identifier: catalog[identifier].sha256 for identifier in sorted(inputs)},
            complete=True,
            epoch=epoch,
            intermediates=["model.json"],
            tool_versions=Path("/opt/ck-tool-versions.txt").read_text(),
        )
        stage.rename(output)
    return result
