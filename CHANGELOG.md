# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.9] - 2026-11-06

### Changed
- Connector surface: agent-definition prompts (operator, secrets steward, platform operator, access administrator), task skills, tool-use contracts for all 42 tools, data locations and roles; ontology classes extend core classes.
- Require `scion-sdk>=0.9.0`; `uv.lock` relocked.
- The action-routed `openbao_mcp_{sys,auth,kv,logical,ssh}` tools are replaced by one typed tool per operation (`openbao_sys_*`, `openbao_auth_*`, `openbao_kv1_*`, `openbao_kv2_*`, `openbao_logical_*`, `openbao_ssh_*`); destructive tools take `confirm`.

## [2.3.7] - 2026-10-30

### Changed
- Require `scion-sdk>=0.6.4,<0.7.0`; `uv.lock` relocked.

## [2.3.4] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [Unreleased]

### Added
- Added the source-backed OpenBao connector development skill and focused
  publication contract checks for the standard spec-delivery workflow.

## [0.15.0] - 2026-05-25

### Added
- Initial dynamic facade API client implementation.
- FastMCP server entry points and modular tools.
- Rich documentation templates, including standardized environment configuration.
- Complete test suite validating startup and facade execution.
- Standardized MIT License.

[Unreleased]: https://github.com/genius-agents/openbao-mcp/compare/v0.15.0...HEAD
[0.15.0]: https://github.com/genius-agents/openbao-mcp/releases/tag/v0.15.0
