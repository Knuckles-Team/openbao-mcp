#!/usr/bin/env python3
"""Autonomous secret-rotation CLI: discover -> plan -> (confirmed) execute -> verify -> rollback.

Wraps ``rotation_lib.py`` (pure discovery/planning) with the live side effects:
kubectl for cluster discovery + rollout, and OpenBao KV v2 for the read-merge-write.
Talks to OpenBao by shelling into the ``openbao-mcp`` pod, which already carries an
``agent-apps-rw``-policy token as its own env (`OPENBAO_URL`/`OPENBAO_TOKEN`) — this
avoids ever putting a vault token into this script's own environment or command line.

SAFETY CONTRACT (see the skill's references/rotation-operational-facts.md):
  - `plan` NEVER writes anything. It is the default and requires no confirmation.
  - `execute` performs real changes and REQUIRES --confirm.
  - Provider-issued credentials (`rotation_lib.CREDENTIAL_TYPES`) are never invented
    locally. Most still require a human-minted `--new-value-file`; the ones in
    `AUTO_MINTABLE` (currently just `OPENBAO_TOKEN`) are minted in-house through a
    narrowly-scoped OpenBao capability (`mint_provider_value` / `mint_openbao_token`,
    see operational fact 8) instead of refusing.
  - A secret VALUE is never passed as a CLI argument (it would leak into `ps`/shell
    history/kubectl audit logs) and never printed/logged — only lengths, hashes, and
    KV version numbers are.
  - Every OpenBao write is read-full -> merge one key -> ONE write call. Never a
    per-key sequential write (KV v2 replaces the whole version on write).
  - `execute` auto-rolls-back to the prior KV version on a failed verification step.

Usage:
    # Safe default — read-only discovery + plan, no side effects:
    python rotate_secret.py plan --credential-key GRAPH_SERVICE_AUTH_SECRET

    # Offline / testable — same plan step, but from JSON snapshots instead of a live cluster:
    python rotate_secret.py plan --credential-key MATTERMOST_TOKEN \\
        --external-secrets-json es.json --secrets-json secrets.json --workloads-json wl.json

    # Real rotation (human-confirmed, requires kubectl + cluster access):
    python rotate_secret.py execute --credential-key GRAPH_SERVICE_AUTH_SECRET --confirm

    # Standalone rollback to the prior KV version:
    python rotate_secret.py rollback --credential-key GRAPH_SERVICE_AUTH_SECRET --confirm
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rotation_lib as rl  # noqa: E402

DEFAULT_MOUNT = "apps"
OPENBAO_EXEC_POD = (
    "apps",
    "deploy/openbao-mcp",
)  # (namespace, kubectl target) — see AGENTS.md secret layout


# ---------------------------------------------------------------------------
# Live kubectl discovery collection (feeds rotation_lib's pure functions)
# ---------------------------------------------------------------------------


def _kubectl_json(*args: str) -> dict:
    result = subprocess.run(
        ["kubectl", *args, "-o", "json"], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def collect_live_snapshot() -> (
    tuple[list[dict], dict[tuple[str, str], set[str]], list[dict]]
):
    """Fetch ExternalSecrets, Secret KEY NAMES (never values), and workloads cluster-wide.

    Returns the exact three inputs ``rotation_lib.discover_credential`` needs.
    """
    es = _kubectl_json("get", "externalsecrets", "-A")["items"]

    secrets_raw = _kubectl_json("get", "secrets", "-A")["items"]
    secret_key_names: dict[tuple[str, str], set[str]] = {}
    for s in secrets_raw:
        ns = s["metadata"]["namespace"]
        name = s["metadata"]["name"]
        secret_key_names[(ns, name)] = set((s.get("data") or {}).keys())
    del (
        secrets_raw
    )  # never hold decoded/base64 values longer than needed to read key names

    workloads: list[dict] = []
    for kind in ("deployments", "statefulsets", "daemonsets"):
        workloads.extend(_kubectl_json("get", kind, "-A")["items"])

    return es, secret_key_names, workloads


def load_snapshot_files(es_path: str, secrets_path: str, workloads_path: str):
    es = json.loads(Path(es_path).read_text())
    if isinstance(es, dict):
        es = es.get("items", es)
    secrets_raw = json.loads(Path(secrets_path).read_text())
    if isinstance(secrets_raw, dict):
        secrets_raw = secrets_raw.get("items", secrets_raw)
    secret_key_names = {
        (s["metadata"]["namespace"], s["metadata"]["name"]): set(
            (s.get("data") or {}).keys()
        )
        for s in secrets_raw
    }
    workloads = json.loads(Path(workloads_path).read_text())
    if isinstance(workloads, dict):
        workloads = workloads.get("items", workloads)
    return es, secret_key_names, workloads


# ---------------------------------------------------------------------------
# OpenBao KV v2 read-merge-write via the openbao-mcp pod (never our own env)
# ---------------------------------------------------------------------------

_KV_HELPER = r"""
import json, os, sys, urllib.request

