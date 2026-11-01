"""The Briar release-source walk includes the audited subset without granting approval."""

import json
from pathlib import Path

from ck.catalog import load_catalog
from ck.publication import corresponding_sources

ROOT = Path(__file__).resolve().parents[1]


def test_briar_release_source_graph_preserves_mailbox_and_excludes_audit_binaries():
    items = load_catalog(ROOT)
    proposal = json.loads((ROOT / "docs/evidence/briar-source-links.json").read_text())
    app = items["briar_android"]
    parent = items[app.source_id]
    assert parent.id == proposal["parent_source_id"]
    assert parent.sha256 == proposal["parent_source_sha256"]
    required = set(proposal["source_ids"]) | set(proposal["existing_inputs_must_remain"])
    resolved = {source.id for source in corresponding_sources(items, app)}
    assert required <= resolved
    assert not set(proposal["excluded_audit_ids"]) & resolved
    assert all(items[identifier].family == "docs" for identifier in resolved)
    assert "briar_mailbox_source" in parent.inputs
    assert "[[VERIFY:" in parent.review
    assert app.requires_legal and not app.legal_reviewer
    assert proposal["complete_application_source_closure"] is False
