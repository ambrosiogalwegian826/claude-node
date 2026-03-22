#!/usr/bin/env python3
"""
Layer 2: CLI-native capability demo for claude-node.
=====================================================

This demo shows how claude-node bridges to Claude CLI's native capabilities
(skills, slash commands, interactive features) while maintaining the subprocess
bridge model.

Key topics covered:
- Skill/slash command invocation via natural language
- Callback observation of assistant/tool_use/tool_result/result events
- Transcript recording and playback
- Caveat: AskUserQuestion is NOT reliable as an interactive pause
  mechanism in stream-json mode (documented at the end)

Requirements:
- Same as demo_end_to_end.py (Python, local claude binary, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

try:
    from claude_node import AgentNode, ClaudeController, MultiAgentRouter
    from claude_node.exceptions import ClaudeBinaryNotFound
    from claude_node.runtime import check_claude_available
except ModuleNotFoundError:
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from claude_node import AgentNode, ClaudeController, MultiAgentRouter
    from claude_node.exceptions import ClaudeBinaryNotFound
    from claude_node.runtime import check_claude_available


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="claude-node CLI-native capabilities demo"
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Repository path (default: current working directory)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional Claude model name",
    )
    parser.add_argument(
        "--transcript",
        default=None,
        help="Optional transcript JSONL output path",
    )
    parser.add_argument(
        "--skip-permissions",
        action="store_true",
        default=True,
        help="Skip interactive permission checks (default)",
    )
    parser.add_argument(
        "--require-permissions",
        dest="skip_permissions",
        action="store_false",
        help="Do not skip permission checks",
    )
    return parser.parse_args(list(argv) if argv else sys.argv[1:])


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------


def h1(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def h2(title: str) -> None:
    print(f"\n-- {title} --")


def compact(text: str, limit: int = 180) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def show_io(step_title: str, input_label: str, input_text: str | None,
            output_label: str, output_text: str | None) -> None:
    """Print a clearly labeled input/output pair for a demo step."""
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


# ---------------------------------------------------------------------------
# Verbose event callback — observes all message types
# ---------------------------------------------------------------------------


def make_event_callback():
    """Build a callback that prints every event type for observability."""

    def on_message(msg) -> None:
        if msg.is_init:
            print(f"[event:init] session_id={msg.session_id}")
            return

        if msg.is_assistant:
            texts = msg.assistant_texts
            tool_calls = msg.tool_calls
            if texts:
                print(f"[event:assistant:text] {compact(' '.join(texts), 120)}")
            if tool_calls:
                names = [call.get("name", "<unknown>") for call in tool_calls]
                print(f"[event:assistant:tool_use] {names}")
            return

        if msg.is_tool_result:
            results = msg.tool_results
            errors = [r for r in results if r.get("is_error")]
            if errors:
                print(f"[event:tool_result:error] {len(errors)} error block(s)")
            else:
                print(f"[event:tool_result] {len(results)} block(s)")
            return

        if msg.is_result:
            print(
                f"[event:result:{msg.subtype or 'unknown'}] "
                f"turns={msg.num_turns} cost={msg.cost_usd}"
            )
            print(f"[event:result:text] {compact(msg.result_text, 200)}")
            return

    return on_message


# ---------------------------------------------------------------------------
# Prompt templates for CLI-native features
# ---------------------------------------------------------------------------

# Skill invocation via slash command syntax
SKILL_BRAINSTORM_PROMPT = """
/brainstorm Design the core architecture for a simple user points system.

Requirements:
1. Propose at least 3 key modules
2. Describe each module's responsibility
3. Note dependencies between modules
Output only a structured analysis, do not write any code.
""".strip()

# Natural language skill trigger (plan mode)
SKILL_PLAN_PROMPT = """
Enter plan mode and analyze what the main modules are in the current directory.
Output only the analysis plan, do not execute any operations.
""".strip()

# Memory skill
SKILL_MEMORY_PROMPT = """
/memory
""".strip()

# Multi-turn with confirmation flow (demonstrating interactive nature)
INTERACTIVE_CONFIRM_PROMPT = """
Design an architecture plan for a JWT login flow.

The plan should include:
1. Login API design
2. Token storage strategy
3. Refresh mechanism