def _req(method, path, payload=None):
    url = os.environ["OPENBAO_URL"] + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"X-Vault-Token": os.environ["OPENBAO_TOKEN"],
                                           "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        return json.loads(body) if body else {}

cmd = json.loads(sys.stdin.read())
action = cmd["action"]
mount = cmd.get("mount", "apps")
path = cmd["path"]

if action == "metadata":
    out = _req("GET", f"/v1/{mount}/metadata/{path}")
    meta = out.get("data", {})
    print(json.dumps({"current_version": meta.get("current_version"),
                       "versions": sorted(meta.get("versions", {}).keys(), key=int)}))
elif action == "read_keys":
    out = _req("GET", f"/v1/{mount}/data/{path}")
    data = out.get("data", {}).get("data", {}) or {}
    print(json.dumps({"keys": sorted(data.keys()), "version": out.get("data", {}).get("metadata", {}).get("version")}))
elif action == "merge_write":
    new_key = cmd["new_key"]
    new_value = cmd["new_value"]
    existing = _req("GET", f"/v1/{mount}/data/{path}").get("data", {}).get("data", {}) or {}
    merged = dict(existing)
    merged[new_key] = new_value
    del existing, new_value
    out = _req("POST", f"/v1/{mount}/data/{path}", {"data": merged})
    del merged
    print(json.dumps({"new_version": out.get("data", {}).get("version")}))
elif action == "rollback":
    to_version = cmd["to_version"]
    old = _req("GET", f"/v1/{mount}/data/{path}?version={to_version}").get("data", {}).get("data", {}) or {}
    out = _req("POST", f"/v1/{mount}/data/{path}", {"data": old})
    del old
    print(json.dumps({"restored_version": out.get("data", {}).get("version")}))
else:
    raise SystemExit(f"unknown action {action!r}")
"""


def _kv_call(payload: dict) -> dict:
    ns, target = OPENBAO_EXEC_POD
    result = subprocess.run(
        ["kubectl", "exec", "-i", "-n", ns, target, "--", "python3", "-c", _KV_HELPER],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def kv_metadata(path: str) -> dict:
    return _kv_call({"action": "metadata", "path": path, "mount": DEFAULT_MOUNT})


def kv_read_keys(path: str) -> dict:
    return _kv_call({"action": "read_keys", "path": path, "mount": DEFAULT_MOUNT})


def kv_merge_write(path: str, new_key: str, new_value: str) -> dict:
    return _kv_call(
        {
            "action": "merge_write",
            "path": path,
            "mount": DEFAULT_MOUNT,
            "new_key": new_key,
            "new_value": new_value,
        }
    )


def kv_rollback(path: str, to_version: int) -> dict:
    return _kv_call(
        {
            "action": "rollback",
            "path": path,
            "mount": DEFAULT_MOUNT,
            "to_version": to_version,
        }
    )


# ---------------------------------------------------------------------------
# In-house provider minting: some provider-issued credentials CAN be minted
# by this tool itself rather than requiring a human to paste a value via
# --new-value-file. Currently that is exactly one provider: OpenBao's own
# token API, reachable from the openbao-mcp pod using its OPENBAO_ADMIN_TOKEN
# env var -- a narrowly-scoped token-minter capability (policy
# `agent-apps-token-minter`, restricted via `allowed_parameters` to only ever
# mint tokens carrying the `agent-apps-rw` policy; see
# references/rotation-operational-facts.md). Everything else (Mattermost
# bot tokens, Keycloak client secrets, ...) has NO entry in AUTO_MINTABLE and
# stays a hard refusal -- this tool must never guess how to mint a credential
# it doesn't have a verified, scoped path to mint.
# ---------------------------------------------------------------------------

#: credential_key -> (policy to grant the minted OpenBao token, ttl)
AUTO_MINTABLE: dict[str, tuple[str, str]] = {
    "OPENBAO_TOKEN": ("agent-apps-rw", "768h"),
}

_MINT_HELPER = r"""
import json, os, sys, urllib.request, urllib.error

