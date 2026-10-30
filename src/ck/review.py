"""Release gates and evidence-based review inventories."""

import re
from pathlib import Path

from ck.catalog import load_catalog
from ck.config import load_config
from ck.render import content_file


def markers(root: Path) -> list[dict]:
    result = []
    for directory in ("content", "config", "catalog"):
        for path in sorted((root / directory).rglob("*")):
            if path.suffix not in {".md", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"\[\[VERIFY[^\]]*\]\]", text):
                result.append(
                    {
                        "path": str(path.relative_to(root)),
                        "line": text.count("\n", 0, match.start()) + 1,
                        "marker": match.group(),
                    }
                )
    return result


def release_blockers(root: Path) -> list[str]:
    config = load_config(root)
    items = load_catalog(root, config)
    problems = [f"{item['path']}:{item['line']}: {item['marker']}" for item in markers(root)]
    for item in items.values():
        problems.extend(item.blockers(release=True))
    for path in sorted((root / "content/en").rglob("*.md")):
        header, _ = content_file(path)
        if header.status != "reviewed" or not header.reviewer or not header.reviewed_on:
            tags = ", ".join(header.review_required) or "English content"
            problems.append(f"{path.relative_to(root)}: named human review required ({tags})")
    return sorted(set(problems))


def require_release_ready(root: Path) -> None:
    problems = release_blockers(root)
    if problems:
        raise ValueError("Release blocked:\n" + "\n".join(problems))
