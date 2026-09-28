# Contributing

Changes must preserve the Agent OS / Agent Platform boundary.

Before opening a pull request:

- run Ruff lint and format checks;
- run mypy;
- run pytest with coverage;
- verify no Agent Platform internal imports were introduced;
- update architecture/security documentation when a boundary changes.

Consequential execution features require an explicit Agent Platform integration
design before implementation.
