import pytest


@pytest.fixture(autouse=True)
def setup_mcp_env(monkeypatch):
    monkeypatch.setenv("SECRETSTOOL", "True")
    monkeypatch.setenv("SYSTOOL", "True")
    monkeypatch.setenv("AUTHTOOL", "True")
    monkeypatch.setenv("SSHTOOL", "True")


@pytest.mark.concept("BO-OS.governance.bao-2")
def test_mcp_server_registration():
    """CONCEPT:BO-OS.governance.bao-2 Test that tools register successfully."""
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
    names = {component.name for component in components.values()}
    assert "openbao_get_mounts" in names  # one tool per operation
    assert "openbao_mcp_kv" not in names  # action-routed tool retired


@pytest.mark.concept("BO-OS.identity.bao")
def test_mcp_server_security_context():
    """CONCEPT:BO-OS.identity.bao Verify that the server registers with correct security credentials."""
    from openbao_mcp.auth import get_client

    client = get_client()
    assert client is not None
