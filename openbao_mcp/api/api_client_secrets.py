from openbao_mcp.api.api_client_base import ApiClientBase


class Api(ApiClientBase):
    def read_secret(self, mount: str, path: str) -> dict:
        """Read a secret key-value path."""
        return self.request("GET", f"/v1/{mount}/data/{path}")

    def write_secret(self, mount: str, path: str, secret_data: dict) -> dict:
        """Write a secret key-value path."""
        return self.request(
            "POST", f"/v1/{mount}/data/{path}", data={"data": secret_data}
        )

    def delete_secret(self, mount: str, path: str) -> dict:
        """Delete a secret path."""
        return self.request("DELETE", f"/v1/{mount}/data/{path}")

    def list_secrets(self, mount: str, path: str = "") -> dict:
        """List secrets under a path."""
        return self.request("LIST", f"/v1/{mount}/metadata/{path}")
