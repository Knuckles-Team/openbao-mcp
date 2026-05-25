import pytest
@pytest.mark.concept("BAO-001")
def test_init_dynamics():
    import openbao_mcp

    assert openbao_mcp._MCP_AVAILABLE is True
