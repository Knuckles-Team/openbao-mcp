"""Characterization for rotate_secret.py's cmd_execute -- the live-side-effect
rotation command (SAFETY CONTRACT: confirm-gated, read-merge-ONE-write,
auto-rollback on verification failure).

Same load-by-path pattern as test_rotation_lib.py / test_rotate_secret_mint.py.
Every kubectl/OpenBao side-effecting helper (kv_metadata, kv_merge_write,
force_sync_external_secret, restart_consumer, kv_rollback,
mint_provider_value) is monkeypatched -- no subprocess is ever spawned and no
live cluster/vault access is required. Discovery + planning are also
monkeypatched to a canned rotation_lib.DiscoveryResult so this file exercises
only cmd_execute's own orchestration logic.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "openbao_mcp"
    / "skills"
    / "secret-vault-manager"
    / "scripts"
    / "rotate_secret.py"
)

_spec = importlib.util.spec_from_file_location("rotate_secret", _SCRIPT)
rs = importlib.util.module_from_spec(_spec)
sys.modules["rotate_secret"] = rs
_spec.loader.exec_module(rs)

rl = rs.rl


def _args(confirm=True, new_value_file=None, credential_key="TEST_KEY"):
    return SimpleNamespace(
        confirm=confirm,
        new_value_file=new_value_file,
        credential_key=credential_key,
        external_secrets_json=None,
        secrets_json=None,
        workloads_json=None,
    )


def _one_consumer_discovery(credential_key="TEST_KEY", path="test-path"):
    consumer = rl.Consumer("Deployment", "apps", "test-svc", "test-svc", "envFrom")
    channel = rl.Channel(
        external_secret="test-secret",
        namespace="apps",
        target_secret="test-secret",
        source_path=path,
        source_property=credential_key,
        consumers=[consumer],
    )
    return rl.DiscoveryResult(credential_key=credential_key, channels=[channel])


def _generated_credential_type():
    return rl.CredentialType(
        kind="generated",
        description="test credential",
        generator=lambda: "GENERATED-VALUE",
        verify="rollout",
    )


def _provider_issued_credential_type():
    return rl.CredentialType(
        kind="provider-issued",
        description="test provider credential",
        mint_procedure="mint it by hand",
        verify="manual",
    )


def test_cmd_execute_refuses_without_confirm(monkeypatch):
    def _boom(args):
        raise AssertionError("_discovery_from_args must not run without --confirm")

    monkeypatch.setattr(rs, "_discovery_from_args", _boom)

    assert rs.cmd_execute(_args(confirm=False)) == 2


def test_cmd_execute_returns_1_when_discovery_not_found(monkeypatch):
    monkeypatch.setattr(
        rs, "_discovery_from_args", lambda args: rl.discover_credential("X", [], {}, [])
    )
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _generated_credential_type()
    )

    def _boom(*a, **k):
        raise AssertionError("no write should happen when nothing was discovered")

    monkeypatch.setattr(rs, "kv_merge_write", _boom)

    assert rs.cmd_execute(_args()) == 1


def test_cmd_execute_generated_credential_happy_path(monkeypatch):
    discovery = _one_consumer_discovery()
    monkeypatch.setattr(rs, "_discovery_from_args", lambda args: discovery)
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _generated_credential_type()
    )

    calls = {"merge_write": [], "sync": [], "restart": [], "rollback": []}
    monkeypatch.setattr(
        rs,
        "kv_metadata",
        lambda path: {"current_version": 3, "versions": ["1", "2", "3"]},
    )

    def fake_merge_write(path, key, value):
        calls["merge_write"].append((path, key, value))
        return {"new_version": 4}

    monkeypatch.setattr(rs, "kv_merge_write", fake_merge_write)
    monkeypatch.setattr(
        rs,
        "force_sync_external_secret",
        lambda ns, name: calls["sync"].append((ns, name)),
    )
    monkeypatch.setattr(
        rs, "restart_consumer", lambda con: calls["restart"].append(con.id())
    )
    monkeypatch.setattr(
        rs, "kv_rollback", lambda path, ver: calls["rollback"].append((path, ver))
    )

    result = rs.cmd_execute(_args())

    assert result == 0
    assert calls["merge_write"] == [("test-path", "TEST_KEY", "GENERATED-VALUE")]
    assert calls["sync"] == [("apps", "test-secret")]
    assert calls["restart"] == ["Deployment/apps/test-svc"]
    assert calls["rollback"] == []  # no rollback on a clean run


def test_cmd_execute_rolls_back_on_consumer_restart_failure(monkeypatch):
    discovery = _one_consumer_discovery()
    monkeypatch.setattr(rs, "_discovery_from_args", lambda args: discovery)
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _generated_credential_type()
    )

    calls = {"restart": 0, "rollback": []}
    monkeypatch.setattr(rs, "kv_metadata", lambda path: {"current_version": 3})
    monkeypatch.setattr(
        rs, "kv_merge_write", lambda path, key, value: {"new_version": 4}
    )
    monkeypatch.setattr(rs, "force_sync_external_secret", lambda ns, name: None)

    def failing_restart(con):
        calls["restart"] += 1
        raise rs.subprocess.CalledProcessError(1, ["kubectl"], stderr="rollout failed")

    monkeypatch.setattr(rs, "restart_consumer", failing_restart)
    monkeypatch.setattr(
        rs, "kv_rollback", lambda path, ver: calls["rollback"].append((path, ver))
    )

    result = rs.cmd_execute(_args())

    assert result == 1
    assert calls["rollback"] == [("test-path", 3)]  # restored to the pre-write version
    # restart_consumer is called once for the failed attempt, once more during rollback
    assert calls["restart"] == 2


def test_cmd_execute_provider_issued_without_mint_path_refuses(monkeypatch):
    discovery = _one_consumer_discovery()
    monkeypatch.setattr(rs, "_discovery_from_args", lambda args: discovery)
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _provider_issued_credential_type()
    )
    monkeypatch.setattr(rs, "mint_provider_value", lambda key: None)

    def _boom(*a, **k):
        raise AssertionError("must not write without a value")

    monkeypatch.setattr(rs, "kv_merge_write", _boom)

    result = rs.cmd_execute(_args(new_value_file=None))

    assert result == 3


def test_cmd_execute_uses_new_value_file_when_provided(monkeypatch, tmp_path):
    discovery = _one_consumer_discovery()
    monkeypatch.setattr(rs, "_discovery_from_args", lambda args: discovery)
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _provider_issued_credential_type()
    )

    value_file = tmp_path / "new_value.txt"
    value_file.write_text("FILE-PROVIDED-VALUE\n")

    calls = []
    monkeypatch.setattr(rs, "kv_metadata", lambda path: {"current_version": 1})
    monkeypatch.setattr(
        rs,
        "kv_merge_write",
        lambda path, key, value: calls.append(value) or {"new_version": 2},
    )
    monkeypatch.setattr(rs, "force_sync_external_secret", lambda ns, name: None)
    monkeypatch.setattr(rs, "restart_consumer", lambda con: None)

    result = rs.cmd_execute(_args(new_value_file=str(value_file)))

    assert result == 0
    assert calls == ["FILE-PROVIDED-VALUE"]  # trailing newline stripped


def test_cmd_execute_auto_mints_when_provider_issued_and_mintable(monkeypatch):
    discovery = _one_consumer_discovery()
    monkeypatch.setattr(rs, "_discovery_from_args", lambda args: discovery)
    monkeypatch.setattr(
        rl, "classify_credential", lambda key: _provider_issued_credential_type()
    )
    monkeypatch.setattr(
        rs, "mint_provider_value", lambda key: ("MINTED-VALUE", "minted via test")
    )

    calls = []
    monkeypatch.setattr(rs, "kv_metadata", lambda path: {"current_version": 1})
    monkeypatch.setattr(
        rs,
        "kv_merge_write",
        lambda path, key, value: calls.append(value) or {"new_version": 2},
    )
    monkeypatch.setattr(rs, "force_sync_external_secret", lambda ns, name: None)
    monkeypatch.setattr(rs, "restart_consumer", lambda con: None)

    result = rs.cmd_execute(_args())

    assert result == 0
    assert calls == ["MINTED-VALUE"]
