# CONN-OPENBAO-MCP — Governed HTTP transport

## Outcome

The connector must reach the OpenBao API only through the shared governed HTTP client.
The client must keep the connector's TLS profile, token and namespace headers, and result shapes.

## Scope and owner

The `openbao-mcp` repository owns the OpenBao operations and their results.
The shared connector SDK owns the governed HTTP client, retry and rate-limit handling, and TLS profiles (SCION-CENTRALIZED-CAPABILITIES-R001, SCION-CENTRALIZED-CAPABILITIES-R008).
The shared pipelines repository owns quality gates and delivery rendering.

Component: OpenBao API client
References: [Connector SDK](https://github.com/Knuckles-Team/scion-sdk/blob/main/README.md)
Code: ../../openbao_mcp/api/api_client_base.py ../../openbao_mcp/api/api_client_full.py ../../tests/test_governed_http.py

## Non-goals

This specification grants no service access, credential creation, deployment, or approval exception.
The `VAULT_ADDR` and `BAO_ADDR` reads stay, because the target system is OpenBao.

## Why a new spec

Searched `specs/` of `openbao-mcp` with `git grep` for the terms of this spec. No other spec of this repository owns the capability, so this spec owns it.

## User Scenarios & Testing

### User Story 1 - Governed transport (Priority: P1)

The fleet operator and the engine rely on this behaviour of `openbao-mcp`: The connector must send every OpenBao request through the SDK governed HTTP client built from its resolved TLS profile in `openbao_mcp/api/api_client_base.py`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `openbao-mcp` connector built from the default branch, **When** `tests/test_governed_http.py::test_requests_go_through_governed_client_with_token` runs, **Then** `tests/test_governed_http.py` must exercise token and basic auth, namespace headers, the `LIST` method, empty bodies, and error statuses through the real client with a mock transport.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Governed transport. Rows: `CONN-OPENBAO-MCP-R001`.

## Success Criteria

- **SC-001**: `tests/test_governed_http.py` must exercise token and basic auth, namespace headers, the `LIST` method, empty bodies, and error statuses through the real client with a mock transport. Rows: `CONN-OPENBAO-MCP-R001`.

## Assumptions

- The `openbao-mcp` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-OPENBAO-MCP-R001` | plan.md Production caller chain | T-001 | tests/test_governed_http.py::test_requests_go_through_governed_client_with_token |
