# CONN-OPENBAO-MCP — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Level | Setup and input | Expected observation | Evidence |
|---|---|---|---|---|---|
| T-001 | CONN-OPENBAO-MCP-R001 | Contract | Mock transport behind the governed client | Token header, namespace header, `LIST`, empty body and error mapping hold | `tests/test_governed_http.py` |

## Negative and boundary cases

A 403 response raises the connector API error. A 204 response returns the success result.

## Quality and release proof

`uv run pytest tests`.
