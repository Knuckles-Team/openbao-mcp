"""EH-410: the OpenBao audit device enters the graph pseudonymized."""

from __future__ import annotations

import json
from typing import Any

from agent_utilities.security.audit_pseudonym import AuditPseudonymizer

from openbao_mcp import audit_feed, kg_ingest

PSEUDO = AuditPseudonymizer(b"test-only-audit-key")
ENTRY = {
    "type": "response",
    "time": "2026-09-24T10:00:00Z",
    "auth": {
        "entity_id": "ent-7",
        "display_name": "approle-graph-os",
        "client_token": "hmac-sha256:aaa",
        "token_type": "service",
        "policies": ["default"],
    },
    "request": {
        "id": "req-1",
        "operation": "read",
        "mount_type": "kv",
        "mount_point": "apps/",
        "path": "apps/data/graph-os",
        "remote_address": "10.0.0.14",
        "headers": {"authorization": ["Bearer leak"]},
    },
    "response": {"data": {"password": "hmac-sha256:bbb"}},
}


def test_entries_become_pseudonymized_secret_access_events(monkeypatch):
    written: dict[str, dict[str, Any]] = {}

    def capture(entities, relationships=None, **_kwargs):
        written.update({entity["id"]: entity for entity in entities})
        return {"nodes": len(entities), "edges": 0}

    monkeypatch.setattr(kg_ingest, "ingest_entities", capture)
    res = audit_feed.ingest_audit_entries([ENTRY], pseudonymizer=PSEUDO)
    assert res == {"nodes": 1, "edges": 0}
    (node,) = written.values()
    assert node["node_type"] == "SecretAccessEvent"
    assert node["request_operation"] == "read" and node["request_mount_type"] == "kv"
    assert node["request_path"] == PSEUDO.secret_path("apps/data/graph-os")
    assert node["auth_entity_id"] == PSEUDO.identity("ent-7")
    assert node["request_remote_address"] == "10.0.0.0/24"
    rendered = repr(written)
    for leaked in ("graph-os", "ent-7", "hmac-sha256", "leak", "10.0.0.14", "policies"):
        assert leaked not in rendered, leaked


def test_the_log_is_read_from_an_offset_and_a_partial_line_waits(tmp_path):
    log = tmp_path / "audit.log"
    first = json.dumps({"type": "request"}) + "\n"
    log.write_text(
        first + "not json\n" + json.dumps({"type": "response"}) + "\n" + '{"par'
    )
    entries, offset = audit_feed.read_audit_log(log)
    assert [e["type"] for e in entries] == ["request", "response"]
    assert offset == log.stat().st_size - len('{"par')
    again, same = audit_feed.read_audit_log(log, offset)
    assert again == [] and same == offset
    entries, _ = audit_feed.read_audit_log(log, len(first))
    assert [e["type"] for e in entries] == ["response"]
