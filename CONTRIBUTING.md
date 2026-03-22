# Contributing to claude-node

Thank you for your interest in contributing to claude-node.

## Project positioning

`claude-node` is a **thin subprocess-based Python bridge** for persistent Claude Code sessions.

It runs the installed `claude` CLI as the runtime, giving Python code direct access to Claude Code's native behavior through the CLI itself. This approach achieves the highest compatibility with the Claude Code CLI.

**This project is not:**
- a workflow engine
- a memory framework
- an orchestration platform
- a higher-level reimplementation of Claude Code

**This project is:**
- a Python bridge to the `claude` CLI runtime
- a persistent session controller for `claude --input-format stream-json`
- a protocol reference implementation for the stream-json mode

## Contribution scope

Before opening a PR, ask: does this still belong to a thin Claude Code session bridge?

If the answer is "this is really a workflow engine / memory system / platform feature," it belongs in another project.

Priority areas for contributions:
- Runtime bridge reliability
- Session control robustness
- Protocol observability
- Testing coverage

## Development setup

```bash
pip install -e .
pip install -e .[dev]  # if available
```

## Testing

### Unit tests (no CLI required)
```bash
python -m pytest tests/unit -q
```

### Integration tests (requires local `claude` CLI)
```bash
python -m pytest tests/integration -q
```

Integration tests are opt-in because they require a working `claude` binary in `PATH`.

## Submission guidelines

- **Small, focused PRs** — one concern per PR
- **Tests for new behavior** — every new behavior must have corresponding tests
- **Docs match code** — if you change behavior, update the relevant docs
- **No scope creep** — don't use a PR to add features unrelated to the stated purpose
- **Descriptive commit messages** — explain the *why*, not just the *what*

## Code style

- Follow existing patterns in the codebase
- Keep functions small and single-purpose
- Prefer explicit over clever
- No new dependencies without strong justification
