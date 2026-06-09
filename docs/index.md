# openbao-mcp

OpenBao secrets-engine **API + MCP Server** for the agent-utilities ecosystem —
a typed, deterministic tool surface over the OpenBao (Vault-compatible) secrets,
system, authentication, and SSH APIs.

!!! info "Official documentation"
    This site is the canonical reference for `openbao-mcp`, maintained alongside every
    release.

[![PyPI](https://img.shields.io/pypi/v/openbao-mcp)](https://pypi.org/project/openbao-mcp/)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
[![License](https://img.shields.io/pypi/l/openbao-mcp)](https://github.com/Knuckles-Team/openbao-mcp/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/Knuckles-Team/openbao-mcp)

## Overview

`openbao-mcp` wraps the [OpenBao](https://openbao.org/) HTTP API — the Linux
Foundation's open-source fork of HashiCorp Vault — with typed, deterministic MCP
tools an agent can call. It provides:

- **`Api`** — a dynamic-facade client (`openbao_mcp.api_client`) over the OpenBao
  secrets, system, authentication, and SSH engines, configured entirely from the
  environment.
- **Action-routed MCP tools** across four namespaces — secrets / key-value,
  system administration, authentication, and SSH — each gated by an enable flag.
- **An optional Pydantic-AI agent server** (`openbao-agent`) that wraps the same tool
  surface for conversational orchestration.

The server **remains inactive when credentials are absent** and never persists
secrets outside the OpenBao backend.

## Explore the documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Installation](installation.md)** — pip, source, extras, and the prebuilt Docker image.
- :material-server-network: **[Deployment](deployment.md)** — run the MCP server, the agent server, Docker Compose, Caddy + Technitium.
- :material-console: **[Usage](usage.md)** — the MCP tools, the `Api` client, and example prompts.
- :material-database-cog: **[Backing Platform](platform.md)** — deploy OpenBao with Docker.
- :material-sitemap: **[Overview](overview.md)** — architecture and the dynamic facade.
- :material-tag-multiple: **[Concepts](concepts.md)** — the `CONCEPT:BAO-*` registry.

</div>

## Quick start

```bash
pip install "openbao-mcp[mcp]"
openbao-mcp                       # stdio MCP server (default transport)
```

Connect it to an OpenBao server:

```bash
export OPENBAO_URL=http://127.0.0.1:8200
export OPENBAO_TOKEN=bao_root_token
openbao-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

See **[Installation](installation.md)** and **[Deployment](deployment.md)** for the
full matrix (PyPI extras, Docker image, all transports, the agent server, reverse
proxy, DNS).
