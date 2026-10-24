"""Main FastMCP server and tool registration."""

from openbao_mcp.mcp.mcp_auth import register_auth_tools
from openbao_mcp.mcp.mcp_secrets import register_secrets_tools
from openbao_mcp.mcp.mcp_ssh import register_ssh_tools
from openbao_mcp.mcp.mcp_sys import register_sys_tools

# Re-exported so register_tool_surface(tools_module=...) auto-discovers them as
# module attributes (and ruff treats the imports as used).
__all__ = [
    "register_auth_tools",
    "register_secrets_tools",
    "register_ssh_tools",
    "register_sys_tools",
]
