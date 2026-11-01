# CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS — Operations the data-platform vocabulary needs

Owner: openbao-mcp. Cross-repo IDs: `MEDULLA-DATAPLAT-VOCAB-R009`.

## Purpose and user stories

The medulla data-platform vocabulary answers competency questions from connector facts. One question needs an operation this connector lacks. This spec owns that operation.

## Why a new spec

The existing specs in `specs/` cover packaged content and identity, not tool operations. None owns a new connector operation.

## Scope and interfaces

Owned: the one operation named in the row, touching `openbao_mcp/mcp/mcp_secrets.py`. Non-goal: anything in the medulla vocabulary itself.

## Open questions

- None.

## Delivery mapping

Component: openbao-mcp connector

Code: ../../openbao_mcp/__init__.py

## User Scenarios & Testing

### User Story 1 - Metadata-only operation (Priority: P1)

The fleet operator and the engine rely on this behaviour of `openbao-mcp`: Returns KV v2 metadata (path, current version, created and updated time) and a policy-to-path capability matrix, with no values and no HCL. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `openbao-mcp` connector built from the default branch, **When** `tests/test_metadata_only_operation.py::test_metadata_response_has_no_value_data_or_token_key` runs, **Then** response schema test asserts no value, data or token key at any depth.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Metadata-only operation. Rows: `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001`.

## Success Criteria

- **SC-001**: response schema test asserts no value, data or token key at any depth. Rows: `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001`.

## Assumptions

- The `openbao-mcp` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-OPENBAO-MCP-DATA-PLATFORM-OPERATIONS-R001` | plan.md Production caller chain | T-001 | tests/test_metadata_only_operation.py::test_metadata_response_has_no_value_data_or_token_key |
