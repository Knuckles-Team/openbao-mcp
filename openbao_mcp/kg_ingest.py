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


logger = logging.getLogger("openbao_mcp.kg")

_SOURCE = "openbao-mcp"
_DOMAIN = "openbao"


def ingest_entities(*args: object, **kwargs: object) -> object:
    """Write canonical typed nodes and relationships in one native transaction.

    SDK-GAP: Always raises now; see KnowledgeGraphIngestUnavailable.
    """
    _kg_unavailable("ingest_entities")


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


def _mount_node(raw_path: str, cfg: Any) -> tuple[str, dict[str, Any]] | None:
    """Build the ``:SecretMount`` node for one ``sys/mounts`` entry.

    Returns ``None`` for entries that are not mount configs at all (OpenBao mixes
    non-mount metadata keys, like ``request_id``, into the same top-level mapping) or
    whose path is empty after normalization. METADATA ONLY: reads path/type/accessor/
    version off ``cfg``, never any nested secret payload.
    """
    if not isinstance(cfg, dict) or "type" not in cfg:
        return None
    path = _norm_path(raw_path)
    if not path:
        return None
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
    return node_id, node


def _validated_mount_data(*args: object, **kwargs: object) -> object:
    """The ``sys/mounts`` payload's mount-keyed mapping, or raise if it is malformed.

    SDK-GAP: Always raises now; see KnowledgeGraphIngestUnavailable.
    """
    _kg_unavailable("_validated_mount_data")


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
    data = _validated_mount_data(mounts)

    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    server_id, server_node = _server_id(server_info)
    if server_node is not None:
        entities.append(server_node)

    for raw_path, cfg in data.items():
        built = _mount_node(raw_path, cfg)
        if built is None:
            continue
        node_id, node = built
        entities.append(node)
        if server_id is not None:
            relationships.append(
                {"source": node_id, "target": server_id, "relationship": "mountedOn"}
            )

    return ingest_entities(entities, relationships, client=client, graph=graph)


def ingest_policies(*args: object, **kwargs: object) -> object:
    """Map a list of ACL policy NAMES -> ``:Policy`` nodes (metadata only, no rules).

    SDK-GAP: Always raises now; see KnowledgeGraphIngestUnavailable.
    """
    _kg_unavailable("ingest_policies")


class KnowledgeGraphIngestUnavailable(RuntimeError):
    """Direct-to-graph ingestion is unavailable from this connector.

    SDK-GAP (EH-48x, /var/tmp/l9/finish/au-decon-G4c/SDK-GAPS.md): raised in
    place of the old ``agent_utilities.knowledge_graph`` native-ingest call --
    agent-connector-sdk has no facade over EG's typed ingestion protocol yet,
    and the fleet precedent (agents/world-reference-mcp) moves direct-to-graph
    delivery to agent_connector_sdk.runner/sinks at the deployment layer, out
    of connector scope.
    """


def _kg_unavailable(name: str) -> None:
    raise KnowledgeGraphIngestUnavailable(
        f"{name}: direct-to-graph ingestion moved out of connector code "
        "(agent-utilities removed); no agent-connector-sdk facade exists yet "
        "-- see SDK-GAPS.md"
    )
