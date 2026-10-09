"""Native epistemic-graph typed-node ingestion — Wire-First coverage (METADATA ONLY).

Exercises the real ``ingest_entities`` / ``ingest_mounts`` / ``ingest_policies`` seam
against a fake ``agent_connector_sdk.ingest`` transport (no engine required). The real
SDK request builder (``agent_connector_sdk.ingest.request.build_request``) still runs,
so a malformed change set is still caught by the SDK's own contract, not re-derived
here; only the final network commit is faked. Also asserts — critically — that secret
VALUES are never copied into the graph.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_connector_sdk.ingest import IngestError, KnowledgeIngest
from epistemic_graph.generated.source_ingestion import SourceIngestionRequest

from openbao_mcp.kg_ingest import (
    ingest_entities,
    ingest_mounts,
    ingest_policies,
)


class _FakeTransport:
    """Records every submitted request; no epistemic-graph engine required."""

    def __init__(self) -> None:
        self.requests: list[SourceIngestionRequest] = []

    async def source_status(self, _connector: str, _stream: str) -> Any:
        return SimpleNamespace(accepted_checkpoint=None)

    async def submit(self, request: SourceIngestionRequest) -> Any:
        self.requests.append(request)
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
        )

    async def store_blob(self, _data: bytes) -> str:
        raise AssertionError("openbao-mcp mount-metadata ingestion carries no media")


@pytest.fixture
def ingest() -> tuple[KnowledgeIngest, _FakeTransport]:
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


@pytest.mark.asyncio
async def test_ingest_entities_writes_nodes_and_edges(ingest):
    service, transport = ingest
    res = await ingest_entities(
        [
            {"id": "a", "node_type": "SecretMount", "mountPath": "secret/"},
            {"id": "b", "node_type": "VaultServer"},
        ],
        [{"source": "a", "target": "b", "relationship": "mountedOn"}],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(transport.requests) == 1
    request = transport.requests[0]
    record_ids = {record.record_id for record in request.records}
    assert record_ids == {"a", "b"}
    a_record = next(r for r in request.records if r.record_id == "a")
    assert a_record.payload["mountPath"] == "secret/"
    assert request.relationships[0].relation_reference.endswith(
        "resources/SecretMount/relations/mountedOn"
    )


@pytest.mark.asyncio
async def test_ingest_mounts_maps_mount_and_server(ingest):
    service, transport = ingest
    mounts = {
        "data": {
            "secret/": {
                "type": "kv",
                "accessor": "kv_abc123",
                "description": "app secrets",
                "options": {"version": "2"},
                # A hostile / fuller payload: a secret value must NOT be copied.
                "data": {"password": "hunter2"},
            },
            "transit/": {"type": "transit", "accessor": "transit_xyz"},
        }
    }
    server = {
        "data": {"cluster_name": "vault-prod", "version": "1.15", "sealed": False}
    }
    res = await ingest_mounts(mounts, server_info=server, ingest=service)

    assert res == {"nodes": 3, "edges": 2}  # server + 2 mounts, each mounted-on server
    request = transport.requests[0]
    kv = next(r for r in request.records if r.record_id == "openbao:mount:secret")
    assert kv.payload["engineType"] == "kv"
    assert kv.payload["mountPath"] == "secret/"
    assert kv.payload["accessor"] == "kv_abc123"
    assert kv.payload["mountVersion"] == "2"
    assert kv.payload["externalToolId"] == "secret"
    # SECURITY: no secret value leaked into the node.
    assert "data" not in kv.payload
    assert "password" not in kv.payload
    assert "hunter2" not in kv.payload.values()

    server_record = next(
        r for r in request.records if r.record_id == "openbao:server:vault-prod"
    )
    assert server_record.payload["clusterName"] == "vault-prod"
    assert server_record.payload["sealed"] is False
    relation_refs = {rel.relation_reference.rsplit("/", 1)[-1] for rel in request.relationships}
    assert relation_refs == {"mountedOn"}
    assert len(request.relationships) == 2


@pytest.mark.asyncio
async def test_ingest_mounts_skips_non_mount_keys(ingest):
    service, transport = ingest
    mounts = {"data": {"secret/": {"type": "kv"}, "request_id": "abc", "lease_id": ""}}
    res = await ingest_mounts(mounts, ingest=service)
    assert res == {"nodes": 1, "edges": 0}
    request = transport.requests[0]
    assert {r.record_id for r in request.records} == {"openbao:mount:secret"}


@pytest.mark.asyncio
async def test_ingest_policies_maps_names_only(ingest):
    service, transport = ingest
    res = await ingest_policies(["default", "app-ro"], ingest=service)
    assert res == {"nodes": 2, "edges": 0}
    request = transport.requests[0]
    default_record = next(r for r in request.records if r.record_id == "openbao:policy:default")
    assert default_record.payload == {"name": "default", "externalToolId": "default"}
    app_ro_record = next(r for r in request.records if r.record_id == "openbao:policy:app-ro")
    assert app_ro_record.payload["name"] == "app-ro"


@pytest.mark.asyncio
async def test_retired_structural_alias_is_rejected(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="node_type"):
        await ingest_entities([{"id": "a", "type": "SecretMount"}], ingest=service)


@pytest.mark.asyncio
async def test_empty_native_ingest_is_rejected(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="at least one entity"):
        await ingest_entities([], ingest=service)
