"""The OpenBao client reaches the API through the governed SDK HTTP client."""

import httpx
import pytest
from agent_connector_sdk.http import client as sdk_http

from openbao_mcp.api import api_client_base
from openbao_mcp.api.api_client_full import Client


def _install(monkeypatch, handler):
    seen = {}
    real = sdk_http.create_http_client

    def build(options, **kwargs):
        seen["options"] = options
        return real(options, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(api_client_base, "create_http_client", build)
    return seen


def test_requests_go_through_governed_client_with_token(monkeypatch):
    """CONN-OPENBAO-MCP-R001: calls use the SDK client and carry the token header."""
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"data": {"ok": True}})

    seen = _install(monkeypatch, handler)
    client = Client("http://openbao.test:8200", token="t-placeholder")
    assert client.request("GET", "/v1/sys/health") == {"data": {"ok": True}}
    assert captured[0].headers["authorization"] == "Bearer t-placeholder"
    assert seen["options"].tls is client.tls_profile
    client.close()


def test_list_method_empty_and_error_mapping(monkeypatch):
    """CONN-OPENBAO-MCP-R001: LIST, 204 and error statuses keep their results."""
    methods = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.path.endswith("/boom"):
            return httpx.Response(403, json={"errors": ["denied"]})
        return httpx.Response(204)

    _install(monkeypatch, handler)
    client = Client("http://openbao.test:8200")
    assert client.request("LIST", "/v1/secret/metadata/") == {"status": "success"}
    assert methods == ["LIST"]
    with pytest.raises(Exception, match="API error: 403"):
        client.request("GET", "/v1/boom")
    client.close()


def test_header_mutation_and_basic_auth(monkeypatch):
    """CONN-OPENBAO-MCP-R001: namespace headers and basic auth apply to requests."""
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={})

    _install(monkeypatch, handler)
    client = Client("http://openbao.test:8200", username="u", password="p")
    client.SetNamespace("team")
    client.request("GET", "/v1/sys/health")
    assert captured[0].headers["x-vault-namespace"] == "team"
    assert captured[0].headers["authorization"].startswith("Basic ")
    client.ClearNamespace()
    client.request("GET", "/v1/sys/health")
    assert "x-vault-namespace" not in captured[1].headers
    assert client.Headers() == httpx.Headers({})
    client.close()
