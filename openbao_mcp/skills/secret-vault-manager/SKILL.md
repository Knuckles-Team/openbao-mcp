---
name: secret-vault-manager
skill_type: skill
description: >-
  Initialize, unseal, mount and read or write KV secrets on OpenBao through openbao-mcp, and rotate a compromised credential end to end with a dry-run plan by default and automatic rollback. Use when a credential is exposed and needs rotating, or when a vault must be set up.
domain: infrastructure
tags:
  - vault
  - openbao
  - secrets
  - security
  - rotation
requires:
  - openbao-mcp
metadata:
  author: Knuckles-Team
  version: '0.2.0'
---

# Secret Vault Manager Skill

Scope: Secret Vault Manager atomic skill. Performs unsealing, initialization, secrets engine mounting, and KV secrets write/read operations on OpenBao (Vault) using openbao-mcp — including autonomous, blast-radius-aware CREDENTIAL ROTATION with a safe dry-run plan by default, coordinated multi-consumer cutover for a secret shared across services (e.g. an HMAC secret consumed by an engine + a whole MCP fleet), and automatic rollback to the prior KV version on a failed verification. Use when a credential is exposed/compromised and needs rotating, not just when reading/writing a known secret.

Stateless atomic operation to configure root credentials, manage initialization phases, access path-level secrets, and **rotate a compromised credential end-to-end** in OpenBao/Vault engines.

## Prerequisites

- `openbao-mcp` — for executing OpenBao initialization, unsealing, sys engine, and KV logical operations.
- `kubectl` cluster access — for rotation's live discovery (ExternalSecrets, Secret key
  names, consumer Deployments/StatefulSets/DaemonSets) and for restarting consumers.

## Bundled resources

- `scripts/rotation_lib.py` — pure, stdlib-only discovery + planning logic (no side
  effects; unit-tested). Given ExternalSecret specs, k8s Secret **key names** (never
  values), and workload specs, it derives which OpenBao path(s) hold a credential, every
  ExternalSecret that projects it, and every consumer that mounts it — dynamically, so it
  never rots as the fleet grows.
- `scripts/rotate_secret.py` — the CLI: `plan` (read-only, default, safe), `execute`
  (real rotation, requires `--confirm`), `rollback` (manual undo, requires `--confirm`).
- `references/rotation-operational-facts.md` — the hard-won operational rules (KV v2
  replace-on-write, `kubectl patch` silently reverting, the two-tokens distinction,
  version-based rollback, never echoing a secret value, multi-path shared secrets,
  provider-issued credentials). **Read this before executing a rotation.**

## Steps

1. Check the server with `openbao_sys_seal_status`() and `openbao_sys_init_status`(). Verify the response shows `initialized: true` and `sealed: false`, otherwise initialize or unseal first.
2. Read the current secret object with `openbao_read_secret`(mount, path) before any write. Verify the response lists every existing key so the write can merge instead of replace.
3. Write the merged object back in one call with `openbao_write_secret`(mount, path, secret_data). Verify a second `openbao_read_secret`(mount, path) shows the new version with all prior keys intact.
4. To rotate a credential, run `python scripts/rotate_secret.py plan --credential-key <KEY>`. Verify the output lists every source path, ExternalSecret and consumer, and whether `is_shared` is set.
5. After explicit human approval of the blast radius, run `python scripts/rotate_secret.py execute --credential-key <KEY> --confirm`. Verify every consumer reports ready and the output shows no rollback.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| Write returns permission denied | Token lacks the path policy or the server is sealed | Check `openbao_sys_seal_status`(), unseal if needed, and log in with a token whose policy covers the path |
| Keys vanished after a write | KV v2 replaced the version with a partial object | Run `python scripts/rotate_secret.py rollback --credential-key <KEY> --confirm`, or read the prior version with `openbao_read_secret`(mount, path) and write it back whole |
| `execute` refuses to run | Missing `--confirm`, or a provider-issued credential without `--new-value-file` | Add `--confirm`, and for provider-issued values mint the credential first and pass `--new-value-file <path>` |

## Procedure detail

### Step 1: Health & Seal Check
Check seal status and initialization state on the vault server endpoints.

### Step 2: Initialize & Unseal Vault (Boot Phase)
If OpenBao/Vault is raw and uninitialized:
- Run initialization, capturing master shares and root token.
- Securely print master shares (or export securely) and store root token.
- Perform unseal steps by supplying necessary key shares.

