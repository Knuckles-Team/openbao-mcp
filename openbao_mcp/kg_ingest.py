"""Native epistemic-graph ingestion for OpenBao control-plane metadata.

Only whitelisted mount paths, engine types, accessors, policy names, and server metadata
are accepted. Secret values, credentials, tokens, and unseal material are never read or
materialized.

All writes use the required ``agent_utilities.knowledge_graph.memory.native_ingest``
primitive. Nodes use canonical ``node_type`` and edges use canonical ``relationship``;
nodes and edges commit in one native transaction. Missing engine dependencies, rejected
records, conflicts, and transaction failures propagate as ``NativeIngestError``.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    NativeIngestError,
)
from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_entities as _native_ingest_entities,
)

logger = logging.getLogger("openbao_mcp.kg")

_SOURCE = "openbao-mcp"
_DOMAIN = "openbao"


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships in one native transaction."""
    return _native_ingest_entities(
        entities, relationships, source=source, domain=domain, client=client, graph=graph
    )


# --- mount metadata (whitelist — NEVER any secret value) -----------------------------

# Only these non-secret keys are ever copied off a mount record. Everything else (crucially
# any nested secret ``data``) is dropped.
_MOUNT_META_KEYS = (
    "accessor",
    "description",
    "local",
    "seal_wrap",
    "running_plugin_version",
)


def _norm_path(path: str) -> str:
    """Strip the trailing slash OpenBao appends to mount paths ('secret/' -> 'secret')."""
    return (path or "").rstrip("/")


def _server_id(
    server_info: dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Map a health/seal_status dict -> (``:VaultServer`` node id, node) or (None, None)."""
    if not server_info:
        return None, None
    data = (
        server_info.get("data")
        if isinstance(server_info.get("data"), dict)
        else server_info
    )
    cluster = data.get("cluster_name") or data.get("cluster_id") or "default"
    node_id = f"openbao:server:{cluster}"
    node = {
        "id": node_id,
        "node_type": "VaultServer",
        "clusterName": data.get("cluster_name"),
        "version": data.get("version"),
        "initialized": data.get("initialized"),
        "sealed": data.get("sealed"),
        "standby": data.get("standby"),
        "externalToolId": str(cluster),
    }
    return node_id, node


def ingest_mounts(
    mounts: dict[str, Any] | None,
    *,
    server_info: dict[str, Any] | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map an OpenBao ``sys/mounts`` response -> ``:SecretMount`` (+ ``:VaultServer``) nodes.

    ``mounts`` is the dict returned by ``get_mounts`` — keyed by mount path, each value a
    mount config (``type``, ``accessor``, ``description``, ``options``…). METADATA ONLY: the
    mapper reads path/type/accessor/version, never any secret payload.
    """
    if not mounts:
        raise NativeIngestError("OpenBao mount ingestion requires mount metadata")
    data = mounts.get("data") if isinstance(mounts.get("data"), dict) else mounts
    if not isinstance(data, dict):
        raise NativeIngestError("OpenBao mount metadata must be a mapping")

    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    server_id, server_node = _server_id(server_info)
    if server_node is not None:
        entities.append(server_node)

    for raw_path, cfg in data.items():
        # Skip non-mount metadata keys OpenBao mixes into the top level.
        if not isinstance(cfg, dict) or "type" not in cfg:
            continue
        path = _norm_path(raw_path)
        if not path:
            continue
        node_id = f"openbao:mount:{path}"
        options = cfg.get("options") or {}
        node: dict[str, Any] = {
            "id": node_id,
            "node_type": "SecretMount",
            "mountPath": raw_path,
            "engineType": cfg.get("type"),
            "externalToolId": path,
        }
        for k in _MOUNT_META_KEYS:
            if cfg.get(k) is not None:
                node[k] = cfg[k]
        if isinstance(options, dict) and options.get("version") is not None:
            node["mountVersion"] = str(options["version"])
        entities.append(node)
        if server_id is not None:
            relationships.append(
                {"source": node_id, "target": server_id, "relationship": "mountedOn"}
            )

    return ingest_entities(entities, relationships, client=client, graph=graph)


def ingest_policies(
    policy_names: list[str] | None,
    *,
    server_info: dict[str, Any] | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map a list of ACL policy NAMES -> ``:Policy`` nodes (metadata only, no rules).

    ``policy_names`` is the list under a ``sys/policies/acl`` LIST (the ``keys``). Only the
    policy identity is ingested — never the HCL rules, which reference secret paths.
    """
    if not policy_names:
        raise NativeIngestError("OpenBao policy ingestion requires policy names")
    entities: list[dict[str, Any]] = []
    server_id, _ = _server_id(server_info)
    for name in policy_names:
        if not name:
            continue
        node_id = f"openbao:policy:{name}"
        node: dict[str, Any] = {
            "id": node_id,
            "node_type": "Policy",
            "name": name,
            "externalToolId": str(name),
        }
        entities.append(node)
    return ingest_entities(entities, None, client=client, graph=graph)
