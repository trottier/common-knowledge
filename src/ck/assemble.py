"""Build a complete, checked drive tree using exact catalog bytes."""

import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from ck.catalog import Item, Modules, attributions, load_catalog, safe_path
from ck.config import Configuration
from ck.core import verify_core
from ck.drive_safety import validate_tree
from ck.fetch import digest, fetch
from ck.planner import plan_variants, selected
from ck.render import epoch_for
from ck.review import require_release_ready


def core_size(core: Path) -> int:
    files = list(core.glob("*/*.pdf"))
    if not files:
        raise ValueError("Build the core PDFs before planning or assembly")
    # Exact PDF copies: START/variant PDFs in START, phone PDFs and card/tags in
    # PHONE_PACK, then the same two directories again in BACKUP.
    primary = sum(path.stat().st_size * (2 if "_phone" in path.name else 1) for path in files)
    html = sum(path.stat().st_size for path in core.glob("*/01_START_phone.html"))
    return primary * 2 + html


def destination(item: Item, config: Configuration, number: int) -> str:
    dest = item.dest
    if "{module}" in dest:
        if not isinstance(item.placement, Modules):
            raise ValueError(f"{item.id}: module destination requires module placement")
        choices = sorted(
            set(item.placement.modules) & set(config.variants.variants[number].modules)
        )
        if not choices:
            raise ValueError(f"{item.id}: no matching module")
        dest = dest.replace("{module}", choices[0])
    return dest


def copy_exact(source: Path, target: Path, checksum: str | None = None) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Expected a regular build input: {source}")
    if checksum is not None and digest(source) != checksum:
        raise ValueError(f"Build input checksum mismatch: {source.name}")
    if target.exists():
        raise ValueError(f"Two inputs target the same drive file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def write_manifest(root: Path) -> str:
    files = validate_tree(root)
    lines = [
        f"{digest(path)}  {path.relative_to(root).as_posix()}\n"
        for path in files
        if path.relative_to(root).as_posix() != "MANIFEST.SHA256"
    ]
    target = root / "MANIFEST.SHA256"
    target.write_text("".join(lines), encoding="utf-8")
    return digest(target)


def check_manifest(root: Path) -> None:
    actual = {
        path.relative_to(root).as_posix(): path
        for path in validate_tree(root)
        if path.relative_to(root).as_posix() != "MANIFEST.SHA256"
    }
    expected = {}
    for line in (root / "MANIFEST.SHA256").read_text(encoding="utf-8").splitlines():
        checksum, relative = line.split("  ", 1)
        safe_path(relative)
        if relative in expected or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid or duplicate manifest entry")
        expected[relative] = checksum
    if set(expected) != set(actual):
        raise ValueError("Manifest file set does not match the tree")
    for relative, checksum in expected.items():
        if digest(actual[relative]) != checksum:
            raise ValueError(f"Manifest checksum mismatch: {relative}")


def _copy_core(config: Configuration, core: Path, tree: Path) -> list[str]:
    editions = []
    for language in config.languages:
        source = core / language.code
        if not (source / "01_START_phone.pdf").exists():
            continue
        folder = language.name
        safe_path(f"1_START/{folder}")
        editions.append(folder)
        for path in sorted(source.glob("*.pdf")):
            start = "START" in path.name or "VARIANTS" in path.name
            if start:
                copy_exact(path, tree / "1_START" / folder / path.name)
            if "_phone" in path.name or not start:
                copy_exact(path, tree / "4_PHONE_PACK" / folder / path.name)
        html_source = source / "01_START_phone.html"
        if html_source.exists():
            # The optional laptop HTML uses local system fonts. Cataloged font
            # subsets remain embedded in PDFs, without build-machine file URLs.
            text = html_source.read_text(encoding="utf-8")
            text = re.sub(r"@font-face\s*\{[^}]*\}", "", text)
            text = text.replace("font-src file:", "font-src 'none'")
            target = tree / "7_LAPTOP" / folder / "01_START.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    if not editions:
        raise ValueError("No rendered language editions found")
    for name in ("1_START", "4_PHONE_PACK"):
        shutil.copytree(tree / name, tree / "BACKUP" / name)
    return editions


def _place_generated(item: Item, generated: Path, tree: Path, dest: str) -> None:
    directory = generated / item.id
    metadata = json.loads((directory / "generation.json").read_text())
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != item.sha256:
        raise ValueError(f"Generated manifest checksum mismatch: {item.id}")
    if metadata["pipeline_version"] != item.pipeline_version:
        raise ValueError(f"Pipeline version mismatch: {item.id}")
    if sum(entry["size_bytes"] for entry in metadata["files"]) != item.size_bytes:
        raise ValueError(f"Generated size mismatch: {item.id}")
    for entry in metadata["files"]:
        relative = str(safe_path(entry["path"]))
        target = dest + relative if dest.endswith("/") else dest
        safe_path(target)
        source = directory / "files" / relative
        if source.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"Generated file size mismatch: {relative}")
        copy_exact(source, tree / target, entry["sha256"])


