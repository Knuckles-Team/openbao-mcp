"""Main FastMCP server and tool registration."""

import sys
from typing import Any

from agent_utilities.mcp_utilities import (
    create_mcp_server,
    load_config,
    register_tool_surface,
)
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from openbao_mcp.api_client import Api
from openbao_mcp.auth import get_client
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

__version__ = "1.0.0"
logger = get_logger(name="openbao_mcp")


def get_mcp_instance() -> tuple[Any, ...]:
    load_config()
    args, mcp, middlewares = create_mcp_server(
        name="OpenBao MCP MCP",
        version=__version__,
        instructions="OpenBao MCP MCP Server - Managed dynamic operations.",
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})

    register_tool_surface(
        mcp,
        client_cls=Api,
        get_client=get_client,
        service="openbao-mcp",
        tools_module=sys.modules[__name__],
    )

    for mw in middlewares:
        mcp.add_middleware(mw)
    return mcp, args, middlewares


def mcp_server() -> None:
    mcp, args, middlewares = get_mcp_instance()
    print(f"OpenBao MCP MCP v{__version__}", file=sys.stderr)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    mcp_server()
