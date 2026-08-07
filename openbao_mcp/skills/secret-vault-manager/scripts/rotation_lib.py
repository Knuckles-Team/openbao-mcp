#!/usr/bin/env python3
"""Pure discovery/planning logic for autonomous secret rotation.

Stdlib-only, no live cluster/vault access — everything here takes
already-fetched JSON (ExternalSecrets, k8s Secret **key names** [never
values], and workload specs) and returns a deterministic blast-radius +
rotation plan. This is what ``rotate_secret.py`` calls; kept separate so it
is trivially unit-testable (mirrors the `analyze_health.py` / `rank_items.py`
pattern used by other skills in this fleet: collect JSON live, analyze pure).

CRITICAL SAFETY RULE encoded throughout: nothing in this module ever reads,
stores, logs, or returns a secret *value*. K8s ``Secret.data`` is consumed
only for its **key names** (``dict.keys()``); OpenBao KV responses are
consumed only for metadata/version/key-name fields. Callers that fetch live
data (``rotate_secret.py``) must uphold the same contract when talking to
kubectl/OpenBao.

Discovery (which OpenBao path(s) hold a credential, which ExternalSecrets
project it, which Deployments/StatefulSets/DaemonSets consume it) is fully
DERIVED from the live ExternalSecret specs + Secret key-name lists + workload
env/envFrom — never a hardcoded per-credential map, so it cannot rot as the
fleet grows. Only the *generation strategy* (how to mint a new value for a
given credential) is inherently provider-specific and lives in a small,
explicit, extensible registry (``CREDENTIAL_TYPES``) — the same way the task
that motivated this tool distinguishes a random HMAC secret from a
Keycloak-issued client secret.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@dataclass
class Consumer:
    """One workload (Deployment/StatefulSet/DaemonSet) that mounts a Secret."""

    kind: str
    namespace: str
    name: str
    container: str
    mount: str  # "envFrom" or f"env:{var_name}"

    def id(self) -> str:
        return f"{self.kind}/{self.namespace}/{self.name}"


@dataclass
class Channel:
    """One ExternalSecret path that projects the credential into a k8s Secret."""

    external_secret: str
    namespace: str
    target_secret: str
    source_path: str
    source_property: str
    consumers: list[Consumer] = field(default_factory=list)


@dataclass
class DiscoveryResult:
    credential_key: str
    channels: list[Channel]

    @property
    def distinct_source_paths(self) -> list[str]:
        return sorted({c.source_path for c in self.channels})

    @property
    def all_consumers(self) -> list[Consumer]:
        seen: dict[str, Consumer] = {}
        for ch in self.channels:
            for con in ch.consumers:
                seen[con.id()] = con
        return sorted(seen.values(), key=lambda c: c.id())

    @property
    def is_shared(self) -> bool:
        """True when rotating this credential requires a coordinated, multi-consumer cutover."""
        return len(self.all_consumers) > 1 or len(self.distinct_source_paths) > 1

    def found(self) -> bool:
        return bool(self.channels)


def _target_secret_name(external_secret: dict) -> str:
    spec = external_secret.get("spec", {})
    target = spec.get("target", {}) or {}
    return target.get("name") or external_secret["metadata"]["name"]


def _es_source_refs(
    external_secret: dict, credential_key: str, target_keys: set[str]
) -> list[tuple[str, str]]:
    """Return [(openbao_path, property_name), ...] this ExternalSecret uses for credential_key.

    Handles both explicit ``spec.data[]`` entries (secretKey == credential_key)
    and whole-path ``spec.dataFrom[].extract`` pulls (only a match when the
    *actual* target Secret's key list — fetched live, never guessed —
    contains ``credential_key``, since an ``extract`` pull's field set isn't
    declared in the ExternalSecret spec itself).
    """
    spec = external_secret.get("spec", {})
    refs: list[tuple[str, str]] = []

    for entry in spec.get("data", []) or []:
        if entry.get("secretKey") == credential_key:
            remote = entry.get("remoteRef", {})
            path = remote.get("key", "")
            prop = remote.get("property") or credential_key
            refs.append((path, prop))

    if credential_key in target_keys:
        for entry in spec.get("dataFrom", []) or []:
            extract = entry.get("extract")
            if extract and extract.get("key"):
                refs.append((extract["key"], credential_key))
            find = entry.get("find")
            if find and find.get("path"):
                refs.append((find["path"], credential_key))

    # de-dupe, keep order
    out: list[tuple[str, str]] = []
    for r in refs:
        if r not in out:
            out.append(r)
    return out


def _workload_consumers(
    secret_name: str, secret_namespace: str, workloads: list[dict]
) -> list[Consumer]:
    consumers: list[Consumer] = []
    for wl in workloads:
        kind = wl.get("kind", "")
        meta = wl.get("metadata", {})
        ns = meta.get("namespace", "")
        if ns != secret_namespace:
            continue
        name = meta.get("name", "")
        pod_spec = wl.get("spec", {}).get("template", {}).get("spec", {})
        for container in pod_spec.get("containers", []) or []:
            cname = container.get("name", "")
            for ef in container.get("envFrom", []) or []:
                if ef.get("secretRef", {}).get("name") == secret_name:
                    consumers.append(Consumer(kind, ns, name, cname, "envFrom"))
            for env in container.get("env", []) or []:
                skr = env.get("valueFrom", {}).get("secretKeyRef", {})
                if skr.get("name") == secret_name:
                    consumers.append(
                        Consumer(kind, ns, name, cname, f"env:{env.get('name')}")
                    )
    return consumers


def discover_credential(
    credential_key: str,
    external_secrets: list[dict],
    secret_key_names: dict[tuple[str, str], set[str]],
    workloads: list[dict],
) -> DiscoveryResult:
    """Resolve every OpenBao path + ExternalSecret + consumer for ``credential_key``.

    Args:
        credential_key: the env-var / KV field name, e.g. ``GRAPH_SERVICE_AUTH_SECRET``.
        external_secrets: list of ExternalSecret objects (``kubectl get externalsecrets -A -o json`` items).
        secret_key_names: ``{(namespace, secret_name): {key1, key2, ...}}`` — KEY NAMES ONLY,
            never values, for every k8s Secret that could be an ExternalSecret target.
        workloads: Deployment/StatefulSet/DaemonSet items (any mix; ``kind`` disambiguates).

    Returns:
        A :class:`DiscoveryResult` — empty (``found() is False``) if no ExternalSecret
        projects this key anywhere, which the caller should treat as a hard stop
        (never guess a path).
    """
    channels: list[Channel] = []
    for es in external_secrets:
        ns = es["metadata"]["namespace"]
        target = _target_secret_name(es)
        target_keys = secret_key_names.get((ns, target), set())
        for path, prop in _es_source_refs(es, credential_key, target_keys):
            consumers = _workload_consumers(target, ns, workloads)
            channels.append(
                Channel(
                    external_secret=es["metadata"]["name"],
                    namespace=ns,
                    target_secret=target,
                    source_path=path,
                    source_property=prop,
                    consumers=consumers,
                )
            )
    return DiscoveryResult(credential_key=credential_key, channels=channels)


# ---------------------------------------------------------------------------
# Credential type / generation strategy registry
# ---------------------------------------------------------------------------


@dataclass
class CredentialType:
    kind: str  # "generated" | "provider-issued" | "unknown"
    description: str
    mint_procedure: str | None = None  # human-readable, for provider-issued
    verify: str = "manual"  # "rollout" | "manual" | custom key a caller understands
    generator: Any = None  # callable() -> str, only set for kind == "generated"


def _random_secret(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


CREDENTIAL_TYPES: dict[str, CredentialType] = {
    "GRAPH_SERVICE_AUTH_SECRET": CredentialType(
        kind="generated",
        description=(
            "HMAC signing secret shared by the epistemic-graph engine, graph-os / "
            "graph-os-host, and every *-mcp fleet pod. Any random high-entropy string "
            "works cryptographically, but EVERY holder/consumer must cut over together "
            "or engine auth breaks mid-flight."
        ),
        generator=_random_secret,
        verify="rollout",
    ),
    "OPENBAO_TOKEN": CredentialType(
        kind="provider-issued",
        description=(
            "OpenBao auth token — self-referential. It must be MINTED by OpenBao's own "
            "token API (it is a capability OpenBao itself tracks/revokes by accessor), "
            "never invented as a random string."
        ),
        mint_procedure=(
            "bao token create -policy=agent-apps-rw -ttl=768h "
            "(or POST /v1/auth/token/create with an admin-capable token). "
            "Revoke the OLD token's accessor only after the new one verifies."
        ),
        verify="openbao-self-lookup",
    ),
    "MATTERMOST_TOKEN": CredentialType(
        kind="provider-issued",
        description=(
            "Mattermost bot / personal-access-token. Must be minted via Mattermost's own "
            "admin API or System Console — a locally-generated string will never be valid."
        ),
        mint_procedure=(
            "POST /api/v4/users/{user_id}/tokens (or System Console > Integrations > "
            "Bot Accounts). Revoke the OLD token via "
            "DELETE /api/v4/users/{user_id}/tokens/{token_id} only after the new one verifies."
        ),
        verify="http-200-check",
    ),
}

#: Suffix-based fallback classification when a credential isn't in the exact-name
#: registry above — a hint, not a hard rule; ``execute`` still refuses to invent
#: a value for anything classified "provider-issued" without an explicit
#: --new-value-file (or a matching mint_procedure the operator confirms).
_PROVIDER_ISSUED_SUFFIXES = ("_CLIENT_SECRET", "_TOKEN", "_API_KEY", "_PASSWORD")

_KEYCLOAK_CLIENT_SECRET = CredentialType(
    kind="provider-issued",
    description="Keycloak client secret — must be regenerated via Keycloak's admin API.",
    mint_procedure=(
        "kcadm.sh create clients/<client-uuid>/client-secret against the Keycloak admin "
        "REST API. NOTE: the keycloak pod ships no `tar`, so `kubectl cp` fails — pipe "
        "base64 through `kubectl exec` instead to move the result out."
    ),
    verify="manual",
)


def classify_credential(credential_key: str) -> CredentialType:
    """Look up (or infer) how a credential's new value should be produced.

    Exact-name matches in ``CREDENTIAL_TYPES`` win. Otherwise infer from a
    naming pattern — a ``*_CLIENT_SECRET`` is treated as Keycloak-shaped,
    any other provider-shaped suffix defaults to "provider-issued, unknown
    provider" (execute refuses to auto-generate), and anything else defaults
    to "generated" (safe to mint locally as a random string) with a WARNING
    kind of "unknown" so the operator confirms before relying on it blindly.
    """
    if credential_key in CREDENTIAL_TYPES:
        return CREDENTIAL_TYPES[credential_key]
    if credential_key.endswith("_CLIENT_SECRET"):
        return _KEYCLOAK_CLIENT_SECRET
    if any(credential_key.endswith(suffix) for suffix in _PROVIDER_ISSUED_SUFFIXES):
        return CredentialType(
            kind="unknown",
            description=(
                f"'{credential_key}' looks provider-issued by name but has no registry "
                "entry. Treated as unknown — execute() refuses to auto-generate; supply "
                "--new-value-file with a value minted by whatever system owns it."
            ),
            verify="manual",
        )
    return CredentialType(
        kind="generated",
        description=(
            f"'{credential_key}' has no registry entry; defaulting to a locally-generated "
            "random secret. Confirm this is correct before executing — a provider-issued "
            "credential with a non-matching suffix would silently get an invalid value."
        ),
        generator=_random_secret,
        verify="manual",
    )


# ---------------------------------------------------------------------------
# Plan assembly
# ---------------------------------------------------------------------------


@dataclass
class RotationPlan:
    credential_key: str
    discovery: DiscoveryResult
    credential_type: CredentialType
    steps: list[str]
    warnings: list[str]

    def render(self) -> str:
        lines = [f"# Rotation plan: {self.credential_key}", ""]
        if not self.discovery.found():
            lines.append(
                "NO OpenBao path / ExternalSecret projects this key anywhere in the "
                "cluster. Refusing to plan further — resolve discovery first."
            )
            return "\n".join(lines)

        lines.append(
            f"Type: **{self.credential_type.kind}** — {self.credential_type.description}"
        )
        if self.credential_type.mint_procedure:
            lines.append(f"Mint via: {self.credential_type.mint_procedure}")
        lines.append("")

        lines.append(
            f"## Blast radius — {'SHARED / coordinated cutover required' if self.discovery.is_shared else 'single consumer'}"
        )
        lines.append(
            f"- OpenBao source path(s): {', '.join(self.discovery.distinct_source_paths)}"
        )
        lines.append(f"- ExternalSecret channel(s): {len(self.discovery.channels)}")
        for ch in self.discovery.channels:
            lines.append(
                f"  - `{ch.external_secret}` (ns={ch.namespace}) apps/{ch.source_path}#{ch.source_property} "
                f"-> Secret/{ch.target_secret} -> {len(ch.consumers)} consumer(s)"
            )
            for con in ch.consumers:
                lines.append(
                    f"      - {con.kind}/{con.namespace}/{con.name} (container={con.container}, {con.mount})"
                )
        lines.append(
            f"- Total distinct consumer workloads: {len(self.discovery.all_consumers)}"
        )
        lines.append("")

        lines.append("## Steps")
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

        if self.warnings:
            lines.append("## Warnings — human decision required")
            for w in self.warnings:
                lines.append(f"- {w}")
        return "\n".join(lines)


def build_plan(
    discovery: DiscoveryResult, credential_type: CredentialType
) -> RotationPlan:
    """Assemble the ordered rotation steps + human-decision warnings for a discovery result.

    Pure function — no side effects, always safe to call (this IS the dry-run).
    """
    warnings: list[str] = []
    if not discovery.found():
        return RotationPlan(
            discovery.credential_key,
            discovery,
            credential_type,
            [],
            [
                "No ExternalSecret/OpenBao path found for this credential — nothing to plan."
            ],
        )

    steps: list[str] = []

    if credential_type.kind == "generated":
        steps.append(
            "Generate a new value locally (cryptographically random, never logged)."
        )
    else:
        steps.append(
            "Mint the new value via the OWNING PROVIDER's API — "
            f"{credential_type.mint_procedure or 'a human-run provider-specific procedure'}. "
            "Do NOT invent this value locally."
        )

    n_paths = len(discovery.distinct_source_paths)
    if n_paths > 1:
        warnings.append(
            f"This credential is duplicated across {n_paths} independent OpenBao KV paths "
            f"({', '.join(discovery.distinct_source_paths)}). All paths currently holding it "
            "must be verified to hold the SAME value before rotating, and all must be "
            "written in the same operation — writing only one path immediately desyncs it "
            "from the others."
        )

    for path in discovery.distinct_source_paths:
        steps.append(
            f"Read the FULL existing secret at apps/{path} (all keys), merge in the new "
            f"{discovery.credential_key} value, and write it back as ONE call (KV v2 "
            "replaces the entire version on write — a per-key write would delete every "
            "other key at that path)."
        )

    unique_channels: list[Channel] = []
    seen_es: set[tuple[str, str]] = set()
    for ch in discovery.channels:
        key = (ch.namespace, ch.external_secret)
        if key not in seen_es:
            seen_es.add(key)
            unique_channels.append(ch)

    if discovery.is_shared:
        sync_cmds = ", ".join(
            f"`kubectl annotate externalsecret -n {ch.namespace} {ch.external_secret} "
            f'force-sync="$(date +%s)" --overwrite`'
            for ch in unique_channels
        )
        steps.append(
            f"Force-sync ALL of these ExternalSecrets together (not one-at-a-time): {sync_cmds}"
        )
    else:
        for ch in unique_channels:
            steps.append(
                f"Force-sync `{ch.external_secret}` (ns={ch.namespace}): "
                f"`kubectl annotate externalsecret -n {ch.namespace} {ch.external_secret} "
                f'force-sync="$(date +%s)" --overwrite` — kubectl patch on the Secret '
                "itself would silently revert on the next 1h refresh; always go through OpenBao."
            )

    consumers = discovery.all_consumers
    if discovery.is_shared and len(consumers) > 1:
        steps.append(
            f"Restart all {len(consumers)} consumer workloads in the SAME batch (not "
            "sequentially): `kubectl rollout restart <kind>/<name> -n <namespace>` for "
            "every consumer listed above, issued back-to-back, then wait on all "
            "`kubectl rollout status` together. A holder/consumer restarted alone while "
            "others still hold the old value means the two sides authenticate with "
            "mismatched secrets and requests between them fail until every pod is on the "
            "new value."
        )
        warnings.append(
            "This shared credential has no built-in dual-secret grace window here — the "
            "restart batch causes a short auth blip for any in-flight request between the "
            "holder and its consumers during the cutover. Confirm a brief blip is "
            "acceptable (or add dual-secret support before rotating) before executing."
        )
    else:
        for con in consumers:
            steps.append(
                f"Restart `{con.kind}/{con.name}` (ns={con.namespace}): `kubectl rollout restart {con.kind.lower()}/{con.name} -n {con.namespace}`."
            )

    if credential_type.verify == "rollout":
        steps.append(
            "Verify: `kubectl rollout status` succeeds (Ready) for every consumer AND at "
            "least one sampled fleet pod's health/readiness endpoint returns healthy — a "
            "CrashLoop or failing readiness probe after restart means the new secret was "
            "rejected."
        )
    elif credential_type.verify == "openbao-self-lookup":
        steps.append(
            "Verify: from the rotated pod, call OpenBao's `/v1/auth/token/lookup-self` "
            "with the new token and confirm it returns 200 with the expected policies."
        )
    elif credential_type.verify == "http-200-check":
        steps.append(
            "Verify: call the provider's own authenticated endpoint with the new value "
            "(e.g. Mattermost `GET /api/v4/users/me`) and confirm HTTP 200."
        )
    else:
        steps.append(
            "Verify: run the credential's functional check manually before proceeding."
        )

    for path in discovery.distinct_source_paths:
        steps.append(
            f"On verification FAILURE: automatically roll back apps/{path} to its prior "
            "KV v2 version (`Rollback`/`kv2_get` old version -> `kv2_put`), force-sync the "
            "affected ExternalSecret(s) again, and restart the same consumer batch again."
        )

    if credential_type.kind == "provider-issued":
        steps.append(
            "After the new value verifies end-to-end, revoke the OLD credential at its "
            "provider (do this LAST, only after verification passes, so a failed rotation "
            "can still roll back to a live old credential)."
        )

    return RotationPlan(
        discovery.credential_key, discovery, credential_type, steps, warnings
    )
