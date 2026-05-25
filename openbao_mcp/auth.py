"""CONCEPT:BAO-003 Identity credentials loader and session manager."""
import os

from agent_utilities.base_utilities import get_logger, to_boolean

from openbao_mcp.api_client import Api

logger = get_logger(__name__)


def get_client() -> Api:
    """Get authenticated client for openbao_mcp."""
    base_url = os.getenv("OPENBAO_URL") or os.getenv("OPENBAO_MCP_BASE_URL", "")
    token = os.getenv("OPENBAO_TOKEN", "")
    username = os.getenv("OPENBAO_MCP_USERNAME", "")
    password = os.getenv("OPENBAO_MCP_PASSWORD", "")
    verify = to_boolean(os.getenv("OPENBAO_MCP_SSL_VERIFY", "True"))

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
