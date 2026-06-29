# Openbao MCP

[![Status](https://img.shields.io/badge/status-active-success)](https://github.com/genius-agents/openbao-mcp)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](pyproject.toml)
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

#### Condensed action-routed tools (default — `MCP_TOOL_MODE=condensed`)

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `openbao_mcp_auth` | `AUTHTOOL` | Manage OpenBao auth operations. |
| `openbao_mcp_kv` | `SECRETSTOOL` | Manage OpenBao Key-Value v1 and v2 engines. |
| `openbao_mcp_logical` | `SECRETSTOOL` | Manage OpenBao logical operations. |
| `openbao_mcp_ssh` | `SSHTOOL` | Manage OpenBao SSH and SSH Helper operations. |
| `openbao_mcp_sys` | `SYSTOOL` | Manage OpenBao sys operations. |

#### Verbose 1:1 API-mapped tools (`MCP_TOOL_MODE=verbose` or `both`)

<details>
<summary>75 per-operation tools — one per public API method (click to expand)</summary>

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `openbao_AddHeader` | `CLIENTTOOL` | Invoke the AddHeader operation. |
| `openbao_Address` | `CLIENTTOOL` | Invoke the Address operation. |
| `openbao_Auth` | `CLIENTTOOL` | Invoke the Auth operation. |
| `openbao_CheckRetry` | `CLIENTTOOL` | Invoke the CheckRetry operation. |
| `openbao_ClearNamespace` | `CLIENTTOOL` | Invoke the ClearNamespace operation. |
| `openbao_ClearToken` | `CLIENTTOOL` | Invoke the ClearToken operation. |
| `openbao_ClientTimeout` | `CLIENTTOOL` | Invoke the ClientTimeout operation. |
| `openbao_Clone` | `CLIENTTOOL` | Invoke the Clone operation. |
| `openbao_CloneConfig` | `CLIENTTOOL` | Invoke the CloneConfig operation. |
| `openbao_CloneHeaders` | `CLIENTTOOL` | Invoke the CloneHeaders operation. |
| `openbao_CloneToken` | `CLIENTTOOL` | Invoke the CloneToken operation. |
| `openbao_CloneWithHeaders` | `CLIENTTOOL` | Invoke the CloneWithHeaders operation. |
| `openbao_CurrentWrappingLookupFunc` | `CLIENTTOOL` | Invoke the CurrentWrappingLookupFunc operation. |
| `openbao_DisableKeepAlives` | `CLIENTTOOL` | Invoke the DisableKeepAlives operation. |
| `openbao_Headers` | `CLIENTTOOL` | Invoke the Headers operation. |
| `openbao_Help` | `CLIENTTOOL` | Invoke the Help operation. |
| `openbao_HelpWithContext` | `CLIENTTOOL` | Invoke the HelpWithContext operation. |
| `openbao_KVv1` | `CLIENTTOOL` | Invoke the KVv1 operation. |
| `openbao_KVv2` | `CLIENTTOOL` | Invoke the KVv2 operation. |
| `openbao_Limiter` | `CLIENTTOOL` | Invoke the Limiter operation. |
| `openbao_Logical` | `CLIENTTOOL` | Invoke the Logical operation. |
| `openbao_MaxIdleConnections` | `CLIENTTOOL` | Invoke the MaxIdleConnections operation. |
| `openbao_MaxRetries` | `CLIENTTOOL` | Invoke the MaxRetries operation. |
| `openbao_MaxRetryWait` | `CLIENTTOOL` | Invoke the MaxRetryWait operation. |
| `openbao_MinRetryWait` | `CLIENTTOOL` | Invoke the MinRetryWait operation. |
| `openbao_Namespace` | `CLIENTTOOL` | Invoke the Namespace operation. |
| `openbao_NewClient` | `CLIENTTOOL` | Invoke the NewClient operation. |
| `openbao_NewLifetimeWatcher` | `CLIENTTOOL` | Invoke the NewLifetimeWatcher operation. |
| `openbao_NewRenewer` | `CLIENTTOOL` | Invoke the NewRenewer operation. |
| `openbao_NewRequest` | `CLIENTTOOL` | Invoke the NewRequest operation. |
| `openbao_OutputCurlString` | `CLIENTTOOL` | Invoke the OutputCurlString operation. |
| `openbao_OutputPolicy` | `CLIENTTOOL` | Invoke the OutputPolicy operation. |
| `openbao_RawRequest` | `CLIENTTOOL` | Invoke the RawRequest operation. |
| `openbao_RawRequestWithContext` | `CLIENTTOOL` | Invoke the RawRequestWithContext operation. |
| `openbao_SRVLookup` | `CLIENTTOOL` | Invoke the SRVLookup operation. |
| `openbao_SSH` | `CLIENTTOOL` | Invoke the SSH operation. |
| `openbao_SSHHelper` | `CLIENTTOOL` | Invoke the SSHHelper operation. |
| `openbao_SSHHelperWithMountPoint` | `CLIENTTOOL` | Invoke the SSHHelperWithMountPoint operation. |
| `openbao_SSHWithMountPoint` | `CLIENTTOOL` | Invoke the SSHWithMountPoint operation. |
| `openbao_SetAddress` | `CLIENTTOOL` | Invoke the SetAddress operation. |
| `openbao_SetBackoff` | `CLIENTTOOL` | Invoke the SetBackoff operation. |
| `openbao_SetCheckRedirect` | `CLIENTTOOL` | Invoke the SetCheckRedirect operation. |
| `openbao_SetCheckRetry` | `CLIENTTOOL` | Invoke the SetCheckRetry operation. |
| `openbao_SetClientTimeout` | `CLIENTTOOL` | Invoke the SetClientTimeout operation. |
| `openbao_SetCloneHeaders` | `CLIENTTOOL` | Invoke the SetCloneHeaders operation. |
| `openbao_SetCloneToken` | `CLIENTTOOL` | Invoke the SetCloneToken operation. |
| `openbao_SetDisableKeepAlives` | `CLIENTTOOL` | Invoke the SetDisableKeepAlives operation. |
| `openbao_SetHeaders` | `CLIENTTOOL` | Invoke the SetHeaders operation. |
| `openbao_SetLimiter` | `CLIENTTOOL` | Invoke the SetLimiter operation. |
| `openbao_SetLogger` | `CLIENTTOOL` | Invoke the SetLogger operation. |
| `openbao_SetMFACreds` | `CLIENTTOOL` | Invoke the SetMFACreds operation. |
| `openbao_SetMaxIdleConnections` | `CLIENTTOOL` | Invoke the SetMaxIdleConnections operation. |
| `openbao_SetMaxRetries` | `CLIENTTOOL` | Invoke the SetMaxRetries operation. |
| `openbao_SetMaxRetryWait` | `CLIENTTOOL` | Invoke the SetMaxRetryWait operation. |
| `openbao_SetMinRetryWait` | `CLIENTTOOL` | Invoke the SetMinRetryWait operation. |
| `openbao_SetNamespace` | `CLIENTTOOL` | Invoke the SetNamespace operation. |
| `openbao_SetOutputCurlString` | `CLIENTTOOL` | Invoke the SetOutputCurlString operation. |
| `openbao_SetOutputPolicy` | `CLIENTTOOL` | Invoke the SetOutputPolicy operation. |
| `openbao_SetPolicyOverride` | `CLIENTTOOL` | Invoke the SetPolicyOverride operation. |
| `openbao_SetSRVLookup` | `CLIENTTOOL` | Invoke the SetSRVLookup operation. |
| `openbao_SetToken` | `CLIENTTOOL` | Invoke the SetToken operation. |
| `openbao_SetWrappingLookupFunc` | `CLIENTTOOL` | Invoke the SetWrappingLookupFunc operation. |
| `openbao_Sys` | `CLIENTTOOL` | Invoke the Sys operation. |
| `openbao_Token` | `CLIENTTOOL` | Invoke the Token operation. |
| `openbao_WithNamespace` | `CLIENTTOOL` | Invoke the WithNamespace operation. |
| `openbao_WithRequestCallbacks` | `CLIENTTOOL` | Invoke the WithRequestCallbacks operation. |
| `openbao_WithResponseCallbacks` | `CLIENTTOOL` | Invoke the WithResponseCallbacks operation. |
| `openbao_delete_secret` | `APITOOL` | Delete a secret path. |
| `openbao_enable_mount` | `APITOOL` | Enable a secrets engine mount. |
| `openbao_get_health` | `APITOOL` | Get OpenBao engine health status. |
| `openbao_get_internal_openapi_spec` | `APITOOL` | Fetch dynamically compiled OpenAPI schema spec. |
| `openbao_get_mounts` | `APITOOL` | Get mounted secret engines. |
| `openbao_list_secrets` | `APITOOL` | List secrets under a path. |
| `openbao_read_secret` | `APITOOL` | Read a secret key-value path. |
| `openbao_write_secret` | `APITOOL` | Write a secret key-value path. |

</details>

_5 action-routed tool(s) (default) · 75 verbose 1:1 tool(s). Each is enabled unless its `<DOMAIN>TOOL` toggle is set false; `MCP_TOOL_MODE` selects the surface (`condensed` default · `verbose` 1:1 · `both`). Auto-generated — do not edit._
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

## Environment Variables

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `OPENBAO_URL` | `http://127.0.0.1:8200` | The primary URL of the OpenBao server. |
| `OPENBAO_TOKEN` | `bao_root_token` | Root or service account access token. |
| `BAO_ADDR` | `http://127.0.0.1:8200` | Fallback address aliases for OpenBao / Vault endpoints. |
| `VAULT_ADDR` | `http://127.0.0.1:8200` |  |
| `OPENBAO_MCP_BASE_URL` | `http://127.0.0.1:8200` | Alternative base URL fallback for user-level client endpoints. |
| `OPENBAO_MCP_USERNAME` | — | Client credentials for user authentication methods. |
| `OPENBAO_MCP_PASSWORD` | — |  |
| `OPENBAO_MCP_SSL_VERIFY` | `True` | Enable/disable SSL/TLS certificate verification (True or False). |
| `SECRETSTOOL` | `True` | Set to True/False to enable or disable specific tool categories in the MCP server. |
| `SYSTOOL` | `True` |  |
| `AUTHTOOL` | `True` |  |
| `SSHTOOL` | `True` |  |

#### Inherited agent-utilities variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `TRANSPORT` | `stdio` | MCP transport: `stdio` | `streamable-http` | `sse` |
| `HOST` | `0.0.0.0` | Bind host (HTTP transports) |
| `PORT` | `8000` | Bind port (HTTP transports) |
| `MCP_TOOL_MODE` | `condensed` | Tool surface: `condensed` | `verbose` | `both` |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool allow-list |
| `MCP_DISABLED_TOOLS` | — | Comma-separated tool deny-list |
| `MCP_ENABLED_TAGS` | — | Comma-separated tag allow-list |
| `MCP_DISABLED_TAGS` | — | Comma-separated tag deny-list |
| `EUNOMIA_TYPE` | `none` | Authorization mode: `none` | `embedded` | `remote` |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` | Embedded Eunomia policy file |
| `EUNOMIA_REMOTE_URL` | — | Remote Eunomia authorization server URL |
| `ENABLE_OTEL` | `False` | Enable OpenTelemetry export |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint |
| `MCP_CLIENT_AUTH` | — | Outbound MCP auth (`oidc-client-credentials` for fleet calls) |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET` | — | OIDC client secret (service-account auth) |
| `DEBUG` | `False` | Verbose logging |
| `PYTHONUNBUFFERED` | `1` | Unbuffered stdout (recommended in containers) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | `openai` | LLM provider for the agent |
| `MODEL_ID` | `gpt-4o` | Model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_12 package + 22 inherited variable(s). Auto-generated from `.env.example` + the shared agent-utilities set — do not edit._
<!-- ENV-VARS-TABLE:END -->
