import pytest

pytestmark = pytest.mark.unit


class TestPackageExports:
    def test_top_level_exports_exist(self):
        import claude_node
        assert hasattr(claude_node, "ClaudeController")
        assert hasattr(claude_node, "ClaudeMessage")
        assert hasattr(claude_node, "MultiAgentRouter")
        assert hasattr(claude_node, "AgentNode")
        assert hasattr(claude_node, "ClaudeError")
        assert hasattr(claude_node, "ClaudeBinaryNotFound")
        assert hasattr(claude_node, "ClaudeStartupError")
        assert hasattr(claude_node, "ClaudeTimeoutError")
        assert hasattr(claude_node, "ClaudeSendConflictError")
        assert "ClaudeController" in claude_node.__all__


class TestExceptionHierarchy:
    def test_base_error_inherits_runtime_error(self):
        from claude_node.exceptions import ClaudeError
        assert issubclass(ClaudeError, RuntimeError)

    @pytest.mark.parametrize(
        "name",
        [
            "ClaudeBinaryNotFound",
            "ClaudeStartupError",
            "ClaudeTimeoutError",
            "ClaudeSendConflictError",
        ],
    )
    def test_specific_errors_inherit_claude_error(self, name):
        import claude_node.exceptions as exc
        cls = getattr(exc, name)
        assert issubclass(cls, exc.ClaudeError)
        assert issubclass(cls, RuntimeError)

    @pytest.mark.parametrize(
        "exc_cls,message",
        [
            ("ClaudeBinaryNotFound", "claude missing"),
            ("ClaudeStartupError", "startup failed"),
            ("ClaudeTimeoutError", "timed out"),
            ("ClaudeSendConflictError", "send in flight"),
        ],
    )
    def test_specific_errors_are_raisable(self, exc_cls, message):
        import claude_node.exceptions as exc
        with pytest.raises(getattr(exc, exc_cls), match=message):
            raise getattr(exc, exc_cls)(message)
