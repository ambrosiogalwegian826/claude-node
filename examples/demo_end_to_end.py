#!/usr/bin/env python3
"""
End-to-end demo for claude-node.

This example is designed as a reference implementation. It shows how to:
- check runtime availability
- start and observe a Claude session
- use async send + wait_for_result
- use send_checked
- fork a session
- use MultiAgentRouter for lightweight parallel review
- record and summarize a JSONL transcript
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

# Support running directly from the repository root without requiring install -e .
# If the package is already installed, the normal import path will work.
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


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="claude-node end-to-end capability demo"
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Repository path to analyze (default: current working directory)",
    )
    parser.add_argument(
        "--repo",
        dest="repo_flag",
        default=None,
        help="Repository path to analyze (overrides positional repo if both are set)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional Claude model name to pass to ClaudeController",
    )
    parser.add_argument(
        "--verbose-events",
        action="store_true",
        help="Print more callback event details",
    )
    parser.add_argument(
        "--transcript",
        default=None,
        help="Optional transcript JSONL output path; if omitted, a temp file is used",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Start controller in bare mode (fewer built-in capabilities, faster startup)",
    )

    perm_group = parser.add_mutually_exclusive_group()
    perm_group.add_argument(
        "--skip-permissions",
        dest="skip_permissions",
        action="store_true",
        default=True,
        help="Skip interactive permission checks (default)",
    )
    perm_group.add_argument(
        "--require-permissions",
        dest="skip_permissions",
        action="store_false",
        help="Do not skip permission checks",
    )

    return parser.parse_args(list(argv))


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


def short_session_id(session_id: str | None) -> str:
    if not session_id:
        return "<none>"
    return session_id[:12]


def print_result_block(title: str, text: str | None) -> None:
    print(f"\n[{title}]")
    print((text or "<no result>").strip())


def normalize_result(obj: Any) -> str:
    if obj is None:
        return "<no result>"
    if hasattr(obj, "result_text"):
        return getattr(obj, "result_text") or "<no result>"
    if isinstance(obj, str):
        return obj
    return str(obj)


# ---------------------------------------------------------------------------
# Event callback
# ---------------------------------------------------------------------------


def make_event_callback(verbose: bool = False):
    def on_message(msg) -> None:
        if msg.is_init:
            print(f"[event:init] session_id={short_session_id(msg.session_id)}")
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
            if verbose:
                print(f"[event:result:text] {compact(msg.result_text, 140)}")
            return

        if verbose:
            print(
                f"[event:{msg.type}:{msg.subtype or 'none'}] "
                f"{compact(str(msg.raw), 140)}"
            )

    return on_message


# ---------------------------------------------------------------------------
# Transcript summary
# ---------------------------------------------------------------------------


def summarize_transcript(path: Path, max_preview: int = 8) -> None:
    h1("Phase 6: Transcript Summary")

    if not path.exists():
        print(f"Transcript file not found: {path}")
        return

    counts: Counter[str] = Counter()
    preview: list[str] = []
    total_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            total_lines += 1
            line = raw_line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                counts["invalid_json"] += 1
                continue

            msg_type = obj.get("type", "unknown")
            subtype = obj.get("subtype")
            key = f"{msg_type}:{subtype}" if subtype else msg_type
            counts[key] += 1

            if len(preview) < max_preview:
                preview.append(key)

    print(f"Transcript path: {path}")
    print(f"Total lines:      {total_lines}")
    print("Message counts:")
    for key, value in sorted(counts.items()):
        print(f"  - {key}: {value}")

    print("Preview:")
    for item in preview:
        print(f"  - {item}")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


REPO_SCAN_PROMPT = """
Scan the current repository and provide:

1. A concise module structure overview
2. The main public APIs and what each one is for
3. The most obvious engineering risk or limitation
4. One sentence describing how this project should be positioned as an open-source library

Keep the answer structured and practical.
""".strip()

CHECKED_SEND_PROMPT = """
Based on the current repository, provide a minimal pre-release checklist for an alpha open-source release.

