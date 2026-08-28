import pytest


@pytest.mark.concept("BO-OS.governance.bao")
@pytest.mark.concept("AU-ECO.messaging.native-backend-abstraction")
def test_init_dynamics():
    """CONCEPT:AU-ECO.messaging.native-backend-abstraction Test unified ecosystem initialization check."""
    import openbao_mcp

    assert openbao_mcp._MCP_AVAILABLE is True


def test_agent_available_flag_reflects_agent_server_importability():
    """__getattr__("_AGENT_AVAILABLE") mirrors whether openbao_mcp.agent_server imports."""
    import openbao_mcp

    assert openbao_mcp._AGENT_AVAILABLE is True


def test_getattr_resolves_name_from_optional_module():
    """An attribute defined only in an optional module (mcp_server) resolves via __getattr__."""
    import openbao_mcp

    assert openbao_mcp.get_mcp_instance is not None
    assert callable(openbao_mcp.get_mcp_instance)


def test_getattr_raises_attribute_error_for_unknown_name():
    """A name that exists in no core or optional module raises AttributeError."""
    import openbao_mcp

    with pytest.raises(AttributeError, match="has no attribute 'totally_unknown_name'"):
        openbao_mcp.totally_unknown_name
