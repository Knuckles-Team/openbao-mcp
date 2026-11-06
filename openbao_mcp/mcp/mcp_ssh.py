"""Typed MCP tools for OpenBao SSH operations (one tool per operation)."""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client

CHANGES_STATE = {"readOnlyHint": False, "destructiveHint": False}


def register_ssh_tools(mcp: FastMCP):
    """Register the OpenBao SSH tools."""

    @mcp.tool(tags={"ssh"}, annotations=CHANGES_STATE)
    async def openbao_ssh_credential(
        role: str = Field(description="SSH role to issue a credential for."),
        data: dict[str, Any] = Field(
            default_factory=dict, description="Request fields such as ip and username."
        ),
        mount_point: str = Field(
            default="ssh", description="SSH secrets engine mount."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Issue a one-time password or key credential from an SSH role."""
        return client.SSHWithMountPoint(mount_point).Credential(role, data)

    @mcp.tool(tags={"ssh"}, annotations=CHANGES_STATE)
    async def openbao_ssh_sign_key(
        role: str = Field(description="SSH CA role that signs the key."),
        data: dict[str, Any] = Field(
            description="Request fields: public_key, valid_principals, ttl."
        ),
        mount_point: str = Field(
            default="ssh", description="SSH secrets engine mount."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Sign a public SSH key with the CA of a role and return the certificate."""
        return client.SSHWithMountPoint(mount_point).SignKey(role, data)

    @mcp.tool(tags={"ssh"}, annotations={"readOnlyHint": True})
    async def openbao_ssh_verify(
        otp: str = Field(description="The one-time password to verify."),
        mount_point: str = Field(
            default="ssh", description="SSH secrets engine mount."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Verify an SSH one-time password and return the role and user it belongs to."""
        return client.SSHHelperWithMountPoint(mount_point).Verify(otp)
