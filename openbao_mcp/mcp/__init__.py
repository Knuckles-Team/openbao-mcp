from openbao_mcp.mcp.mcp_auth import register_auth_tools
from openbao_mcp.mcp.mcp_secrets import register_secrets_tools
from openbao_mcp.mcp.mcp_ssh import register_ssh_tools
from openbao_mcp.mcp.mcp_sys import register_sys_tools

__all__ = [
    "register_secrets_tools",
    "register_sys_tools",
    "register_auth_tools",
    "register_ssh_tools",
]
