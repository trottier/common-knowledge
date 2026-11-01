"""Release gates and evidence-based review inventories."""

import re
from pathlib import Path

from ck.catalog import load_catalog
from ck.config import load_config, read_yaml
from ck.render import citation_ids, content_file


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
    source_file = root / "content/sources.yaml"
    sources = read_yaml(source_file) if source_file.exists() else {}
    for path in sorted((root / "content").rglob("*.md")):
        _, body = content_file(path)
        try:
            citation_ids(body, sources)
        except ValueError as error:
            problems.append(f"{path.relative_to(root)}: citations: {error}")
    for path in sorted((root / "content/en").rglob("*.md")):
        header, _ = content_file(path)
        if header.status != "reviewed" or not header.reviewer or not header.reviewed_on:
            tags = ", ".join(header.review_required) or "English content"
            problems.append(f"{path.relative_to(root)}: named human review required ({tags})")
    edition = root / "content/en/edition.yaml"
    if (root / "catalog/medpdf_topics.yaml").exists():
        from ck.zim2pdf import Topics

        selection = Topics.model_validate(read_yaml(root / "catalog/medpdf_topics.yaml"))
        if selection.status != "reviewed" or not selection.reviewer or not selection.reviewed_on:
            problems.append("catalog/medpdf_topics.yaml: named human medical review required")
    if edition.exists():
        labels = read_yaml(edition)
        if labels["status"] != "reviewed" or not labels["reviewer"] or not labels["reviewed_on"]:
            problems.append(
                "content/en/edition.yaml: named human review of English labels required"
            )
    if (root / "pipelines/referencepacks/selection.yaml").exists():
        from ck.referencepacks import selections

        for identifier, pack in selections(root).items():
            if pack.status != "reviewed" or not pack.reviewer or not pack.reviewed_on:
                problems.append(
                    f"pipelines/referencepacks/selection.yaml ({identifier}): "
                    "named human source-accuracy, safety and suitability review required"
                )
    return sorted(set(problems))


def require_release_ready(root: Path) -> None:
    problems = release_blockers(root)
    if problems:
        raise ValueError("Release blocked:\n" + "\n".join(problems))


