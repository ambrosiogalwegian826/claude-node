import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from test_helpers import DummyThread, FakePipe, FakeProcess, make_assistant_line, make_init_line, make_result_line, make_tool_result_line

pytestmark = pytest.mark.unit


class TestControllerInitAndProperties:
    def test_builds_base_command(self, make_controller):
        ctrl = make_controller()
        assert ctrl._cmd[:5] == [
            "claude",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
        ]
        assert "--verbose" in ctrl._cmd

    def test_builds_optional_command_flags(self, make_controller):
        ctrl = make_controller(
            system_prompt="sys",
            append_system_prompt="append",
            tools=["Read", "Write"],
            allowed_tools=["Read"],
            disallowed_tools=["Bash"],
            permission_mode="acceptEdits",
            bare=True,
            resume="sess-1",
            model="sonnet",
            cwd="/tmp",
            add_dirs=["/a", "/b"],
        )
        cmd = ctrl._cmd
        assert ["--system-prompt", "sys"] == cmd[cmd.index("--system-prompt"):cmd.index("--system-prompt") + 2]
        assert ["--append-system-prompt", "append"] == cmd[cmd.index("--append-system-prompt"):cmd.index("--append-system-prompt") + 2]
        assert ["--tools", "Read,Write"] == cmd[cmd.index("--tools"):cmd.index("--tools") + 2]
        assert ["--allowedTools", "Read"] == cmd[cmd.index("--allowedTools"):cmd.index("--allowedTools") + 2]
        assert ["--disallowedTools", "Bash"] == cmd[cmd.index("--disallowedTools"):cmd.index("--disallowedTools") + 2]
        assert ["--permission-mode", "acceptEdits"] == cmd[cmd.index("--permission-mode"):cmd.index("--permission-mode") + 2]
        assert ["--model", "sonnet"] == cmd[cmd.index("--model"):cmd.index("--model") + 2]
        assert ["--resume", "sess-1"] == cmd[cmd.index("--resume"):cmd.index("--resume") + 2]
        assert "--bare" in cmd
        add_dir_positions = [i for i, token in enumerate(cmd) if token == "--add-dir"]
        assert len(add_dir_positions) == 2
        assert cmd[add_dir_positions[0] + 1] == "/a"
        assert cmd[add_dir_positions[1] + 1] == "/b"
        assert ctrl.cwd == "/tmp"

    def test_continue_used_only_without_resume(self, make_controller):
        ctrl = make_controller(continue_session=True)
        assert "--continue" in ctrl._cmd
        ctrl2 = make_controller(resume="sess-2", continue_session=True)
        assert "--continue" not in ctrl2._cmd
        assert "--resume" in ctrl2._cmd

    def test_ctrl_kwargs_store_replayable_config(self, make_controller):
        cb = lambda msg: None
        ctrl = make_controller(
            system_prompt="sys",
            append_system_prompt="append",
            tools=["Read"],
            allowed_tools=["Read"],
            disallowed_tools=["Bash"],
            permission_mode="acceptEdits",
            bare=True,
            model="sonnet",
            cwd="/tmp",
            add_dirs=["/a"],
            on_message=cb,
        )
        assert ctrl._ctrl_kwargs["system_prompt"] == "sys"
        assert ctrl._ctrl_kwargs["disallowed_tools"] == ["Bash"]
        assert ctrl._ctrl_kwargs["on_message"] is cb
        assert "resume" not in ctrl._ctrl_kwargs
        assert "continue_session" not in ctrl._ctrl_kwargs

    def test_pid_alive_session_and_repr(self, live_controller):
        live_controller._session_id = "abcdef123456"
        assert live_controller.pid == 12345
        assert live_controller.alive is True
        assert live_controller.session_id == "abcdef123456"
        text = repr(live_controller)
        assert "alive" in text
        assert "abcdef12" in text

    def test_repr_when_stopped(self, make_controller):
        ctrl = make_controller()
        assert ctrl.pid is None
        assert ctrl.alive is False
        text = repr(ctrl)
        assert "stopped" in text