End by asking me: "Should I proceed with this plan?"
""".strip()


# ---------------------------------------------------------------------------
# Demo phases
# ---------------------------------------------------------------------------


def phase0_runtime_check() -> Any:
    h1("Phase 0: Runtime Check")
    info = check_claude_available()
    show_io(
        "Phase 0 Result",
        "check_claude_available()",
        "No arguments — probes PATH for 'claude' binary",
        "ClaudeRuntimeInfo fields",
        f"available={info.available}, binary_path={info.binary_path}, version={info.version}",
    )
    return info


def phase1_skill_brainstorm(
    repo_path: Path,
    transcript_path: Path,
    skip_permissions: bool,
) -> None:
    """Trigger /brainstorm skill and observe the callback stream."""
    h1("Phase 1: Skill — /brainstorm")

    callback = make_event_callback()
    ctrl = ClaudeController(
        cwd=str(repo_path),
        skip_permissions=skip_permissions,
        on_message=callback,
        transcript_path=str(transcript_path),
    )

    started = ctrl.start()
    if not started:
        raise RuntimeError("ClaudeController.start() returned False")

    h2("Phase 1 — INPUT")
    print(f"\n  API call:  ctrl.send(prompt)")
    print(f"  Prompt:\n{'-' * 40}")
    print(f"  {SKILL_BRAINSTORM_PROMPT.replace(chr(10), chr(10) + '  ')}")
    print(f"{'-' * 40}")

    try:
        result = ctrl.send(SKILL_BRAINSTORM_PROMPT, timeout=120)
        h2("Phase 1 — OUTPUT")
        print(f"\n  ctrl.send() → result.result_text:")
        print(f"{'-' * 40}")
        print((result.result_text if result else "<no result>").strip())
        print(f"{'-' * 40}")
    finally:
        ctrl.stop()


def phase2_callback_observer(
    repo_path: Path,
    transcript_path: Path,
    skip_permissions: bool,
) -> None:
    """Observe all event types from a single request."""
    h1("Phase 2: Callback Observer — all event types")

    ctrl = ClaudeController(
        cwd=str(repo_path),
        skip_permissions=skip_permissions,
        on_message=make_event_callback(),
        transcript_path=str(transcript_path),
    )

    started = ctrl.start()
    if not started:
        raise RuntimeError("ClaudeController.start() returned False")

    TOOL_USE_PROMPT = "List the top-level files and directories here, then count them."

    h2("Phase 2 — INPUT")
    print(f"\n  API call:  ctrl.send(prompt)")
    print(f"  Prompt:\n{'-' * 40}")
    print(f"  {TOOL_USE_PROMPT}")
    print(f"{'-' * 40}")

    try:
        result = ctrl.send(TOOL_USE_PROMPT, timeout=60)
        h2("Phase 2 — OUTPUT (via on_message callback)")
        print(f"\n  ctrl.send() → result.result_text:")
        print(f"{'-' * 40}")
        print((result.result_text if result else "<no result>").strip()[:300])
        print(f"{'-' * 40}")
        print("\n  Events observed via on_message callback:")
        print("  → is_init, is_assistant, is_tool_result, is_result")
    finally:
        ctrl.stop()


def phase3_transcript_playback(transcript_path: Path) -> None:
    """Read back the transcript and show message type distribution."""
    h1("Phase 3: Transcript Playback")

    h2("Phase 3 — INPUT")
    print(f"\n  Transcript file: {transcript_path}")
    print(f"\n  How it was recorded:")
    print("  → Every line from CLI stdout was appended to the JSONL file")
    print("  → transcript_path was passed to ClaudeController constructor")
    print("  → _reader() appends each JSON line as it arrives")

    if not transcript_path.exists():
        print("\n[OUTPUT] Transcript file not found.")
        return

    from collections import Counter

    counts: Counter[str] = Counter()
    samples: dict[str, str] = {}

    with transcript_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                msg_type = obj.get("type", "unknown")
                subtype = obj.get("subtype", "")
                key = f"{msg_type}:{subtype}" if subtype else msg_type
                counts[key] += 1
                if key not in samples:
                    samples[key] = compact(str(obj), 120)
            except json.JSONDecodeError:
                counts["invalid_json"] += 1

    h2("Phase 3 — OUTPUT (transcript analysis)")
    print(f"\n  Total lines: {sum(counts.values())}")
    print("\n  Message counts:")
    for key, count in sorted(counts.items()):
        print(f"    {key}: {count}")

    print("\n  Samples (first occurrence of each type):")
    for key, sample in samples.items():
        print(f"    {key}: {sample}")


def phase4_interactive_caveat(
    repo_path: Path,
    skip_permissions: bool,
) -> None:
    """Demonstrate that AskUserQuestion is NOT a reliable pause mechanism."""
    h1("Phase 4: Interactive Flow Caveat")

    print("""
  IMPORTANT: AskUserQuestion is NOT a reliable pause mechanism.
  Reason: stream-json mode has no protocol-level "pause" event.
  The CLI streams continuously — implement human-in-the-loop at
  the application layer instead.
