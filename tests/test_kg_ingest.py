"""Native epistemic-graph typed-node ingestion — Wire-First coverage (METADATA ONLY).

Exercises the real ``ingest_entities`` / ``ingest_mounts`` / ``ingest_policies`` seam with a
fake engine client (no engine required), asserting the txn add_node/commit + edge calls, the
OpenBao mount -> :SecretMount/:VaultServer mapping, and — critically — that secret VALUES are
never copied into the graph. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from typing import Any

import msgpack
import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError
from agent_utilities.security.brain_context import ActorContext, use_actor
from agent_utilities.models.company_brain import ActorType
from agent_utilities.knowledge_graph.core.session import GraphSession, use_session

from openbao_mcp.kg_ingest import (
    ingest_entities,
    ingest_mounts,
    ingest_policies,
)


@pytest.fixture(autouse=True)
def _governed_session():
    actor = ActorContext(
        actor_id="subject:opaque:synthetic",
        actor_type=ActorType.AUTOMATED_SERVICE,
        roles=(),
        tenant_id="tenant:opaque:synthetic",
        authenticated=True,
    )
    session = GraphSession(
        actor=actor,
        tenant=actor.tenant_id,
        scopes=frozenset({"kg:write"}),
        graph="graph:opaque:synthetic",
        policy_version="policy:opaque:synthetic",
        audience="epistemic-graph",
    )
    with use_actor(actor), use_session(session):
        yield


class _FakeNodes:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def properties(self, node_id: str) -> dict[str, Any] | None:
        return self.values.get(node_id)

    def list(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self.values.items())


class _FakeChanges:
    def __init__(self, nodes: _FakeNodes) -> None:
        self.nodes = nodes
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.applied: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, dict[str, Any]] = {}

    def get(self, envelope_id: str) -> dict[str, Any] | None:
        return self.records.get(envelope_id)

    def content_version(self, object_id: str) -> dict[str, Any] | None:
        return self.versions.get(object_id)

    def cursor(self, _source: str, _partition: str = "") -> None:
        return None

    def apply(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.applied.append(envelope)
        mutation = envelope["mutation"]
        for operation in mutation["operations"]:
            method = operation["method"]
            params = method["params"]
            properties = msgpack.unpackb(params["properties_msgpack"], raw=False)
            if method["method"] == "AddNode":
                self.nodes.values[params["node_id"]] = properties
            elif method["method"] == "AddEdge":
                self.edges.append(
                    (params["source_id"], params["target_id"], properties)
                )
        version = envelope["content_version"]
        self.versions[version["object_id"]] = version
        self.records[envelope["envelope_id"]] = envelope
        return {
            "batch_id": mutation["batch_id"],
            "replayed": False,
            "projection_pending": False,
        }


class _FakeRdf:
    def validate_shacl(self, _shapes: str, _data_graph: str) -> dict[str, Any]:
        return {"conforms": True, "results": []}


class _FakeClient:
    def __init__(self) -> None:
        self.nodes = _FakeNodes()
        self.changes = _FakeChanges(self.nodes)
        self.rdf = _FakeRdf()

    @staticmethod
    def supports(operation: str) -> bool:
        return operation == "ApplyChangeEnvelope"


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "SecretMount", "mountPath": "secret/"},
            {"id": "b", "node_type": "VaultServer"},
        ],
        [{"source": "a", "target": "b", "relationship": "mountedOn"}],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(c.changes.applied) == 1
    assert set(c.nodes.values) == {"a", "b"}
    assert c.nodes.values["a"]["source"] == "openbao-mcp"
    assert c.nodes.values["a"]["domain"] == "openbao"
    assert c.changes.edges == [("a", "b", {"relationship": "mountedOn"})]


def test_ingest_mounts_maps_mount_and_server():
    c = _FakeClient()
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
    res = ingest_mounts(mounts, server_info=server, client=c)

    assert res == {"nodes": 3, "edges": 2}  # server + 2 mounts, each mounted-on server
    kv = c.nodes.values["openbao:mount:secret"]
    assert kv["node_type"] == "SecretMount"
    assert kv["engineType"] == "kv"
    assert kv["mountPath"] == "secret/"
    assert kv["accessor"] == "kv_abc123"
    assert kv["mountVersion"] == "2"
    assert kv["externalToolId"] == "secret"
    # SECURITY: no secret value leaked into the node.
    assert "data" not in kv
    assert "password" not in kv
    assert "hunter2" not in kv.values()

    server_node = c.nodes.values["openbao:server:vault-prod"]
    assert server_node["node_type"] == "VaultServer"
    assert server_node["clusterName"] == "vault-prod"
    assert server_node["sealed"] is False
    assert (
        "openbao:mount:secret",
        "openbao:server:vault-prod",
        {"relationship": "mountedOn"},
    ) in c.changes.edges


def test_ingest_mounts_skips_non_mount_keys():
    c = _FakeClient()
    mounts = {"data": {"secret/": {"type": "kv"}, "request_id": "abc", "lease_id": ""}}
    res = ingest_mounts(mounts, client=c)
    assert res == {"nodes": 1, "edges": 0}
    assert set(c.nodes.values) == {"openbao:mount:secret"}


def test_ingest_policies_maps_names_only():
    c = _FakeClient()
    res = ingest_policies(["default", "app-ro"], client=c)
    assert res == {"nodes": 2, "edges": 0}
    assert c.nodes.values["openbao:policy:default"]["node_type"] == "Policy"
    assert c.nodes.values["openbao:policy:app-ro"]["name"] == "app-ro"


def test_retired_structural_alias_is_rejected():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "a", "type": "SecretMount"}], client=_FakeClient())


def test_empty_native_ingest_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())