def _req(method, path, token, payload=None):
    url = os.environ["OPENBAO_URL"] + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"X-Vault-Token": token,
                                           "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        return json.loads(body) if body else {}

cmd = json.loads(sys.stdin.read())
admin_token = os.environ.get("OPENBAO_ADMIN_TOKEN")
if not admin_token:
    print(json.dumps({"error": "OPENBAO_ADMIN_TOKEN not set on this pod -- "
                                "see TASK 3 wiring in references/rotation-operational-facts.md"}))
    sys.exit(1)

try:
    # NOTE: "policies" MUST be a plain string here, not a JSON list. OpenBao's
    # ACL "allowed_parameters" match for this list-typed field only matches a
    # comma-string request value against the policy's allowed-values list --
    # a JSON array value (`["agent-apps-rw"]`) is denied ("permission denied")
    # even though the calling token's policy legitimately permits it. Verified
    # live: identical request/token, only this field's JSON type changed
    # (array -> string) flips 403 -> 200. See D-OBP-1 / D-OBP-2.
    resp = _req("POST", "/v1/auth/token/create", admin_token, {
        "policies": cmd["policy"],
        "ttl": cmd["ttl"],
        "display_name": cmd.get("display_name", "rotate_secret-minted"),
    })
except urllib.error.HTTPError as e:
    print(json.dumps({"error": f"token/create failed: {e.code} {e.reason}"}))
    sys.exit(1)

auth = resp.get("auth") or {}
token = auth.get("client_token")
if not token:
    print(json.dumps({"error": "mint returned no client_token"}))
    sys.exit(1)