def assemble(
    root: Path,
    config: Configuration,
    core: Path,
    output: Path,
    number: int,
    profile: str,
    cache: Path,
    generated: Path,
    epoch: int | None = None,
    allow_download: bool = False,
) -> Path:
    if number not in config.variants.variants:
        raise ValueError("variant must be from 1 through 8")
    if profile == "full":
        require_release_ready(root)
    timestamp = epoch_for(config, epoch)
    verify_core(root, core, timestamp, profile)
    if profile == "full":
        metadata = json.loads((core / "core-manifest.json").read_text())
        if set(metadata["languages"]) != {language.code for language in config.languages}:
            raise ValueError("All fifteen rendered editions are required for a full image")
    items = load_catalog(root, config)
    plan = plan_variants(config, items, profile, core_size(core))[number - 1]
    if not plan.fits:
        raise ValueError("Variant cannot be assembled:\n" + "\n".join(plan.blockers))
    if output.exists():
        raise ValueError("Output already exists; choose a clean build directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-stage-") as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        editions = _copy_core(config, core, tree)
        placed = {
            key: item for key, item in items.items() if selected(item, config, number, profile)
        }
        for item in placed.values():
            dest = destination(item, config, number)
            if item.family == "generated":
                _place_generated(item, generated, tree, dest)
            else:
                source = cache / item.sha256
                if not source.exists() and not allow_download:
                    raise ValueError(f"Missing cached item {item.id}; run ck fetch or use --fetch")
                source = fetch(item, cache)
                filename = unquote(PurePosixPath(urlparse(item.url).path).name)
                relative = dest + filename if dest.endswith("/") else dest
                safe_path(relative)
                copy_exact(source, tree / relative, item.sha256)
        attributions(placed, tree / "7_LAPTOP/THIRD_PARTY.txt")
        readme = ["COMMON KNOWLEDGE", f"Version {config.build.version}; variant {number}", ""]
        if profile != "full":
            readme += ["DEVELOPMENT BUILD — NOT APPROVED FOR EMERGENCY DISTRIBUTION", ""]
        readme += [f"{name}: Open 1_START/{name}/01_START_phone.pdf" for name in editions]
        readme += [
            "",
            "Phone PDFs include their fonts. If laptop HTML text is missing, open the PDF.",
        ]
        (tree / "README.TXT").write_text("\n".join(readme) + "\n", encoding="utf-8")
        tool_versions = Path("/opt/ck-tool-versions.txt")
        if not tool_versions.is_file():
            raise ValueError("Assembly must run in Dockerfile.build")
        packages = sorted(
            f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()
        )
        provenance = [
            f"Common Knowledge {config.build.version}",
            f"Variant: {number}",
            f"Profile: {profile}",
            f"SOURCE_DATE_EPOCH: {timestamp}",
            f"Verification URL: {config.build.site_base_url}",
            f"Dockerfile SHA-256: {digest(root / 'Dockerfile.build')}",
            f"uv.lock SHA-256: {digest(root / 'uv.lock')}",
            f"Python: {sys.version.split()[0]}",
            "",
            "Python packages:",
            *packages,
            "",
            "System tools:",
            tool_versions.read_text(),
        ]
        (tree / "VERIFY.TXT").write_text("\n".join(provenance), encoding="utf-8")
        write_manifest(tree)
        check_manifest(tree)
        actual_size = sum(path.stat().st_size for path in validate_tree(tree))
        if actual_size > plan.usable_bytes:
            raise ValueError(
                f"Assembled tree overflows capacity by {actual_size - plan.usable_bytes} bytes"
            )
        for path in [*tree.rglob("*"), tree]:
            os.utime(path, (timestamp, timestamp), follow_symlinks=False)
        tree.rename(output)
    output.with_suffix(".plan.json").write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
    return output
