"""Typed MCP tools for OpenBao logical and key-value operations (one tool per operation)."""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client
from openbao_mcp.mcp._guard import CONFIRMATION_REQUIRED

READ_ONLY = {"readOnlyHint": True, "idempotentHint": True}
CHANGES_STATE = {"readOnlyHint": False, "destructiveHint": False}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}

_CTX = Field(default=None, description="MCP context")


def register_secrets_tools(mcp: FastMCP):
    """Register the OpenBao logical and KV tools."""

    @mcp.tool(tags={"logical"}, annotations=READ_ONLY)
    async def openbao_logical_read(
        path: str = Field(description="Full API path, for example secret/data/app."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Read any OpenBao API path through the logical client."""
        return client.Logical().Read(path)

    @mcp.tool(tags={"logical"}, annotations=CHANGES_STATE)
    async def openbao_logical_write(
        path: str = Field(description="Full API path to write."),
        data: dict[str, Any] = Field(description="Request body."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Write a JSON body to any OpenBao API path."""
        return client.Logical().Write(path, data)

    @mcp.tool(tags={"logical"}, annotations=CHANGES_STATE)
    async def openbao_logical_write_bytes(
        path: str = Field(description="Full API path to write."),
        data_bytes: str = Field(description="Raw request body, UTF-8 text."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Write a raw byte body to an OpenBao API path."""
        return client.Logical().WriteBytes(path, data_bytes.encode("utf-8"))

    @mcp.tool(tags={"logical"}, annotations=DESTRUCTIVE)
    async def openbao_logical_delete(
        path: str = Field(description="Full API path to delete."),
        confirm: bool = Field(
            default=False, description="Must be true; set only after the person agrees."
        ),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Delete an OpenBao API path."""
        if not confirm:
            return CONFIRMATION_REQUIRED
        return client.Logical().Delete(path)

    @mcp.tool(tags={"logical"}, annotations=READ_ONLY)
    async def openbao_logical_list(
        path: str = Field(description="Full API path whose children are listed."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """List the child keys under an OpenBao API path."""
        return client.Logical().List(path)

    @mcp.tool(tags={"logical"}, annotations=CHANGES_STATE)
    async def openbao_logical_unwrap(
        token: str = Field(description="The single-use wrapping token."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Unwrap a response-wrapping token and return the wrapped secret once."""
        return client.Logical().Unwrap(token)

    @mcp.tool(tags={"kv"}, annotations=READ_ONLY)
    async def openbao_kv2_get(
        secret_path: str = Field(description="Secret path inside the mount."),
        mount_path: str = Field(default="secret", description="KV v2 mount."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Read the latest version of a KV v2 secret."""
        return client.KVv2(mount_path).Get(None, secret_path)

    @mcp.tool(tags={"kv"}, annotations=CHANGES_STATE)
    async def openbao_kv2_put(
        secret_path: str = Field(description="Secret path inside the mount."),
        data: dict[str, Any] = Field(description="The full secret data to store."),
        mount_path: str = Field(default="secret", description="KV v2 mount."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Write a new version of a KV v2 secret, replacing its data."""
        return client.KVv2(mount_path).Put(None, secret_path, data)

    @mcp.tool(tags={"kv"}, annotations=CHANGES_STATE)
    async def openbao_kv2_patch(
        secret_path: str = Field(description="Secret path inside the mount."),
        new_data: dict[str, Any] = Field(description="Keys to merge into the secret."),
        mount_path: str = Field(default="secret", description="KV v2 mount."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Merge keys into a KV v2 secret and write a new version; other keys stay."""
        return client.KVv2(mount_path).Patch(None, secret_path, new_data)

    @mcp.tool(tags={"kv"}, annotations=DESTRUCTIVE)
    async def openbao_kv2_delete(
        secret_path: str = Field(description="Secret path inside the mount."),
        mount_path: str = Field(default="secret", description="KV v2 mount."),
        confirm: bool = Field(
            default=False, description="Must be true; set only after the person agrees."
        ),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Soft-delete the latest version of a KV v2 secret."""
        if not confirm:
            return CONFIRMATION_REQUIRED
        return client.KVv2(mount_path).Delete(None, secret_path)

    @mcp.tool(tags={"kv"}, annotations=READ_ONLY)
    async def openbao_kv1_get(
        secret_path: str = Field(description="Secret path inside the mount."),
        mount_path: str = Field(default="secret", description="KV v1 mount."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Read a KV v1 secret."""
        return client.KVv1(mount_path).Get(None, secret_path)

    @mcp.tool(tags={"kv"}, annotations=CHANGES_STATE)
    async def openbao_kv1_put(
        secret_path: str = Field(description="Secret path inside the mount."),
        data: dict[str, Any] = Field(description="The secret data to store."),
        mount_path: str = Field(default="secret", description="KV v1 mount."),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Write a KV v1 secret, replacing its data."""
        return client.KVv1(mount_path).Put(None, secret_path, data)

    @mcp.tool(tags={"kv"}, annotations=DESTRUCTIVE)
    async def openbao_kv1_delete(
        secret_path: str = Field(description="Secret path inside the mount."),
        mount_path: str = Field(default="secret", description="KV v1 mount."),
        confirm: bool = Field(
            default=False, description="Must be true; set only after the person agrees."
        ),
        client=Depends(get_client),
        ctx: Context | None = _CTX,
    ) -> Any:
        """Delete a KV v1 secret permanently."""
        if not confirm:
            return CONFIRMATION_REQUIRED
        return client.KVv1(mount_path).Delete(None, secret_path)
