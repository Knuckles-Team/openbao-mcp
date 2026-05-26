"""MCP tools for auth operations."""

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from openbao_mcp.auth import get_client


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
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if action == "login":
            # auth_method is represented by standard dictionary containing mount/credentials
            class MockAuthMethod:
                def __init__(self, mount_val, data_val):
                    self.mount = mount_val
                    self.data = data_val

            mount = kwargs.get("mount", "auth/userpass")
            data = kwargs.get("data", {})
            return client.Auth().Login(None, MockAuthMethod(mount, data))

        if action == "mfa_login":

            class MockMFAMethod:
                def __init__(self, mount_val, data_val):
                    self.mount = mount_val
                    self.data = data_val

            mount = kwargs.get("mount", "auth/userpass")
            data = kwargs.get("data", {})
            creds = kwargs.get("creds", [])
            return client.Auth().MFALogin(None, MockMFAMethod(mount, data), *creds)

        if action == "mfa_validate":
            mfa_secret = kwargs.get("mfa_secret", "")
            payload = kwargs.get("payload", {})
            return client.Auth().MFAValidate(None, mfa_secret, payload)

        if action == "token_create":
            opts = kwargs.get("opts", {})
            return client.Auth().Token().Create(opts)

        if action == "token_lookup":
            token = kwargs.get("token", "")
            return client.Auth().Token().Lookup(token)

        if action == "token_renew":
            token = kwargs.get("token", "")
            increment = kwargs.get("increment", 0)
            return client.Auth().Token().Renew(token, increment)

        if action == "token_revoke":
            token = kwargs.get("token", "")
            return client.Auth().Token().RevokeTree(token)

        raise ValueError(f"Unknown auth action: {action}")
