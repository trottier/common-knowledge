"""Validate paths and executable placement before writing any drive image."""

import unicodedata
from pathlib import Path

from ck.catalog import safe_path


def executable_allowed(path: str) -> bool:
    parts = safe_path(path).parts
    if parts[0] in {"7_LAPTOP", "8_MESH_CHAT", "9_OFFLINE_AI"}:
        return True
    if any(part.casefold() == "android" for part in parts[:-1]):
        return True
    return (
        len(parts) >= 5
        and parts[0] == "6_VIDEOS_AND_IN_DEPTH"
        and parts[1] in {"topics", "in_depth"}
        and parts[3] == "laptop"
    )


def is_executable(path: Path) -> bool:
    if path.suffix.casefold() in {
        ".exe",
        ".apk",
        ".bat",
        ".cmd",
        ".command",
        ".sh",
        ".appimage",
        ".jar",
        ".dmg",
        ".llamafile",
        ".dll",
        ".so",
        ".ps1",
        ".py",
        ".com",
        ".msi",
        ".pkg",
        ".vbs",
        ".wasm",
    }:
        return True
    with path.open("rb") as stream:
        prefix = stream.read(4)
    return prefix.startswith((b"#!", b"MZ", b"\x7fELF")) or prefix in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
    }


def validate_tree(root: Path) -> list[Path]:
    files = []
    seen = set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink cannot be shipped: {path}")
        relative = str(path.relative_to(root).as_posix())
        safe_path(relative)
        key = unicodedata.normalize("NFC", relative).casefold()
        if key in seen:
            raise ValueError(f"FAT name collision: {relative}")
        seen.add(key)
        if path.is_file():
            if path.stat().st_size > 0xFFFFFFFF:
                raise ValueError(f"File exceeds FAT32's single-file limit: {relative}")
            if is_executable(path) and not executable_allowed(relative):
                raise ValueError(f"Executable outside allowed folders: {relative}")
            files.append(path)
    return files
