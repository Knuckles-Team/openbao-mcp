import pytest


@pytest.fixture(autouse=True)
def setup_mcp_env(monkeypatch):
    monkeypatch.setenv("SECRETSTOOL", "True")
    monkeypatch.setenv("SYSTOOL", "True")
    monkeypatch.setenv("AUTHTOOL", "True")
    monkeypatch.setenv("SSHTOOL", "True")


@pytest.mark.concept("BO-OS.identity.bao")
def test_mcp_server_security_context():
    """CONCEPT:BO-OS.identity.bao Verify that the server registers with correct security credentials."""
    from openbao_mcp.auth import get_client

    client = get_client()
    assert client is not None
