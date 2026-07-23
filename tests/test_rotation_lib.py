"""Regression tests for the secret-vault-manager rotation planning helper.

Loads ``skills/secret-vault-manager/scripts/rotation_lib.py`` by path (it is a
standalone stdlib script, not an importable package module) and pins discovery
(single-consumer, shared/multi-consumer, multi-path shared), credential-type
classification, and plan assembly (including the shared-secret ordering
constraints and the auto-rollback step).
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "openbao_mcp"
    / "skills"
    / "secret-vault-manager"
    / "scripts"
    / "rotation_lib.py"
)

_spec = importlib.util.spec_from_file_location("rotation_lib", _SCRIPT)
rl = importlib.util.module_from_spec(_spec)
sys.modules["rotation_lib"] = (
    rl  # dataclasses needs the module registered to resolve type hints
)
_spec.loader.exec_module(rl)


# ---------------------------------------------------------------------------
# Fixtures — shaped exactly like `kubectl get ... -o json` items
# ---------------------------------------------------------------------------


def _external_secret(name, namespace, target=None, data=None, data_from_extract=None):
    spec = {}
    if data is not None:
        spec["data"] = data
    if data_from_extract is not None:
        spec["dataFrom"] = [{"extract": {"key": data_from_extract}}]
    spec["target"] = {"name": target or name}
    return {"metadata": {"name": name, "namespace": namespace}, "spec": spec}


def _deployment(name, namespace, secret_ref=None, explicit=None, kind="Deployment"):
    containers = [{"name": name}]
    if secret_ref:
        containers[0]["envFrom"] = [{"secretRef": {"name": secret_ref}}]
    if explicit:
        var_name, secret_name, secret_key = explicit
        containers[0]["env"] = [
            {
                "name": var_name,
                "valueFrom": {"secretKeyRef": {"name": secret_name, "key": secret_key}},
            }
        ]
    return {
        "kind": kind,
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": containers}}},
    }


# ---------------------------------------------------------------------------
# Discovery — single consumer, explicit `data[]` ExternalSecret entry
# ---------------------------------------------------------------------------


def test_discover_single_consumer_explicit_data_entry():
    es = [
        _external_secret(
            "mattermost-mcp-secrets",
            "apps",
            data=[
                {
                    "secretKey": "MATTERMOST_TOKEN",
                    "remoteRef": {
                        "key": "mattermost-mcp",
                        "property": "MATTERMOST_TOKEN",
                    },
                }
            ],
        )
    ]
    secret_keys = {
        ("apps", "mattermost-mcp-secrets"): {"MATTERMOST_TOKEN", "MATTERMOST_URL"}
    }
    workloads = [
        _deployment("mattermost-mcp", "apps", secret_ref="mattermost-mcp-secrets")
    ]

    result = rl.discover_credential("MATTERMOST_TOKEN", es, secret_keys, workloads)

    assert result.found()
    assert result.distinct_source_paths == ["mattermost-mcp"]
    assert len(result.channels) == 1
    assert len(result.all_consumers) == 1
    assert result.all_consumers[0].name == "mattermost-mcp"
    assert not result.is_shared


def test_discover_not_found_returns_empty():
    result = rl.discover_credential("NOPE", [], {}, [])
    assert not result.found()
    assert result.distinct_source_paths == []
    assert result.all_consumers == []


# ---------------------------------------------------------------------------
# Discovery — dataFrom.extract (whole-path pull), only matches when the
# target Secret's ACTUAL key list contains the credential.
# ---------------------------------------------------------------------------


def test_discover_dataFrom_extract_requires_key_present_in_target_secret():
    es = [
        _external_secret(
            "mcp-engine-auth", "apps", data_from_extract="agent-utilities/deployment"
        )
    ]
    workloads = [
        _deployment(f"svc{i}-mcp", "apps", secret_ref="mcp-engine-auth")
        for i in range(3)
    ]

    # target secret genuinely has the key -> matches
    secret_keys_present = {("apps", "mcp-engine-auth"): {"GRAPH_SERVICE_AUTH_SECRET"}}
    found = rl.discover_credential(
        "GRAPH_SERVICE_AUTH_SECRET", es, secret_keys_present, workloads
    )
    assert found.found()
    assert found.distinct_source_paths == ["agent-utilities/deployment"]
    assert len(found.all_consumers) == 3
    assert found.is_shared  # multiple consumers

    # target secret does NOT have the key -> no false positive
    secret_keys_absent = {("apps", "mcp-engine-auth"): {"SOME_OTHER_KEY"}}
    not_found = rl.discover_credential(
        "GRAPH_SERVICE_AUTH_SECRET", es, secret_keys_absent, workloads
    )
    assert not not_found.found()


# ---------------------------------------------------------------------------
# Discovery — multi-path shared secret (the GRAPH_SERVICE_AUTH_SECRET shape:
# two independent OpenBao paths both feed consumers of the same key).
# ---------------------------------------------------------------------------


def test_discover_multi_path_shared_secret():
    es = [
        _external_secret(
            "epistemic-graph-secrets",
            "platform",
            data_from_extract="agent-utilities/deployment",
        ),
        _external_secret(
            "mcp-engine-auth", "apps", data_from_extract="agent-utilities/deployment"
        ),
        _external_secret("graph-os-secrets", "platform", data_from_extract="graph-os"),
    ]
    secret_keys = {
        ("platform", "epistemic-graph-secrets"): {
            "GRAPH_SERVICE_AUTH_SECRET",
            "STATE_DB_URI",
        },
        ("apps", "mcp-engine-auth"): {"GRAPH_SERVICE_AUTH_SECRET"},
        ("platform", "graph-os-secrets"): {
            "GRAPH_SERVICE_AUTH_SECRET",
            "OIDC_CLIENT_ID",
        },
    }
    workloads = [
        _deployment(
            "epistemic-graph", "platform", secret_ref="epistemic-graph-secrets"
        ),
        _deployment("graph-os", "platform", secret_ref="graph-os-secrets"),
        _deployment("graph-os-host", "platform", secret_ref="graph-os-secrets"),
    ] + [
        _deployment(f"svc{i}-mcp", "apps", secret_ref="mcp-engine-auth")
        for i in range(36)
    ]

    result = rl.discover_credential(
        "GRAPH_SERVICE_AUTH_SECRET", es, secret_keys, workloads
    )

    assert result.found()
    assert result.distinct_source_paths == ["agent-utilities/deployment", "graph-os"]
    assert (
        len(result.all_consumers) == 1 + 2 + 36
    )  # engine + graph-os + graph-os-host + fleet
    assert result.is_shared


def test_explicit_env_secretKeyRef_is_also_detected():
    es = [
        _external_secret(
            "soak-secrets",
            "soak",
            data=[
                {
                    "secretKey": "GRAPH_SERVICE_AUTH_SECRET",
                    "remoteRef": {
                        "key": "soak",
                        "property": "GRAPH_SERVICE_AUTH_SECRET",
                    },
                }
            ],
        )
    ]
    secret_keys = {("soak", "soak-secrets"): {"GRAPH_SERVICE_AUTH_SECRET"}}
    workloads = [
        _deployment(
            "eg-soak",
            "soak",
            explicit=(
                "GRAPH_SERVICE_AUTH_SECRET",
                "soak-secrets",
                "GRAPH_SERVICE_AUTH_SECRET",
            ),
            kind="StatefulSet",
        )
    ]

    result = rl.discover_credential(
        "GRAPH_SERVICE_AUTH_SECRET", es, secret_keys, workloads
    )
    assert len(result.all_consumers) == 1
    assert result.all_consumers[0].kind == "StatefulSet"
    assert result.all_consumers[0].mount == "env:GRAPH_SERVICE_AUTH_SECRET"


# ---------------------------------------------------------------------------
# Credential-type classification
# ---------------------------------------------------------------------------


def test_classify_known_generated():
    ct = rl.classify_credential("GRAPH_SERVICE_AUTH_SECRET")
    assert ct.kind == "generated"
    assert callable(ct.generator)
    value = ct.generator()
    assert isinstance(value, str) and len(value) > 20


def test_classify_known_provider_issued_openbao_and_mattermost():
    for key in ("OPENBAO_TOKEN", "MATTERMOST_TOKEN"):
        ct = rl.classify_credential(key)
        assert ct.kind == "provider-issued"
        assert ct.generator is None
        assert ct.mint_procedure


def test_classify_unknown_client_secret_pattern_is_keycloak_shaped():
    ct = rl.classify_credential("SOME_APP_CLIENT_SECRET")
    assert ct.kind == "provider-issued"
    assert "kcadm" in ct.mint_procedure


def test_classify_unknown_token_suffix_defaults_to_unknown_not_generated():
    ct = rl.classify_credential("RANDOM_SERVICE_TOKEN")
    assert ct.kind == "unknown"
    assert ct.generator is None


def test_classify_unrecognized_defaults_to_generated_with_warning():
    ct = rl.classify_credential("SOME_APP_SECRET")
    assert ct.kind == "generated"
    assert callable(ct.generator)


# ---------------------------------------------------------------------------
# Plan assembly
# ---------------------------------------------------------------------------


def test_plan_not_found_has_no_steps():
    discovery = rl.discover_credential("NOPE", [], {}, [])
    ct = rl.classify_credential("NOPE")
    plan = rl.build_plan(discovery, ct)
    assert plan.steps == []
    assert plan.warnings  # a "nothing to plan" warning is present
    assert "NO OpenBao path" in plan.render()


def test_plan_single_consumer_no_shared_warning():
    es = [
        _external_secret(
            "mattermost-mcp-secrets",
            "apps",
            data=[
                {
                    "secretKey": "MATTERMOST_TOKEN",
                    "remoteRef": {"key": "mattermost-mcp"},
                }
            ],
        )
    ]
    secret_keys = {("apps", "mattermost-mcp-secrets"): {"MATTERMOST_TOKEN"}}
    workloads = [
        _deployment("mattermost-mcp", "apps", secret_ref="mattermost-mcp-secrets")
    ]
    discovery = rl.discover_credential("MATTERMOST_TOKEN", es, secret_keys, workloads)
    ct = rl.classify_credential("MATTERMOST_TOKEN")
    plan = rl.build_plan(discovery, ct)

    rendered = plan.render()
    assert "single consumer" in rendered
    assert "provider-issued" in rendered
    assert not any("multiple independent OpenBao" in w for w in plan.warnings)
    # provider-issued -> plan must not claim it will locally generate the value
    assert any("OWNING PROVIDER" in s for s in plan.steps)


def test_plan_shared_secret_has_batch_restart_and_multi_path_warning():
    es = [
        _external_secret(
            "epistemic-graph-secrets",
            "platform",
            data_from_extract="agent-utilities/deployment",
        ),
        _external_secret(
            "mcp-engine-auth", "apps", data_from_extract="agent-utilities/deployment"
        ),
        _external_secret("graph-os-secrets", "platform", data_from_extract="graph-os"),
    ]
    secret_keys = {
        ("platform", "epistemic-graph-secrets"): {"GRAPH_SERVICE_AUTH_SECRET"},
        ("apps", "mcp-engine-auth"): {"GRAPH_SERVICE_AUTH_SECRET"},
        ("platform", "graph-os-secrets"): {"GRAPH_SERVICE_AUTH_SECRET"},
    }
    workloads = [
        _deployment(
            "epistemic-graph", "platform", secret_ref="epistemic-graph-secrets"
        ),
        _deployment("graph-os", "platform", secret_ref="graph-os-secrets"),
    ] + [
        _deployment(f"svc{i}-mcp", "apps", secret_ref="mcp-engine-auth")
        for i in range(5)
    ]

    discovery = rl.discover_credential(
        "GRAPH_SERVICE_AUTH_SECRET", es, secret_keys, workloads
    )
    ct = rl.classify_credential("GRAPH_SERVICE_AUTH_SECRET")
    plan = rl.build_plan(discovery, ct)

    assert discovery.is_shared
    assert any("SAME batch" in s for s in plan.steps)
    assert any("2 independent OpenBao KV paths" in w for w in plan.warnings)
    assert any("same operation" in w for w in plan.warnings)
    assert any("automatically roll back" in s for s in plan.steps)


def test_plan_includes_rollback_step_per_source_path():
    es = [
        _external_secret("openbao-mcp-secrets", "apps", data_from_extract="openbao-mcp")
    ]
    secret_keys = {("apps", "openbao-mcp-secrets"): {"OPENBAO_TOKEN"}}
    workloads = [_deployment("openbao-mcp", "apps", secret_ref="openbao-mcp-secrets")]
    discovery = rl.discover_credential("OPENBAO_TOKEN", es, secret_keys, workloads)
    ct = rl.classify_credential("OPENBAO_TOKEN")
    plan = rl.build_plan(discovery, ct)

    assert any("prior" in s and "KV v2 version" in s for s in plan.steps)
    assert any("revoke the OLD" in s for s in plan.steps)
