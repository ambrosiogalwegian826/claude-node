# Protocol Notes

`claude-node` communicates with Claude Code through newline-delimited JSON over stdin/stdout in `stream-json` mode.

## Launch shape

```bash
claude --input-format stream-json --output-format stream-json --verbose
```

Additional flags are appended by `ClaudeController` depending on options (e.g., `--resume`, `--continue`, permission flags).

## Input shape

Write one JSON object per line to stdin:

```json
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"your message"}]}}
```

The `message` field must contain `role` and `content` as a nested structure. This format has been verified against the CLI's actual behavior.

## Output message sequence per turn

The CLI emits messages in a predictable order per turn:

```
system/init        → startup metadata, session_id, available tools
assistant          → text and/or tool_use blocks
user/tool_result   → (optional) synthetic user message with tool results
result             → turn complete — this is the main synchronization signal
```

Not every turn produces all four types — some turns may skip `tool_result` if no tools were invoked.

## Synchronization rule

> **Wait for `type=result` before sending the next user message.**

This is the backbone of the protocol. The CLI is a sequential conversational runtime. Sending the next message before `result` is received causes context confusion or CLI errors.

The one exception is `send_nowait()` + `wait_for_result()`, which releases the lock during the wait so the caller can do other work before calling `wait_for_result()`.

## Session identity

- `session_id` appears in both `system/init` and `result` messages.
- Multi-turn context is maintained within the same session automatically.
- Explicit resume via `resume=<session_id>` restores a specific session.
- The `--continue` flag resumes the most recent session in the working directory — prefer explicit `resume=` in multi-session environments.

## Multi-turn context

Context persists across turns within a single session. The CLI maintains conversational state. You can verify this with a simple test:

```
Turn 1: "记住数字 42。只回复 OK。"  → result: OK
Turn 2: "我刚才让你记的数字是多少？"  → result: 42
Turn 3: "用那个数字乘以 2，只回复结果。" → result: 84
```

The same `session_id` is present in all three `result` messages.

## Transcript JSONL

When `transcript_path` is set in `ClaudeController`, every line read from stdout is appended to the JSONL file. This records the complete session as a sequence of JSON objects.

You can replay or analyze the session from the file. The recorded lines are exactly what `_reader()` receives from the CLI stdout — no transformation is applied.

## Caveats

### Some CLI-native behaviors are not reliable automation targets in stream-json mode

Certain interactive behaviors that work well in a human-facing REPL do not translate cleanly to automated stream-json use:

- **`AskUserQuestion`**: The CLI does not emit a protocol-level "pause" event that your controller can intercept. The assistant message streams continuously. If you need structured human-in-the-loop checkpoints, implement them at the application layer, not inside the Claude session.
- **Interactive slash commands**: Some slash commands are designed for interactive use and may produce output that is hard to parse reliably in an automated context.
- **`--print` mode**: Using `--print` changes the CLI's output format and is not compatible with the stream-json session model used here.

These behaviors work — they are part of the CLI — but they are not reliable automation primitives in this context.

## Error handling

The CLI may emit error-like result texts even when `subtype` is `success`. This can happen with API/auth/rate-limit conditions. `ClaudeMessage.is_api_error` provides a defensive check for these cases.

## Protocol reference demo

For a runnable demonstration of the raw protocol, see [`examples/demo_protocol_trace.py`](../examples/demo_protocol_trace.py).
