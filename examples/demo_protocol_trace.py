#!/usr/bin/env python3
"""
Layer 3: Protocol trace demo for claude-node.
=============================================

This demo is a reference implementation of the stream-json protocol,
extracted from the protocol exploration scripts in archive/.

It is NOT a library usage demo — it is a protocol reference that shows:
- How the CLI is launched
- What the initialize handshake looks like
- The exact JSON shape for user messages
- The complete output event sequence per turn
- How multi-turn context works
- Common error patterns and what they mean

This file is derived from archive/test_handshake.py, archive/test_multiturn.py,
archive/test_nested.py, and related protocol exploration scripts.

Requirements:
- Same as demo_end_to_end.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Iterable

try:
    from claude_node.exceptions import ClaudeBinaryNotFound
    from claude_node.runtime import check_claude_available
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from claude_node.exceptions import ClaudeBinaryNotFound
    from claude_node.runtime import check_claude_available


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def h1(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def h2(title: str) -> None:
    print(f"\n-- {title} --")


def show_io(step_title: str, input_label: str, input_text: str | None,
            output_label: str, output_text: str | None) -> None:
    """Print a clearly labeled input/output pair."""
    h2(step_title)
    print(f"\n{'─' * 40}")
    print(f"  {input_label} (INPUT)")
    print(f"{'─' * 40}")
    print(input_text or "")
    print(f"\n{'─' * 40}")
    print(f"  {output_label} (OUTPUT)")
    print(f"{'─' * 40}")
    print(output_text or "")
    print(f"{'─' * 40}")


def raw_reader(pipe, buf, label):
    """Read lines from a pipe into a buffer, printing to stdout."""
    for line in iter(pipe.readline, ""):
        line = line.rstrip("\n")
        if line:
            buf.append(line)
            print(f"[{label}] {line[:300]}", flush=True)


def send(proc, obj, label: str = ""):
    """Send a JSON object as a line to the subprocess stdin."""
    line = json.dumps(obj, ensure_ascii=False)
    print(f"\n>>> [{label}] {line[:250]}", flush=True)
    proc.stdin.write(line + "\n")
    proc.stdin.flush()


def wait_seconds(buf, seconds: float, label: str) -> list[str]:
    """Wait N seconds and return new lines received."""
    before = len(buf)
    time.sleep(seconds)
    return buf[before:]


# ---------------------------------------------------------------------------
# Protocol reference data
# ---------------------------------------------------------------------------

# How the CLI is launched
LAUNCH_CMD = [
    "claude",
    "--input-format", "stream-json",
    "--output-format", "stream-json",
    "--verbose",
]

# The correct user message format (verified by test_multiturn.py)
USER_MESSAGE_FORMAT = {
    "type": "user",
    "message": {
        "role": "user",
        "content": [{"type": "text", "text": "your message here"}],
    },
}

# Known message types observed from CLI output
MESSAGE_TYPES = [
    ("system/init", "Startup metadata, session_id, available tools"),
    ("assistant", "Assistant text and/or tool_use blocks"),
    ("user/tool_result", "Synthetic user message with tool results after tool execution"),
    ("result", "Turn completion signal — the main sync point"),
    ("system/task_started", "Background task started"),
    ("system/task_progress", "Background task progress update"),
    ("system/task_notification", "Background task notification"),
]


# ---------------------------------------------------------------------------
# Demo phases
# ---------------------------------------------------------------------------

def phase0_runtime_check():
    h1("Phase 0: Runtime Check")
    info = check_claude_available()
    show_io(
        "Phase 0 Result",
        "check_claude_available()",
        "No arguments — probes PATH for 'claude' binary",
        "ClaudeRuntimeInfo fields",
        f"available={info.available}, binary_path={info.binary_path}, version={info.version}",
    )
    if not info.available:
        raise ClaudeBinaryNotFound(
            f"claude binary not found at: {info.binary_path}"
        )
    return info


def phase1_launch_shape():
    """Show how the CLI is launched and what the startup sequence looks like."""
    h1("Phase 1: Launch Shape")

    h2("Phase 1 — INPUT")
    print(f"\n  API call:  subprocess.Popen(LAUNCH_CMD)")
    print(f"  Command:\n{'-' * 40}")
    print(f"  {' '.join(LAUNCH_CMD)}")
    print(f"{'-' * 40}")
    print("\n  Protocol significance:")
    print("  → --input-format stream-json  : we write JSON to stdin")
    print("  → --output-format stream-json : we read JSON from stdout")
    print("  → --verbose                   : richer stderr for debugging")

    proc = subprocess.Popen(
        LAUNCH_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={**os.environ, "TERM": "dumb"},
    )
    out, err = [], []
    threading.Thread(target=raw_reader, args=(proc.stdout, out, "OUT"), daemon=True).start()
    threading.Thread(target=raw_reader, args=(proc.stderr, err, "ERR"), daemon=True).start()

    time.sleep(2)
    h2("Phase 1 — OUTPUT")
    print(f"\n  proc.poll() → {proc.poll()}")
    if proc.poll() is not None:
        print(f"  Process exited with code: {proc.returncode}")
        print("  stderr:", "\n".join(err[-5:]))
        proc = None
    else:
        print(f"  Process running, PID={proc.pid}")

    return proc, out, err


def phase2_user_message_format(proc, out):
    """Send the verified correct user message format and observe output."""
    h1("Phase 2: User Message Format")

    h2("Phase 2 — INPUT")
    print(f"\n  API call:  send(proc, USER_MESSAGE_FORMAT)")
    print(f"  Format:\n{'-' * 40}")
    print(json.dumps(USER_MESSAGE_FORMAT, indent=2, ensure_ascii=False))
    print(f"{'-' * 40}")
    print("\n  This format was verified by archive/test_multiturn.py")

    if proc is None:
        print("\n[OUTPUT] Process not running, skipping.")
        return

    send(proc, USER_MESSAGE_FORMAT, "first-turn")
    new_lines = wait_seconds(out, 15, "after first message")

    h2("Phase 2 — OUTPUT")
    print(f"\n  Received {len(new_lines)} lines after sending first message.")
    print("  (Raw lines appear above via raw_reader thread)")

    return new_lines


def phase3_event_sequence(proc, out):
    """Show the complete event sequence for a single turn."""
    h1("Phase 3: Event Sequence Per Turn")

    LS_PROMPT = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "What files are in the current directory? Reply with a brief list."}],
        },
    }

    h2("Phase 3 — INPUT")
    print(f"\n  API call:  send(proc, ls_request)")
    print(f"  Prompt:\n{'-' * 40}")
    print("  What files are in the current directory? Reply with a brief list.")
    print(f"{'-' * 40}")

    if proc is None:
        print("\n[OUTPUT] Process not running, skipping.")
        return

    send(proc, LS_PROMPT, "ls-request")

    # Wait for result
    start = time.time()
    seen = len(out)
    result = None
    while time.time() - start < 60:
        for line in out[seen:]:
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    result = obj
                    break
            except:
                pass
        seen = len(out)
        if result:
            break
        time.sleep(0.5)

    h2("Phase 3 — OUTPUT (event sequence)")
    print("\n  Event sequence observed:")
    event_order = []
    for line in out[-(len(out) - seen + 1):]:
        try:
            obj = json.loads(line)
            t = obj.get("type", "?")
            sub = obj.get("subtype", "")
            event_order.append(f"    {t}" + (f"/{sub}" if sub else ""))
        except:
            pass

    for e in event_order:
        print(e)

    if result:
        print(f"\n  Final result: {result.get('result', '')[:200]}")

    print("\n  Key insight: wait for type=result before sending next message.")


def phase4_multiturn_context(proc, out):
    """Demonstrate multi-turn context persistence."""
    h1("Phase 4: Multi-Turn Context")

    TURN1_PROMPT = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "Remember the number 42. Reply only OK."}],
        },
    }
    TURN2_PROMPT = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "What number did I ask you to remember? Reply with only the number."}],
        },
    }

    h2("Phase 4 — INPUT (Turn 1)")
    print(f"\n  API call:  send(proc, TURN1_PROMPT)")
    print(f"  Prompt:\n{'-' * 40}")
    print("  Remember the number 42. Reply only OK.")
    print(f"{'-' * 40}")

    if proc is None:
        print("\n[OUTPUT] Process not running, skipping.")
        return

    send(proc, TURN1_PROMPT, "remember-42")

    r1 = None
    start = time.time()
    seen = len(out)
    while time.time() - start < 60:
        for line in out[seen:]:
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    r1 = obj
                    break
            except:
                pass
        seen = len(out)
        if r1:
            break
        time.sleep(0.5)

    h2("Phase 4 — OUTPUT (Turn 1 result)")
    print(f"\n  Turn 1 result: {r1.get('result', '')[:80] if r1 else 'TIMEOUT'}")

    h2("Phase 4 — INPUT (Turn 2)")
    print(f"\n  API call:  send(proc, TURN2_PROMPT)")
    print(f"  Prompt:\n{'-' * 40}")
    print("  What number did I ask you to remember? Reply with only the number.")
    print(f"{'-' * 40}")

    send(proc, TURN2_PROMPT, "recall-42")

    r2 = None
    start = time.time()
    seen = len(out)
    while time.time() - start < 60:
        for line in out[seen:]:
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    r2 = obj
                    break
            except:
                pass
        seen = len(out)
        if r2:
            break
        time.sleep(0.5)

    h2("Phase 4 — OUTPUT (Turn 2 result)")
    print(f"\n  Turn 2 result: {r2.get('result', '')[:80] if r2 else 'TIMEOUT'}")

    has_42 = r2 and "42" in r2.get("result", "")
    print(f"\n  Context preserved (42 recalled): {'✅' if has_42 else '❌'}")
    if r1:
        print(f"  session_id: {r1.get('session_id', '')}")


def phase5_protocol_summary():
    """Print a protocol reference summary."""
    h1("Phase 5: Protocol Reference Summary")

    print("Launch command:")
    print(f"  {' '.join(LAUNCH_CMD)}")
    print("\nUser message format:")
    print(json.dumps(USER_MESSAGE_FORMAT, indent=2, ensure_ascii=False))
    print("\nKnown message types:")
    for t, desc in MESSAGE_TYPES:
        print(f"  {t}")
        print(f"    → {desc}")

    print("\nKey synchronization rule:")
    print("  Wait for type=result before sending the next user message.")
    print("\nCommon error patterns:")
    print("  1. Sending before previous result → context confusion")
    print("  2. Wrong message format (missing 'message' wrapper) → CLI error")
    print("  3. Not waiting for system/init before first send → race condition")
    print("\nNested message format (verified working):")
    print("  The 'message' field must contain 'role' and 'content':")
    print("  {type:'user', message:{role:'user', content:[{type:'text', text:'...'}]}}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Iterable[str] | None = None) -> int:
    print("Protocol Trace Demo for claude-node")
    print("=" * 60)
    print("This demo shows the raw stream-json protocol as observed")
    print("by the archive/ protocol exploration scripts.")
    print("=" * 60)

    try:
        phase0_runtime_check()
    except ClaudeBinaryNotFound as e:
        print("Claude Code CLI is not available.")
        print(str(e))
        return 1

    proc, out, err = phase1_launch_shape()

    try:
        phase2_user_message_format(proc, out)
        phase3_event_sequence(proc, out)
        phase4_multiturn_context(proc, out)
        phase5_protocol_summary()

        h1("Protocol Demo Complete")
        print("Key takeaways:")
        print("  1. Launch: claude --input-format stream-json --output-format stream-json")
        print("  2. User format: {type:'user', message:{role:'user', content:[{type:'text', text:'...'}]}}")
        print("  3. Sync rule: wait for type=result before next send")
        print("  4. Multi-turn: context persists within the same session")
        print("  5. session_id: found in system/init and result messages")
        return 0

    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