Also mention whether you observed any signs of tool failure, permission limitations,
or missing implementation details during your analysis.
""".strip()

MAIN_BRANCH_PROMPT = """
Assume the goal is: ship the fastest credible alpha open-source release.

Give:
1. the shortest path to launch,
2. the 3 highest-leverage fixes,
3. the biggest thing we should deliberately not do yet.
""".strip()

FORK_BRANCH_PROMPT = """
Assume the goal is: turn this into a stable long-term infrastructure library over 6 months.

Give:
1. the architectural priorities,
2. the engineering risks to remove,
3. the capability areas to delay until later.
""".strip()

ROUTER_QUESTION = """
Give exactly 3 bullets on the current state of this project:
- one strength,
- one weakness,
- one recommendation.
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


def phase1_main_controller(
    repo_path: Path,
    model: str | None,
    transcript_path: Path,
    verbose_events: bool,
    bare: bool,
    skip_permissions: bool,
) -> ClaudeController:
    h1("Phase 1: Main Controller + Callback + Transcript")

    # Show constructor inputs
    constructor_args = {
        "cwd": str(repo_path),
        "model": model,
        "bare": bare,
        "skip_permissions": skip_permissions,
        "on_message": "<callback>",
        "transcript_path": str(transcript_path),
    }
    input_summary = "\n".join(f"  {k}={v!r}" for k, v in constructor_args.items())

    callback = make_event_callback(verbose=verbose_events)

    ctrl = ClaudeController(
        cwd=str(repo_path),
        model=model,
        bare=bare,
        skip_permissions=skip_permissions,
        on_message=callback,
        transcript_path=str(transcript_path),
    )

    started = ctrl.start()
    if not started:
        raise RuntimeError("ClaudeController.start() returned False")

    show_io(
        "Phase 1 Result",
        "ClaudeController constructor + start()",
        input_summary,
        "ctrl.session_id / ctrl.alive / ctrl.pid",
        f"session_id={short_session_id(ctrl.session_id)}, alive={ctrl.alive}, pid={ctrl.pid}",
    )
    return ctrl


def phase2_async_repo_scan(ctrl: ClaudeController) -> Any:
    h1("Phase 2: Async Repository Scan")

    ctrl.send_nowait(REPO_SCAN_PROMPT)
    result = ctrl.wait_for_result(timeout=120)

    if result is None:
        raise RuntimeError("No result returned from async repository scan")

    show_io(
        "Phase 2 Result",
        "send_nowait() + wait_for_result()",
        REPO_SCAN_PROMPT,
        "result.result_text",
        result.result_text,
    )
    print(f"\nSession ID: {short_session_id(result.session_id)}")
    print(f"Transcript: {ctrl.get_transcript_path()}")
    return result


def phase3_checked_send(ctrl: ClaudeController) -> tuple[Any, list[dict]]:
    h1("Phase 3: Checked Send")

    result, tool_errors = ctrl.send_checked(CHECKED_SEND_PROMPT, timeout=120)

    show_io(
        "Phase 3 Result",
        "send_checked()",
        CHECKED_SEND_PROMPT,
        "result.result_text",
        result.result_text if result is not None else None,
    )
    print(f"\nTool errors: {len(tool_errors)}")

    if tool_errors:
        print("Tool error summary:")
        for idx, err in enumerate(tool_errors[:5], 1):
            print(f"  {idx}. {compact(str(err), 160)}")

    return result, tool_errors


