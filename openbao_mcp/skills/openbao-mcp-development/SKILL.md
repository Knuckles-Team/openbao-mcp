---
name: openbao-mcp-development
skill_type: skill
description: >-
  Develop and verify openbao-mcp as a connector-owned package while preserving
  its SDK Connector wiring, OpenBao authentication and TLS boundary, action
  tools, packaged content, and source-backed spec-delivery publication.
---

# OpenBao MCP Development

Use this skill for changes to the `openbao-mcp` connector. The package owns
OpenBao API calls, MCP action mappings, connector content, and its packaged
skills; the SDK transport, shared Pages renderer, and Pipelines hooks remain
external boundaries.

## Repository map and runtime boundary

- `openbao_mcp/__init__.py` creates the SDK `Connector` with `Api`,
  `get_client`, and `openbao_mcp.mcp_server` as its tool module. It serves
  `stdio` and `streamable-http`; preserve this connector identity and transport
  declaration.
- `openbao_mcp/mcp_server.py` re-exports the four actual registrar functions:
  `register_auth_tools`, `register_secrets_tools`, `register_ssh_tools`, and
  `register_sys_tools`. The SDK tool-surface loader discovers these module
  attributes; keep the module boundary and registrar names stable.
- `openbao_mcp/mcp/mcp_auth.py` owns `openbao_mcp_auth` for login, MFA, and
  token actions. `openbao_mcp/mcp/mcp_secrets.py` owns
  `openbao_mcp_logical` and `openbao_mcp_kv`; `openbao_mcp/mcp/mcp_ssh.py`
  owns `openbao_mcp_ssh`; and `openbao_mcp/mcp/mcp_sys.py` owns
  `openbao_mcp_sys` plus metadata-only `openbao_ingest_mounts`.
  Preserve each action name, payload shape, and tool tag.
- `openbao_mcp/auth.py` reads `OPENBAO_URL` with
  `OPENBAO_MCP_BASE_URL` fallback, `OPENBAO_TOKEN`, and optional
  `OPENBAO_MCP_USERNAME`/`OPENBAO_MCP_PASSWORD`. `api_client_base.py` uses
  the SDK HTTP client and resolves the named `openbao` TLS profile while
  retaining the existing BasicAuth/token behavior. Never embed credentials or
  weaken verification.
- `openbao_mcp/ontology/`, `openbao_mcp/prompts/`,
  `openbao_mcp/connectors/`, and `openbao_mcp/skills/` are packaged connector
  content. `pyproject.toml` includes these trees through package data; inspect
  a built wheel when changing packaged content.
- The declared console script is
  `openbao-mcp = agent_connector_sdk.cli:serve`, and the connector entry point
  is `openbao-mcp = openbao_mcp:connector`. Do not invent another server or
  entry point.

## Rapid delivery: the 5-minute contract

1. Read the owning `specs/` row, this repository's `AGENTS.md`, and focused
   tests before editing.
2. Inspect the active SDK Connector, registrar module, action maps, API client,
   auth/TLS path, and package-data declaration before changing runtime or
   packaged content.
3. Prefer the smallest connector-owned change. Preserve action names and
   payload schemas, OpenBao API paths, `OPENBAO_*` settings, TLS resolution,
   ontology mappings, metadata-only ingestion, and the SDK Connector boundary
   unless the owning requirement changes.
4. Run focused publication/runtime tests through the narrow test-slot wrapper;
   run repository hooks normally without `--no-verify` or skipped gates.
5. When packaged content changes, advance the patch version and update
   `uv.lock` together; inspect the wheel for the skill and declared resources.
6. Treat Pages as separate proof: after the exact main SHA has a successful
   Pages run, check `/spec-delivery/`, its `index.html`, and `snapshot.json`
   over HTTPS and record the snapshot revision.

## Focused development commands

From the repository root:

```bash
uv sync --locked

/var/tmp/arbora-delivery/scale/run-narrow-test-slot.sh \
  uv run --locked --extra test pytest -q \
    tests/test_publication_workflow.py \
    tests/test_init_dynamics.py \
    tests/test_mcp_server.py \
    tests/test_api_client.py \
    tests/test_governed_http.py

uvx pre-commit run --all-files
uvx pre-commit run --all-files --hook-stage pre-push
```

These checks cover the shared Pages/release contract, lazy runtime imports,
action dispatch, API client behavior, and SDK centralization. Do not replace
them with a live OpenBao call or a credential-bearing test.

## Pages and package publication

`.github/workflows/pages.yml` is the sole Pages caller. It invokes
`pages_pipeline.yml@main` with `content_source: docs`,
`spec_dashboard_enabled: true`, and `.github/spec-dashboard.json`; its push
filters cover `docs/**`, `mkdocs.yml`, `README.md`, `specs/**`, the dashboard
config, and the Pages workflow. Keep this caller and the existing permissions
intact. The package workflow uses the shared `connector: true` and
`render_connector: true` callers.

After a merge, verify the exact main SHA in the successful Pages run and probe:

```bash
curl -fsSI https://knuckles-team.github.io/openbao-mcp/
curl -fsSI https://knuckles-team.github.io/openbao-mcp/spec-delivery/
curl -fsSI https://knuckles-team.github.io/openbao-mcp/spec-delivery/index.html
curl -fsS https://knuckles-team.github.io/openbao-mcp/spec-delivery/snapshot.json
```

Do not claim a Pages or package result from local source inspection alone. Keep
generated status changes with the Pipelines/status owner.

## Change discipline

- Keep OpenBao API calls, MCP schemas, auth settings, TLS resolution, ontology
  mappings, and metadata ingestion under the connector's existing boundary.
  SDK and shared renderer behavior belong to their owner repositories.
- Use injected `OPENBAO_*` configuration only; never print or commit token,
  username, password, TLS material, or generated runtime state.
- Preserve the OpenBao request/auth/TLS semantics and existing action-to-method
  mappings. For mutations, inspect current state and verify durable results
  through the governed procedure.
- Generated status files and central promotion are owned by Pipelines; this
  skill does not authorize editing `specs/*/status.json`.
