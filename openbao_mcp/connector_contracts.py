"""Tool-use contracts, surface links, data locations and business roles of openbao-mcp.

The SDK serves this declaration as the connector's surface ontology and checks it
against the served tools, prompts and skills (SCION-CONNECTOR-CONTROL-R916).
"""

# ruff: noqa: E501
from __future__ import annotations

from scion_sdk.surface_contracts import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

CONTRACTS: tuple[ToolUseContract, ...] = (
    ToolUseContract(
        "find-a-secret",
        description="Locate and read a stored secret",
        steps=(
            ToolStep(
                "openbao_get_mounts",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_list_secrets",
                params=("mount",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_logical_list",
                params=("path",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_read_secret",
                params=("mount", "path"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "openbao_kv2_get",
                params=("secret_path",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_kv1_get",
                params=("secret_path",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_logical_read",
                params=("path",),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "store-a-secret",
        description="Write a secret, change a single key of it, and read it back",
        steps=(
            ToolStep(
                "openbao_write_secret",
                params=("mount", "path", "secret_data"),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_kv2_put",
                params=("secret_path", "data"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_kv2_patch",
                params=("secret_path", "new_data"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_kv1_put",
                params=("secret_path", "data"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_logical_write",
                params=("path", "data"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_logical_write_bytes",
                params=("path", "data_bytes"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_read_secret",
                params=("mount", "path"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
        ),
    ),
    ToolUseContract(
        "retire-a-secret",
        description="Delete a secret that is no longer used",
        steps=(
            ToolStep(
                "openbao_list_secrets",
                params=("mount",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_delete_secret",
                params=("mount", "path"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "openbao_kv2_delete",
                params=("secret_path",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
            ToolStep(
                "openbao_kv1_delete",
                params=("secret_path",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
            ToolStep(
                "openbao_logical_delete",
                params=("path",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "hand-over-a-wrapped-secret",
        description="Receive a response-wrapped secret exactly once",
        steps=(
            ToolStep(
                "openbao_logical_unwrap",
                params=("token",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "mount-a-secrets-engine",
        description="Enable a secrets engine and read the API schema of the server",
        steps=(
            ToolStep(
                "openbao_get_mounts",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_enable_mount",
                params=("mount", "mount_type"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_get_internal_openapi_spec",
                params=(),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "ingest-mount-metadata",
        description="Mirror mount and server metadata into the knowledge graph (never secret values)",
        steps=(
            ToolStep(
                "openbao_get_mounts",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep("openbao_get_health", params=(), result=("result",), refusals=()),
            ToolStep(
                "openbao_ingest_mounts", params=(), result=("result",), refusals=()
            ),
        ),
    ),
    ToolUseContract(
        "check-server-health",
        description="Read health, initialization, seal, leader, HA and raft state",
        steps=(
            ToolStep(
                "openbao_get_health",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep("openbao_sys_health", params=(), result=("result",), refusals=()),
            ToolStep(
                "openbao_sys_init_status", params=(), result=("result",), refusals=()
            ),
            ToolStep(
                "openbao_sys_seal_status", params=(), result=("result",), refusals=()
            ),
            ToolStep("openbao_sys_leader", params=(), result=("result",), refusals=()),
            ToolStep(
                "openbao_sys_ha_status", params=(), result=("result",), refusals=()
            ),
            ToolStep(
                "openbao_sys_raft_autopilot_state",
                params=(),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "initialize-and-unseal-server",
        description="Initialize a new server and unseal it shard by shard",
        steps=(
            ToolStep(
                "openbao_sys_init_status",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_sys_init", params=("opts",), result=("result",), refusals=()
            ),
            ToolStep(
                "openbao_sys_seal_status", params=(), result=("result",), refusals=()
            ),
            ToolStep(
                "openbao_sys_unseal", params=("shard",), result=("result",), refusals=()
            ),
        ),
    ),
    ToolUseContract(
        "seal-server",
        description="Seal the server in an emergency",
        steps=(
            ToolStep(
                "openbao_sys_seal_status",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_sys_seal",
                params=("confirm",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "join-raft-cluster",
        description="Add a node to the raft cluster and watch autopilot",
        steps=(
            ToolStep(
                "openbao_sys_raft_join",
                params=("opts",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_sys_raft_autopilot_state",
                params=(),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_sys_ha_status", params=(), result=("result",), refusals=()
            ),
        ),
    ),
    ToolUseContract(
        "log-in-and-validate-mfa",
        description="Log in to an auth method, including MFA",
        steps=(
            ToolStep(
                "openbao_auth_login",
                params=("data",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_auth_mfa_login",
                params=("data",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_auth_mfa_validate",
                params=("mfa_secret", "payload"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "manage-tokens",
        description="Create, inspect, renew and revoke tokens",
        steps=(
            ToolStep(
                "openbao_auth_token_create",
                params=("opts",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_auth_token_lookup",
                params=("token",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_auth_token_renew",
                params=("token",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_auth_token_revoke",
                params=("token",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "issue-ssh-access",
        description="Issue an SSH credential, sign a key, or verify a one-time password",
        steps=(
            ToolStep(
                "openbao_ssh_credential",
                params=("role",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "openbao_ssh_sign_key",
                params=("role", "data"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "openbao_ssh_verify", params=("otp",), result=("result",), refusals=()
            ),
        ),
    ),
)

LINKS: tuple[SurfaceLink, ...] = (
    SurfaceLink(
        "find-a-secret",
        tools=(
            "openbao_get_mounts",
            "openbao_list_secrets",
            "openbao_logical_list",
            "openbao_read_secret",
            "openbao_kv2_get",
            "openbao_kv1_get",
            "openbao_logical_read",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-secrets-steward"),
        skills=("secret-vault-manager",),
    ),
    SurfaceLink(
        "store-a-secret",
        tools=(
            "openbao_write_secret",
            "openbao_kv2_put",
            "openbao_kv2_patch",
            "openbao_kv1_put",
            "openbao_logical_write",
            "openbao_logical_write_bytes",
            "openbao_read_secret",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-secrets-steward"),
        skills=("secret-vault-manager",),
    ),
    SurfaceLink(
        "retire-a-secret",
        tools=(
            "openbao_list_secrets",
            "openbao_delete_secret",
            "openbao_kv2_delete",
            "openbao_kv1_delete",
            "openbao_logical_delete",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-secrets-steward"),
        skills=("secret-vault-manager",),
    ),
    SurfaceLink(
        "hand-over-a-wrapped-secret",
        tools=("openbao_logical_unwrap",),
        prompts=("openbao-mcp-operator", "openbao-mcp-secrets-steward"),
        skills=("secret-vault-manager",),
    ),
    SurfaceLink(
        "mount-a-secrets-engine",
        tools=(
            "openbao_get_mounts",
            "openbao_enable_mount",
            "openbao_get_internal_openapi_spec",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-secrets-steward"),
        skills=("openbao-mcp-operations", "secret-vault-manager"),
    ),
    SurfaceLink(
        "ingest-mount-metadata",
        tools=("openbao_get_mounts", "openbao_get_health", "openbao_ingest_mounts"),
        prompts=(
            "openbao-mcp-operator",
            "openbao-mcp-secrets-steward",
            "openbao-mcp-platform-operator",
        ),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "check-server-health",
        tools=(
            "openbao_get_health",
            "openbao_sys_health",
            "openbao_sys_init_status",
            "openbao_sys_seal_status",
            "openbao_sys_leader",
            "openbao_sys_ha_status",
            "openbao_sys_raft_autopilot_state",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-platform-operator"),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "initialize-and-unseal-server",
        tools=(
            "openbao_sys_init_status",
            "openbao_sys_init",
            "openbao_sys_seal_status",
            "openbao_sys_unseal",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-platform-operator"),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "seal-server",
        tools=("openbao_sys_seal_status", "openbao_sys_seal"),
        prompts=("openbao-mcp-operator", "openbao-mcp-platform-operator"),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "join-raft-cluster",
        tools=(
            "openbao_sys_raft_join",
            "openbao_sys_raft_autopilot_state",
            "openbao_sys_ha_status",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-platform-operator"),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "log-in-and-validate-mfa",
        tools=(
            "openbao_auth_login",
            "openbao_auth_mfa_login",
            "openbao_auth_mfa_validate",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-access-administrator"),
        skills=("openbao-mcp-operations",),
    ),
    SurfaceLink(
        "manage-tokens",
        tools=(
            "openbao_auth_token_create",
            "openbao_auth_token_lookup",
            "openbao_auth_token_renew",
            "openbao_auth_token_revoke",
        ),
        prompts=("openbao-mcp-operator", "openbao-mcp-access-administrator"),
        skills=("secret-vault-manager",),
    ),
    SurfaceLink(
        "issue-ssh-access",
        tools=("openbao_ssh_credential", "openbao_ssh_sign_key", "openbao_ssh_verify"),
        prompts=("openbao-mcp-operator", "openbao-mcp-access-administrator"),
        skills=("openbao-mcp-operations",),
    ),
)

LOCATIONS: tuple[DataLocation, ...] = (
    DataLocation(
        "openbao-secrets",
        ("Credential",),
        "BAO_ADDR",
        "openbao_list_secrets",
        federation_key="path",
    ),
    DataLocation(
        "openbao-mounts",
        ("Service",),
        "BAO_ADDR",
        "openbao_get_mounts",
        federation_key="mount",
    ),
    DataLocation(
        "openbao-server",
        ("Server",),
        "BAO_ADDR",
        "openbao_get_health",
        federation_key=None,
    ),
    DataLocation(
        "openbao-tokens",
        ("Credential",),
        "BAO_ADDR",
        "openbao_auth_token_lookup",
        federation_key="token",
    ),
)

ROLES: tuple[BusinessRole, ...] = (
    BusinessRole(
        "secrets-steward",
        tasks=(
            "find-a-secret",
            "store-a-secret",
            "retire-a-secret",
            "hand-over-a-wrapped-secret",
            "mount-a-secrets-engine",
            "ingest-mount-metadata",
        ),
    ),
    BusinessRole(
        "platform-operator",
        tasks=(
            "check-server-health",
            "initialize-and-unseal-server",
            "seal-server",
            "join-raft-cluster",
            "ingest-mount-metadata",
        ),
    ),
    BusinessRole(
        "access-administrator",
        tasks=("log-in-and-validate-mfa", "manage-tokens", "issue-ssh-access"),
    ),
)
