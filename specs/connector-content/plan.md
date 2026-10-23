# CONN-OPENBAO-MCP-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `openbao-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `openbao_mcp` from it.
