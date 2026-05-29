"""Main FastMCP server and tool registration."""

import os
import sys
from typing import Any

from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import create_mcp_server
from dotenv import find_dotenv, load_dotenv
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from openbao_mcp.mcp.mcp_auth import register_auth_tools
from openbao_mcp.mcp.mcp_secrets import register_secrets_tools
from openbao_mcp.mcp.mcp_ssh import register_ssh_tools
from openbao_mcp.mcp.mcp_sys import register_sys_tools

__version__ = "0.21.0"
logger = get_logger(name="openbao_mcp")


def get_mcp_instance() -> tuple[Any, ...]:
    load_dotenv(find_dotenv())
    args, mcp, middlewares = create_mcp_server(
        name="OpenBao MCP MCP",
        version=__version__,
        instructions="OpenBao MCP MCP Server - Managed dynamic operations.",
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})

    DEFAULT_SECRETSTOOL = to_boolean(os.getenv("SECRETSTOOL", "True"))
    if DEFAULT_SECRETSTOOL:
        register_secrets_tools(mcp)

    DEFAULT_SYSTOOL = to_boolean(os.getenv("SYSTOOL", "True"))
    if DEFAULT_SYSTOOL:
        register_sys_tools(mcp)

    DEFAULT_AUTHTOOL = to_boolean(os.getenv("AUTHTOOL", "True"))
    if DEFAULT_AUTHTOOL:
        register_auth_tools(mcp)

    DEFAULT_SSHTOOL = to_boolean(os.getenv("SSHTOOL", "True"))
    if DEFAULT_SSHTOOL:
        register_ssh_tools(mcp)

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
