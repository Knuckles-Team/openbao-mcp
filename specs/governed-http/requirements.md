# CONN-OPENBAO-MCP — Requirements

Governing specification: [spec.md](spec.md).

Each row identifies one connector behavior and its verification target.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-OPENBAO-MCP-R001` | **Governed transport.** The connector must send every OpenBao request through the SDK governed HTTP client built from its resolved TLS profile in `openbao_mcp/api/api_client_base.py`. | `tests/test_governed_http.py` must exercise token and basic auth, namespace headers, the `LIST` method, empty bodies, and error statuses through the real client with a mock transport. |
