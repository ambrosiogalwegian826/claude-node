# Development Guide

## Repository goals

When developing in this repository, optimize for:

- correctness,
- clarity,
- narrow scope,
- and honest documentation.

Do not optimize for feature count.

## Local setup

```bash
pip install -e .
pip install -e .[dev]
```

## Runtime expectation

A working local `claude` binary is required for most real integration paths.

Check first:

```bash
claude --version
```

## Current testing reality

The repository currently contains a mixture of:

- pytest-discoverable tests,
- integration-style tests,
- and protocol exploration scripts.

This is important because the test suite is not yet fully normalized into a pure unit-test-first structure.

## Running tests

```bash
pytest
```

Example single-file run:

```bash
pytest tests/test_multiturn.py -v
```

## Important caveat

Some current test files have import-time side effects and assume a real local Claude runtime.

That means even:

```bash
pytest --collect-only
```

may fail when `claude` is unavailable.

This is not ideal, but it is the current reality and should be documented honestly.

## Documentation rule for contributors

Whenever you update docs, always separate:

- **current behavior**
- **planned improvements**
- **out-of-scope ideas**

This repository should not accumulate misleading “already implemented” claims.

## Recommended contribution areas

Good contributions improve one of these:

- runtime checks,
- error handling,
- message parsing clarity,
- session handling,
- tests,
- examples,
- protocol transparency.

## Contributions that should be treated cautiously

Be careful with contributions that try to turn the repository into:

- a workflow engine,
- a memory platform,
- a full multi-agent operating system,
- or a product-like orchestration layer.

Those directions may be interesting, but they are not the right fit for this repository.
