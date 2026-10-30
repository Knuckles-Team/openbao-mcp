# CONN-OPENBAO-MCP — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Existing system and reuse

`ApiClientBase` builds one governed client through `scion_sdk.http`. `Client` in `api_client_full.py` mutates its headers for token and namespace changes.

## Architecture

The SDK client owns timeouts, retry, and TLS. The connector owns request building and result shaping. The connector declares no HTTP library dependency of its own.

## Interfaces and data model

Tool names, signatures, and return values are unchanged. `Client.Headers()` returns a case-insensitive header mapping.

## Live integration path

Every tool calls `ApiClientBase.request`, which calls the governed client.

## Quality and release gates

Run `uv run pytest tests` and the repository pre-commit hooks.

## Risks, alternatives, and decisions

The governed client retries idempotent methods on transient statuses. `LIST` and writes are not retried.
