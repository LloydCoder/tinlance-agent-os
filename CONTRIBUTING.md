# Contributing

Keep changes inside the documented dependency direction:

`contracts -> domain -> services -> integrations -> apps`

Do not add direct imports of Agent Platform implementation internals or Tinlance domain
products. Add contract and architecture tests for new boundaries.

Run locally:

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest --cov=tinlance_agent_os --cov-report=term-missing --cov-fail-under=85
```
