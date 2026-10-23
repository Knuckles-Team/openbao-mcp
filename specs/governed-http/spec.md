# CONN-OPENBAO-MCP — Governed HTTP transport

## Outcome

The connector must reach the OpenBao API only through the shared governed HTTP client.
The client must keep the connector's TLS profile, token and namespace headers, and result shapes.

## Scope and owner

The `openbao-mcp` repository owns the OpenBao operations and their results.
The shared connector SDK owns the governed HTTP client, retry and rate-limit handling, and TLS profiles (SDK-CENTRALIZED-CAPABILITIES-R001, SDK-CENTRALIZED-CAPABILITIES-R008).
The shared pipelines repository owns quality gates and delivery rendering.

Component: OpenBao API client
References: [Connector SDK](https://github.com/Knuckles-Team/agent-connector-sdk/blob/main/README.md)
Code: ../../openbao_mcp/api/api_client_base.py ../../openbao_mcp/api/api_client_full.py ../../tests/test_governed_http.py

## Non-goals

This specification grants no service access, credential creation, deployment, or approval exception.
The `VAULT_ADDR` and `BAO_ADDR` reads stay, because the target system is OpenBao.