class TestControllerStartStopAndContextManager:
    def test_start_success_starts_threads_and_process(self, make_controller, tmp_path):
        ctrl = make_controller(transcript_path=str(tmp_path / "events.jsonl"))
        proc = FakeProcess()
        threads = []

        def thread_factory(*args, **kwargs):
            t = DummyThread(*args, **kwargs)
            threads.append(t)
            return t

        with patch("claude_node.controller.check_claude_available") as mock_check, \
             patch("claude_node.controller.subprocess.Popen", return_value=proc) as mock_popen, \
             patch("claude_node.controller.threading.Thread", side_effect=thread_factory):
            assert ctrl.start() is True

        mock_check.assert_called_once_with()
        mock_popen.assert_called_once()
        assert len(threads) == 2
        assert all(t.started for t in threads)
        assert ctrl._transcript_file is not None
        ctrl.stop()

    def test_start_returns_false_if_process_exits_immediately(self, make_controller):
        ctrl = make_controller()
        proc = FakeProcess(poll_value=1)
        with patch("claude_node.controller.check_claude_available"), \
             patch("claude_node.controller.subprocess.Popen", return_value=proc), \
             patch("claude_node.controller.threading.Thread", side_effect=DummyThread):
            assert ctrl.start() is False

    def test_start_waits_for_init_when_requested(self, make_controller):
        ctrl = make_controller()
        proc = FakeProcess()
        with patch("claude_node.controller.check_claude_available"), \
             patch("claude_node.controller.subprocess.Popen", return_value=proc), \
             patch("claude_node.controller.threading.Thread", side_effect=DummyThread), \
             patch.object(ctrl, "_wait_for_init", return_value=True) as mock_wait:
            assert ctrl.start(wait_init_timeout=1.5) is True
        mock_wait.assert_called_once_with(1.5)

    def test_stop_terminates_then_waits(self, live_controller):
        live_controller.stop(timeout=2.0)
        assert live_controller._proc.terminated is True
        assert live_controller._proc.wait_calls == [2.0]

    def test_stop_kills_after_timeout(self, live_controller):
        live_controller._proc.raise_timeout_once = True
        live_controller.stop(timeout=0.1)
        assert live_controller._proc.killed is True
        assert live_controller._proc.wait_calls == [0.1, None]

    def test_stop_closes_transcript_file(self, make_controller, tmp_path):
        path = tmp_path / "events.jsonl"
        ctrl = make_controller(transcript_path=str(path))
        ctrl._proc = FakeProcess()
        ctrl._transcript_file = path.open("a", encoding="utf-8")
        ctrl.stop()
        assert ctrl._transcript_file is None

    def test_context_manager_starts_and_stops(self, make_controller):
        ctrl = make_controller()
        with patch.object(ctrl, "start", return_value=True) as mock_start, \
             patch.object(ctrl, "stop") as mock_stop:
            with ctrl as entered:
                assert entered is ctrl
            mock_start.assert_called_once_with()
            mock_stop.assert_called_once_with()


