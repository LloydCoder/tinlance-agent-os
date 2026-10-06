# Changelog

All notable changes to Tinlance Agent OS are documented here.

The format follows Keep a Changelog principles, and the project uses Semantic Versioning for released package versions.

## [Unreleased]

### Maintenance

- Updated pinned release-workflow actions to `actions/checkout` 7.0.1, `actions/setup-python` 7.0.0, and `sigstore/cosign-installer` 4.1.2.


### Changed

- Documentation and repository community-health overhaul for 2026 GitHub standards.
- Added structured issue forms, pull request guidance, support policy, code of conduct, and LLM discovery metadata.
- Added supply-chain security workflows for Scorecard and CodeQL.

## [0.1.0] - 2026-10-06

### Added

- Agent OS control-plane foundation through M41.
- Tinlance Agent Platform adapter boundary.
- Durable workspaces, sessions, tasks, workflows, memory, applications, extensions, scheduling, fleet, evaluation, registry, operator, reliability, enterprise-security, adaptive-runtime, and release-assurance contracts.
- Agent Catalog semantic program and interoperability surfaces.
- Python 3.12–3.14 CI with Ruff, mypy, pytest/coverage, and pip-audit.
- SHA-pinned GitHub Actions and production release workflow with SBOM, Sigstore signing, and provenance attestations.

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0
