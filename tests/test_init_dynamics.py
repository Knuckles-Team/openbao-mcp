import pytest


@pytest.mark.concept("BO-OS.governance.bao")
@pytest.mark.concept("AU-ECO.messaging.native-backend-abstraction")
def test_init_dynamics():
    """CONCEPT:AU-ECO.messaging.native-backend-abstraction Test unified ecosystem initialization check."""
    import openbao_mcp

    assert openbao_mcp._MCP_AVAILABLE is True


def test_getattr_raises_attribute_error_for_unknown_name():
    """A name that exists in no core or optional module raises AttributeError."""
    import openbao_mcp

    with pytest.raises(AttributeError, match="has no attribute 'totally_unknown_name'"):
        _ = openbao_mcp.totally_unknown_name
