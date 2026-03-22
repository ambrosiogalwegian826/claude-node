import json

import pytest

from test_helpers import make_assistant_line, make_init_line, make_result_line, make_tool_result_line

pytestmark = pytest.mark.unit


class TestClaudeMessageTypePredicates:
    def test_init_message_properties(self, message_cls):
        raw = json.loads(make_init_line(session_id="abc123"))
        msg = message_cls(type=raw["type"], subtype=raw["subtype"], raw=raw)
        assert msg.is_init is True
        assert msg.is_result is False
        assert msg.is_assistant is False
        assert msg.is_task_event is False
        assert msg.session_id == "abc123"

    def test_result_success_properties(self, message_cls):
        raw = json.loads(make_result_line(result="done", subtype="success"))
        msg = message_cls(type=raw["type"], subtype=raw["subtype"], raw=raw)
        assert msg.is_result is True
        assert msg.is_result_ok is True
        assert msg.is_result_error is False
        assert msg.truly_succeeded is True
        assert msg.result_text == "done"
        assert msg.cost_usd == 0.1
        assert msg.num_turns == 1

    def test_result_error_properties(self, message_cls):
        raw = json.loads(make_result_line(result="bad", subtype="error"))
        msg = message_cls(type=raw["type"], subtype=raw["subtype"], raw=raw)
        assert msg.is_result is True
        assert msg.is_result_ok is False
        assert msg.is_result_error is True
        assert msg.truly_succeeded is False

    @pytest.mark.parametrize(
        "text",
        [
            "API Error: rate limit",
            "Not logged in to Claude",
            "Rate limit exceeded",
            "Error: unknown",
            "Authentication failed",
        ],
    )
    def test_api_error_prefixes_detected(self, message_cls, text):
        raw = json.loads(make_result_line(result=text, subtype="success"))
        msg = message_cls(type=raw["type"], subtype=raw["subtype"], raw=raw)
        assert msg.is_api_error is True
        assert msg.truly_succeeded is False

    def test_non_result_never_api_error(self, message_cls):
        raw = json.loads(make_init_line())
        msg = message_cls(type=raw["type"], subtype=raw["subtype"], raw=raw)
        assert msg.is_api_error is False

    def test_task_event_detected(self, message_cls):
        raw = {"type": "system", "subtype": "task_progress", "description": "working"}
        msg = message_cls(type="system", subtype="task_progress", raw=raw)
        assert msg.is_task_event is True


class TestClaudeMessageContentExtraction:
    def test_assistant_texts_and_tool_calls(self, message_cls):
        raw = json.loads(
            make_assistant_line(
                [
                    {"type": "text", "text": "hello"},
                    {"type": "tool_use", "name": "Read", "input": {"path": "x"}},
                    {"type": "text", "text": "world"},
                ]
            )
        )
        msg = message_cls(type="assistant", raw=raw)
        assert msg.is_assistant is True
        assert msg.assistant_texts == ["hello", "world"]
        assert msg.tool_calls == [{"type": "tool_use", "name": "Read", "input": {"path": "x"}}]
        assert msg.tool_results == []

    def test_tool_results_detected(self, message_cls):
        raw = json.loads(
            make_tool_result_line(
                [
                    {"type": "tool_result", "tool_use_id": "1", "content": "ok", "is_error": False},
                    {"type": "tool_result", "tool_use_id": "2", "content": "bad", "is_error": True},
                ]
            )
        )
        msg = message_cls(type="user", raw=raw)
        assert msg.is_tool_result is True
        assert len(msg.tool_results) == 2
        assert msg.assistant_texts == []
        assert msg.tool_calls == []

    def test_tool_result_false_for_non_list_content(self, message_cls):
        raw = {"type": "user", "message": {"content": "not-a-list"}}
        msg = message_cls(type="user", raw=raw)
        assert msg.is_tool_result is False
        assert msg.tool_results == []

    def test_assistant_texts_empty_for_non_assistant(self, message_cls):
        raw = json.loads(make_result_line())
        msg = message_cls(type="result", subtype="success", raw=raw)
        assert msg.assistant_texts == []
        assert msg.tool_calls == []

    def test_default_scalar_properties_when_missing(self, message_cls):
        msg = message_cls(type="assistant", raw={})
        assert msg.result_text == ""
        assert msg.session_id == ""
        assert msg.cost_usd == 0.0
        assert msg.num_turns == 0


class TestClaudeMessageRepr:
    def test_repr_for_init_contains_session_prefix(self, message_cls):
        raw = json.loads(make_init_line(session_id="abcdef123456"))
        msg = message_cls(type="system", subtype="init", raw=raw)
        text = repr(msg)
        assert "INIT" in text
        assert "abcdef12" in text

    def test_repr_for_result_contains_prefix(self, message_cls):
        raw = json.loads(make_result_line(result="hello there", subtype="success"))
        msg = message_cls(type="result", subtype="success", raw=raw)
        text = repr(msg)
        assert "RESULT" in text
        assert "hello there" in text

    def test_repr_for_assistant_with_text_and_tool(self, message_cls):
        raw = json.loads(make_assistant_line([
            {"type": "text", "text": "thinking"},
            {"type": "tool_use", "name": "Bash"},
        ]))
        msg = message_cls(type="assistant", raw=raw)
        text = repr(msg)
        assert "ASSISTANT" in text
        assert "text:" in text
        assert "tool:Bash" in text

    def test_repr_for_task_event(self, message_cls):
        msg = message_cls(type="system", subtype="task_started", raw={"description": "index repo"})
        assert "TASK/task_started" in repr(msg)

    def test_repr_for_fallback_case(self, message_cls):
        msg = message_cls(type="unknown", subtype="mystery", raw={})
        assert repr(msg) == "<ClaudeMessage unknown/mystery>"
