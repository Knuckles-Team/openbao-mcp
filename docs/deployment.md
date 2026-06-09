# Deployment

This page covers running `openbao-mcp` as a long-lived server: the transports, a
Docker Compose stack, putting it behind a Caddy reverse proxy, and giving it a DNS
name with Technitium. To provision the **OpenBao server** it connects to, see
[Backing Platform](platform.md).

> `openbao-mcp` ships **two** console scripts: an **MCP server** (`openbao-mcp`) — a
> typed, deterministic tool surface a policy router / agent calls — and an **A2A agent
> server** (`openbao-agent`) that wraps that surface for conversational orchestration.

## Run the MCP server

The transport is selected with `--transport` (or the `TRANSPORT` env var):

=== "stdio (default)"

    ```bash
    openbao-mcp
    ```
    For IDE / desktop MCP clients that launch the server as a subprocess.

=== "streamable-http"

    ```bash
    openbao-mcp --transport streamable-http --host 0.0.0.0 --port 8000
    ```
    A network server with a `/health` endpoint and `/mcp` route.

=== "sse"

    ```bash
    openbao-mcp --transport sse --host 0.0.0.0 --port 8000
    ```

Health check (HTTP transports):

```bash
curl -s http://localhost:8000/health        # {"status":"OK"}
```

## Configuration (environment)

`openbao-mcp` is configured entirely from the environment. The **required** set:

| Var | Default | Meaning |
|---|---|---|
| `OPENBAO_URL` | `http://127.0.0.1:8200` | Primary OpenBao server URL |
| `OPENBAO_TOKEN` | `bao_root_token` | Root or service-account access token |
| `OPENBAO_MCP_SSL_VERIFY` | `True` | Verify TLS certificates |
| `SECRETSTOOL` | `True` | Register the secrets / key-value tool set |
| `SYSTOOL` | `True` | Register the system-administration tool set |
| `AUTHTOOL` | `True` | Register the authentication tool set |
| `SSHTOOL` | `True` | Register the SSH tool set |

Optional fallbacks and username/password authentication are also recognized:
`BAO_ADDR`, `VAULT_ADDR`, `OPENBAO_MCP_BASE_URL`, `OPENBAO_MCP_USERNAME`,
`OPENBAO_MCP_PASSWORD`. Plus `HOST` / `PORT` / `TRANSPORT` for HTTP transports. The
full set is documented in
[`.env.example`](https://github.com/Knuckles-Team/openbao-mcp/blob/main/.env.example).
Copy it to `.env` and fill in only what you use.

## Docker Compose

The repo ships [`docker/mcp.compose.yml`](https://github.com/Knuckles-Team/openbao-mcp/blob/main/docker/mcp.compose.yml).
It reads a sibling `.env` and publishes the HTTP server on `:8000`:

```yaml
services:
  openbao-mcp:
    image: knucklessg1/openbao-mcp:latest
    container_name: openbao-mcp
    hostname: openbao-mcp
    restart: always
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=8000
      - TRANSPORT=streamable-http
      - OPENBAO_URL
      - OPENBAO_TOKEN
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
cp .env.example .env          # then edit OPENBAO_* values
docker compose -f docker/mcp.compose.yml up -d
docker compose -f docker/mcp.compose.yml logs -f
```

## Run the agent server

`openbao-mcp` also ships the `openbao-agent` console script — a Pydantic-AI A2A agent
server that connects to the MCP tool surface and exposes a conversational endpoint.
It reads its toolset from the MCP server (over `--mcp-url`) or from a bundled
`mcp_config.json`:

```bash
# Point the agent at a running MCP HTTP server
openbao-agent --mcp-url http://openbao-mcp:8000/mcp --host 0.0.0.0 --port 9000

# …or let it launch the MCP server from the bundled mcp_config.json
openbao-agent --host 0.0.0.0 --port 9000
```

The agent listens on its own port (`9000` by convention). Provide the model
provider / API key with `--provider`, `--model-id`, `--base-url`, and `--api-key`, or
the equivalent environment variables. A Compose service mirrors the MCP one — wire
`MCP_URL` to the MCP container and publish the agent port:

```yaml
# docker/agent.compose.yml
services:
  openbao-agent:
    image: knucklessg1/openbao-mcp:latest
    container_name: openbao-agent
    hostname: openbao-agent
    restart: always
    entrypoint: ["openbao-agent"]
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=9000
      - MCP_URL=http://openbao-mcp:8000/mcp
    ports:
      - "9000:9000"
    depends_on:
      - openbao-mcp
```

## Behind a Caddy reverse proxy

Expose the HTTP server on a hostname with automatic TLS. Add to your `Caddyfile`:

```caddy
# Internal (self-signed) — homelab .arpa zone
openbao-mcp.arpa {
    tls internal
    reverse_proxy openbao-mcp:8000
}
```

```caddy
# Public — automatic Let's Encrypt
openbao-mcp.example.com {
    reverse_proxy openbao-mcp:8000
}
```

Reload Caddy:

```bash
docker compose -f services/caddy/compose.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## DNS with Technitium

Point the hostname at the host running Caddy. Via the Technitium API:

```bash
curl -s "http://technitium.arpa:5380/api/zones/records/add" \
  --data-urlencode "token=$TECHNITIUM_DNS_TOKEN" \
  --data-urlencode "domain=openbao-mcp.arpa" \
  --data-urlencode "zone=arpa" \
  --data-urlencode "type=A" \
  --data-urlencode "ipAddress=10.0.0.10" \
  --data-urlencode "ttl=3600"
```

…or add an **A record** `openbao-mcp.arpa → <caddy-host-ip>` in the Technitium web
console (`http://technitium.arpa:5380`). The ecosystem
[`technitium-dns-mcp`](https://knuckles-team.github.io/technitium-dns-mcp/) automates
this as a tool.

## Register with an MCP client

Add to your client's `mcp_config.json` (multiplexer nickname `bao`):

```json
{
  "mcpServers": {
    "openbao-mcp": {
      "command": "uv",
      "args": ["run", "openbao-mcp"],
      "env": {
        "OPENBAO_URL": "http://your-openbao:8200",
        "OPENBAO_TOKEN": "bao_root_token"
      }
    }
  }
}
```

For a remote HTTP server, point the client at `http://openbao-mcp.arpa/mcp` instead.
