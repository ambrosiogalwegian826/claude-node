# Roadmap and Limitations

This file separates the **current limitations** from the **recommended next steps**.

## Current limitations

The repository is functional but still has gaps.

### 1. Timeout paths return None rather than raising

`send()` timeout still returns `None` in some cases instead of raising `ClaudeTimeoutError`. Full exception integration is partially complete (exception classes exist and are used for binary-not-found and send-conflict cases).

## Completed items

The following were previously listed as limitations and are now implemented:

- **Runtime discovery** — `claude_node/runtime.py` provides `find_claude_binary()`, `get_claude_version()`, and `check_claude_available()`. `controller.start()` calls `check_claude_available()` before launching.
- **Exception hierarchy** — `claude_node/exceptions.py` defines `ClaudeError` (base), `ClaudeBinaryNotFound`, `ClaudeStartupError`, `ClaudeTimeoutError`, and `ClaudeSendConflictError`.
- **Controller-level send serialization** — `_send_lock` protects the full send transaction. Concurrent `send()` calls raise `ClaudeSendConflictError`. `send_nowait()` + `wait_for_result()` correctly releases the lock on all exit paths.
- **`fork()` API** — `ClaudeController.fork()` creates a new controller resuming the current session. `controller.fork()` raises `RuntimeError` if no session is established.
- **Transcript / JSONL export** — `transcript_path` parameter enables JSONL recording of all stdout messages.
- **Test structure** — Unit tests in `tests/unit/`, integration scripts in `tests/integration/`, `conftest.py` with `claude_required` fixture, pytest markers configured.

## Recommended next steps

### Priority 1: complete exception integration

- Make `send()` raise `ClaudeTimeoutError` instead of returning `None` on timeout.

### Priority 2: observability

- Additional observability improvements (beyond the current transcript export) are not planned — the current JSONL export provides sufficient session replay capability for debugging.

## Explicit non-goals

The roadmap should not drift into:

- workflow DSLs,
- DAG engines,
- memory systems,
- governance frameworks,
- dashboards,
- hosted services,
- or giant multi-agent platforms.

## Strategic rule

The project wins by becoming the clearest and most dependable bridge at its layer.

It does not win by becoming the largest project in the surrounding ecosystem.
