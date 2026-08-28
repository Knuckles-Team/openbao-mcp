"""MCP tools for secrets and logical operations."""

from typing import Any, Callable

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


def _logical_read(client, kwargs: dict) -> Any:
    return client.Logical().Read(kwargs.get("path", ""))


def _logical_write(client, kwargs: dict) -> Any:
    return client.Logical().Write(kwargs.get("path", ""), kwargs.get("data", {}))


def _logical_delete(client, kwargs: dict) -> Any:
    return client.Logical().Delete(kwargs.get("path", ""))


def _logical_list(client, kwargs: dict) -> Any:
    return client.Logical().List(kwargs.get("path", ""))


def _logical_unwrap(client, kwargs: dict) -> Any:
    return client.Logical().Unwrap(kwargs.get("token", ""))


def _logical_write_bytes(client, kwargs: dict) -> Any:
    raw_data = kwargs.get("data_bytes", b"")
    if isinstance(raw_data, str):
        raw_data = raw_data.encode("utf-8")
    return client.Logical().WriteBytes(kwargs.get("path", ""), raw_data)


_LOGICAL_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    "read": _logical_read,
    "write": _logical_write,
    "delete": _logical_delete,
    "list": _logical_list,
    "unwrap": _logical_unwrap,
    "write_bytes": _logical_write_bytes,
}


def _dispatch_logical_action(action: str, client, kwargs: dict) -> Any:
    handler = _LOGICAL_ACTIONS.get(action)
    if handler is None:
        raise ValueError(f"Unknown logical action: {action}")
    return handler(client, kwargs)


def _kv2_get(client, kwargs: dict) -> Any:
    return client.KVv2(kwargs.get("mount_path", "secret")).Get(
        None, kwargs.get("secret_path", "")
    )


def _kv2_put(client, kwargs: dict) -> Any:
    return client.KVv2(kwargs.get("mount_path", "secret")).Put(
        None, kwargs.get("secret_path", ""), kwargs.get("data", {})
    )


def _kv2_delete(client, kwargs: dict) -> Any:
    return client.KVv2(kwargs.get("mount_path", "secret")).Delete(
        None, kwargs.get("secret_path", "")
    )


def _kv2_patch(client, kwargs: dict) -> Any:
    return client.KVv2(kwargs.get("mount_path", "secret")).Patch(
        None, kwargs.get("secret_path", ""), kwargs.get("new_data", {})
    )


def _kv1_get(client, kwargs: dict) -> Any:
    return client.KVv1(kwargs.get("mount_path", "secret")).Get(
        None, kwargs.get("secret_path", "")
    )


def _kv1_put(client, kwargs: dict) -> Any:
    return client.KVv1(kwargs.get("mount_path", "secret")).Put(
        None, kwargs.get("secret_path", ""), kwargs.get("data", {})
    )


def _kv1_delete(client, kwargs: dict) -> Any:
    return client.KVv1(kwargs.get("mount_path", "secret")).Delete(
        None, kwargs.get("secret_path", "")
    )


_KV_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    "kv2_get": _kv2_get,
    "kv2_put": _kv2_put,
    "kv2_delete": _kv2_delete,
    "kv2_patch": _kv2_patch,
    "kv1_get": _kv1_get,
    "kv1_put": _kv1_put,
    "kv1_delete": _kv1_delete,
}


def _dispatch_kv_action(action: str, client, kwargs: dict) -> Any:
    handler = _KV_ACTIONS.get(action)
    if handler is None:
        raise ValueError(f"Unknown KV action: {action}")
    return handler(client, kwargs)


def register_secrets_tools(mcp: FastMCP):
    """Register OpenBao MCP secrets tools."""

    @mcp.tool(tags={"logical"})
    async def openbao_mcp_logical(
        action: str = Field(
            description="Action to perform: 'read', 'write', 'delete', 'list', 'unwrap', 'write_bytes'"
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao logical operations."""
        if ctx:
            await ctx.info("Executing logical operations...")
        import json

        try:
            kwargs = json.loads(params_json)
        except Exception:
            return {"error": "Operation failed"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return _dispatch_logical_action(action, client, kwargs)

    @mcp.tool(tags={"kv"})
    async def openbao_mcp_kv(
        action: str = Field(
            description="Action: 'kv2_get', 'kv2_put', 'kv2_delete', 'kv2_patch', 'kv1_get', 'kv1_put', 'kv1_delete'"
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao Key-Value v1 and v2 engines."""
        if ctx:
            await ctx.info("Executing KV operations...")
        import json

        try:
            kwargs = json.loads(params_json)
        except Exception:
            return {"error": "Operation failed"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return _dispatch_kv_action(action, client, kwargs)
