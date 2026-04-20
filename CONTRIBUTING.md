# Contributing to nativeagents-sdk-py

Thank you for your interest in contributing to the Native Agents SDK.

## Development setup

```bash
pip install -e ".[dev]"
```

Or with uv:

```bash
uv pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Linting and type checking

```bash
ruff check .
mypy --strict src/nativeagents_sdk
```

## Contract first

Before changing any Python code, update the relevant `contract/*.md` file.
The contract is the source of truth; the code is the implementation.

## Commit messages

Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.

## Pull requests

All PRs must pass CI (pytest + ruff + mypy on Python 3.11 and 3.12).
