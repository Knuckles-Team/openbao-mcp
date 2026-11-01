# CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001` | `tests/test_metadata_only_operation.py::test_metadata_response_has_no_value_data_or_token_key` (planned) | response schema test asserts no value, data or token key at any depth. |

## Negative and boundary cases

Each proving test above includes the refusal or error case that its row names. A vendor outage or an unauthorised call must return the SDK typed error.

## Quality and release proof

Run `uv run pytest tests` and `pre-commit run --all-files` from the repository root. A planned test is added by the code change that lands the row.
