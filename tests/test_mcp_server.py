from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def setup_mcp_env(monkeypatch):
    monkeypatch.setenv("SECRETSTOOL", "True")
    monkeypatch.setenv("SYSTOOL", "True")
    monkeypatch.setenv("AUTHTOOL", "True")
    monkeypatch.setenv("SSHTOOL", "True")


@pytest.mark.concept("BAO-002")
def test_mcp_server_registration():
    """CONCEPT:BAO-002 Test that tools register successfully."""
    from openbao_mcp.mcp_server import get_mcp_instance

    res = get_mcp_instance()
    if isinstance(res, tuple):
        mcp = res[0]
    else:
        mcp = res
    assert mcp is not None

    # Verify tool registry count is greater than zero
    assert len(mcp._local_provider._components) > 0

    # Verify all tool components exist in registry
    components = mcp._local_provider._components
    assert "tool:openbao_mcp_logical@" in components
    assert "tool:openbao_mcp_kv@" in components
    assert "tool:openbao_mcp_sys@" in components
    assert "tool:openbao_mcp_auth@" in components
    assert "tool:openbao_mcp_ssh@" in components


@pytest.mark.concept("BAO-003")
def test_mcp_server_security_context():
    """CONCEPT:BAO-003 Verify that the server registers with correct security credentials."""
    from openbao_mcp.auth import get_client

    client = get_client()
    assert client is not None


@pytest.mark.concept("BAO-002")
@pytest.mark.asyncio
async def test_mcp_secrets_and_logical_tool():
    """CONCEPT:BAO-002 Test OpenBao secrets and logical tool interaction."""
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()

    mock_client = MagicMock()
    mock_client.Logical = MagicMock()
    mock_client.Logical().Read = MagicMock(return_value={"data": "test-data"})

    logical_tool = mcp._local_provider._components["tool:openbao_mcp_logical@"].fn

    # Test 'read' action
    res = await logical_tool(
        action="read",
        params_json='{"path": "secret/test"}',
        client=mock_client,
        ctx=None,
    )
    assert res == {"data": "test-data"}
    mock_client.Logical().Read.assert_called_with("secret/test")


@pytest.mark.concept("BAO-002")
@pytest.mark.asyncio
async def test_mcp_kv_tool():
    """CONCEPT:BAO-002 Test OpenBao KV tool interaction."""
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()

    mock_client = MagicMock()
    mock_client.KVv2 = MagicMock()
    mock_client.KVv2().Get = MagicMock(return_value={"data": "kv2-data"})

    kv_tool = mcp._local_provider._components["tool:openbao_mcp_kv@"].fn

    # Test 'kv2_get' action
    res = await kv_tool(
        action="kv2_get",
        params_json='{"mount_path": "secret", "secret_path": "foo"}',
        client=mock_client,
        ctx=None,
    )
    assert res == {"data": "kv2-data"}
    mock_client.KVv2.assert_called_with("secret")
    mock_client.KVv2().Get.assert_called_with(None, "foo")


@pytest.mark.concept("BAO-002")
@pytest.mark.asyncio
async def test_mcp_sys_tool():
    """CONCEPT:BAO-002 Test OpenBao Sys tool interaction."""
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()

    mock_client = MagicMock()
    mock_client.Sys = MagicMock()
    mock_client.Sys().SealStatus = MagicMock(return_value={"sealed": False})

    sys_tool = mcp._local_provider._components["tool:openbao_mcp_sys@"].fn

    # Test 'seal_status' action
    res = await sys_tool(
        action="seal_status", params_json="{}", client=mock_client, ctx=None
    )
    assert res == {"sealed": False}
    mock_client.Sys().SealStatus.assert_called_once()


@pytest.mark.concept("BAO-002")
@pytest.mark.asyncio
async def test_mcp_auth_tool():
    """CONCEPT:BAO-002 Test OpenBao Auth tool interaction."""
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()

    mock_client = MagicMock()
    mock_client.Auth = MagicMock()
    mock_client.Auth().Token = MagicMock()
    mock_client.Auth().Token().Lookup = MagicMock(return_value={"id": "tok-1"})

    auth_tool = mcp._local_provider._components["tool:openbao_mcp_auth@"].fn

    # Test 'token_lookup' action
    res = await auth_tool(
        action="token_lookup",
        params_json='{"token": "tok-1"}',
        client=mock_client,
        ctx=None,
    )
    assert res == {"id": "tok-1"}
    mock_client.Auth().Token().Lookup.assert_called_with("tok-1")


@pytest.mark.concept("BAO-002")
@pytest.mark.asyncio
async def test_mcp_ssh_tool():
    """CONCEPT:BAO-002 Test OpenBao SSH tool interaction."""
    from openbao_mcp.mcp_server import get_mcp_instance

    mcp, _, _ = get_mcp_instance()

    mock_client = MagicMock()
    mock_client.SSHHelperWithMountPoint = MagicMock()
    mock_client.SSHHelperWithMountPoint().Verify = MagicMock(
        return_value={"valid": True}
    )

    ssh_tool = mcp._local_provider._components["tool:openbao_mcp_ssh@"].fn

    # Test 'verify' action
    res = await ssh_tool(
        action="verify",
        params_json='{"otp": "otp-1", "mount_point": "ssh-custom"}',
        client=mock_client,
        ctx=None,
    )
    assert res == {"valid": True}
    mock_client.SSHHelperWithMountPoint.assert_called_with("ssh-custom")
    mock_client.SSHHelperWithMountPoint().Verify.assert_called_with("otp-1")
