# claude-node examples

This directory contains three layers of examples, organized by purpose.

## Layer 1: Library Usage — `demo_end_to_end.py`

The primary reference demo. Shows how to use the library's core APIs
in one coherent workflow.

**What it covers:**

| Phase | API / Feature |
|---|---|---|
| 0 | `check_claude_available()` |
| 1 | `ClaudeController` + `on_message` callback + `transcript_path` |
| 2 | `send_nowait()` + `wait_for_result()` |
| 3 | `send_checked()` |
| 4 | `fork()` |
| 5 | `MultiAgentRouter` + `parallel_send()` + `route()` |
| 6 | JSONL transcript summary |

**Run:**
```bash
python examples/demo_end_to_end.py
```

---

## Layer 2: CLI-Native Capabilities — `demo_cli_native_features.py`

Shows how claude-node bridges to Claude CLI's native capabilities
(skills, slash commands, interactive features).

**What it covers:**

- Slash command skill invocation (`/brainstorm`)
- Natural language skill trigger (plan mode)
- Full event callback observation (`is_assistant`, `is_tool_result`, `is_result`)
- Transcript recording and playback
- **Caveat**: `AskUserQuestion` is NOT a reliable interactive pause
  mechanism in stream-json mode (full explanation in the file)

**Run:**
```bash
python examples/demo_cli_native_features.py
```

---

## Layer 3: Protocol Reference — `demo_protocol_trace.py`

A raw protocol trace derived from the archive/ protocol exploration scripts.
Not a library usage demo — a reference for understanding the stream-json protocol.

**What it covers:**

- Launch command shape (`--input-format stream-json --output-format stream-json`)
- User message format (verified: `{"type":"user","message":{...}}`)
- Complete event sequence per turn
- Multi-turn context persistence
- Protocol reference summary

**Run:**
```bash
python examples/demo_protocol_trace.py
```

---

## Running all demos

All demos require:

- Python 3.11+
- a local `claude` CLI in `PATH`
- a working Claude Code login on the host machine

For the cleanest developer experience:

```bash
pip install -e .
python examples/demo_end_to_end.py
python examples/demo_cli_native_features.py
python examples/demo_protocol_trace.py
```

If Claude Code is not installed, each demo will exit gracefully with a
clear error message.
