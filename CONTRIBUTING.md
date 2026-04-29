# Contributing to nativeagents-sdk-py

Thank you for your interest in contributing to the Native Agents SDK.

## Development setup

```bash
git clone https://github.com/nativeagents/nativeagents-sdk-py
cd nativeagents-sdk-py

# uv (recommended)
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Or with plain pip
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
.venv/bin/python -m pytest tests/ -v --cov=nativeagents_sdk --cov-fail-under=90
```

All 314 tests should pass with ≥90% coverage.

## Linting and type checking

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy --strict src/nativeagents_sdk
```

## Contract first

Before changing any Python code, update the relevant `contract/*.md` file.
The contract is the source of truth; the code is the implementation.

## Commit messages

Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.

## Pull requests

All PRs must pass CI (pytest + ruff + mypy on Python 3.11 and 3.12).
Coverage must stay at ≥90% — the CI enforces this via `--cov-fail-under=90`.