### Step 3: Mount KV2 Secrets Engine
Configure dynamic secret engines:
- Enable the key-value version 2 (KV2) storage backend at target path (e.g. `/secret`).
- Setup custom path policies and access groups.

### Step 4: KV Secret Operations (CRUD)
Manage application credentials and settings:
- Write secrets containing dynamic database passwords, API tokens (e.g. GitLab PATs), or SSH parameters.
- Verify read permissions on registered paths.
- **Read-merge-ONE-write, always.** KV v2 replaces the entire version on write; a
  per-key sequential write deletes every key it doesn't mention. Read the full existing
  object, merge in the one changed key, write the merged object back in a single call.

### Step 5: Autonomous Credential Rotation

Turn "rotate `<credential>`" into one operation instead of a manual multi-system chore —
safe by default, explicit and confirmed before anything changes.

1. **Resolve** — `python scripts/rotate_secret.py plan --credential-key <KEY>` discovers,
   from the LIVE cluster + OpenBao (never a hardcoded list): every OpenBao KV path
   holding `<KEY>`, every ExternalSecret projecting it into a k8s Secret, and every
   Deployment/StatefulSet/DaemonSet that mounts that Secret (via `envFrom` or an
   explicit `secretKeyRef`). It also classifies the credential's **type** — a
   locally-`generated` random value (e.g. an HMAC secret) vs. a `provider-issued` one
   that must be minted by its owning system (a Keycloak client secret, an OpenBao
   token, a Mattermost bot token) — via a small, explicit, extensible registry in
   `rotation_lib.CREDENTIAL_TYPES` (the blast-radius discovery above is dynamic; only
   "how do I mint a NEW value for this specific provider" is inherently
   credential-specific and lives in that registry).
2. **Plan / show blast radius BEFORE acting** — `plan` is read-only and is the default:
   it prints every consumer that will need a restart, whether the credential is
   **shared** (multiple consumers and/or more than one OpenBao source path — the case
   that needs a coordinated cutover, not a sequential one), and the exact ordering
   constraints for a shared secret (all source paths written together, all
   ExternalSecrets force-synced together, all consumers restarted in the same batch —
   never one at a time, or the holder and a consumer briefly disagree on the secret and
   auth fails between them).
3. **Generate** the new value per the classified type — a random value locally for
   `generated` credentials, or a REQUIRED `--new-value-file` (a value already minted via
   the provider's own admin API/console) for `provider-issued` ones. `execute` refuses
   to invent a provider-issued value.
4. **Write it back** read-merge-ONE-write at every discovered source path, force-sync
   every discovered ExternalSecret, and roll every discovered consumer.
5. **Verify** — post-rollout readiness for every consumer (a CrashLoop/failing
   readiness probe means the new secret was rejected), plus a credential-type-specific
   check where the registry defines one (OpenBao self-lookup, an authenticated HTTP
   call). **On failure, `execute` automatically rolls back** every affected KV path to
   the version recorded before the write, re-syncs, and restarts the same consumers
   again.
6. **Idempotent & logged** — every step is safe to re-run (writes are keyed by the
   credential's current state, restarts are `kubectl rollout restart`, sync is
   idempotent annotation). Every log line reports lengths/versions/hashes, never a
   secret value.

**Safety default: `plan`, never `execute`, unless a human explicitly asks to rotate.**
`execute` requires `--confirm`; there is no environment variable or config flag that
bypasses it. Treat a `plan` output showing `is_shared` (multiple consumers or more than
one source path) as requiring explicit human sign-off on the blast radius before ever
passing `--confirm` — a shared secret rotation can take down the whole dependent fleet if
mishandled, and the tested rollback exists precisely so a mistake is quick to undo, not
so mistakes are cheap to make.

```bash
# 1. Always plan first (no side effects):
python scripts/rotate_secret.py plan --credential-key GRAPH_SERVICE_AUTH_SECRET

# 2. Only after reviewing the blast radius and getting explicit go-ahead:
python scripts/rotate_secret.py execute --credential-key GRAPH_SERVICE_AUTH_SECRET --confirm

# Provider-issued credential — mint first, then point execute at the result:
python scripts/rotate_secret.py execute --credential-key MATTERMOST_TOKEN \
    --confirm --new-value-file /path/to/freshly-minted-token

# Manual undo at any time:
python scripts/rotate_secret.py rollback --credential-key GRAPH_SERVICE_AUTH_SECRET --confirm
```