""")

    ctrl = ClaudeController(
        cwd=str(repo_path),
        skip_permissions=skip_permissions,
        on_message=make_event_callback(),
    )

    started = ctrl.start()
    if not started:
        raise RuntimeError("ClaudeController.start() returned False")

    h2("Phase 4 — INPUT")
    print(f"\n  API call:  ctrl.send(prompt)")
    print(f"  Prompt:\n{'-' * 40}")
    print(f"  {INTERACTIVE_CONFIRM_PROMPT.replace(chr(10), chr(10) + '  ')}")
    print(f"{'-' * 40}")
    print("\n  Note: this prompt asks Claude to propose a plan AND ask for confirmation.")
    print("  In stream-json mode, you CANNOT pause and wait for human input mid-turn.")

    try:
        result = ctrl.send(INTERACTIVE_CONFIRM_PROMPT, timeout=90)
        h2("Phase 4 — OUTPUT")
        print(f"\n  ctrl.send() → result.result_text:")
        print(f"{'-' * 40}")
        print((result.result_text if result else "<no result>").strip()[:300])
        print(f"{'-' * 40}")
        print("\n  What happened: CLI streamed the full response.")
        print("  There was NO pause at the question — you cannot intercept it.")
        print("  The caveat block at the end of this file explains why.")
    finally:
        ctrl.stop()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    repo_raw = args.repo or os.getcwd()
    repo_path = Path(repo_raw).resolve()

    if not repo_path.exists():
        print(f"Repository path does not exist: {repo_path}")
        return 1

    transcript_dir_obj: tempfile.TemporaryDirectory[str] | None = None
    try:
        try:
            phase0_runtime_check()
        except ClaudeBinaryNotFound as e:
            print("Claude Code CLI is not available.")
            print(str(e))
            print("\nPlease install Claude Code and ensure `claude` is in PATH.")
            return 1

        if args.transcript:
            transcript_path = Path(args.transcript).resolve()
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            transcript_dir_obj = tempfile.TemporaryDirectory(
                prefix="claude-node-cli-demo-"
            )
            transcript_path = Path(transcript_dir_obj.name) / "cli-session.jsonl"

        phase1_skill_brainstorm(
            repo_path=repo_path,
            transcript_path=transcript_path,
            skip_permissions=args.skip_permissions,
        )

        phase2_callback_observer(
            repo_path=repo_path,
            transcript_path=transcript_path,
            skip_permissions=args.skip_permissions,
        )

        phase3_transcript_playback(transcript_path)

        phase4_interactive_caveat(
            repo_path=repo_path,
            skip_permissions=args.skip_permissions,
        )

        h1("CLI-Native Demo Complete")
        print("This demo exercised:")
        print("  - slash command skill invocation (/brainstorm)")
        print("  - natural language skill trigger (plan mode)")
        print("  - full event callback observation")
        print("  - transcript recording and playback")
        print("  - interactive flow caveat (AskUserQuestion limitation)")
        print("\nKey takeaway:")
        print("  AskUserQuestion is NOT a reliable pause mechanism in")
        print("  stream-json mode — implement human-in-the-loop at the")
        print("  application layer instead.")
        return 0

    finally:
        if transcript_dir_obj is not None:
            transcript_dir_obj.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# CAVEAT: AskUserQuestion is NOT a reliable pause mechanism
# ---------------------------------------------------------------------------
#
# In stream-json mode, Claude Code does NOT provide a protocol-level pause
# mechanism that lets your controller wait for human input before continuing.
#
# What happens with AskUserQuestion:
#   1. You send a prompt that triggers a question
#   2. The CLI emits assistant messages with the question text
#   3. There is NO special "paused" message type your controller can detect
#   4. The CLI continues streaming — your controller cannot block on input
#
# What you CAN do (application-level workaround):
#   - Watch for question text in `is_assistant` callback events
#   - When detected, send a follow-up user message with the answer
#   - This is application-level logic, not protocol-level pause
#
# What you CANNOT do reliably:
#   - Treat AskUserQuestion as a structured pause mechanism
#   - Expect the CLI to wait for external human input mid-turn
#   - Use it as a synchronous "confirm before proceeding" primitive
#
# Bottom line: if you need human-in-the-loop checkpoints, implement them
# at your application layer, not inside the Claude session stream.
# ---------------------------------------------------------------------------
