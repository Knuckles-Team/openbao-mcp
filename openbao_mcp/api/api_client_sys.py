from openbao_mcp.api.api_client_base import ApiClientBase


class Api(ApiClientBase):
    def get_health(self) -> dict:
        """Get OpenBao engine health status."""
        return self.request("GET", "/v1/sys/health")

    def get_mounts(self) -> dict:
        """Get mounted secret engines."""
        return self.request("GET", "/v1/sys/mounts")

    def enable_mount(self, mount: str, mount_type: str) -> dict:
        """Enable a secrets engine mount."""
        return self.request(
            "POST", f"/v1/sys/mounts/{mount}", data={"type": mount_type}
        )

    def get_internal_openapi_spec(self) -> dict:
        """Fetch dynamically compiled OpenAPI schema spec."""
        return self.request("GET", "/v1/sys/internal/specs/openapi")
