# CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001` | **Metadata-only operation.** Returns KV v2 metadata (path, current version, created and updated time) and a policy-to-path capability matrix, with no values and no HCL. Touches `openbao_mcp/mcp/mcp_secrets.py`. Moved from `EG-DATAPLAT-VOCAB-R009.3` (medulla). | response schema test asserts no value, data or token key at any depth. |
