"""MCP tools for secrets operations."""
from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field
from openbao_mcp.auth import get_client

def register_secrets_tools(mcp: FastMCP):
    """Register OpenBao MCP secrets tools.
    CONCEPT:BAO-001
    """
    @mcp.tool(tags={"secrets"})
    async def openbao_mcp_secrets(
        action: str = Field(description="Action to perform. Must be one of: 'read_secret', 'write_secret', 'delete_secret', 'list_secrets'"),
        params_json: str = Field(default="{}", description="JSON string of parameters."),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao MCP secrets operations."""
        if ctx:
            await ctx.info("Executing secrets operations...")
        import json
        try:
            kwargs = json.loads(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        if action == "read_secret":
            return client.read_secret(**kwargs)
        if action == "write_secret":
            return client.write_secret(**kwargs)
        if action == "delete_secret":
            return client.delete_secret(**kwargs)
        if action == "list_secrets":
            return client.list_secrets(**kwargs)

        raise ValueError(f"Unknown action: {action}")
