# Rotation operational facts (learned the hard way — read before executing)

These are hard-won, cluster-verified facts. Every one of them is encoded into
`scripts/rotate_secret.py` / `rotation_lib.py`, but restated here so a human
(or an agent working from first principles) doesn't relearn them by breaking
something.

## 1. KV v2 REPLACES THE ENTIRE VERSION ON WRITE

`POST apps/data/<path>` overwrites every key at that path with exactly the
`data` object you send. A per-key sequential write (`{"GRAPH_SERVICE_AUTH_SECRET": "..."}`
alone) **deletes every other key** that was at that path — this happened live
and clobbered a real secret. Always **read the full existing object, merge in
the one changed key, and write the full merged object back in ONE call**
(`kv_merge_write` in `rotate_secret.py`). The alternative — an HTTP `PATCH`
(RFC 7396 merge-patch, exposed as `kv2_patch` / `KVv2.Patch` in this repo's
API client) — also avoids the clobber and is a valid alternative if your
OpenBao build supports it, but the explicit read-merge-write is what this
skill standardizes on because it works everywhere and is trivial to reason
about.

## 2. `kubectl patch` on a `*-secrets` Secret SILENTLY REVERTS

Every `apps/*-secrets` Secret in this cluster is **ExternalSecret-managed**
with a 1-hour `refreshInterval`. Patching the k8s Secret directly "works" for
up to an hour, then the controller overwrites your patch back to whatever
OpenBao holds — with no error, no event that's obvious to a casual `kubectl
get events`. **Always write to OpenBao, then force the sync immediately**:

```bash
kubectl annotate externalsecret -n <ns> <name> force-sync="$(date +%s)" --overwrite
```

## 3. Two tokens, two purposes — don't confuse them

- The `ClusterSecretStore/openbao`'s own auth to OpenBao uses
  `external-secrets/openbao-token` — this is **read-only** (`eso-read`
  policy). It can sync secrets down into the cluster but cannot write.
- The **writable** token used by this skill (and by `openbao-mcp` itself) is
  scoped `agent-apps-rw` (create/read/update/delete on `apps/data/*`). It
  lives at OpenBao `apps/_meta-agent-apps-rw`, and the deployed `openbao-mcp`
  pod already carries a copy of it as its own `OPENBAO_TOKEN` env var — which
  is why `rotate_secret.py` shells KV operations through that pod
  (`kubectl exec -n apps deploy/openbao-mcp -- python3 ...`) rather than
  requiring a fresh token in the calling environment.

## 4. KV v2 keeps versions — rollback is the fast undo path

Every write to a KV v2 path creates a new version; old versions stay
retrievable until explicitly deleted/destroyed. `rotate_secret.py execute`
records the `current_version` at every affected path **before** writing, and
if verification fails after the restart, automatically re-writes the prior
version's full data, re-forces the ExternalSecret sync, and restarts the same
consumers again. This is the fast, tested undo — it worked live during the
incident that motivated this skill. `rotate_secret.py rollback` exposes the
same mechanism standalone for a manual undo.

## 5. NEVER echo a secret VALUE — test presence/length only

`${VAR:-somefallback}` in a shell **prints the fallback if unset, but prints
the real value if set** — that's how a secret gets printed by mistake. Use
`${VAR:+SET}` (prints literally `SET` if the var has any value, nothing
otherwise) to check presence without risk. To check length safely:
`echo ${#VAR}`. Every tool in this skill follows the same rule in Python:
read a value, act on it, never `print()`/`log()` it — only lengths, SHA-256
prefixes (for equality checks across duplicated paths), and KV version
numbers are safe to surface.

## 6. A shared secret can have MORE THAN ONE source-of-truth path

Discovery in this skill is fully derived from live ExternalSecret specs —
it does **not** assume a credential lives at exactly one OpenBao path.
`GRAPH_SERVICE_AUTH_SECRET` used to be independently sourced from **two**
paths (`apps/agent-utilities/deployment` used by the engine + mcp fleet, and
`apps/graph-os` used by graph-os/graph-os-host/alert-bridge) that happened to
hold the same value. **Reconciled 2026-07-23**: `apps/agent-utilities/deployment`
is now the sole canonical path (deployment-identity home; already read by
the engine and 65/69 fleet consumers before reconciliation). The two
ExternalSecrets that used to pull the whole `apps/graph-os` path for this key
(`platform/graph-os-secrets`, `apps/alert-bridge-oidc`) now carry an
**explicit** `spec.data[]` entry for just `GRAPH_SERVICE_AUTH_SECRET` pointing
at the canonical path, alongside their existing `dataFrom.extract` of
`graph-os` for their other (graph-os-specific) keys; the key itself was then
deleted from `apps/graph-os` (read-merge-write, dropping only that one key —
every other key at that path was left untouched). The VALUE was never
rotated in this reconciliation — verified byte-identical (SHA-256) before
and after.

**Known discovery-tool caveat surfaced by this**: `discover_credential`'s
`dataFrom.extract` matching only checks whether the credential key is
present in the *target Secret's* actual key set — it cannot tell whether
that key came from the `data[]` entry or the `dataFrom.extract`. So for an
ExternalSecret with both (like `graph-os-secrets` now), `plan` still lists
`apps/graph-os` as a nominal "source path" even though the real OpenBao data
there no longer has the key. Ground truth is always the direct KV read
(`kv2_get`/`read_keys`), not the plan's `distinct_source_paths` alone, when
an ExternalSecret mixes `data[]` and `dataFrom` for overlapping keys.

Always check `distinct_source_paths` in the plan output before executing —
if it's more than one, every path that *actually* holds the key must be
written in the same operation (verify with a direct KV read, per the caveat
above, rather than trusting the ExternalSecret spec shape alone).

## 7. Provider-issued credentials must be minted BY the provider

Some credentials are not "any random string" — they are tokens/secrets the
owning system tracks by identity and can revoke. Inventing a value locally
produces something that looks like a secret but authenticates nowhere:

- **OpenBao tokens** (e.g. `OPENBAO_TOKEN`) — mint via
  `bao token create -policy=<policy> -ttl=<ttl>` or
  `POST /v1/auth/token/create`. Revoke the OLD token's accessor only after
  the new one verifies.
- **Mattermost bot/personal-access tokens** (e.g. `MATTERMOST_TOKEN`) — mint
  via `POST /api/v4/users/{user_id}/tokens` or the System Console. Revoke via
  `DELETE /api/v4/users/{user_id}/tokens/{token_id}`.
- **Keycloak client secrets** — regenerate via
  `kcadm.sh create clients/<client-uuid>/client-secret` against the admin
  REST API. The Keycloak pod ships **no `tar`**, so `kubectl cp` silently
  fails when moving files in/out — pipe base64 through `kubectl exec` instead
  (`kubectl exec ... -- base64 /path | base64 -d > local-file`, and the
  reverse for pushing a file in).

`rotate_secret.py`'s `CREDENTIAL_TYPES` registry (`rotation_lib.py`)
classifies a credential by name and refuses to auto-generate a value for
anything provider-issued — it requires `--new-value-file` pointing at a
value already minted through the provider's own flow.

## 8. openbao-mcp's admin capability — how it mints its own OpenBao tokens

`OPENBAO_TOKEN` is provider-issued (fact 7), but for exactly one provider —
OpenBao itself — this tool CAN mint the new value in-house, because
`openbao-mcp` was given a narrowly-scoped minting capability rather than a
blanket admin/root token:

- A dedicated ACL policy, `agent-apps-token-minter`, grants `create`/`update`
  on `auth/token/create` **only**, with `allowed_parameters.policies`
  restricted to `["agent-apps-rw"]` and `denied_parameters` blocking `id` /
  `no_parent` / `no_default_policy`. It cannot mint a token with any other
  policy (never `root`), cannot mint an orphan token, and cannot do anything
  outside token creation — it is not a copy of the OpenBao root token.
- A token carrying that policy (period `720h`, renewable) lives at OpenBao
  `apps/openbao-mcp` as the `OPENBAO_ADMIN_TOKEN` key, alongside the existing
  `OPENBAO_TOKEN` (agent-apps-rw, used for ordinary KV reads/writes) and
  `OPENBAO_URL`. It reaches the pod the same way every other credential in
  this cluster does: the whole-path `openbao-mcp-secrets` ExternalSecret
  already `dataFrom.extract`s this path, so adding the key to OpenBao and
  force-syncing was enough — no ExternalSecret spec change was needed. The
  pod picks it up as an env var on its next restart (envFrom is read at
  container start, not live-reloaded).
- The **root** token that bootstrapped `agent-apps-token-minter` (from
  `services/openbao/.env`, `BAO_ROOT_TOKEN`) is used exactly once, in-memory,
  piped via stdin into an ephemeral `kubectl exec` — never written to disk,
  never stored in any pod's env, never printed. It has no ongoing role.
- `rotate_secret.py`'s `AUTO_MINTABLE` registry maps `OPENBAO_TOKEN ->
  ("agent-apps-rw", "768h")`. `mint_provider_value()` consults it first;
  anything NOT listed there (Mattermost tokens, Keycloak client secrets, …)
  still falls through to the original hard refusal — auto-minting is opt-in
  per credential type, never a blanket bypass of the provider-issued check.
- The mint call itself (`mint_openbao_token`) execs into
  `deploy/openbao-mcp` and POSTs `/v1/auth/token/create` using the pod's own
  `OPENBAO_ADMIN_TOKEN` — never this script's local environment — mirroring
  exactly how `_kv_call` already talks to OpenBao through that pod's
  `OPENBAO_TOKEN`. The minted value is returned to the caller for immediate
  use in `kv_merge_write` and is never `print()`'d/logged by this tool; only
  its accessor (safe — cannot authenticate anything) appears in output.

### 8a. Two compounding gaps that made this 403 in practice until 2026-07-31 (D-OBP-1/2)

Both are fixed now (policy in `services/openbao/k8s/bootstrap-policies.sh`; code in
this file's `_MINT_HELPER`), but restated here because either one alone still looks
like "the documented payload, still 403" if it regresses:

1. **`sudo` was missing from the policy.** OpenBao requires the calling token to
   have `sudo` on `auth/token/create` to mint a token whose `policies` are NOT a
   subset of the calling token's own policies. `agent-apps-token-minter`'s own
   policies are `[agent-apps-token-minter, default]` — asking for `agent-apps-rw`
   is not a subset, so without `sudo` this is a 403 regardless of
   `allowed_parameters` being satisfied. Verified live with a fresh token minted
   from the corrected policy.
2. **`"policies"` must be sent as a plain string, not a JSON list.** OpenBao's ACL
   `allowed_parameters` match for this field only matches a comma-string request
   value against the policy's allowed-value list; a JSON array value
   (`{"policies": ["agent-apps-rw"]}`) is denied even with `sudo` present and even
   from a token whose only relevant policy is `agent-apps-token-minter` — flip the
   *identical* request to `{"policies": "agent-apps-rw"}` and it succeeds. Verified
   live, same token, same TTL/display_name, only this one field's JSON type
   changed. `_MINT_HELPER` sends the string form for exactly this reason — do not
   "simplify" it back to a list.