def phase4_fork_comparison(ctrl: ClaudeController) -> tuple[Any, Any]:
    h1("Phase 4: Fork Comparison")
    forked = ctrl.fork()

    started = forked.start()
    if not started:
        raise RuntimeError("Forked ClaudeController failed to start")

    try:
        main_result = ctrl.send(MAIN_BRANCH_PROMPT, timeout=120)
        fork_result = forked.send(FORK_BRANCH_PROMPT, timeout=120)
    finally:
        forked.stop()

    show_io(
        "Phase 4 — Main Branch (ctrl.send())",
        "ctrl.send()",
        MAIN_BRANCH_PROMPT,
        "main_result",
        normalize_result(main_result),
    )
    show_io(
        "Phase 4 — Fork Branch (forked.send())",
        "forked.send()  [fork of same session]",
        FORK_BRANCH_PROMPT,
        "fork_result",
        normalize_result(fork_result),
    )
    return main_result, fork_result


def phase5_router_demo(
    repo_path: Path,
    model: str | None,
    bare: bool,
    skip_permissions: bool,
) -> None:
    h1("Phase 5: Router Demo")

    router = MultiAgentRouter()
    router.add(
        AgentNode(
            "pm",
            system_prompt=(
                "You are a pragmatic open-source PM. Focus on positioning, scope, and launch readiness."
            ),
            cwd=str(repo_path),
            skip_permissions=skip_permissions,
            bare=bare,
        )
    )
    router.add(
        AgentNode(
            "reviewer",
            system_prompt=(
                "You are a strict engineering reviewer. Focus on correctness, maintainability, and risk."
            ),
            cwd=str(repo_path),
            skip_permissions=skip_permissions,
            bare=bare,
        )
    )

    try:
        router.start_all()

        parallel = router.parallel_send(ROUTER_QUESTION, ["pm", "reviewer"])
        pm_out = normalize_result(parallel.get("pm"))
        reviewer_out = normalize_result(parallel.get("reviewer"))

        show_io(
            "Phase 5 — PM Agent (parallel_send)",
            "router.parallel_send(question, ['pm', 'reviewer'])",
            ROUTER_QUESTION,
            "PM output",
            pm_out,
        )
        show_io(
            "Phase 5 — Reviewer Agent (parallel_send)",
            "router.parallel_send(question, ['pm', 'reviewer'])",
            ROUTER_QUESTION,
            "Reviewer output",
            reviewer_out,
        )

        routed = router.route(
            pm_out,
            "reviewer",
            (
                "Here is the PM's summary:\n\n"
                "{message}\n\n"
                "In 1-2 paragraphs, critique it as an engineering reviewer."
            ),
        )
        show_io(
            "Phase 5 — Reviewer critiques PM (route)",
            "router.route(pm_out, 'reviewer', wrap_template)",
            pm_out,
            "Reviewer critique",
            normalize_result(routed),
        )
    finally:
        router.stop_all()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_raw = args.repo_flag or args.repo or os.getcwd()
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
            print("\nPlease install Claude Code / Claude CLI and ensure `claude` is in PATH.")
            return 1

        if args.transcript:
            transcript_path = Path(args.transcript).resolve()
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            transcript_dir_obj = tempfile.TemporaryDirectory(prefix="claude-node-demo-")
            transcript_path = Path(transcript_dir_obj.name) / "main-session.jsonl"

        ctrl = phase1_main_controller(
            repo_path=repo_path,
            model=args.model,
            transcript_path=transcript_path,
            verbose_events=args.verbose_events,
            bare=args.bare,
            skip_permissions=args.skip_permissions,
        )

        try:
            phase2_async_repo_scan(ctrl)
            phase3_checked_send(ctrl)
            phase4_fork_comparison(ctrl)
        finally:
            ctrl.stop()

        phase5_router_demo(
            repo_path=repo_path,
            model=args.model,
            bare=args.bare,
            skip_permissions=args.skip_permissions,
        )

        summarize_transcript(transcript_path)

        h1("Demo Complete")
        print("This demo exercised:")
        print("  - runtime discovery")
        print("  - controller lifecycle")
        print("  - callbacks")
        print("  - async send + wait_for_result")
        print("  - send_checked")
        print("  - fork")
        print("  - lightweight router patterns")
        print("  - transcript JSONL export + summary")
        return 0

    finally:
        if transcript_dir_obj is not None:
            transcript_dir_obj.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())