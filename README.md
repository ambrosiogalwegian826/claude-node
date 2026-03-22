# claude-node

**A thin subprocess-based Python bridge for persistent Claude Code sessions.**

`claude-node` drives the local `claude` CLI as a long-lived subprocess and communicates with it over `stream-json`. Because it runs the installed CLI directly as its runtime, Python code gets access to Claude Code's native behavior through the CLI itself — achieving maximum compatibility with the CLI.

This is not a higher-level reimplementation or a message API wrapper. It is a direct bridge to the installed `claude` executable.

---

## The CLI bridge

`claude-node` sits at the subprocess boundary:

```
Your Python code          claude-node           Your local claude CLI
─────────────────        ────────────          ──────────────────────
ClaudeController  ───►   stdin/stdout   ───►   Claude Code runtime
                    ◄──   JSON events  ◄───
```

- **Maximum compatibility**: because `claude-node` delegates entirely to the local `claude` CLI, any capability the CLI exposes is available — skills, slash commands, tools, agent modes, and session management.
- **Process isolation**: the Claude runtime lives in its own OS process, independent of the Python interpreter.
- **Protocol transparency**: raw `stream-json` behavior is visible and debuggable.
- **Easy embedding**: drop it into any Python environment — workers, web backends, job runners, or supervisor processes.

---

## Positioning

### What this project is

`claude-node` is a:

- **Python bridge** to a local Claude Code runtime,
- **persistent session controller** for `claude --input-format stream-json`,
- **runtime integration layer** for existing Python systems,
- **protocol reference implementation** for developers who want to understand or embed the CLI.

### What this project is not

It is **not**:

- an API SDK replacement,
- a workflow engine,
- a memory framework,
- a dashboard product,
- or a full “AI organization system”.

The official Agent SDK provides a higher-level integration surface. `claude-node` takes a different position: it stays close to the CLI process itself, with minimal abstraction and explicit lifecycle control.

---

## Runtime model

This project is a **pure Python package**, but it has an **external runtime dependency**:

- The package itself is standard Python.
- At runtime, it requires a local `claude` executable in `PATH`.

In other words:

- `pip install claude-node` installs the Python package.
- `claude-node` only works if `claude --version` works on that machine.

This split is intentional. The project does not attempt to ship or emulate Claude Code. It controls an existing local Claude Code runtime.

---

## Installation

### Python package

```bash
pip install claude-node
```

### Runtime requirement

Make sure Claude Code / Claude CLI is installed and available:

```bash
claude --version
```

If that command fails, `claude-node` cannot start a session.

---

## Requirements

- Python 3.11+
- a local `claude` executable in `PATH`
- a working Claude Code login / configuration on the host machine
- macOS or Linux recommended

Windows support has not been validated in this repository.

---

## Quick start

### Single controller

```python
from claude_node import ClaudeController

with ClaudeController(skip_permissions=True) as ctrl:
    result = ctrl.send("List the files in the current directory")
    if result:
        print(result.result_text)
        print("session:", ctrl.session_id)
```

### Real-time callback

```python
def on_message(msg):
    if msg.is_assistant:
        for text in msg.assistant_texts:
            print("[assistant]", text)
    if msg.is_tool_result:
        for block in msg.tool_results:
            print("[tool_result]", block.get("tool_use_id"), block.get("is_error"))

ctrl = ClaudeController(on_message=on_message, skip_permissions=True)
ctrl.start()
result = ctrl.send("Run the tests and summarize failures", timeout=120)
ctrl.stop()
```

### Resume a session

```python
from claude_node import ClaudeController

with ClaudeController(skip_permissions=True) as ctrl:
    result = ctrl.send("Remember that the project codename is ALPHA. Reply only OK.")
    saved_session_id = ctrl.session_id

ctrl = ClaudeController(resume=saved_session_id, skip_permissions=True)
ctrl.start()
result = ctrl.send("What is the project codename?")
print(result.result_text if result else None)
ctrl.stop()
```

### Lightweight multi-session routing

```python
from claude_node import MultiAgentRouter, AgentNode

with MultiAgentRouter() as router:
    router.add(AgentNode("PM", system_prompt="You are a product manager."))
    router.add(AgentNode("DEV", system_prompt="You are a backend engineer."))
    router.start_all()

    pm_reply = router.send("PM", "Design a JWT login feature.")
    dev_reply = router.route(
        pm_reply or "",
        to="DEV",
        wrap="PM proposal:\n{message}\n\nPlease review technical feasibility.",
    )

    print("PM:", pm_reply)
    print("DEV:", dev_reply)
```

---

## Public API

The current public surface is intentionally small:

```python
from claude_node import (
    ClaudeController,
    ClaudeMessage,
    MultiAgentRouter,
    AgentNode,
)
```

### `ClaudeController`

Controls one long-lived Claude CLI subprocess.

Current responsibilities:

- start / stop one `claude` process,
- write `user` messages to stdin,
- read JSON lines from stdout / stderr,
- wait for `type=result` as the turn-completion signal,
- track `session_id`,
- provide parsed messages via `ClaudeMessage`,
- expose simple callbacks through `on_message`.

### `ClaudeMessage`

Represents one parsed JSON event from the CLI stream.

Useful helpers include:

- `is_init`
- `is_result`
- `is_result_ok`
- `is_result_error`
- `is_api_error`
- `truly_succeeded`
- `is_assistant`
- `is_tool_result`
- `assistant_texts`
- `tool_calls`
- `tool_results`
- `result_text`
- `session_id`
- `cost_usd`
- `num_turns`

