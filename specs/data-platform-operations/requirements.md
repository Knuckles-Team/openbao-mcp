# CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001` | **Metadata-only operation.** Returns KV v2 metadata (path, current version, created and updated time) and a policy-to-path capability matrix, with no values and no HCL. Touches `openbao_mcp/mcp/mcp_secrets.py`. Moved from `MEDULLA-DATAPLAT-VOCAB-R009.3` (medulla). Caller chain: arbora `fleet.call` reaches the secrets tool of `openbao_mcp/mcp/mcp_secrets.py`, which dispatches a new `metadata` action through `_dispatch_logical_action` to the KV v2 `GetMetadata` method (`openbao_mcp/api/api_client_full.py`). Shape: a new action in `openbao_mcp/mcp/mcp_secrets.py` that returns path, current version, created and updated time from `GetMetadata`, plus a policy-to-path capability matrix; reuses `GetMetadata` and returns no value, data or token key. Proving test (planned): `tests/test_metadata_only_operation.py::test_metadata_response_has_no_value_data_or_token_key`. Proving test (planned): `tests/test_metadata_only_operation.py::test_metadata_response_has_no_value_data_or_token_key`. | response schema test asserts no value, data or token key at any depth. |
