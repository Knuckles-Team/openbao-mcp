# CONN-OPENBAO-MCP-CONNECTOR-CONTENT — The connector serves its packaged content

Owner: openbao-mcp. Cross-repo IDs: `SCION-CONNECTOR-CONTROL-R071`, `SCION-CONNECTOR-CONTROL-R073`.

## Purpose and user stories

The `openbao-mcp` server serves its packaged skills, prompts and ontology to any client, with no wiring of its own.

## Delivery mapping

Component: openbao-mcp connector

Code: ../../openbao_mcp/__init__.py

## Why a new spec

Searched `specs/` of `openbao-mcp` with `git grep` for the terms of this spec. No other spec of this repository owns the capability, so this spec owns it.

## User Scenarios & Testing

### User Story 1 - Default content (Priority: P1)

The fleet operator and the engine rely on this behaviour of `openbao-mcp`: `pyproject.toml` declares `openbao-mcp` as the single `scion_sdk.connector` entry point. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `openbao-mcp` connector built from the default branch, **When** `tests/test_default_content_surfaces.py::test_default_content_surfaces` runs, **Then** `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Default content. Rows: `CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R001`.
- **FR-002**: The packaged ontology extends only the core ontology and redeclares no core term (`CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R004`).
- **FR-003**: The revoke and delete tools are declared destructive (`CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R005`).

## Success Criteria

- **SC-001**: `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Rows: `CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R001`.

## Assumptions

- The `openbao-mcp` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R001` | plan.md Production caller chain | T-001 | tests/test_default_content_surfaces.py::test_default_content_surfaces |
| FR-002 | `CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R004` | plan.md Production caller chain | T-004 | tests/test_ontology_extends_core.py::test_pack_declares_no_core_term |
| FR-003 | `CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R005` | plan.md Production caller chain | T-005 | tests/test_destructive_declaration.py::test_destructive_tools_declare_the_destructive_hint |
