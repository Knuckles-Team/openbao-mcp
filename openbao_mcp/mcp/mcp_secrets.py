"""MCP tools for secrets and logical operations."""

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


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
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        path = kwargs.get("path", "")
        data = kwargs.get("data", {})

        if action == "read":
            return client.Logical().Read(path)
        if action == "write":
            return client.Logical().Write(path, data)
        if action == "delete":
            return client.Logical().Delete(path)
        if action == "list":
            return client.Logical().List(path)
        if action == "unwrap":
            token = kwargs.get("token", "")
            return client.Logical().Unwrap(token)
        if action == "write_bytes":
            raw_data = kwargs.get("data_bytes", b"")
            if isinstance(raw_data, str):
                raw_data = raw_data.encode("utf-8")
            return client.Logical().WriteBytes(path, raw_data)

        raise ValueError(f"Unknown logical action: {action}")

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
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        mount_path = kwargs.get("mount_path", "secret")
        secret_path = kwargs.get("secret_path", "")
        data = kwargs.get("data", {})
        new_data = kwargs.get("new_data", {})

        if action == "kv2_get":
            return client.KVv2(mount_path).Get(None, secret_path)
        if action == "kv2_put":
            return client.KVv2(mount_path).Put(None, secret_path, data)
        if action == "kv2_delete":
            return client.KVv2(mount_path).Delete(None, secret_path)
        if action == "kv2_patch":
            return client.KVv2(mount_path).Patch(None, secret_path, new_data)
        if action == "kv1_get":
            return client.KVv1(mount_path).Get(None, secret_path)
        if action == "kv1_put":
            return client.KVv1(mount_path).Put(None, secret_path, data)
        if action == "kv1_delete":
            return client.KVv1(mount_path).Delete(None, secret_path)

        raise ValueError(f"Unknown KV action: {action}")
