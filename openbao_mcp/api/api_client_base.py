from typing import Any
from urllib.parse import urljoin

import httpx
from scion_sdk.http.client import build_http_client
from scion_sdk.http.options import HttpClientOptions
from scion_sdk.tls.profile import ResolvedTLSProfile
from scion_sdk.tls.resolve import resolve_tls_profile


class ApiClientBase:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        tls_profile: ResolvedTLSProfile | None = None,
    ):
        self.base_url = base_url
        self.token = token
        self.username = username
        self.password = password
        self.tls_profile = tls_profile or resolve_tls_profile("openbao")
        self._session = build_http_client(
            HttpClientOptions(
                base_url=base_url,
                tls=self.tls_profile,
                allow_plaintext=True,
                auth=(
                    httpx.BasicAuth(username, password)
                    if not token and username and password
                    else None
                ),
            )
        )

        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})

    def close(self) -> None:
        """Release transport resources and runtime-only TLS material."""
        self._session.close()
        self.tls_profile.cleanup()

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = urljoin(self.base_url, endpoint)

        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        response = self._session.request(
            method=method,
            url=url,
            headers=req_headers,
            params=params,
            json=data,
        )

        if 300 <= response.status_code < 400:
            raise Exception(
                f"API error: {response.status_code} redirect to "
                f"{response.headers.get('location', '?')}; OPENBAO_URL must be the "
                "address that serves the API directly (a redirect is never a result)"
            )
        if response.status_code >= 400:
            raise Exception(f"API error: {response.status_code}{_api_errors(response)}")

        if response.status_code == 204 or not response.text.strip():
            return {"status": "success"}

        try:
            return response.json()
        except Exception as exc:
            raise Exception(
                f"API error: {response.status_code} non-JSON response "
                f"({response.headers.get('content-type', 'unknown')})"
            ) from exc


def _api_errors(response: httpx.Response) -> str:
    """The OpenBao ``errors`` list of an error response, never the request."""
    try:
        errors = response.json().get("errors") or []
    except Exception:
        return ""
    return f": {'; '.join(str(e) for e in errors)}" if errors else ""
