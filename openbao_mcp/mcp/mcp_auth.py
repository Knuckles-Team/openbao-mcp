"""Typed MCP tools for OpenBao auth operations (one tool per operation)."""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client
from openbao_mcp.mcp._guard import CONFIRMATION_REQUIRED

READ_ONLY = {"readOnlyHint": True, "idempotentHint": True}
CHANGES_STATE = {"readOnlyHint": False, "destructiveHint": False}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


class _AuthMethod:
    """auth_method shape the underlying client expects: a mount + credential data."""

    def __init__(self, mount_val, data_val):
        self.mount = mount_val
        self.data = data_val


def register_auth_tools(mcp: FastMCP):
    """Register the OpenBao auth tools."""

    @mcp.tool(tags={"auth"}, annotations=CHANGES_STATE)
    async def openbao_auth_login(
        data: dict[str, Any] = Field(
            description="Credential fields of the auth method, e.g. username and password."
        ),
        mount: str = Field(
            default="auth/userpass", description="Auth method mount path."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Log in through an auth method mount and return the issued client token."""
        return client.Auth().Login(None, _AuthMethod(mount, data))

    @mcp.tool(tags={"auth"}, annotations=CHANGES_STATE)
    async def openbao_auth_mfa_login(
        data: dict[str, Any] = Field(
            description="Credential fields of the auth method."
        ),
        creds: list[str] = Field(
            default_factory=list, description="MFA credentials, one per method."
        ),
        mount: str = Field(
            default="auth/userpass", description="Auth method mount path."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Start an MFA-protected login and return the MFA requirement or the token."""
        return client.Auth().MFALogin(None, _AuthMethod(mount, data), *creds)

    @mcp.tool(tags={"auth"}, annotations=CHANGES_STATE)
    async def openbao_auth_mfa_validate(
        mfa_secret: str = Field(
            description="The MFA request id returned by the login."
        ),
        payload: dict[str, Any] = Field(
            description="MFA method id mapped to its passcode."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Complete an MFA login with the passcodes and return the issued token."""
        return client.Auth().MFAValidate(None, mfa_secret, payload)

    @mcp.tool(tags={"auth"}, annotations=CHANGES_STATE)
    async def openbao_auth_token_create(
        opts: dict[str, Any] = Field(
            description="Token request: policies, ttl, renewable, display_name, num_uses."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Create a child token. The token value appears only in this response."""
        return client.Auth().Token().Create(opts)

    @mcp.tool(tags={"auth"}, annotations=READ_ONLY)
    async def openbao_auth_token_lookup(
        token: str = Field(description="The token to look up."),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Read a token's policies, ttl and metadata."""
        return client.Auth().Token().Lookup(token)

    @mcp.tool(tags={"auth"}, annotations=CHANGES_STATE)
    async def openbao_auth_token_renew(
        token: str = Field(description="The token to renew."),
        increment: int = Field(
            default=0, description="Requested ttl increment in seconds."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Extend a renewable token's lease."""
        return client.Auth().Token().Renew(token, increment)

    @mcp.tool(tags={"auth"}, annotations=DESTRUCTIVE)
    async def openbao_auth_token_revoke(
        token: str = Field(
            description="The token to revoke together with its children."
        ),
        confirm: bool = Field(
            default=False, description="Must be true; set only after the person agrees."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> Any:
        """Revoke a token and every child token and lease it created."""
        if not confirm:
            return CONFIRMATION_REQUIRED
        return client.Auth().Token().RevokeTree(token)
