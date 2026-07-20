"""Native epistemic-graph typed-node ingestion — Wire-First coverage (METADATA ONLY).

Exercises the real ``ingest_entities`` / ``ingest_mounts`` / ``ingest_policies`` seam with a
fake engine client (no engine required), asserting the txn add_node/commit + edge calls, the
OpenBao mount -> :SecretMount/:VaultServer mapping, and — critically — that secret VALUES are
never copied into the graph. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError

from openbao_mcp.kg_ingest import (
    ingest_entities,
    ingest_mounts,
    ingest_policies,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def add_edge(self, txn, source, target, props):
        self.edges.append((source, target, props))

    def commit(self, txn):
        self.committed = True
        return True


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "SecretMount", "mountPath": "secret/"},
            {"id": "b", "node_type": "VaultServer"},
        ],
        [{"source": "a", "target": "b", "relationship": "mountedOn"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    assert c.txn.nodes["a"]["source"] == "openbao-mcp"
    assert c.txn.nodes["a"]["domain"] == "openbao"
    assert c.txn.edges == [("a", "b", {"relationship": "mountedOn"})]


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
    res = ingest_mounts(mounts, server_info=server, client=c, graph="__commons__")

    assert res == {"nodes": 3, "edges": 2}  # server + 2 mounts, each mounted-on server
    kv = c.txn.nodes["openbao:mount:secret"]
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

    server_node = c.txn.nodes["openbao:server:vault-prod"]
    assert server_node["node_type"] == "VaultServer"
    assert server_node["clusterName"] == "vault-prod"
    assert server_node["sealed"] is False
    assert (
        "openbao:mount:secret",
        "openbao:server:vault-prod",
        {"relationship": "mountedOn"},
    ) in c.txn.edges


def test_ingest_mounts_skips_non_mount_keys():
    c = _FakeClient()
    mounts = {"data": {"secret/": {"type": "kv"}, "request_id": "abc", "lease_id": ""}}
    res = ingest_mounts(mounts, client=c, graph="__commons__")
    assert res == {"nodes": 1, "edges": 0}
    assert set(c.txn.nodes) == {"openbao:mount:secret"}


def test_ingest_policies_maps_names_only():
    c = _FakeClient()
    res = ingest_policies(["default", "app-ro"], client=c, graph="__commons__")
    assert res == {"nodes": 2, "edges": 0}
    assert c.txn.nodes["openbao:policy:default"]["node_type"] == "Policy"
    assert c.txn.nodes["openbao:policy:app-ro"]["name"] == "app-ro"


def test_retired_structural_alias_is_rejected():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "a", "type": "SecretMount"}], client=_FakeClient())


def test_empty_native_ingest_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())