def write_release_review(root: Path, output: Path) -> None:
    """Inventory remaining gates without changing anyone's review status."""
    items = load_catalog(root, load_config(root))
    outstanding = markers(root)
    lines = [
        "# v0.1 release review",
        "",
        "This is a development checkpoint, not release approval. v0.1.0 is incomplete.",
        "Regenerate with `ck review-report --output docs/release-review.md` after source changes.",
        "",
        "## Current milestone: Variant 1 and Rhode Island",
        "",
        "- Resolve the selected Variant 1 sample graph and reuse checksum-verified artifacts "
        "under their actual recipes, input pins, completeness flags, and source epochs. "
        "Keep exact missing, stale, held, and ready inventories.",
        "- Inspect one complete county's folder names, overview, detailed maps, and places "
        "index. Apply the configured PDF budget and measure rendering and navigation; "
        "split only where measured limits require it.",
        "- Build the actual browsable tree first and inspect it in the loopback Drive "
        "Explorer, including phone-width full filenames, file sizes, and native file "
        "previews. Label a partial tree incomplete and show every selected omission. "
        "The website does not certify phone or USB behavior.",
        "- Use the fast English/county loop before a wider render. Freeze the coherent "
        "milestone's selected inputs, code, configuration, tool image, and epoch before "
        "the required full checks and clean sample reproducibility pair.",
        "- Defer new image-verifier tool development during this inspection milestone. "
        "Existing checksum, manifest, reproducibility, and release gates remain in force.",
        "- Offline AI is a v0.2 integration on variants 7 and 8, not a current Variant 1 "
        "milestone dependency or device-check requirement. Preserve its research and "
        "historical outputs. The global catalog and VERIFY inventories below remain "
        "unchanged and include held candidates.",
        "",
        "## Later v0.1 implementation and release gaps",
        "",
        "- Finish corrected national atlas/directory repeats and all 56 Android maps. "
        "State or territory repeats do not establish full-image coverage or capacity.",
        "- FCC geographic exceptions, FEMA county-profile gaps and atlas page/grid closure "
        "require resolution and documented source coverage.",
        "- Topic video libraries, all eight in-depth collections, official translated guides, "
        "mesh apps and remaining catalog candidates need complete placement and review.",
        "- Preserve the exact WikEM API snapshot and regenerated archive, with independent "
        "pin, source-hosting and reader review. Do not refresh responses under existing pins.",
        "- Complete corresponding GPL source and dependency notices for shipped applications; "
        "a top-level repository archive alone does not establish source closure.",
        "- Freeze the toolchain and regenerate derived inputs before pinning final outputs. "
        "Prototype fingerprints do not establish a rebuild from the release tag.",
        "- After the browsable sample and selected recipe are stable, run the actual "
        "sample profile twice, then all eight full images twice. "
        "Development-image reproducibility does not establish either result.",
        "- Publish only after sample/full checks, release gates and physical checks pass. "
        "No production tag, release or full-image hashes are approved by this report.",
        "",
        "## Publisher inputs and physical checks",
        "",
        "- Measure the usable capacity of the production USB part in bytes. The publisher's "
        "32 GB answer is a nominal target, not that measurement.",
        "- Confirm release epoch, the verification site's public URL and immutable preservation "
        "of pinned inputs. Choose full-image hosting separately.",
        (
            "- Follow the publisher's edition-selection policy in docs/language-selection.md "
            "and repeat the pinned ACS order audit before tagging."
            if (root / "docs/language-selection.md").exists()
            else "- Verify edition order with current ACS limited-English-proficiency data."
        ),
        "- Complete docs/phone-test-checklist.md on at least three phones and two laptop "
        "operating systems, including a USB-A-only laptop with an adapter. Check video "
        "language switching, offline apps, mapping, and sharing. Offline-AI launcher "
        "and model-loading checks belong to the separate v0.2 checklist.",
        "- English content, clinical protocols, legal/radio text and medical topic selection "
        "need named human reviewers. The agent cannot grant these reviews.",
        "",
        "## Permission and legal decisions",
        "",
        "Red Cross, Stop the Bleed, Hesperian, Khan Academy and iFixit remain excluded "
        "without a written free emergency-use license from each rights holder. No request "
        "has been sent and no permission is claimed. See docs/permission-requests.md.",
        "",
        "Army publications require per-document distribution statement A verification and "
        "legal sign-off. For the deferred v0.2 offline AI, preserve exact model/runner "
        "license, quantization, and dependency-notice questions with their research. "
        "These do not add AI cargo or checks to the current milestone; their held "
        "catalog records remain in the unchanged global release inventory.",
        "",
        "Catalog items explicitly requiring legal review:",
        "",
    ]
    for item in sorted(items.values(), key=lambda item: item.id):
        if item.requires_legal:
            lines.append(
                f"- `{item.id}`: {item.title}; license `{item.license}`; "
                f"reviewer: {item.legal_reviewer or 'unassigned'}; "
                f"review date: {item.legal_reviewed_on or 'unassigned'}."
            )
    lines += ["", "## Named human content reviews", ""]
    blockers = release_blockers(root)
    for problem in blockers:
        if "named human" in problem:
            lines.append("- " + problem)
    citation_problems = [problem for problem in blockers if ": citations: " in problem]
    if citation_problems:
        lines += ["", "## Citation problems", ""]
        lines += ["- " + problem for problem in citation_problems]
    lines += [
        "",
        f"## Remaining VERIFY markers ({len(outstanding)})",
        "",
        "Every marker in content/, config/ and catalog/ is listed below. "
        "Candidate and hub-only entries also remain subject to the release gate.",
        "",
    ]
    for marker in outstanding:
        lines.append(f"- `{marker['path']}:{marker['line']}` — {marker['marker']}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
