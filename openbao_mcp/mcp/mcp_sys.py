"""MCP tools for sys operations."""
from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field
from openbao_mcp.auth import get_client

def register_sys_tools(mcp: FastMCP):
    """Register OpenBao MCP sys tools.
    CONCEPT:BAO-001
    """
    @mcp.tool(tags={"sys"})
    async def openbao_mcp_sys(
        action: str = Field(description="Action to perform. Must be one of: 'get_health', 'get_mounts', 'enable_mount', 'get_internal_openapi_spec'"),
        params_json: str = Field(default="{}", description="JSON string of parameters."),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao MCP sys operations."""
        if ctx:
            await ctx.info("Executing sys operations...")
        import json
        try:
            kwargs = json.loads(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        if action == "get_health":
            return client.get_health(**kwargs)
        if action == "get_mounts":
            return client.get_mounts(**kwargs)
        if action == "enable_mount":
            return client.enable_mount(**kwargs)
        if action == "get_internal_openapi_spec":
            return client.get_internal_openapi_spec(**kwargs)

        raise ValueError(f"Unknown action: {action}")
