"""Per-action characterization for the flat action-string dispatchers in
openbao_mcp.mcp.mcp_auth / mcp_secrets / mcp_sys.

tests/test_mcp_server.py already exercises one action per tool (token_lookup,
read, kv2_get, seal_status). This file pins every OTHER action branch so the
dispatch tables those functions get refactored into cannot silently drop or
rewire a branch.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def setup_mcp_env(monkeypatch):
    monkeypatch.setenv("SECRETSTOOL", "True")
    monkeypatch.setenv("SYSTOOL", "True")
    monkeypatch.setenv("AUTHTOOL", "True")
    monkeypatch.setenv("SSHTOOL", "True")


@pytest.fixture
def mcp_instance():
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()
    return mcp


def _tool(mcp, name):
    return mcp._local_provider._components[f"tool:{name}@"].fn


# --- auth --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_login_passes_mount_and_data(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().Login = MagicMock(return_value={"auth": {"client_token": "t"}})

    res = await auth_tool(
        action="login",
        params_json='{"mount": "auth/ldap", "data": {"username": "u"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"auth": {"client_token": "t"}}
    args, _ = mock_client.Auth().Login.call_args
    assert args[0] is None
    assert args[1].mount == "auth/ldap"
    assert args[1].data == {"username": "u"}


@pytest.mark.asyncio
async def test_auth_login_defaults_mount_when_absent(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().Login = MagicMock(return_value={})

    await auth_tool(action="login", params_json="{}", client=mock_client, ctx=None)

    args, _ = mock_client.Auth().Login.call_args
    assert args[1].mount == "auth/userpass"
    assert args[1].data == {}


@pytest.mark.asyncio
async def test_auth_mfa_login_passes_mount_data_and_creds(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().MFALogin = MagicMock(return_value={"mfa": "pending"})

    res = await auth_tool(
        action="mfa_login",
        params_json='{"mount": "auth/ldap", "data": {"username": "u"}, "creds": ["c1", "c2"]}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"mfa": "pending"}
    args, _ = mock_client.Auth().MFALogin.call_args
    assert args[0] is None
    assert args[1].mount == "auth/ldap"
    assert args[1].data == {"username": "u"}
    assert args[2:] == ("c1", "c2")


@pytest.mark.asyncio
async def test_auth_mfa_validate_passes_secret_and_payload(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().MFAValidate = MagicMock(return_value={"validated": True})

    res = await auth_tool(
        action="mfa_validate",
        params_json='{"mfa_secret": "s1", "payload": {"code": "123"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"validated": True}
    mock_client.Auth().MFAValidate.assert_called_with(None, "s1", {"code": "123"})


@pytest.mark.asyncio
async def test_auth_token_create_passes_opts(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().Token().Create = MagicMock(return_value={"id": "new-tok"})

    res = await auth_tool(
        action="token_create",
        params_json='{"opts": {"ttl": "1h"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"id": "new-tok"}
    mock_client.Auth().Token().Create.assert_called_with({"ttl": "1h"})


@pytest.mark.asyncio
async def test_auth_token_renew_passes_token_and_increment(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().Token().Renew = MagicMock(return_value={"renewed": True})

    res = await auth_tool(
        action="token_renew",
        params_json='{"token": "tok-1", "increment": 60}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"renewed": True}
    mock_client.Auth().Token().Renew.assert_called_with("tok-1", 60)


@pytest.mark.asyncio
async def test_auth_token_revoke_passes_token(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()
    mock_client.Auth().Token().RevokeTree = MagicMock(return_value={"revoked": True})

    res = await auth_tool(
        action="token_revoke",
        params_json='{"token": "tok-1"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"revoked": True}
    mock_client.Auth().Token().RevokeTree.assert_called_with("tok-1")


@pytest.mark.asyncio
async def test_auth_unknown_action_raises(mcp_instance):
    auth_tool = _tool(mcp_instance, "openbao_mcp_auth")
    mock_client = MagicMock()

    with pytest.raises(ValueError, match="Unknown auth action: bogus"):
        await auth_tool(
            action="bogus", params_json="{}", client=mock_client, ctx=None
        )


# --- logical -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logical_write_passes_path_and_data(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()
    mock_client.Logical().Write = MagicMock(return_value={"ok": True})

    res = await tool(
        action="write",
        params_json='{"path": "secret/x", "data": {"k": "v"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.Logical().Write.assert_called_with("secret/x", {"k": "v"})


@pytest.mark.asyncio
async def test_logical_delete_passes_path(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()
    mock_client.Logical().Delete = MagicMock(return_value={"ok": True})

    res = await tool(
        action="delete", params_json='{"path": "secret/x"}', client=mock_client, ctx=None
    )

    assert res == {"ok": True}
    mock_client.Logical().Delete.assert_called_with("secret/x")


@pytest.mark.asyncio
async def test_logical_list_passes_path(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()
    mock_client.Logical().List = MagicMock(return_value={"keys": ["a"]})

    res = await tool(
        action="list", params_json='{"path": "secret/"}', client=mock_client, ctx=None
    )

    assert res == {"keys": ["a"]}
    mock_client.Logical().List.assert_called_with("secret/")


@pytest.mark.asyncio
async def test_logical_unwrap_passes_token(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()
    mock_client.Logical().Unwrap = MagicMock(return_value={"data": "unwrapped"})

    res = await tool(
        action="unwrap", params_json='{"token": "wrap-1"}', client=mock_client, ctx=None
    )

    assert res == {"data": "unwrapped"}
    mock_client.Logical().Unwrap.assert_called_with("wrap-1")


@pytest.mark.asyncio
async def test_logical_write_bytes_encodes_str_payload(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()
    mock_client.Logical().WriteBytes = MagicMock(return_value={"ok": True})

    res = await tool(
        action="write_bytes",
        params_json='{"path": "secret/x", "data_bytes": "hello"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.Logical().WriteBytes.assert_called_with("secret/x", b"hello")


@pytest.mark.asyncio
async def test_logical_unknown_action_raises(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_logical")
    mock_client = MagicMock()

    with pytest.raises(ValueError, match="Unknown logical action: bogus"):
        await tool(action="bogus", params_json="{}", client=mock_client, ctx=None)


# --- kv ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kv2_put_passes_mount_secret_path_and_data(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv2().Put = MagicMock(return_value={"ok": True})

    res = await tool(
        action="kv2_put",
        params_json='{"mount_path": "secret", "secret_path": "foo", "data": {"k": "v"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.KVv2.assert_called_with("secret")
    mock_client.KVv2().Put.assert_called_with(None, "foo", {"k": "v"})


@pytest.mark.asyncio
async def test_kv2_delete_passes_mount_and_secret_path(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv2().Delete = MagicMock(return_value={"ok": True})

    res = await tool(
        action="kv2_delete",
        params_json='{"mount_path": "secret", "secret_path": "foo"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.KVv2().Delete.assert_called_with(None, "foo")


@pytest.mark.asyncio
async def test_kv2_patch_passes_new_data(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv2().Patch = MagicMock(return_value={"ok": True})

    res = await tool(
        action="kv2_patch",
        params_json='{"mount_path": "secret", "secret_path": "foo", "new_data": {"k": "v2"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.KVv2().Patch.assert_called_with(None, "foo", {"k": "v2"})


@pytest.mark.asyncio
async def test_kv1_get_passes_mount_and_secret_path(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv1().Get = MagicMock(return_value={"data": "kv1-data"})

    res = await tool(
        action="kv1_get",
        params_json='{"mount_path": "secret", "secret_path": "foo"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"data": "kv1-data"}
    mock_client.KVv1.assert_called_with("secret")
    mock_client.KVv1().Get.assert_called_with(None, "foo")


@pytest.mark.asyncio
async def test_kv1_put_passes_data(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv1().Put = MagicMock(return_value={"ok": True})

    res = await tool(
        action="kv1_put",
        params_json='{"mount_path": "secret", "secret_path": "foo", "data": {"k": "v"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.KVv1().Put.assert_called_with(None, "foo", {"k": "v"})


@pytest.mark.asyncio
async def test_kv1_delete_passes_mount_and_secret_path(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()
    mock_client.KVv1().Delete = MagicMock(return_value={"ok": True})

    res = await tool(
        action="kv1_delete",
        params_json='{"mount_path": "secret", "secret_path": "foo"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.KVv1().Delete.assert_called_with(None, "foo")


@pytest.mark.asyncio
async def test_kv_unknown_action_raises(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_kv")
    mock_client = MagicMock()

    with pytest.raises(ValueError, match="Unknown KV action: bogus"):
        await tool(action="bogus", params_json="{}", client=mock_client, ctx=None)


# --- sys -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sys_get_health_delegates_to_legacy_client_method(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.get_health = MagicMock(return_value={"initialized": True})

    res = await tool(action="get_health", params_json="{}", client=mock_client, ctx=None)

    assert res == {"initialized": True}
    mock_client.get_health.assert_called_with()


@pytest.mark.asyncio
async def test_sys_get_mounts_delegates_to_legacy_client_method(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.get_mounts = MagicMock(return_value={"data": {}})

    res = await tool(action="get_mounts", params_json="{}", client=mock_client, ctx=None)

    assert res == {"data": {}}
    mock_client.get_mounts.assert_called_with()


@pytest.mark.asyncio
async def test_sys_enable_mount_passes_kwargs(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.enable_mount = MagicMock(return_value={"ok": True})

    res = await tool(
        action="enable_mount",
        params_json='{"mount": "kv2", "mount_type": "kv"}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"ok": True}
    mock_client.enable_mount.assert_called_with(mount="kv2", mount_type="kv")


@pytest.mark.asyncio
async def test_sys_get_internal_openapi_spec_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.get_internal_openapi_spec = MagicMock(return_value={"openapi": "3.0"})

    res = await tool(
        action="get_internal_openapi_spec",
        params_json="{}",
        client=mock_client,
        ctx=None,
    )

    assert res == {"openapi": "3.0"}
    mock_client.get_internal_openapi_spec.assert_called_with()


@pytest.mark.asyncio
async def test_sys_init_passes_opts(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().Init = MagicMock(return_value={"root_token": "r"})

    res = await tool(
        action="init",
        params_json='{"opts": {"secret_shares": 5}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"root_token": "r"}
    mock_client.Sys().Init.assert_called_with({"secret_shares": 5})


@pytest.mark.asyncio
async def test_sys_init_status_wraps_bool_in_dict(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().InitStatus = MagicMock(return_value=True)

    res = await tool(
        action="init_status", params_json="{}", client=mock_client, ctx=None
    )

    assert res == {"initialized": True}


@pytest.mark.asyncio
async def test_sys_seal_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().Seal = MagicMock(return_value={"sealed": True})

    res = await tool(action="seal", params_json="{}", client=mock_client, ctx=None)

    assert res == {"sealed": True}
    mock_client.Sys().Seal.assert_called_once()


@pytest.mark.asyncio
async def test_sys_unseal_passes_shard(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().Unseal = MagicMock(return_value={"sealed": False})

    res = await tool(
        action="unseal", params_json='{"shard": "abc"}', client=mock_client, ctx=None
    )

    assert res == {"sealed": False}
    mock_client.Sys().Unseal.assert_called_with("abc")


@pytest.mark.asyncio
async def test_sys_health_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().Health = MagicMock(return_value={"sealed": False})

    res = await tool(action="health", params_json="{}", client=mock_client, ctx=None)

    assert res == {"sealed": False}
    mock_client.Sys().Health.assert_called_once()


@pytest.mark.asyncio
async def test_sys_leader_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().Leader = MagicMock(return_value={"leader_address": "x"})

    res = await tool(action="leader", params_json="{}", client=mock_client, ctx=None)

    assert res == {"leader_address": "x"}
    mock_client.Sys().Leader.assert_called_once()


@pytest.mark.asyncio
async def test_sys_ha_status_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().HAStatus = MagicMock(return_value={"nodes": []})

    res = await tool(action="ha_status", params_json="{}", client=mock_client, ctx=None)

    assert res == {"nodes": []}
    mock_client.Sys().HAStatus.assert_called_once()


@pytest.mark.asyncio
async def test_sys_raft_join_passes_opts(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().RaftJoin = MagicMock(return_value={"joined": True})

    res = await tool(
        action="raft_join",
        params_json='{"opts": {"leader_api_addr": "http://x"}}',
        client=mock_client,
        ctx=None,
    )

    assert res == {"joined": True}
    mock_client.Sys().RaftJoin.assert_called_with({"leader_api_addr": "http://x"})


@pytest.mark.asyncio
async def test_sys_raft_autopilot_state_delegates(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()
    mock_client.Sys().RaftAutopilotState = MagicMock(return_value={"healthy": True})

    res = await tool(
        action="raft_autopilot_state", params_json="{}", client=mock_client, ctx=None
    )

    assert res == {"healthy": True}
    mock_client.Sys().RaftAutopilotState.assert_called_once()


@pytest.mark.asyncio
async def test_sys_unknown_action_raises(mcp_instance):
    tool = _tool(mcp_instance, "openbao_mcp_sys")
    mock_client = MagicMock()

    with pytest.raises(ValueError, match="Unknown sys action: bogus"):
        await tool(action="bogus", params_json="{}", client=mock_client, ctx=None)