# Emitted ONCE on stdout for the calling process to hold in memory and feed
# straight into kv_merge_write -- callers must never print()/log() this.
print(json.dumps({"client_token": token, "accessor": auth.get("accessor")}))
"""


def mint_openbao_token(policy: str, ttl: str) -> tuple[str, str]:
    """Mint a new OpenBao token carrying ``policy`` via the openbao-mcp pod's
    own ``OPENBAO_ADMIN_TOKEN`` (never this script's own environment).

    Returns ``(client_token, accessor)``. Raises ``RuntimeError`` on failure.
    The token value must be treated exactly like any other secret value by
    the caller: fed directly into ``kv_merge_write``, never printed/logged.
    """
    ns, target = OPENBAO_EXEC_POD
    result = subprocess.run(
        [
            "kubectl",
            "exec",
            "-i",
            "-n",
            ns,
            target,
            "--",
            "python3",
            "-c",
            _MINT_HELPER,
        ],
        input=json.dumps({"policy": policy, "ttl": ttl}),
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout.strip().splitlines()[-1])
    if "error" in out:
        raise RuntimeError(f"OpenBao token mint failed: {out['error']}")
    return out["client_token"], out["accessor"]


def mint_provider_value(credential_key: str) -> tuple[str, str] | None:
    """Return ``(new_value, safe_description)`` if ``credential_key`` can be
    auto-minted in-house, else ``None`` -- meaning the caller must fall back
    to refusing (the credential has no verified in-house minting path and
    needs a human to run the provider's own mint flow + ``--new-value-file``).

    ``safe_description`` never contains the minted value -- only policy/ttl/
    accessor, which are safe to print.
    """
    if credential_key not in AUTO_MINTABLE:
        return None
    policy, ttl = AUTO_MINTABLE[credential_key]
    token, accessor = mint_openbao_token(policy, ttl)
    return (
        token,
        f"minted via OpenBao POST /v1/auth/token/create (policy={policy}, "
        f"ttl={ttl}, accessor={accessor})",
    )


# ---------------------------------------------------------------------------
# kubectl side effects: force-sync + restart + verify
# ---------------------------------------------------------------------------


def force_sync_external_secret(namespace: str, name: str) -> None:
    subprocess.run(
        [
            "kubectl",
            "annotate",
            "externalsecret",
            "-n",
            namespace,
            name,
            f"force-sync={_now()}",
            "--overwrite",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _now() -> str:
    import time

    return str(int(time.time()))


def restart_consumer(consumer: rl.Consumer, timeout: str = "120s") -> None:
    kind = consumer.kind.lower()
    subprocess.run(
        [
            "kubectl",
            "rollout",
            "restart",
            f"{kind}/{consumer.name}",
            "-n",
            consumer.namespace,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "kubectl",
            "rollout",
            "status",
            f"{kind}/{consumer.name}",
            "-n",
            consumer.namespace,
            f"--timeout={timeout}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _discovery_from_args(args) -> rl.DiscoveryResult:
    if args.external_secrets_json:
        es, keys, workloads = load_snapshot_files(
            args.external_secrets_json, args.secrets_json, args.workloads_json
        )
    else:
        es, keys, workloads = collect_live_snapshot()
    return rl.discover_credential(args.credential_key, es, keys, workloads)


def cmd_plan(args) -> int:
    discovery = _discovery_from_args(args)
    credential_type = rl.classify_credential(args.credential_key)
    plan = rl.build_plan(discovery, credential_type)
    print(plan.render())
    return 0 if discovery.found() else 1


def cmd_execute(args) -> int:
    if not args.confirm:
        print(
            "Refusing to execute without --confirm. Run `plan` first, review the blast "
            "radius, then re-run with --confirm.",
            file=sys.stderr,
        )
        return 2

    discovery = _discovery_from_args(args)
    credential_type = rl.classify_credential(args.credential_key)
    plan = rl.build_plan(discovery, credential_type)
    print(plan.render())
    print()

    if not discovery.found():
        print("Nothing to execute — no discovered path/consumers.", file=sys.stderr)
        return 1

    if args.new_value_file:
        new_value = Path(args.new_value_file).read_text().strip()
    elif credential_type.kind == "provider-issued":
        minted = mint_provider_value(args.credential_key)
        if minted is None:
            print(
                f"'{args.credential_key}' is provider-issued ({credential_type.description}). "
                "This tool has no verified in-house minting path for it (see AUTO_MINTABLE "
                "in rotate_secret.py). Mint it via the provider first, save the result to a "
                "file, and pass --new-value-file <path>. Refusing to invent a value.",
                file=sys.stderr,
            )
            return 3
        new_value, mint_desc = minted
        print(f"[mint] Auto-minted new value in-house: {mint_desc}")
    else:
        new_value = credential_type.generator()

    prior_versions: dict[str, int] = {}
    print("[1/5] Reading current KV version at each source path (for rollback)...")
    for path in discovery.distinct_source_paths:
        meta = kv_metadata(path)
        prior_versions[path] = meta["current_version"]
        print(f"  apps/{path}: current_version={meta['current_version']}")

    print("[2/5] Read-merge-ONE-write: writing the new value into every source path...")
    for path in discovery.distinct_source_paths:
        result = kv_merge_write(path, args.credential_key, new_value)
        print(f"  apps/{path}: wrote new_version={result['new_version']}")
    del new_value

    print("[3/5] Force-syncing every ExternalSecret channel...")
    seen: set[tuple[str, str]] = set()
    for ch in discovery.channels:
        key = (ch.namespace, ch.external_secret)
        if key in seen:
            continue
        seen.add(key)
        force_sync_external_secret(ch.namespace, ch.external_secret)
        print(f"  {ch.namespace}/{ch.external_secret} force-synced")

    print("[4/5] Restarting consumer workloads...")
    failed_consumers = []
    for con in discovery.all_consumers:
        try:
            restart_consumer(con)
            print(f"  {con.id()} rolled out OK")
        except subprocess.CalledProcessError as exc:
            failed_consumers.append(con)
            print(
                f"  {con.id()} FAILED to roll out: {exc.stderr[:200]}", file=sys.stderr
            )

    print("[5/5] Verification...")
    verification_ok = not failed_consumers
    if not verification_ok:
        print(
            "  Verification FAILED — one or more consumers did not roll out cleanly.",
            file=sys.stderr,
        )
    else:
        print(
            f"  All {len(discovery.all_consumers)} consumer(s) report Ready "
            f"(verify strategy: {credential_type.verify}). Deeper functional verification "
            "(e.g. an authenticated request through the new credential) should be run "
            "before declaring success in a real environment."
        )

    if not verification_ok:
        print(
            "\n[ROLLBACK] Restoring prior KV version(s) and re-syncing/restarting...",
            file=sys.stderr,
        )
        for path, version in prior_versions.items():
            kv_rollback(path, version)
            print(f"  apps/{path} restored to version {version}", file=sys.stderr)
        for ns, name in seen:
            force_sync_external_secret(ns, name)
        for con in discovery.all_consumers:
            try:
                restart_consumer(con)
            except subprocess.CalledProcessError:
                pass
        print(
            "Rollback complete. Rotation FAILED — original credential is back in place.",
            file=sys.stderr,
        )
        return 1

    if credential_type.kind == "provider-issued":
        print(
            "\nNOTE: revoke the OLD credential at its provider now that the new one "
            f"verified — {credential_type.mint_procedure}"
        )
    print("\nRotation complete.")
    return 0


def cmd_rollback(args) -> int:
    if not args.confirm:
        print("Refusing to roll back without --confirm.", file=sys.stderr)
        return 2
    discovery = _discovery_from_args(args)
    if not discovery.found():
        print("Nothing found for this credential — cannot roll back.", file=sys.stderr)
        return 1
    for path in discovery.distinct_source_paths:
        meta = kv_metadata(path)
        versions = [int(v) for v in meta["versions"]]
        versions.sort()
        if len(versions) < 2:
            print(
                f"apps/{path}: only {len(versions)} version(s) recorded — nothing to roll back to.",
                file=sys.stderr,
            )
            continue
        target_version = args.to_version or versions[-2]
        result = kv_rollback(path, target_version)
        print(
            f"apps/{path}: restored to version {target_version} (new_version={result['restored_version']})"
        )
    seen: set[tuple[str, str]] = set()
    for ch in discovery.channels:
        key = (ch.namespace, ch.external_secret)
        if key in seen:
            continue
        seen.add(key)
        force_sync_external_secret(ch.namespace, ch.external_secret)
    for con in discovery.all_consumers:
        restart_consumer(con)
    print("Rollback complete.")
    return 0


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--credential-key",
        required=True,
        help="Env-var / KV field name, e.g. GRAPH_SERVICE_AUTH_SECRET",
    )
    p.add_argument(
        "--external-secrets-json",
        help="Offline snapshot instead of live kubectl (testing/dry-run)",
    )
    p.add_argument("--secrets-json", help="Paired with --external-secrets-json")
    p.add_argument("--workloads-json", help="Paired with --external-secrets-json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser(
        "plan", help="Read-only discovery + blast-radius plan. Default and safe."
    )
    _add_common_args(p_plan)
    p_plan.set_defaults(func=cmd_plan)

    p_exec = sub.add_parser("execute", help="Perform the rotation. Requires --confirm.")
    _add_common_args(p_exec)
    p_exec.add_argument("--confirm", action="store_true")
    p_exec.add_argument(
        "--new-value-file", help="Path to a file containing a provider-minted value"
    )
    p_exec.set_defaults(func=cmd_execute)

    p_roll = sub.add_parser(
        "rollback", help="Roll back to a prior KV version. Requires --confirm."
    )
    _add_common_args(p_roll)
    p_roll.add_argument("--confirm", action="store_true")
    p_roll.add_argument(
        "--to-version",
        type=int,
        default=None,
        help="Defaults to the second-to-last version",
    )
    p_roll.set_defaults(func=cmd_rollback)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
