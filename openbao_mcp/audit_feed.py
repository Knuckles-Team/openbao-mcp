"""EH-410: the OpenBao audit device as a pseudonymized security-audit feed.

OpenBao's file audit device writes one JSON object per request and response.
:func:`read_audit_log` tails it from a byte offset; :func:`ingest_audit_entries`
turns entries into ``:SecretAccessEvent`` nodes through agent-utilities'
``AuditPseudonymizer`` (operator ruling 2026-09-24):

* secret paths and mount points become keyed HMAC references (key in OpenBao);
* entity ids / display names become identity references;
* the remote address is cut to its /24 (IPv4) or /48 (IPv6) network;
* only allowlisted scalar fields pass -- request/response ``data`` (already
  HMAC'd by OpenBao, and secret material either way), tokens and headers never do.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openbao_mcp import kg_ingest

#: The largest slice one read returns.
MAX_ENTRIES = 1000

_POLICY = {
    "keep": (
        "type",
        "time",
        "error",
        "request.operation",
        "request.mount_type",
        "auth.token_type",
    ),
    "identities": ("auth.entity_id", "auth.display_name"),
    "secret_paths": ("request.path", "request.mount_point"),
    "ips": ("request.remote_address",),
}


def read_audit_log(
    path: str | Path, offset: int = 0, max_entries: int = MAX_ENTRIES
) -> tuple[list[dict[str, Any]], int]:
    """Complete JSON lines after ``offset``; returns (entries, next offset).

    A trailing partial line is left for the next read; a malformed line is
    skipped (the offset still moves past it) rather than stalling the feed.
    """
    entries: list[dict[str, Any]] = []
    with Path(path).open("rb") as handle:
        handle.seek(max(0, int(offset)))
        position = handle.tell()
        for raw in handle:
            if not raw.endswith(b"\n") or len(entries) >= max_entries:
                break
            position += len(raw)
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)
    return entries, position


def _entry_node(entry: dict[str, Any], pseudo: Any, policy: Any) -> dict[str, Any]:
    fingerprint = json.dumps(entry, sort_keys=True, default=str)
    node = pseudo.record(entry, policy)
    node.update(
        {
            "id": f"openbao:audit:{pseudo.reference('audit', fingerprint)}",
            "node_type": "SecretAccessEvent",
            "epistemic_class": "observation",
        }
    )
    return node


def ingest_audit_entries(
    entries: list[dict[str, Any]],
    *,
    pseudonymizer: Any | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Ingest audit entries as pseudonymized ``:SecretAccessEvent`` nodes."""
    from agent_utilities.security.audit_pseudonym import (
        AuditFieldPolicy,
        AuditPseudonymizer,
    )

    pseudo = pseudonymizer or AuditPseudonymizer.from_settings()
    policy = AuditFieldPolicy(**_POLICY)
    nodes = [
        _entry_node(e, pseudo, policy) for e in entries or [] if isinstance(e, dict)
    ]
    if not nodes:
        return {"nodes": 0, "edges": 0}
    return kg_ingest.ingest_entities(nodes, client=client, graph=graph)
