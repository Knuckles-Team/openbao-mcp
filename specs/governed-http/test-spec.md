# CONN-OPENBAO-MCP — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-OPENBAO-MCP-R001` | `tests/test_governed_http.py::test_requests_go_through_governed_client_with_token` | `tests/test_governed_http.py` must exercise token and basic auth, namespace headers, the `LIST` method, empty bodies, and error statuses through the real client with a mock transport. |

## Negative and boundary cases

Each proving test above includes the refusal or error case that its row names. A vendor outage or an unauthorised call must return the SDK typed error.

## Quality and release proof

Run `uv run pytest tests` and `pre-commit run --all-files` from the repository root. A planned test is added by the code change that lands the row.
