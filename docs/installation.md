# Installation

`openbao-mcp` is a standard Python package and a prebuilt container image. Pick the
path that matches how you want to run it.

## Requirements

- **Python 3.11 – 3.14**.
- A reachable **OpenBao server** (or a Vault-compatible endpoint) — see
  [Backing Platform](platform.md) to deploy one locally.

## From PyPI (recommended)

```bash
pip install openbao-mcp
```

### Optional extras

The base install is intentionally minimal. Install the extra for what you need:

| Extra | Install | Pulls in |
|---|---|---|
| `mcp` | `pip install "openbao-mcp[mcp]"` | FastMCP MCP-server runtime (`agent-utilities[mcp]`) |
| `agent` | `pip install "openbao-mcp[agent]"` | Pydantic-AI agent server + Logfire tracing |
| `all` | `pip install "openbao-mcp[all]"` | Everything above |
| `test` | `pip install "openbao-mcp[test]"` | `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-xdist` |

```bash
# Typical: run the MCP server and the agent server
pip install "openbao-mcp[all]"
```

## From source

```bash
git clone https://github.com/Knuckles-Team/openbao-mcp.git
cd openbao-mcp
pip install -e ".[all]"          # editable install with every extra
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv pip install -e ".[all]"
uv run openbao-mcp
```

## Prebuilt Docker image

A multi-stage, slim image is published on every release (installs
`openbao-mcp[all]`, entrypoint `openbao-mcp`):

```bash
docker pull knucklessg1/openbao-mcp:latest

docker run --rm -i \
  -e OPENBAO_URL=http://your-openbao:8200 \
  -e OPENBAO_TOKEN=bao_root_token \
  knucklessg1/openbao-mcp:latest        # stdio transport (default)
```

For an HTTP server with a published port, see [Deployment](deployment.md).

## Verify the install

```bash
openbao-mcp --help
python -c "import openbao_mcp; print(openbao_mcp.__version__)"
```

## Next steps

- **[Deployment](deployment.md)** — run it as a long-lived MCP server behind Caddy + DNS.
- **[Usage](usage.md)** — call the tools and the `Api` client.
- **[Configuration](deployment.md#configuration-environment)** — every environment variable.
