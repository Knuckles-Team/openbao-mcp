---
name: openbao-mcp-operations
skill_type: skill
description: >-
  Operate an OpenBao server through the openbao-mcp tools: health, initialization, seal, raft, mounts, login and SSH access. Use for platform operation and access issuance. For reading and writing secrets use secret-vault-manager.
license: MIT
tags: [openbao, vault, operations]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# OpenBao server operations

Server operations act on the OpenBao API at BAO_ADDR. Check status first: most failures are a sealed or uninitialized server.

## Rules

- Read seal and init status before any change.
- Seal and token revocation are destructive; ask first.
- Never print tokens, unseal shards or secret values.

## Steps

1. Read the server state with `openbao_sys_seal_status`() and `openbao_sys_init_status`(). Verify the response shows whether the server is initialized and sealed before any change.
2. For a new server, run `openbao_sys_init`(opts) once. Verify the response returns the unseal shards, and keep them out of logs and output.
3. Unseal with `openbao_sys_unseal`(shard) once per shard. Verify `openbao_sys_seal_status`() reports `sealed: false`.
4. Confirm cluster health with `openbao_sys_health`() and `openbao_sys_raft_autopilot_state`(). Verify a leader is reported and every raft server is healthy.
5. For an emergency seal, ask the person first and call `openbao_sys_seal`(confirm=true). Verify `openbao_sys_seal_status`() reports `sealed: true`.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| Calls fail with a connection error | `BAO_ADDR` is wrong or the server is down | Set `BAO_ADDR` to the server address and confirm with `openbao_get_health`() |
| `openbao_sys_unseal` keeps reporting sealed | Fewer shards supplied than the threshold | Call `openbao_sys_unseal`(shard) with the remaining shards until `openbao_sys_seal_status`() shows `sealed: false` |
| `openbao_sys_seal` refuses | `confirm=true` was not passed | Get the person's agreement, then call `openbao_sys_seal`(confirm=true) |

## Task workflows

### check-server-health

Read health, initialization, seal, leader, HA and raft state. Contract steps, in order:

1. `openbao_get_health`(no arguments)
2. `openbao_sys_health`(no arguments)
3. `openbao_sys_init_status`(no arguments)
4. `openbao_sys_seal_status`(no arguments)
5. `openbao_sys_leader`(no arguments)
6. `openbao_sys_ha_status`(no arguments)
7. `openbao_sys_raft_autopilot_state`(no arguments)

### initialize-and-unseal-server

Initialize a new server and unseal it shard by shard. Contract steps, in order:

1. `openbao_sys_init_status`(no arguments)
2. `openbao_sys_init`(opts)
3. `openbao_sys_seal_status`(no arguments)
4. `openbao_sys_unseal`(shard)

### seal-server

Seal the server in an emergency. Contract steps, in order:

1. `openbao_sys_seal_status`(no arguments)
2. `openbao_sys_seal`(; optional confirm) (destructive: pass confirm=true only after the person agrees)

### join-raft-cluster

Add a node to the raft cluster and watch autopilot. Contract steps, in order:

1. `openbao_sys_raft_join`(opts)
2. `openbao_sys_raft_autopilot_state`(no arguments)
3. `openbao_sys_ha_status`(no arguments)

### ingest-mount-metadata

Mirror mount and server metadata into the knowledge graph (never secret values). Contract steps, in order:

1. `openbao_get_mounts`(no arguments)
2. `openbao_get_health`(no arguments)
3. `openbao_ingest_mounts`(no arguments)

### log-in-and-validate-mfa

Log in to an auth method, including MFA. Contract steps, in order:

1. `openbao_auth_login`(data; optional mount)
2. `openbao_auth_mfa_login`(data; optional creds, mount)
3. `openbao_auth_mfa_validate`(mfa_secret, payload)

### issue-ssh-access

Issue an SSH credential, sign a key, or verify a one-time password. Contract steps, in order:

1. `openbao_ssh_credential`(role; optional data, mount_point)
2. `openbao_ssh_sign_key`(role, data; optional mount_point)
3. `openbao_ssh_verify`(otp; optional mount_point)

### mount-a-secrets-engine

Enable a secrets engine and read the API schema of the server. Contract steps, in order:

1. `openbao_get_mounts`(no arguments)
2. `openbao_enable_mount`(mount, mount_type)
3. `openbao_get_internal_openapi_spec`(no arguments)
