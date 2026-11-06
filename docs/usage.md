# Usage — API / CLI / MCP

`openbao-mcp` exposes the same capability three ways: as **MCP tools** an agent calls,
as a **Python API** (`Api`) the operator import, and as a **CLI** (the `openbao-mcp` and
`openbao-agent` console scripts). The architecture and the dynamic facade are
described in [Overview](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers one typed tool per operation across
four namespaces, each toggled by its enable flag (`SECRETSTOOL`, `SYSTOOL`, `AUTHTOOL`,
`SSHTOOL`):

| Namespace | Tools |
|---|---|
| Secrets | `openbao_logical_read`, `openbao_logical_write`, `openbao_logical_write_bytes`, `openbao_logical_delete`, `openbao_logical_list`, `openbao_logical_unwrap`, `openbao_read_secret`, `openbao_write_secret`, `openbao_delete_secret`, `openbao_list_secrets` |
| Key-value | `openbao_kv2_get`, `openbao_kv2_put`, `openbao_kv2_patch`, `openbao_kv2_delete`, `openbao_kv1_get`, `openbao_kv1_put`, `openbao_kv1_delete` |
| System | `openbao_get_health`, `openbao_get_mounts`, `openbao_enable_mount`, `openbao_sys_init`, `openbao_sys_init_status`, `openbao_sys_seal`, `openbao_sys_unseal`, `openbao_sys_seal_status`, `openbao_sys_health`, `openbao_sys_leader`, `openbao_sys_ha_status`, `openbao_sys_raft_join`, `openbao_sys_raft_autopilot_state` |
| Authentication | `openbao_auth_login`, `openbao_auth_mfa_login`, `openbao_auth_mfa_validate`, `openbao_auth_token_create`, `openbao_auth_token_lookup`, `openbao_auth_token_renew`, `openbao_auth_token_revoke` |
| SSH | `openbao_ssh_credential`, `openbao_ssh_sign_key`, `openbao_ssh_verify` |

Destructive tools take `confirm=true`. Example agent prompts that map onto these tools:

- *"Read the secret at `secret/data/app/config`"* -> `openbao_kv2_get`
- *"Is the OpenBao server healthy and unsealed?"* -> `openbao_get_health`, `openbao_sys_seal_status`
- *"Issue a short-lived SSH credential for role `web`"* -> `openbao_ssh_credential`

## As a Python API

`Api` is a dynamic-facade client that composes the secrets, system, and base
sub-clients. Build one directly or from the environment:

```python
from openbao_mcp.api_client import Api

api = Api(
    base_url="http://127.0.0.1:8200",
    token="bao_root_token",
)

# Reads
health = api.get_health()                     # server health / seal status
mounts = api.get_mounts()                      # mounted secrets engines
secret = api.read_secret("secret", "app/config")
keys = api.list_secrets("secret", "app")
```

Build a client from the configured endpoint and credential references. Custom
trust, private CA, and mTLS policy come from `TLS_PROFILE` or `TLS_PROFILE_REF`
in AgentConfig; certificate verification is mandatory:

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
