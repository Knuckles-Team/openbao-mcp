"""Typed MCP tools for OpenBao system operations (one tool per operation)."""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client
from openbao_mcp.mcp._guard import CONFIRMATION_REQUIRED

READ_ONLY = {"readOnlyHint": True, "idempotentHint": True}
CHANGES_STATE = {"readOnlyHint": False, "destructiveHint": False}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


def register_sys_tools(mcp: FastMCP):
    """Register the OpenBao sys tools."""

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_init_status(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Report whether the OpenBao server is initialized."""
        return {"initialized": client.Sys().InitStatus()}

    @mcp.tool(tags={"sys"}, annotations=CHANGES_STATE)
    async def openbao_sys_init(
        opts: dict[str, Any] = Field(
            description="Init request, e.g. secret_shares and secret_threshold."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Initialize a new OpenBao server and return its root token and unseal shards."""
        return client.Sys().Init(opts)

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_seal_status(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Report the seal state, threshold and progress of the OpenBao server."""
        return client.Sys().SealStatus()

    @mcp.tool(tags={"sys"}, annotations=DESTRUCTIVE)
    async def openbao_sys_seal(
        confirm: bool = Field(
            default=False, description="Must be true; set only after the person agrees."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Seal the OpenBao server. Every secret read fails until it is unsealed."""
        if not confirm:
            return CONFIRMATION_REQUIRED
        return client.Sys().Seal()

    @mcp.tool(tags={"sys"}, annotations=CHANGES_STATE)
    async def openbao_sys_unseal(
        shard: str = Field(description="One unseal key shard."),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Submit one unseal key shard and return the resulting seal status."""
        return client.Sys().Unseal(shard)

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_health(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Read the server health through the system client."""
        return client.Sys().Health()

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_leader(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Read the current cluster leader."""
        return client.Sys().Leader()

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_ha_status(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Read the high-availability node status."""
        return client.Sys().HAStatus()

    @mcp.tool(tags={"sys"}, annotations=CHANGES_STATE)
    async def openbao_sys_raft_join(
        opts: dict[str, Any] = Field(
            description="Join request: leader_api_addr and the leader CA or unseal settings."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Join this node to a raft cluster."""
        return client.Sys().RaftJoin(opts)

    @mcp.tool(tags={"sys"}, annotations=READ_ONLY)
    async def openbao_sys_raft_autopilot_state(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Read the raft autopilot state: voters, health and failure tolerance."""
        return client.Sys().RaftAutopilotState()

    @mcp.tool(tags={"sys", "kg"})
    async def openbao_ingest_mounts(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Natively ingest OpenBao secrets-engine METADATA into medulla.

        Lists mounted secrets engines via ``get_mounts`` and pushes them into the
        knowledge graph as typed ``:SecretMount`` nodes (plus a ``:VaultServer`` node
        from ``get_health`` and their ``:mountedOn`` links) via the fast engine client.

        SECURITY: METADATA ONLY — mount paths, engine types, accessors and server
        health. Secret VALUES are never read or ingested. Best-effort: returns
        ``{"ingested": None}`` when no engine is reachable.
        CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        if ctx:
            await ctx.info("Ingesting OpenBao mount metadata into the KG...")
        from openbao_mcp.kg_ingest import ingest_mounts

        mounts = client.get_mounts()
        try:
            server_info = client.get_health()
        except Exception:  # noqa: BLE001 — health is best-effort context
            server_info = None
        data = mounts.get("data") if isinstance(mounts, dict) else None
        listed = len(data) if isinstance(data, dict) else 0
        result = await ingest_mounts(mounts, server_info=server_info)
        return {"listed": listed, "ingested": result}
