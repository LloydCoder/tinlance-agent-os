# Contributing to Tinlance Agent OS

Thank you for contributing. Tinlance Agent OS is a security-sensitive control-plane project, so changes must preserve explicit authority boundaries and deterministic lifecycle semantics.

## Before you start

Read:

- [README.md](README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Threat model](security/threat-model.md)
- [Security policy](SECURITY.md)

The dependency direction is:

`contracts -> domain -> services -> integrations -> apps`

Do not import Agent Platform implementation internals into the OS. Do not make FAS, FDSE, TADS, ReconOS, ThreatFade, Hezqara, or another domain product a kernel dependency.

## Development setup

```bash
python -m pip install -e ".[dev]"
```

Supported Python versions are 3.12–3.14.

## Branch and pull request flow

1. Fork or create a feature branch from `main`.
2. Keep the change focused and explain the architectural impact.
3. Add or update tests for behavior and security invariants.
4. Reconcile affected documentation and ADRs.
5. Run all local quality gates.
6. Open a pull request against `main`.
7. Address review feedback and keep CI green.
8. Merge only after required repository checks and owner review are satisfied.

Never commit credentials, tokens, private keys, local state, generated secrets, or customer data.

## Quality gates

Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=tinlance_agent_os --cov-report=term-missing --cov-fail-under=85
pip-audit
```

Architecture and contract checks:

```bash
pytest tests/architecture tests/contract -q
```

## Coding standards

- Prefer small, typed, deterministic functions.
- Keep authority decisions in Tinlance Agent Platform.
- Treat external, retrieved, model-generated, memory, and tool data as untrusted.
- Fail closed on invalid identity, scope, version, classification, or generation data.
- Never add an automatic retry without defining idempotency semantics.
- Preserve workspace and tenant boundaries.
- Add regression tests for security-sensitive behavior.
- Keep public APIs backwards compatible unless a deliberate version change is documented.

## Commit messages

Use Conventional Commit style where practical, for example:

`feat(workflow): add durable checkpoint recovery`

`fix(memory): reject stale version updates`

`docs(security): clarify private vulnerability reporting`

## Pull request expectations

A PR should state:

- what changed;
- why it changed;
- affected architecture boundaries;
- tests and quality gates run;
- documentation updated;
- security implications;
- migration or compatibility impact, if any.

Security vulnerabilities must never be disclosed through a public issue or PR. Follow [SECURITY.md](SECURITY.md).