### `MultiAgentRouter`

A minimal multi-session routing layer.

It currently provides:

- named node registration,
- bulk start / stop,
- send to one named agent,
- message wrapping and routing,
- simple parallel fan-out,
- access to an underlying controller via `get_ctrl()`.

This is a lightweight primitive layer, not a full orchestration framework.

---

## Current architecture

```text
claude_node/
├── __init__.py       # Public exports
├── controller.py     # ClaudeController, ClaudeMessage
├── router.py        # AgentNode, MultiAgentRouter
├── runtime.py       # Binary discovery and version checking
└── exceptions.py    # Typed exception hierarchy
```

### `controller.py`

Contains:

- `ClaudeMessage`
- `ClaudeController`
- `_send_lock` for serializing concurrent send calls

### `router.py`

Contains:

- `AgentNode`
- `MultiAgentRouter`

### `runtime.py`

Binary discovery and version introspection:

- `find_claude_binary(cli_path)` — resolve CLI path via `shutil.which`
- `get_claude_version(binary_path)` — read version from `--version`
- `check_claude_available(cli_path)` — raises `ClaudeBinaryNotFound` if missing

### `exceptions.py`

Typed exception hierarchy (all inherit from `ClaudeError → RuntimeError`):

- `ClaudeBinaryNotFound` — claude binary not in PATH
- `ClaudeStartupError` — subprocess failed to start
- `ClaudeTimeoutError` — operation exceeded timeout
- `ClaudeSendConflictError` — concurrent send to same controller

The codebase is intentionally compact. The long-term direction is to keep the library **narrow and dependable**, not large and feature-heavy.

---

## The protocol this library is built on

`claude-node` communicates with Claude Code through newline-delimited JSON over stdin/stdout.

Typical launch shape:

```bash
claude --input-format stream-json --output-format stream-json --verbose
```

Typical input shape:

```json
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"your message"}]}}
```

Typical output flow per turn:

1. `system/init` — appears on initial startup and includes session metadata
2. `assistant` — may include thinking, text, and `tool_use` blocks
3. `user/tool_result` — emitted by the CLI after internal tool execution
4. `result` — the turn is complete; this is the main synchronization point

The most important rule is simple:

> Wait for `type=result` before sending the next message.

That rule is the backbone of the current implementation.

---

## Session model

The repository currently supports:

- new sessions,
- explicit resume via `resume=<session_id>`,
- implicit “continue most recent” via `continue_session=True`,
- session forking via `controller.fork()` — creates a new controller resuming the current session.

### Recommended practice

In multi-session or multi-node environments, prefer:

- explicit `resume=<session_id>`

and avoid depending on:

- `--continue`

because `--continue` resumes the most recent session in the working directory rather than the exact session you intend.

### Important note

The README you are reading is intentionally honest about the **current code**:

- `resume` exists now,
- `continue_session` exists now,
- `fork()` exists now — creates a new controller resuming the current session.

---

## Current status and known limitations

This repository is functional and in **alpha** state.

### What works now

- persistent Claude subprocess control,
- multi-turn sessions,
- result waiting,
- assistant / tool result parsing,
- basic session resume,
- session forking via `controller.fork()`,
- lightweight router patterns,
- controller-level send serialization (`_send_lock`),
- structured exception hierarchy (`ClaudeError`, `ClaudeBinaryNotFound`, etc.),
- runtime discovery (`claude_node.runtime`),
- transcript / JSONL export (`transcript_path` parameter).

### Current limitations

- `send()` timeout returns `None` rather than raising `ClaudeTimeoutError` (partial exception integration),
- integration tests require a working local `claude` binary and are opt-in (see [CONTRIBUTING.md](CONTRIBUTING.md)).

This is why the project should currently be described as **alpha**.

For the full list of known limitations, see [docs/06-roadmap-and-limitations.md](docs/06-roadmap-and-limitations.md).

---

## Design principles

These principles define the project’s direction.

### 1. Subprocess-first
The library controls a real Claude CLI process.

### 2. Thin wrapper, not platform
The goal is a dependable bridge, not a giant framework.

### 3. Explicit session control
Lifecycle, resume behavior, and routing should stay visible and controllable.

### 4. Protocol transparency
The stream should remain understandable and debuggable.

### 5. Lightweight routing only
Multi-session patterns are welcome; orchestration sprawl is not.

---

## Documentation map

Additional docs live under `docs/`:

- `docs/00-index.md` — documentation index
- `docs/01-positioning.md` — project identity and scope
- `docs/02-architecture.md` — architecture and internal boundaries
- `docs/03-api-reference.md` — API reference based on the current code
- `docs/04-protocol.md` — stream-json protocol notes
- `docs/05-development.md` — repository workflow and testing reality
- `docs/06-roadmap-and-limitations.md` — current gaps and next steps

### Runnable examples

All examples are in `examples/`:

- [`examples/demo_end_to_end.py`](examples/demo_end_to_end.py) — library usage reference (all core APIs)
- [`examples/demo_cli_native_features.py`](examples/demo_cli_native_features.py) — CLI-native capabilities (skills, callbacks, transcript)
- [`examples/demo_protocol_trace.py`](examples/demo_protocol_trace.py) — raw stream-json protocol reference

See [`examples/README.md`](examples/README.md) for the full demo map.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, testing instructions, and scope boundaries.

---

## License

Apache-2.0
