# Tinlance Agent OS

> An agent-native operating environment for teams building governed AI agents, workflows, and enterprise agent applications on the Tinlance Agent Platform.

[![CI](https://github.com/LloydCoder/tinlance-agent-os/actions/workflows/ci.yml/badge.svg)](https://github.com/LloydCoder/tinlance-agent-os/actions/workflows/ci.yml) [![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml) [![Security](https://img.shields.io/badge/security-policy-blue.svg)](SECURITY.md)

[!NOTE]
Tinlance Agent OS is the OS/control-plane layer above Tinlance Agent Platform. It composes intent and lifecycle; Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, governed execution, sandbox/tool authority, and authoritative evidence.

## Why Tinlance Agent OS

Agent systems need durable state and lifecycle semantics around the model loop: workspaces, sessions, tasks, workflows, memory, applications, extensions, scheduling, remote workers, observability, and release state.

Tinlance Agent OS provides those composition primitives without creating a second authorization kernel.

| Layer | Owns | Does not own |
| --- | --- | --- |
| Agent OS | Workspaces, sessions, tasks, workflows, memory, applications, extensions, lifecycle, scheduling, fleet metadata, operator projections | Consequential authorization or authoritative evidence |
| Agent Platform | Identity, tenancy, authorization, policy, approvals, budgets, governed execution, sandbox/tool authority, evidence | OS presentation and workspace lifecycle |
| Domain products | FAS, FDSE, TADS, ReconOS, ThreatFade, Hezqara and other integrations | Agent OS kernel authority |

## Architecture

```text
Human / organization
        |
        v
+-----------------------------+
|       Tinlance Agent OS     |
| workspace / session / task  |
| workflow / memory / agents  |
| apps / extensions / fleet   |
+--------------+--------------+
               |
        governed adapter
               v
+-----------------------------+
|   Tinlance Agent Platform   |
| identity / authz / policy   |
| approvals / budgets / runs  |
| sandbox / tools / evidence  |
+--------------+--------------+
               |
               v
       Tools / MCP / APIs
```

The consequential path is:

```text
intent -> OS task/workflow -> Platform request
       -> Platform authorization/policy/approval
       -> governed execution -> Platform evidence/events
       -> OS lifecycle/presentation
```

Model output, retrieved content, memory, tool output, extension requests, remote responses, and inter-agent messages are data—not authority.

## Quick start

Requirements: Python 3.12+.

```bash
python -m pip install -e ".[dev]"
agentos --help
pytest -q
```

For the full quality gate:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=tinlance_agent_os --cov-report=term-missing --cov-fail-under=85
pip-audit
```

[!WARNING]
A production deployment requires a real Tinlance Agent Platform gateway and its associated identity, policy, approval, secrets, telemetry, and execution infrastructure. This repository intentionally does not pretend to provide those external controls.

## Installation

### Editable development install

```bash
python -m pip install -e ".[dev]"
```

### Runtime package install

Build artifacts are produced by the release workflow. For source development, the editable install above is the supported path.

### Prerequisites

- Python 3.12, 3.13, or 3.14.
- A supported Linux/macOS development environment for local execution.
- A configured Agent Platform gateway for real governed execution.

## Usage

### CLI

```bash
agentos --help
```

### Python

```python
from tinlance_agent_os import AgentSDK, CapabilityDeclaration

sdk = AgentSDK()
app = sdk.scaffold(
    agent_id="research-agent",
    workspace_id="workspace-1",
    name="Research Agent",
    version="1.0.0",
    entrypoint="research.main",
    capabilities=(
        CapabilityDeclaration("research.read", "Read approved research sources"),)
)
print(app.scaffold.definition.agent_id)
```

The SDK composes OS contracts; it does not grant Platform capabilities.

### Advanced integration

The supported integration shape is:

```text
application -> Agent SDK -> OS runtime -> Platform adapter
           -> Agent Platform authority -> governed execution
```

Use the architecture and integration references before connecting consequential operations.

## Configuration

| Area | Default / invariant | Notes |
| --- | --- | --- |
| Python | >=3.12 | CI validates 3.12–3.14 |
| Package | `tinlance-agent-os` | setuptools build |
| CLI | `agentos` | `tinlance_agent_os.cli:main` |
| Type checking | strict mypy | `mypy src` |
| Lint | Ruff E/F/UP/B/SIM | line length 100 |
| Coverage gate | 85% | enforced in CI |
| Platform retries | bounded and semantics-aware | non-idempotent operations are not automatically retried |
| Local persistence | SQLite | production distributed persistence remains a deployment concern |
| Release integrity | SHA-256 plus Sigstore/attestation in release workflow | signing/provenance infrastructure is external to the OS runtime |

## Features

| Capability | Scope |
| --- | --- |
| Agent lifecycle | Durable registration, state transitions, heartbeats, recovery |
| Workspaces and sessions | Explicit lifecycle and isolation boundaries |
| Durable workflows | DAG validation, checkpoints, retries, approvals, recovery |
| Trusted memory | Scope, classification, provenance, versioning, poisoning detection |
| Agent SDK | Typed application/developer surface |
| Model gateway | Provider-neutral routing and bounded fallback |
| Multi-agent runtime | Coordination and team composition contracts |
| Agent catalog | Taxonomy, capability profiles, discovery, matching, team planning |
| Connectors | Connector and data-space contracts |
| Scheduler | Durable temporal/job runtime |
| Resource runtime | Cost, capacity, and resource accounting contracts |
| Evaluation | Agent quality/evaluation runtime |
| Fleet/device layer | Remote-agent, fleet, and device-state contracts |
| Registry | Agent/application/extension/connector registry lifecycle |
| Operator plane | Workspace-scoped projections and command intents |
| Reliability | HA/DR/chaos contracts without embedding infrastructure |
| Enterprise security | OIDC/SAML/SCIM/KMS/HSM/audit integration metadata |
| Release assurance | Artifact, SBOM, provenance, compatibility, and readiness records |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Agent Platform integration](docs/architecture/agent-platform-integration.md)
- [Roadmap](docs/ROADMAP.md)
- [Security controls](docs/SECURITY-CONTROLS.md)
- [Threat model](security/threat-model.md)
- [Architecture decision records](docs/adr/)
- [Agent Catalog v2](docs/agent-catalog-v2/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Support](SUPPORT.md)
- [Changelog](CHANGELOG.md)

## Repository layout

```text
src/tinlance_agent_os/   Core OS implementation
tests/                    Unit, architecture, contract, and integration tests
docs/                     Architecture, roadmap, status, and catalog documentation
security/                 Threat models and security material
.github/                  CI, release automation, Dependabot, CODEOWNERS, templates
```

## What it is—and is not

**It is:** an agent-native OS composition/control-plane foundation with durable lifecycle, workflow, memory, application, integration, fleet, evaluation, and release-assurance contracts.

**It is not:** a replacement authorization kernel, sandbox implementation, hosted enterprise IdP, hosted fleet SaaS, model provider, EDR/MDM/VPN, package registry service, or Linux distribution.

These boundaries are intentional and are tested architecturally.

## Contributing

Contributions are welcome when they preserve the authority boundary and dependency direction. Start with [CONTRIBUTING.md](CONTRIBUTING.md), run the local quality gates, and submit a focused pull request.

## License and acknowledgements

Tinlance Agent OS is licensed under the [Apache License 2.0](LICENSE).

The project uses OpenTelemetry APIs/SDKs and follows relevant open-source ecosystem practices for supply-chain security, agent interoperability, and repository governance. See the dependency metadata and documentation for implementation-specific details.

<details>
<summary>Roadmap status</summary>

The repository currently records implementation through M41 and the Agent Catalog v3 GA program. The roadmap describes repository contracts and integration seams; it does not imply that external enterprise infrastructure is bundled.

</details>

<details>
<summary>Troubleshooting</summary>

If the editable install fails, verify Python 3.12+ and rerun the install command. If tests fail, run the failing test directly with `pytest path/to/test.py -q`. For architecture failures, inspect the relevant contract and ADR before changing dependency direction.

</details>

<details>
<summary>Support</summary>

See [SUPPORT.md](SUPPORT.md). Security vulnerabilities must follow [SECURITY.md](SECURITY.md), not a public issue.

</details>
