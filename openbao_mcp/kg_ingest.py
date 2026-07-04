"""Native epistemic-graph ingestion for OpenBao control-plane METADATA (typed nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The openbao-mcp package natively pushes
its control-plane metadata into the epistemic-graph knowledge graph as **typed OWL nodes**
(``:VaultServer``, ``:SecretMount``, ``:AuthMount``, ``:Policy``) + links, using the fast
engine client (``GraphComputeEngine()._client`` + ``txn``) — the same client the blob
``MediaStore`` uses, NOT the heavy in-process ingestion engine.

SECURITY INVARIANT — METADATA ONLY. This module ingests mount **paths / engine types /
accessors**, policy **names**, and server **health/version** ONLY. It NEVER reads, maps, or
writes secret VALUES (KV data, tokens, unseal keys, credentials). The mappers whitelist
non-secret fields explicitly and drop everything else, so a secret can never leak into the
graph even if a caller passes a fuller record.

Entirely best-effort and dependency-/engine-guarded: with no agent-utilities KG stack or no
reachable engine, every entry point **no-ops** (returns ``None``), so the connector keeps
working with zero KG infrastructure. Nodes carry the shared provenance (``domain``/``source``)
and match the classes federated by ``openbao_mcp.ontology``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("openbao_mcp.kg")

_SOURCE = "openbao-mcp"
_DOMAIN = "openbao"


def _client() -> tuple[Any | None, str]:
    """Return ``(engine_client, graph_name)`` or ``(None, "")`` when unavailable."""
    try:
        from agent_utilities.knowledge_graph.core.graph_compute import (
            GraphComputeEngine,
        )
    except Exception as e:  # noqa: BLE001 — KG stack absent
        logger.debug("KG ingest unavailable (import): %s", e)
        return None, ""
    try:
        engine = GraphComputeEngine()
        client = getattr(engine, "_client", None)
        if client is None:
            return None, ""
        graph = getattr(engine, "graph_name", None) or "__commons__"
        return client, graph
    except Exception as e:  # noqa: BLE001 — engine unreachable
        logger.debug("KG ingest: engine unreachable: %s", e)
        return None, ""


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write typed nodes (+ edges) into epistemic-graph via the fast engine client.

    ``entities``: ``[{"id":..., "type":..., ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "type":rel}]``.
    Returns ``{"nodes":n, "edges":m}`` or ``None`` (no engine / failure; never raises).
    ``client``/``graph`` may be injected (tests); otherwise resolved on demand.
    """
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None
    if client is None:
        client, graph = _client()
    if client is None:
        return None
    graph = graph or "__commons__"

    try:
        txn = client.txn.begin(graph=graph)
        for ent in entities:
            props = {k: v for k, v in ent.items() if k != "id" and v is not None}
            props.setdefault("source", _SOURCE)
            props.setdefault("domain", _DOMAIN)
            client.txn.add_node(txn, ent["id"], props)
        committed = client.txn.commit(txn)
    except Exception as e:  # noqa: BLE001 — engine/txn failure is non-fatal
        logger.warning("KG ingest: txn failed: %s", e)
        return None
    if not committed:
        logger.warning("KG ingest: txn not committed (conflict)")
        return None

    edges = 0
    for rel in relationships or []:
        try:
            client.edges.add(
                rel["source"], rel["target"], {"type": rel.get("type", "RELATED")}
            )
            edges += 1
        except Exception as e:  # noqa: BLE001 — pure edge link, best-effort
            logger.debug("KG ingest: edge skipped: %s", e)

    logger.info("KG ingest: wrote %d nodes, %d edges", len(entities), edges)
    return {"nodes": len(entities), "edges": edges}


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
        "type": "VaultServer",
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
) -> dict[str, int] | None:
    """Map an OpenBao ``sys/mounts`` response -> ``:SecretMount`` (+ ``:VaultServer``) nodes.

    ``mounts`` is the dict returned by ``get_mounts`` — keyed by mount path, each value a
    mount config (``type``, ``accessor``, ``description``, ``options``…). METADATA ONLY: the
    mapper reads path/type/accessor/version, never any secret payload.
    """
    if not mounts:
        return None
    data = mounts.get("data") if isinstance(mounts.get("data"), dict) else mounts
    if not isinstance(data, dict):
        return None

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
            "type": "SecretMount",
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
                {"source": node_id, "target": server_id, "type": "mountedOn"}
            )

    return ingest_entities(entities, relationships, client=client, graph=graph)


def ingest_policies(
    policy_names: list[str] | None,
    *,
    server_info: dict[str, Any] | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Map a list of ACL policy NAMES -> ``:Policy`` nodes (metadata only, no rules).

    ``policy_names`` is the list under a ``sys/policies/acl`` LIST (the ``keys``). Only the
    policy identity is ingested — never the HCL rules, which reference secret paths.
    """
    if not policy_names:
        return None
    entities: list[dict[str, Any]] = []
    server_id, _ = _server_id(server_info)
    for name in policy_names:
        if not name:
            continue
        node_id = f"openbao:policy:{name}"
        node: dict[str, Any] = {
            "id": node_id,
            "type": "Policy",
            "name": name,
            "externalToolId": str(name),
        }
        entities.append(node)
    return ingest_entities(entities, None, client=client, graph=graph)
