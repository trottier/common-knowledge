"""Medical admission checks bind unchanged clinical HTML to actual PDF IDs."""

import hashlib

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject

from tools.admit_medical_proof import clinical_pair


def document(tmp_path, name, text, identity_text=None):
    html = tmp_path / (name + ".html")
    pdf = tmp_path / (name + ".pdf")
    html.write_text(text)
    writer = PdfWriter()
    writer.add_blank_page(width=255, height=453)
    identity = hashlib.sha256((identity_text or text).encode()).hexdigest().encode()
    writer._ID = ArrayObject([ByteStringObject(identity), ByteStringObject(b"fixture")])
    writer.write(pdf)
    return html, pdf


def test_source_notes_can_move_without_changing_clinical_main(tmp_path):
    old = document(
        tmp_path, "old", "<header>Source</header><main><p>Clinical fixture123.</p></main>"
    )
    new = document(
        tmp_path, "new", "<aside>Quiet source</aside><main><p>Clinical fixture123.</p></main>"
    )
    assert clinical_pair(*old, *new) == hashlib.sha256(b"<p>Clinical fixture123.</p>").hexdigest()


@pytest.mark.parametrize("kind", ["body", "identity", "ambiguous"])
def test_rebound_or_ambiguous_clinical_content_is_never_accepted(tmp_path, kind):
    text = "<main><p>Clinical fixture123.</p></main>"
    old = document(tmp_path, "old", text)
    changed = (
        text.replace("123", "124")
        if kind == "body"
        else text + text
        if kind == "ambiguous"
        else text
    )
    new = document(tmp_path, "new", changed, "different HTML" if kind == "identity" else None)
    with pytest.raises(ValueError):
        clinical_pair(*old, *new)
