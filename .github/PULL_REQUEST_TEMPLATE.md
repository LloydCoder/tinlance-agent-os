## Summary

Describe what changed and why.

## Scope and architecture

- [ ] Preserves `contracts -> domain -> services -> integrations -> apps`
- [ ] Does not duplicate Agent Platform authority
- [ ] Preserves workspace/tenant boundaries
- [ ] Treats external/model/retrieved/tool data as untrusted
- [ ] Updates relevant ADRs or architecture docs

## Validation

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy src`
- [ ] `pytest --cov=tinlance_agent_os --cov-report=term-missing --cov-fail-under=85`
- [ ] `pip-audit`
- [ ] Architecture/contract tests run when applicable

## Security

Describe security implications, threat-model changes, and any new trust boundary.

## Documentation

- [ ] README updated if user-facing behavior changed
- [ ] Changelog updated
- [ ] API/reference documentation updated where applicable

## Compatibility

Describe migration, persistence, API, or release implications.

## Checklist

- [ ] No secrets or sensitive data added
- [ ] Tests cover the changed behavior
- [ ] Failure modes fail closed where appropriate
- [ ] Retry/idempotency semantics are explicit for consequential operations
