"""CONCEPT:BAO-003 Identity credentials loader and session manager."""

from agent_utilities.base_utilities import get_logger
from agent_utilities.core.config import setting

from openbao_mcp.api_client import Api

logger = get_logger(__name__)


def get_client() -> Api:
    """Get authenticated client for openbao_mcp."""
    base_url = setting("OPENBAO_URL", "") or setting("OPENBAO_MCP_BASE_URL", "")
    token = setting("OPENBAO_TOKEN", "")
    username = setting("OPENBAO_MCP_USERNAME", "")
    password = setting("OPENBAO_MCP_PASSWORD", "")
    verify = setting("OPENBAO_MCP_SSL_VERIFY", True)

    if not base_url:
        # Default fallback for testing
        base_url = "http://localhost"

    return Api(
        base_url=base_url,
        token=token,
        username=username,
        password=password,
        verify=verify,
    )
