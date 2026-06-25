# Openbao MCP

[![Status](https://img.shields.io/badge/status-active-success)](https://github.com/genius-agents/openbao-mcp)
[![Version](https://img.shields.io/badge/version-0.32.0-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

OpenBao Secrets and Encryption Key Vault orchestrator. Built with the highest architectural standards, incorporating dynamic facades, custom API routing, and FastMCP tool decoration.

> **Documentation** — Installation, deployment, usage across the API, CLI, and MCP
> interfaces, and guidance for provisioning the OpenBao backend are maintained in the
> [official documentation](https://knuckles-team.github.io/openbao-mcp/).

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [MCP Tools](#mcp-tools)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Openbao MCP provides a high-performance, model-optimized interface to Openbao capabilities. It isolates the model from underlying API transport complexity, ensuring safe, idempotent, and highly traceable system interactions.

---

## Features

- **Dynamic Facade Orchestration**: Integrates multi-inheritance clients cleanly under a single facade.
- **Battle-Tested Resilience**: Out-of-the-box credential authentication, connection polling, and request retry strategies.
- **FastMCP Declarative Tools**: Fast, native schema registration with full inline validation.
- **Complete Test Intent Diversity**: Deep, automated unit, integration, and mock tests ensuring high code coverage.

---

## ⚙️ Dynamic Tool Selection & Visibility

This MCP server supports dynamic toolset selection and visibility filtering at runtime. This allows you to restrict the set of exposed tools in order to prevent blowing up the LLM's context window.

You can configure tool filtering via multiple input channels:

- **CLI Arguments:** Pass `--tools` or `--toolsets` (or their disabled counterparts `--disabled-tools` and `--disabled-toolsets`) during startup.
- **Environment Variables:** Define standard environment variables:
  - `MCP_ENABLED_TOOLS` / `MCP_DISABLED_TOOLS`
  - `MCP_ENABLED_TAGS` / `MCP_DISABLED_TAGS`
- **HTTP SSE Request Headers:** Pass custom headers during transport initialization:
  - `x-mcp-enabled-tools` / `x-mcp-disabled-tools`
  - `x-mcp-enabled-tags` / `x-mcp-disabled-tags`
- **HTTP SSE Request Query Parameters:** Append query parameters directly to your transport connection URL:
  - `?tools=tool1,tool2`
  - `?tags=tag1`

When query strings or parameters are supplied, an LLM-free **Knowledge Graph resolution layer** (using `DynamicToolOrchestrator`) matches query intents against known tool tags, names, or descriptions, with safe fallback and automated 24-hour background cache refreshing.


---

## Installation

> **Install the slim `[mcp]` extra.** For MCP-server hosting (including `uvx` /
> container deploys), install `openbao-mcp[mcp]` — the MCP-server extra that pulls
> only the FastMCP / FastAPI tooling (`agent-utilities[mcp]`). It deliberately
> **excludes** the heavy agent runtime (the epistemic-graph engine, `pydantic-ai`,
> `dspy`, `llama-index`, `tree-sitter`), so installs are dramatically smaller and
> faster. Use the full `[agent]` extra only when you need the integrated Pydantic
> AI agent.

Pick the extra that matches what you want to run:

| Extra | Installs | Use when |
|-------|----------|----------|
| `openbao-mcp[mcp]` | Slim MCP server only (`agent-utilities[mcp]` — FastMCP/FastAPI) | You only run the **MCP server** (smallest install / image) |
| `openbao-mcp[agent]` | Full agent runtime (`agent-utilities[agent,logfire]` — Pydantic AI + the epistemic-graph engine) | You run the **integrated A2A agent** |
| `openbao-mcp[all]` | Everything (`mcp` + `agent` + `logfire`) | Development / both surfaces |

```bash
# MCP server only (recommended for tool hosting — slim deps)
uv pip install "openbao-mcp[mcp]"

# Full agent runtime (Pydantic AI + epistemic-graph engine)
uv pip install "openbao-mcp[agent]"

# Everything (development)
uv pip install "openbao-mcp[all]"      # or: python -m pip install "openbao-mcp[all]"
```

### Container images (`:mcp` vs `:agent`)

One multi-stage `docker/Dockerfile` builds two right-sized images, selected by `--target`:

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `knucklessg1/openbao-mcp:mcp` | `--target mcp` | `openbao-mcp[mcp]` — **slim**, no engine/`pydantic-ai`/`dspy`/`llama-index`/`tree-sitter` | `openbao-mcp` |
| `knucklessg1/openbao-mcp:latest` | `--target agent` (default) | `openbao-mcp[agent]` — **full** agent runtime + epistemic-graph engine | `openbao-agent` |

```bash
docker build --target mcp   -t knucklessg1/openbao-mcp:mcp    docker/   # slim MCP server
docker build --target agent -t knucklessg1/openbao-mcp:latest docker/   # full agent
```

`docker/mcp.compose.yml` runs the slim `:mcp` server; `docker/compose.yml` runs the
agent (`:latest`).

### Knowledge-graph database (`epistemic-graph`)

The **full agent** (`[agent]` / `:latest`) embeds the **epistemic-graph** engine (pulled in
transitively via `agent-utilities[agent]`). For production — or to share one knowledge graph
across multiple agents — run **epistemic-graph as its own database container** and point the
agent at it instead of embedding it. Deployment recipes (single-node + Raft HA), connection
config, and the full database architecture (with diagrams) are documented in the
[epistemic-graph deployment guide](https://knuckles-team.github.io/epistemic-graph/deployment/).
The slim `[mcp]` server does **not** require the database.

---

## Usage

You can launch the FastMCP server in stdio mode via Python module execution:

```python
import asyncio
from openbao_mcp.mcp_server import get_mcp_instance

async def main():
    mcp = get_mcp_instance()
    # Execute stdio loop or launch server
    print("MCP Server ready.")

if __name__ == "__main__":
    asyncio.run(main())
```

For direct shell launch, execute:

```bash
python -m openbao_mcp.mcp_server
```

---

## Configuration

The package is fully configurable via the environment variables listed below:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENBAO_URL` | The primary URL of the OpenBao server. | `http://127.0.0.1:8200` | Yes |
| `OPENBAO_TOKEN` | Root or service account access token. | `bao_root_token` | Yes |
| `BAO_ADDR` | Alias/fallback for the OpenBao server address. | None | No |
| `VAULT_ADDR` | Alias/fallback for the OpenBao/Vault server address. | None | No |
| `OPENBAO_MCP_BASE_URL` | Alternative fallback URL for user-level client endpoints. | `http://127.0.0.1:8200` | No |
| `OPENBAO_MCP_USERNAME` | Username for username/password authentication methods. | None | No |
| `OPENBAO_MCP_PASSWORD` | Password for username/password authentication methods. | None | No |
| `OPENBAO_MCP_SSL_VERIFY` | Enable/disable SSL/TLS certificate verification (True/False). | `True` | No |
| `SECRETSTOOL` | Enable/disable Secrets Engine MCP tools namespace. | `True` | No |
| `SYSTOOL` | Enable/disable System Administration MCP tools namespace. | `True` | No |
| `AUTHTOOL` | Enable/disable Authentication Engine MCP tools namespace. | `True` | No |
| `SSHTOOL` | Enable/disable SSH Management MCP tools namespace. | `True` | No |

A local template is supplied inside [.env.example](.env.example). Copy this file as `.env` and fill out your specific service endpoint parameters before starting execution.

---

## MCP Tools

The following declarative FastMCP tools are registered and available to upstream AI agents. This table is auto-generated from the live server — do not edit by hand.

<!-- MCP-TOOLS-TABLE:START -->

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `openbao_mcp_auth` | `AUTHTOOL` | Manage OpenBao auth operations. |
| `openbao_mcp_kv` | `SECRETSTOOL` | Manage OpenBao Key-Value v1 and v2 engines. |
| `openbao_mcp_logical` | `SECRETSTOOL` | Manage OpenBao logical operations. |
| `openbao_mcp_ssh` | `SSHTOOL` | Manage OpenBao SSH and SSH Helper operations. |
| `openbao_mcp_sys` | `SYSTOOL` | Manage OpenBao sys operations. |

_5 action-routed tools (default `MCP_TOOL_MODE=condensed`). Each is enabled unless its toggle is set false; set `MCP_TOOL_MODE=verbose` (or `both`) for the 1:1 per-operation surface. Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

See [docs/overview.md](docs/overview.md) or [docs/concepts.md](docs/concepts.md) for deeper operational examples.

---

## Architecture

This package uses the standardized Agent-Utilities dynamic facade architecture:

```mermaid
graph TD
    User([User Agent]) --> Server[FastMCP Server]
    Server --> Facade[Api Dynamic Facade]
    Facade --> ClientBase[ApiClientBase]
    Facade --> Auth[Credentials Auth Handler]
    ClientBase --> Service([External Service API])
```

---

## Deployment

### Bare-Metal (Standard pip)
1. Set up your Python virtual environment (>= 3.10).
2. Install the package: `pip install .[all]`
3. Export credentials:
   ```bash
   export OPENBAO_URL="http://127.0.0.1:8200"
   ```
4. Run: `python -m openbao_mcp.mcp_server`

### Container (Docker Compose)
A standard compose structure is provided inside the `docker/` folder. Build and deploy:

```bash
docker compose -f docker/mcp.compose.yml up -d    # slim :mcp server
docker compose -f docker/compose.yml up --build -d # full :latest agent
```

Or pull a prebuilt image:

```bash
docker pull knucklessg1/openbao-mcp:mcp      # slim MCP server
docker pull knucklessg1/openbao-mcp:latest   # full agent (default)
```

> The `:mcp` tag is the **slim MCP-server image** (`docker/Dockerfile --target mcp`,
> installing `openbao-mcp[mcp]`); the default `:latest` tag is the **full agent image**
> (`--target agent`, `openbao-mcp[agent]`) which also bundles the Pydantic AI agent and
> the epistemic-graph engine. See [Container images](#container-images-mcp-vs-agent).

---

<!-- BEGIN GENERATED: additional-deployment-options -->
### Additional Deployment Options

`openbao-mcp` can also run as a **local container** (Docker / Podman / `uv`) or be
consumed from a **remote deployment**. The
[Deployment guide](https://knuckles-team.github.io/openbao-mcp/deployment/) has full, copy-paste
`mcp_config.json` for all four transports — **stdio**, **streamable-http**,
**local container / uv**, and **remote URL**:

- **Local container / uv** — launch the server from `mcp_config.json` via `uvx`,
  `docker run`, or `podman run`, or point at a local streamable-http container by `url`.
- **Remote URL** — connect to a server deployed behind Caddy at
  `http://openbao-mcp.arpa/mcp` using the `"url"` key.
<!-- END GENERATED: additional-deployment-options -->

## Documentation

The complete documentation is published as the
[official documentation site](https://knuckles-team.github.io/openbao-mcp/) and is the
recommended reference for installation, deployment, and day-to-day operation.

| Page | Contents |
|---|---|
| [Installation](https://knuckles-team.github.io/openbao-mcp/installation/) | pip, source, extras, prebuilt Docker image |
| [Deployment](https://knuckles-team.github.io/openbao-mcp/deployment/) | run the MCP server, the agent server, Compose, Caddy + Technitium, env config |
| [Usage](https://knuckles-team.github.io/openbao-mcp/usage/) | the MCP tools, the `Api` client, example prompts |
| [Backing Platform](https://knuckles-team.github.io/openbao-mcp/platform/) | deploy OpenBao with Docker |
| [Overview](https://knuckles-team.github.io/openbao-mcp/overview/) | architecture and the dynamic facade |
| [Concepts](https://knuckles-team.github.io/openbao-mcp/concepts/) | concept registry (`CONCEPT:BAO-*`) |

`AGENTS.md` is the canonical contributor/agent guidance.

## Contributing

Please audit all code changes against ecosystem guidelines in [CONTRIBUTING.md](CONTRIBUTING.md) if available, and run:

```bash
pre-commit run --all-files
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete details.


<!-- BEGIN agent-os-genesis-deploy (generated; do not edit between markers) -->

## Deploy with `agent-os-genesis`

This package can be provisioned for you — skill-guided — by the **`agent-os-genesis`**
universal skill (its *single-package deploy mode*): it picks your install method, seeds
secrets to OpenBao/Vault (or `.env`), trusts your enterprise CA, registers the MCP
server, and verifies it — the same machinery that stands up the whole Agent OS, narrowed
to just this package. Ask your agent to **"deploy `openbao-mcp` with agent-os-genesis"**.

| Install mode | Command |
|------|---------|
| Bare-metal, prod (PyPI) | `uvx openbao-mcp` · or `uv tool install openbao-mcp` |
| Bare-metal, dev (editable) | `uv pip install -e ".[all]"` · or `pip install -e ".[all]"` |
| Container, prod | deploy `knucklessg1/openbao-mcp:latest` via docker-compose / swarm / podman / podman-compose / kubernetes |
| Container, dev (editable) | deploy `docker/compose.dev.yml` (source-mounted at `/src`; edits live on restart) |

Secrets are read-existing + seeded via `vault_sync` — you are only prompted for what's missing.

<!-- END agent-os-genesis-deploy -->
