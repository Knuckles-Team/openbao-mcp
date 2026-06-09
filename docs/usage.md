# Usage — API / CLI / MCP

`openbao-mcp` exposes the same capability three ways: as **MCP tools** an agent calls,
as a **Python API** (`Api`) you import, and as a **CLI** (the `openbao-mcp` and
`openbao-agent` console scripts). The architecture and the dynamic facade are
described in [Overview](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers action-routed tools across four
namespaces, each toggled by its enable flag (`SECRETSTOOL`, `SYSTOOL`, `AUTHTOOL`,
`SSHTOOL`):

| Namespace | Tool | Actions |
|---|---|---|
| Secrets | `openbao_mcp_logical` | `read`, `write`, `delete`, `list`, `unwrap`, `write_bytes` |
| Key-value | `openbao_mcp_kv` | `kv2_get`, `kv2_put`, `kv2_delete`, `kv2_patch`, `kv1_get`, `kv1_put`, `kv1_delete` |
| System | `openbao_mcp_sys` | `get_health`, `get_mounts`, `enable_mount`, `init`, `seal`, `unseal`, `seal_status`, `leader`, … |
| Authentication | `openbao_mcp_auth` | `login`, `mfa_login`, `mfa_validate`, `token_create`, `token_lookup`, `token_renew`, `token_revoke` |
| SSH | `openbao_mcp_ssh` | `credential`, `sign_key`, `verify` |

Each tool takes an `action` plus a `params_json` JSON string of parameters.
Example agent prompts that map onto these tools:

- *"Read the secret at `secret/data/app/config`"* → `openbao_mcp_kv` (`kv2_get`)
- *"Is the OpenBao server healthy and unsealed?"* → `openbao_mcp_sys` (`get_health`, `seal_status`)
- *"Issue a short-lived SSH credential for role `web`"* → `openbao_mcp_ssh` (`credential`)

## As a Python API

`Api` is a dynamic-facade client that composes the secrets, system, and base
sub-clients. Build one directly or from the environment:

```python
from openbao_mcp.api_client import Api

api = Api(
    base_url="http://127.0.0.1:8200",
    token="bao_root_token",
    verify=True,
)

# Reads
health = api.get_health()                     # server health / seal status
mounts = api.get_mounts()                      # mounted secrets engines
secret = api.read_secret("secret", "app/config")
keys = api.list_secrets("secret", "app")
```

Build a client straight from the environment (reads `OPENBAO_URL`,
`OPENBAO_TOKEN`, `OPENBAO_MCP_SSL_VERIFY`, and the username/password fallbacks):

```python
from openbao_mcp.auth import get_client
api = get_client()
```

### Writes

```python
api.write_secret("secret", "app/config", {"password": "s3cr3t"})
api.enable_mount("kv", "kv-v2")
api.delete_secret("secret", "app/config")
```

## As a CLI

The MCP server itself is the primary CLI; the bundled agent server is the second.

```bash
# Run the MCP server (stdio default; see Deployment for HTTP transports)
openbao-mcp
openbao-mcp --transport streamable-http --host 0.0.0.0 --port 8000

# Run the Pydantic-AI agent server against a running MCP endpoint
openbao-agent --mcp-url http://openbao-mcp:8000/mcp --host 0.0.0.0 --port 9000
```

The server **remains inactive when credentials are absent** — each namespace can be
disabled with its enable flag, and writes degrade to a clear error rather than acting
against an unreachable backend.
