"""MCP tools for auth operations."""

from collections.abc import Callable
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


class _AuthMethod:
    """auth_method shape the underlying client expects: a mount + credential data."""

    def __init__(self, mount_val, data_val):
        self.mount = mount_val
        self.data = data_val


def _auth_login(client, kwargs: dict) -> Any:
    mount = kwargs.get("mount", "auth/userpass")
    data = kwargs.get("data", {})
    return client.Auth().Login(None, _AuthMethod(mount, data))


def _auth_mfa_login(client, kwargs: dict) -> Any:
    mount = kwargs.get("mount", "auth/userpass")
    data = kwargs.get("data", {})
    creds = kwargs.get("creds", [])
    return client.Auth().MFALogin(None, _AuthMethod(mount, data), *creds)


def _auth_mfa_validate(client, kwargs: dict) -> Any:
    mfa_secret = kwargs.get("mfa_secret", "")
    payload = kwargs.get("payload", {})
    return client.Auth().MFAValidate(None, mfa_secret, payload)


def _auth_token_create(client, kwargs: dict) -> Any:
    return client.Auth().Token().Create(kwargs.get("opts", {}))


def _auth_token_lookup(client, kwargs: dict) -> Any:
    return client.Auth().Token().Lookup(kwargs.get("token", ""))


def _auth_token_renew(client, kwargs: dict) -> Any:
    token = kwargs.get("token", "")
    increment = kwargs.get("increment", 0)
    return client.Auth().Token().Renew(token, increment)


def _auth_token_revoke(client, kwargs: dict) -> Any:
    return client.Auth().Token().RevokeTree(kwargs.get("token", ""))


_AUTH_ACTIONS: dict[str, Callable[[Any, dict], Any]] = {
    "login": _auth_login,
    "mfa_login": _auth_mfa_login,
    "mfa_validate": _auth_mfa_validate,
    "token_create": _auth_token_create,
    "token_lookup": _auth_token_lookup,
    "token_renew": _auth_token_renew,
    "token_revoke": _auth_token_revoke,
}


def _dispatch_auth_action(action: str, client, kwargs: dict) -> Any:
    handler = _AUTH_ACTIONS.get(action)
    if handler is None:
        raise ValueError(f"Unknown auth action: {action}")
    return handler(client, kwargs)


def register_auth_tools(mcp: FastMCP):
    """Register OpenBao MCP auth tools."""

    @mcp.tool(tags={"auth"})
    async def openbao_mcp_auth(
        action: str = Field(
            description=(
                "Action: 'login', 'mfa_login', 'mfa_validate', 'token_create', "
                "'token_lookup', 'token_renew', 'token_revoke'"
            )
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters."
        ),
        client=Depends(get_client),
        ctx: Context | None = Field(default=None, description="MCP context"),
    ) -> dict:
        """Manage OpenBao auth operations."""
        if ctx:
            await ctx.info("Executing auth operations...")
        import json

        try:
            kwargs = json.loads(params_json)
        except Exception:
            return {"error": "Operation failed"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return _dispatch_auth_action(action, client, kwargs)
