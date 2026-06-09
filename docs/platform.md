# Backing Platform — OpenBao

`openbao-mcp` is a **client** of an [OpenBao](https://openbao.org/) server (the Linux
Foundation's open-source fork of HashiCorp Vault). This page provides a Docker recipe
for deploying one locally to serve as the target of `OPENBAO_URL`. For production
topologies, follow the upstream
[OpenBao documentation](https://openbao.org/docs/).

!!! note "Backing-system recipe"
    Each connector in the ecosystem follows the same convention — a
    `docs/platform.md` recipe for the system it integrates with, accompanied by a
    sample Compose stack that mirrors [`services/`](https://github.com/Knuckles-Team).
    Systems offered only as a managed service have no local recipe.

## Single-node deployment (Compose)

OpenBao publishes the `quay.io/openbao/openbao` image. The following stack runs one
server on `:8200` with file storage and TLS disabled for local development:

```yaml
# docker/openbao.compose.yml
services:
  openbao:
    image: quay.io/openbao/openbao:2.0.0
    container_name: openbao
    hostname: openbao
    restart: unless-stopped
    command: ["sh", "-c", "chmod -R 777 /bao/data && docker-entrypoint.sh server"]
    user: "0"
    environment:
      BAO_ADDR: "http://0.0.0.0:8200"
      BAO_LOCAL_CONFIG: >-
        {"storage": {"file": {"path": "/bao/data"}},
         "listener": {"tcp": {"address": "0.0.0.0:8200", "tls_disable": 1}},
         "ui": true}
    ports:
      - "8200:8200"            # API + web UI (HTTP, TLS disabled for local dev)
    cap_add:
      - IPC_LOCK
    volumes:
      - openbao-data:/bao/data

volumes:
  openbao-data:
    driver: local
```

```bash
docker compose -f docker/openbao.compose.yml up -d

# Initialize and unseal (first run), then verify the server is healthy
curl -s http://localhost:8200/v1/sys/health
```

## Connect openbao-mcp

```bash
export OPENBAO_URL=http://localhost:8200
export OPENBAO_TOKEN=bao_root_token
export OPENBAO_MCP_SSL_VERIFY=False          # TLS disabled for local dev

openbao-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

## Combined deployment

A combined stack places OpenBao and the MCP server on one Docker network, so the
server reaches the backend by container name:

```yaml
# docker/stack.compose.yml
services:
  openbao:
    image: quay.io/openbao/openbao:2.0.0
    command: ["sh", "-c", "chmod -R 777 /bao/data && docker-entrypoint.sh server"]
    user: "0"
    environment:
      BAO_ADDR: "http://0.0.0.0:8200"
      BAO_LOCAL_CONFIG: '{"storage": {"file": {"path": "/bao/data"}}, "listener": {"tcp": {"address": "0.0.0.0:8200", "tls_disable": 1}}, "ui": true}'
    cap_add: ["IPC_LOCK"]
    volumes: ["openbao-data:/bao/data"]
    ports: ["8200:8200"]

  openbao-mcp:
    image: knucklessg1/openbao-mcp:latest
    depends_on: [openbao]
    environment:
      - OPENBAO_URL=http://openbao:8200
      - OPENBAO_TOKEN=bao_root_token
      - OPENBAO_MCP_SSL_VERIFY=False
      - TRANSPORT=streamable-http
      - HOST=0.0.0.0
      - PORT=8000
    ports: ["8000:8000"]

volumes:
  openbao-data:
    driver: local
```

```bash
docker compose -f docker/stack.compose.yml up -d
```

## Operate the backend

With the server running and a valid `OPENBAO_TOKEN`, the
[system tool](usage.md#as-an-mcp-server) (`openbao_mcp_sys`) drives initialization,
seal / unseal, and mount management, while the secrets and key-value tools read and
write secrets against the engines you enable.