class TestControllerSendAndWaitBehavior:
    def test_send_writes_json_message_and_returns_result(self, live_controller):
        result_msg = json.loads(make_result_line(result="hello", session_id="sess-9"))
        with patch.object(live_controller, "_wait_result", return_value=live_controller._parse(json.dumps(result_msg))):
            result = live_controller.send("你好")
        payload = json.loads(live_controller._proc.stdin.writes[0])
        assert payload["type"] == "user"
        assert payload["message"]["content"][0]["text"] == "你好"
        assert live_controller._proc.stdin.flushed is True
        assert result.result_text == "hello"

    def test_send_raises_runtime_error_when_not_alive(self, make_controller):
        ctrl = make_controller()
        with pytest.raises(RuntimeError, match="not running"):
            ctrl.send("x")

    def test_send_conflict_when_lock_already_held(self, live_controller):
        from claude_node.exceptions import ClaudeSendConflictError

        live_controller._send_lock.acquire()
        try:
            with pytest.raises(ClaudeSendConflictError):
                live_controller.send("x")
        finally:
            live_controller._send_lock.release()

    def test_send_nowait_conflict_when_lock_already_held(self, live_controller):
        from claude_node.exceptions import ClaudeSendConflictError

        live_controller._send_lock.acquire()
        try:
            with pytest.raises(ClaudeSendConflictError):
                live_controller.send_nowait("x")
        finally:
            live_controller._send_lock.release()

    def test_send_nowait_then_wait_for_result_releases_lock(self, live_controller):
        msg = live_controller._parse(make_result_line(result="done", session_id="sess-2"))
        with patch.object(live_controller, "_wait_result", return_value=msg):
            live_controller.send_nowait("hello")
            assert live_controller._send_lock.acquire(blocking=False) is False
            result = live_controller.wait_for_result(timeout=1.0, start_index=0)
            assert result.result_text == "done"
            assert live_controller._send_lock.acquire(blocking=False) is True
            live_controller._send_lock.release()

    def test_wait_for_result_releases_lock_on_exception(self, live_controller):
        live_controller.send_nowait("hello")
        with patch.object(live_controller, "_wait_result", side_effect=ValueError("boom")):
            with pytest.raises(ValueError, match="boom"):
                live_controller.wait_for_result(timeout=1.0)
        assert live_controller._send_lock.acquire(blocking=False) is True
        live_controller._send_lock.release()

    def test_wait_for_result_releases_lock_on_timeout_none(self, live_controller):
        live_controller.send_nowait("hello")
        with patch.object(live_controller, "_wait_result", return_value=None):
            assert live_controller.wait_for_result(timeout=0.01) is None
        assert live_controller._send_lock.acquire(blocking=False) is True
        live_controller._send_lock.release()

    def test_wait_for_result_returns_first_result_and_sets_session(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.extend([
            make_assistant_line([{"type": "text", "text": "thinking"}]),
            make_result_line(result="done", session_id="sess-55"),
        ])
        msg = ctrl._wait_result(start_index=0, timeout=0.01)
        assert msg.result_text == "done"
        assert ctrl.session_id == "sess-55"

    def test_wait_result_returns_none_on_timeout(self, make_controller):
        ctrl = make_controller()
        assert ctrl._wait_result(start_index=0, timeout=0.01) is None

    def test_wait_for_init_sets_session(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.append(make_init_line(session_id="sess-init"))
        assert ctrl._wait_for_init(timeout=0.01) is True
        assert ctrl.session_id == "sess-init"

    def test_wait_for_init_returns_false_on_timeout(self, make_controller):
        ctrl = make_controller()
        assert ctrl._wait_for_init(timeout=0.01) is False

    def test_wait_for_tool_use_returns_matching_call(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.append(make_assistant_line([
            {"type": "tool_use", "name": "Read", "input": {"path": "a"}},
            {"type": "tool_use", "name": "Bash", "input": {"cmd": "ls"}},
        ]))
        call = ctrl.wait_for_tool_use("Bash", timeout=0.01)
        assert call["name"] == "Bash"

    def test_wait_for_tool_use_returns_none_on_timeout(self, make_controller):
        ctrl = make_controller()
        assert ctrl.wait_for_tool_use("Read", timeout=0.01) is None


class TestControllerMessageCollectionAndParsing:
    def test_parse_valid_json_message(self, controller_cls):
        msg = controller_cls._parse(make_result_line(result="ok"))
        assert msg is not None
        assert msg.is_result is True

    def test_parse_invalid_json_returns_none(self, controller_cls):
        assert controller_cls._parse("not-json") is None

    def test_get_messages_parses_only_valid_lines(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.extend([
            make_init_line(),
            "not-json",
            make_result_line(),
        ])
        msgs = ctrl.get_messages()
        assert len(msgs) == 2
        assert msgs[0].is_init
        assert msgs[1].is_result

    def test_get_init_message_and_available_tools_and_skills(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.append(make_init_line(session_id="s1", tools=["Read"], slash_commands=["/memory", "/brainstorm"]))
        init = ctrl.get_init_message()
        assert init is not None and init.is_init
        assert ctrl.get_available_tools() == ["Read"]
        assert ctrl.get_available_skills() == ["/memory", "/brainstorm"]

    def test_get_init_message_none_when_absent(self, make_controller):
        ctrl = make_controller()
        assert ctrl.get_init_message() is None
        assert ctrl.get_available_tools() == []
        assert ctrl.get_available_skills() == []

    def test_get_stderr_returns_copy(self, make_controller):
        ctrl = make_controller()
        ctrl._err_buf.extend(["a", "b"])
        out = ctrl.get_stderr()
        assert out == ["a", "b"]
        out.append("c")
        assert ctrl._err_buf == ["a", "b"]

    def test_get_tool_errors_filters_failed_tool_results(self, make_controller):
        ctrl = make_controller()
        ctrl._out_buf.extend([
            make_tool_result_line([
                {"type": "tool_result", "tool_use_id": "1", "is_error": False, "content": "ok"}
            ]),
            make_tool_result_line([
                {"type": "tool_result", "tool_use_id": "2", "is_error": True, "content": "bad"}
            ]),
        ])
        errs = ctrl.get_tool_errors(0)
        assert errs == [{"type": "tool_result", "tool_use_id": "2", "is_error": True, "content": "bad"}]

    def test_send_checked_returns_result_and_tool_errors(self, live_controller):
        result_msg = live_controller._parse(make_result_line(result="done"))

        def _send_side_effect(text, timeout=60.0):
            live_controller._out_buf.append(make_tool_result_line([
                {"type": "tool_result", "tool_use_id": "2", "is_error": True, "content": "bad"}
            ]))
            return result_msg

        with patch.object(live_controller, "send", side_effect=_send_side_effect) as mock_send:
            result, errs = live_controller.send_checked("task", timeout=3.0)
        mock_send.assert_called_once_with("task", timeout=3.0)
        assert result.result_text == "done"
        assert errs == [{"type": "tool_result", "tool_use_id": "2", "is_error": True, "content": "bad"}]


class TestControllerReaderAndTranscript:
    def test_reader_appends_stdout_and_calls_callback(self, make_controller):
        seen = []
        ctrl = make_controller(on_message=seen.append)
        proc = FakeProcess(stdout_lines=[make_result_line(result="hello") + "\n", ""])
        ctrl._proc = proc
        ctrl._reader(proc.stdout, ctrl._out_buf)
        assert ctrl._out_buf == [make_result_line(result="hello")]
        assert len(seen) == 1
        assert seen[0].result_text == "hello"

    def test_reader_appends_stderr_without_callback(self, make_controller):
        ctrl = make_controller(on_message=lambda msg: (_ for _ in ()).throw(RuntimeError("boom")))
        proc = FakeProcess(stderr_lines=["warn\n", ""])
        ctrl._proc = proc
        ctrl._reader(proc.stderr, ctrl._err_buf)
        assert ctrl._err_buf == ["warn"]

    def test_reader_skips_blank_lines(self, make_controller):
        ctrl = make_controller()
        proc = FakeProcess(stdout_lines=["\n", make_result_line(result="x") + "\n", ""])
        ctrl._proc = proc
        ctrl._reader(proc.stdout, ctrl._out_buf)
        assert len(ctrl._out_buf) == 1

    def test_reader_writes_stdout_to_transcript_only(self, make_controller, tmp_path):
        path = tmp_path / "events.jsonl"
        ctrl = make_controller(transcript_path=str(path))
        ctrl._transcript_file = path.open("a", encoding="utf-8")
        proc = FakeProcess(stdout_lines=[make_result_line(result="ok") + "\n", ""], stderr_lines=["warn\n", ""])
        ctrl._proc = proc
        ctrl._reader(proc.stdout, ctrl._out_buf)
        ctrl._reader(proc.stderr, ctrl._err_buf)
        ctrl._transcript_file.close()
        assert path.read_text(encoding="utf-8").splitlines() == [make_result_line(result="ok")]


class TestControllerFork:
    def test_fork_requires_session(self, make_controller):
        ctrl = make_controller()
        with pytest.raises(RuntimeError, match="session_id"):
            ctrl.fork()

    def test_fork_returns_new_controller_with_resume_and_same_config(self, make_controller):
        cb = lambda msg: None
        ctrl = make_controller(
            system_prompt="sys",
            append_system_prompt="append",
            tools=["Read"],
            allowed_tools=["Read"],
            disallowed_tools=["Bash"],
            permission_mode="acceptEdits",
            bare=True,
            model="sonnet",
            cwd="/tmp",
            add_dirs=["/repo"],
            on_message=cb,
        )
        ctrl._session_id = "sess-fork"
        forked = ctrl.fork()
        assert forked is not ctrl
        assert "--resume" in forked._cmd
        assert forked._cmd[forked._cmd.index("--resume") + 1] == "sess-fork"
        assert forked._proc is None
        assert forked._ctrl_kwargs["system_prompt"] == "sys"
        assert forked._ctrl_kwargs["disallowed_tools"] == ["Bash"]
        assert forked._ctrl_kwargs["on_message"] is cb
