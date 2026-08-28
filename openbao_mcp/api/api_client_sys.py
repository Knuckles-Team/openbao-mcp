from openbao_mcp.api.api_client_base import ApiClientBase


def _entitled(namespace: str, names: list[str]) -> list[str]:
    """Filter ``names`` to the subset the calling identity's Okta/Keycloak groups
    entitle (CONCEPT:AU-OS.identity.identity-scoped-resource-autoload). Degrades
    to the full list if agent-utilities predates the resolver.
    """
    try:
        from agent_utilities.security.entitlements import identity_scoped_resources
    except Exception:
        return list(names)
    return list(identity_scoped_resources(namespace, names))


def _mount_paths(data: dict) -> list[str]:
    """Mount paths present in a sys/mounts ``data`` mapping (entries shaped like a mount)."""
    return [k for k, v in data.items() if isinstance(v, dict) and "type" in v]


def _without_denied_mounts(mounts: dict, denied: set[str]) -> dict:
    """Copy of ``mounts`` with every denied mount path removed from both response shapes."""
    filtered = dict(mounts)
    if isinstance(filtered.get("data"), dict):
        filtered["data"] = {
            k: v for k, v in filtered["data"].items() if k not in denied
        }
    for path in denied:
        filtered.pop(path, None)
    return filtered


class Api(ApiClientBase):
    def get_health(self) -> dict:
        """Get OpenBao engine health status."""
        return self.request("GET", "/v1/sys/health")

    def get_mounts(self) -> dict:
        """Get mounted secret engines, scoped to the caller's identity entitlements."""
        mounts = self.request("GET", "/v1/sys/mounts")
        if not isinstance(mounts, dict):
            return mounts
        data = mounts.get("data") if isinstance(mounts.get("data"), dict) else mounts
        if not isinstance(data, dict):
            return mounts
        mount_paths = _mount_paths(data)
        denied = set(mount_paths) - set(_entitled("mount", mount_paths))
        if not denied:
            return mounts
        return _without_denied_mounts(mounts, denied)

    def enable_mount(self, mount: str, mount_type: str) -> dict:
        """Enable a secrets engine mount."""
        return self.request(
            "POST", f"/v1/sys/mounts/{mount}", data={"type": mount_type}
        )

    def get_internal_openapi_spec(self) -> dict:
        """Fetch dynamically compiled OpenAPI schema spec."""
        return self.request("GET", "/v1/sys/internal/specs/openapi")
