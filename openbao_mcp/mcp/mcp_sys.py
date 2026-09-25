"""MCP tools for sys operations."""

from collections.abc import Callable
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client

# Backwards-compatible methods mapped straight onto the legacy client:
_SYS_LEGACY_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    "get_health": lambda client, kwargs: client.get_health(**kwargs),
    "get_mounts": lambda client, kwargs: client.get_mounts(**kwargs),
    "enable_mount": lambda client, kwargs: client.enable_mount(**kwargs),
    "get_internal_openapi_spec": lambda client, kwargs: (
        client.get_internal_openapi_spec(**kwargs)
    ),
}

# Advanced Sys interface matching the Go API:
_SYS_ADVANCED_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    "init": lambda client, kwargs: client.Sys().Init(kwargs.get("opts", {})),
    "init_status": lambda client, kwargs: {"initialized": client.Sys().InitStatus()},
    "seal": lambda client, kwargs: client.Sys().Seal(),
    "unseal": lambda client, kwargs: client.Sys().Unseal(kwargs.get("shard", "")),
    "seal_status": lambda client, kwargs: client.Sys().SealStatus(),
    "health": lambda client, kwargs: client.Sys().Health(),
    "leader": lambda client, kwargs: client.Sys().Leader(),
    "ha_status": lambda client, kwargs: client.Sys().HAStatus(),
    "raft_join": lambda client, kwargs: client.Sys().RaftJoin(kwargs.get("opts", {})),
    "raft_autopilot_state": lambda client, kwargs: client.Sys().RaftAutopilotState(),
}

_SYS_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    **_SYS_LEGACY_ACTIONS,
    **_SYS_ADVANCED_ACTIONS,
}


def _dispatch_sys_action(action: str, client, kwargs: dict) -> Any:
    handler = _SYS_ACTIONS.get(action)
    if handler is None:
        raise ValueError(f"Unknown sys action: {action}")
    return handler(client, kwargs)


def register_sys_tools(mcp: FastMCP):
    """Register OpenBao MCP sys tools."""

    @mcp.tool(
        tags={"sys"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
        meta={
            "eg.annotations": {"modalities_in": ["text"], "modalities_out": ["text"]}
        },
    )
    async def openbao_mcp_sys(
        action: Literal[
            "enable_mount",
            "get_health",
            "get_internal_openapi_spec",
            "get_mounts",
            "ha_status",
            "health",
            "init",
            "init_status",
            "leader",
            "raft_autopilot_state",
            "raft_join",
            "seal",
            "seal_status",
            "unseal",
        ] = Field(
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
        except Exception:
            return {"error": "Operation failed"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return _dispatch_sys_action(action, client, kwargs)

    @mcp.tool(tags={"sys", "kg"})
    async def openbao_ingest_mounts(
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Natively ingest OpenBao secrets-engine METADATA into epistemic-graph.

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
        result = ingest_mounts(mounts, server_info=server_info)
        return {"listed": listed, "ingested": result}
