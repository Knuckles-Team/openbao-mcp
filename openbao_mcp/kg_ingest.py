"""Native epistemic-graph ingestion for OpenBao control-plane metadata.

Only whitelisted mount paths, engine types, accessors, policy names, and server metadata
are accepted. Secret values, credentials, tokens, and unseal material are never read or
materialized.

All writes go through ``agent_connector_sdk.ingest`` -- the generated ``SourceIngest``
client, not a local ingestion helper. Nodes use canonical ``node_type`` and edges use
canonical ``relationship``; nodes and edges commit in one request. Missing engine
dependencies, rejected records, and transaction failures propagate as ``IngestError``.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    Entity,
    IngestBinding,
    IngestError,
    KnowledgeIngest,
    Relationship,
    current_ingest,
)

logger = logging.getLogger("openbao_mcp.kg")

_BINDING = IngestBinding(connector="openbao-mcp", stream="openbao")

_ENTITY_RESERVED_KEYS = frozenset({"id", "node_type"})
_RELATIONSHIP_RESERVED_KEYS = frozenset({"source", "target", "relationship"})


def _to_entity(record: dict[str, Any]) -> Entity:
    return Entity(
        id=record.get("id"),
        node_type=record.get("node_type"),
        properties={
            key: value
            for key, value in record.items()
            if key not in _ENTITY_RESERVED_KEYS
        },
    )


def _to_relationship(record: dict[str, Any]) -> Relationship:
    properties = {
        key: value
        for key, value in record.items()
        if key not in _RELATIONSHIP_RESERVED_KEYS
    }
    return Relationship(
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
        properties=properties or None,
    )


async def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships via the SDK ingest facade."""
    if not entities:
        raise IngestError("ingest_entities needs at least one entity")
    change_set = ChangeSet(
        entities=tuple(_to_entity(entity) for entity in entities),
        relationships=tuple(
            _to_relationship(relationship) for relationship in relationships or ()
        ),
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


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


def _validated_mount_data(mounts: dict[str, Any] | None) -> dict[str, Any]:
    """The ``sys/mounts`` payload's mount-keyed mapping, or raise if it is malformed."""
    if not mounts:
        raise IngestError("OpenBao mount ingestion requires mount metadata")
    data = mounts.get("data") if isinstance(mounts.get("data"), dict) else mounts
    if not isinstance(data, dict):
        raise IngestError("OpenBao mount metadata must be a mapping")
    return data


async def ingest_mounts(
    mounts: dict[str, Any] | None,
    *,
    server_info: dict[str, Any] | None = None,
    ingest: KnowledgeIngest | None = None,
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

    return await ingest_entities(entities, relationships, ingest=ingest)


async def ingest_policies(
    policy_names: list[str] | None,
    *,
    server_info: dict[str, Any] | None = None,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Map a list of ACL policy NAMES -> ``:Policy`` nodes (metadata only, no rules).

    ``policy_names`` is the list under a ``sys/policies/acl`` LIST (the ``keys``). Only the
    policy identity is ingested — never the HCL rules, which reference secret paths.
    """
    if not policy_names:
        raise IngestError("OpenBao policy ingestion requires policy names")
    entities: list[dict[str, Any]] = []
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
    return await ingest_entities(entities, None, ingest=ingest)
