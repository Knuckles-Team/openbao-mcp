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
it does **not** assume a credential lives at exactly one OpenBao path. In
this cluster, `GRAPH_SERVICE_AUTH_SECRET` is independently sourced from
**two** paths (`apps/agent-utilities/deployment` used by the engine +
mcp fleet, and `apps/graph-os` used by graph-os/graph-os-host) that happen to
currently hold the same value. Rotating only one desyncs them immediately.
Always check `distinct_source_paths` in the plan output before executing —
if it's more than one, every path must be written in the same operation.

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
