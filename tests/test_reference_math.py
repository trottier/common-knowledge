"""Only verified vector equations can enter attributed reference output."""

import io
import tarfile

import pytest

from ck.reference_math import extract_package, validate_svg


@pytest.mark.parametrize(
    "body",
    [
        "<script>bad()</script>",
        '<image href="https://example.invalid/pixel"/>',
        '<use href="file:///private/fixture"/>',
        '<g onload="bad()"/>',
        '<path style="fill:url(https://example.invalid/pixel)"/>',
        '<g data-mml-node="merror"/>',
        "<text>unrendered glyph</text>",
    ],
)
def test_active_external_or_failed_equation_output_is_rejected(body):
    with pytest.raises(ValueError):
        validate_svg('<svg xmlns="http://www.w3.org/2000/svg">' + body + "</svg>")


def test_local_vector_glyphs_need_no_external_resources():
    validate_svg(
        '<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="g" d="M0 0L1 1"/>'
        '</defs><use href="#g"/></svg>'
    )


def test_empty_mathjax_table_alignment_marker_carries_no_fallback_glyph():
    validate_svg('<svg xmlns="http://www.w3.org/2000/svg"><text data-id-align="true"/></svg>')
    with pytest.raises(ValueError):
        validate_svg(
            '<svg xmlns="http://www.w3.org/2000/svg"><text data-id-align="true">x</text></svg>'
        )


@pytest.mark.parametrize(
    "name,kind", [("../escape", tarfile.REGTYPE), ("package/link", tarfile.SYMTYPE)]
)
def test_package_extraction_rejects_paths_and_links(tmp_path, name, kind):
    path = tmp_path / "bad.tgz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        if kind == tarfile.SYMTYPE:
            member.linkname = "/outside"
        archive.addfile(member, io.BytesIO())
    with pytest.raises(ValueError, match="Unsafe"):
        extract_package(path, tmp_path / "output")
    assert not (tmp_path / "escape").exists()
