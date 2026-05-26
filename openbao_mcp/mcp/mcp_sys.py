"""MCP tools for sys operations."""

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


def register_sys_tools(mcp: FastMCP):
    """Register OpenBao MCP sys tools."""

    @mcp.tool(tags={"sys"})
    async def openbao_mcp_sys(
        action: str = Field(
            description=(
                "Action: 'get_health', 'get_mounts', 'enable_mount', 'get_internal_openapi_spec', "
                "'init', 'init_status', 'seal', 'unseal', 'seal_status', 'health', 'leader', "
                "'ha_status', 'raft_join', 'raft_autopilot_state'"
            )
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao sys operations."""
        if ctx:
            await ctx.info("Executing sys operations...")
        import json

        try:
            kwargs = json.loads(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Backwards compatible methods mapped on the legacy client:
        if action == "get_health":
            return client.get_health(**kwargs)
        if action == "get_mounts":
            return client.get_mounts(**kwargs)
        if action == "enable_mount":
            return client.enable_mount(**kwargs)
        if action == "get_internal_openapi_spec":
            return client.get_internal_openapi_spec(**kwargs)

        # Advanced Sys interface matching Go API:
        if action == "init":
            opts = kwargs.get("opts", {})
            return client.Sys().Init(opts)
        if action == "init_status":
            return {"initialized": client.Sys().InitStatus()}
        if action == "seal":
            return client.Sys().Seal()
        if action == "unseal":
            shard = kwargs.get("shard", "")
            return client.Sys().Unseal(shard)
        if action == "seal_status":
            return client.Sys().SealStatus()
        if action == "health":
            return client.Sys().Health()
        if action == "leader":
            return client.Sys().Leader()
        if action == "ha_status":
            return client.Sys().HAStatus()
        if action == "raft_join":
            opts = kwargs.get("opts", {})
            return client.Sys().RaftJoin(opts)
        if action == "raft_autopilot_state":
            return client.Sys().RaftAutopilotState()

        raise ValueError(f"Unknown sys action: {action}")
