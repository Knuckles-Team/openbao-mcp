# CONN-OPENBAO-MCP — Requirements

Governing specification: [spec.md](spec.md).

Each row identifies one connector behavior and its verification target.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-OPENBAO-MCP-R001` | **Governed transport.** The connector must send every OpenBao request through the SDK governed HTTP client built from its resolved TLS profile in `openbao_mcp/api/api_client_base.py`. Caller chain: an MCP tool of `openbao_mcp/mcp/mcp_secrets.py` calls `Client` in `openbao_mcp/api/api_client_full.py`, which calls `ApiClientBase.request` (`openbao_mcp/api/api_client_base.py:46`); the session was built by `create_http_client` (`openbao_mcp/api/api_client_base.py:25`). Shape: `create_http_client` with the resolved TLS profile in `openbao_mcp/api/api_client_base.py`; `Client.Headers()` in `openbao_mcp/api/api_client_full.py` mutates the governed client headers. Proving test: `tests/test_governed_http.py::test_requests_go_through_governed_client_with_token`. | `tests/test_governed_http.py` must exercise token and basic auth, namespace headers, the `LIST` method, empty bodies, and error statuses through the real client with a mock transport. |
