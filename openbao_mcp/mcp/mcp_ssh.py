"""MCP tools for SSH operations."""

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


def register_ssh_tools(mcp: FastMCP):
    """Register OpenBao MCP SSH tools."""

    @mcp.tool(tags={"ssh"})
    async def openbao_mcp_ssh(
        action: str = Field(description="Action: 'credential', 'sign_key', 'verify'"),
        params_json: str = Field(
            default="{}", description="JSON string of parameters."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao SSH and SSH Helper operations."""
        if ctx:
            await ctx.info("Executing SSH operations...")
        import json

        try:
            kwargs = json.loads(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        mount_point = kwargs.get("mount_point", "ssh")
        role = kwargs.get("role", "")
        data = kwargs.get("data", {})

        if action == "credential":
            return client.SSHWithMountPoint(mount_point).Credential(role, data)

        if action == "sign_key":
            return client.SSHWithMountPoint(mount_point).SignKey(role, data)

        if action == "verify":
            otp = kwargs.get("otp", "")
            return client.SSHHelperWithMountPoint(mount_point).Verify(otp)

        raise ValueError(f"Unknown SSH action: {action}")
