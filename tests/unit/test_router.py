from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestAgentNode:
    def test_agentnode_stores_controller_kwargs(self):
        from claude_node.router import AgentNode
        cb = lambda msg: None
        node = AgentNode(
            "DEV",
            system_prompt="sys",
            append_system_prompt="append",
            tools=["Read"],
            allowed_tools=["Read"],
            disallowed_tools=["Bash"],
            skip_permissions=False,
            bare=True,
            cwd="/tmp",
            on_message=cb,
        )
        assert node.name == "DEV"
        assert node._ctrl_kwargs["system_prompt"] == "sys"
        assert node._ctrl_kwargs["disallowed_tools"] == ["Bash"]
        assert node._ctrl_kwargs["on_message"] is cb
        assert node.ctrl is None

    def test_start_creates_controller_and_returns_bool(self):
        from claude_node.router import AgentNode
        node = AgentNode("DEV")
        fake_ctrl = MagicMock()
        fake_ctrl.start.return_value = True
        with patch("claude_node.router.ClaudeController", return_value=fake_ctrl) as mock_cls:
            assert node.start() is True
        mock_cls.assert_called_once_with(**node._ctrl_kwargs)
        assert node.ctrl is fake_ctrl

    def test_stop_delegates_to_controller(self):
        from claude_node.router import AgentNode
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.stop()
        node.ctrl.stop.assert_called_once_with()

    def test_alive_reflects_controller_state(self):
        from claude_node.router import AgentNode
        node = AgentNode("DEV")
        assert node.alive is False
        node.ctrl = MagicMock()
        node.ctrl.alive = True
        assert node.alive is True

    def test_send_requires_started_node(self):
        from claude_node.router import AgentNode
        node = AgentNode("DEV")
        with pytest.raises(RuntimeError, match="not started"):
            node.send("hello")

    def test_send_returns_result_text_or_none(self):
        from claude_node.router import AgentNode
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.ctrl.send.return_value = MagicMock(result_text="done")
        assert node.send("hello", timeout=3) == "done"
        node.ctrl.send.return_value = None
        assert node.send("hello") is None


class TestMultiAgentRouter:
    def test_add_is_chainable(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node = AgentNode("DEV")
        assert router.add(node) is router
        assert router._nodes["DEV"] is node

    def test_send_routes_to_agent(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.ctrl.alive = True
        node.send = MagicMock(return_value="done")
        router.add(node)
        assert router.send("DEV", "hello", timeout=2) == "done"
        node.send.assert_called_once_with("hello", timeout=2)

    def test_route_wraps_message(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.ctrl.alive = True
        node.send = MagicMock(return_value="ok")
        router.add(node)
        assert router.route("spec", to="DEV", wrap="PM says: {message}") == "ok"
        node.send.assert_called_once_with("PM says: spec", timeout=60)

    def test_parallel_send_collects_results(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        for name in ["A", "B"]:
            node = AgentNode(name)
            node.ctrl = MagicMock()
            node.ctrl.alive = True
            node.send = MagicMock(return_value=f"{name}-reply")
            router.add(node)
        result = router.parallel_send("hello", ["A", "B"], timeout=1)
        assert result == {"A": "A-reply", "B": "B-reply"}

    def test_get_ctrl_returns_controller(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.ctrl.alive = True
        router.add(node)
        assert router.get_ctrl("DEV") is node.ctrl

    def test_get_raises_for_missing_node(self):
        from claude_node.router import MultiAgentRouter
        router = MultiAgentRouter()
        with pytest.raises(ValueError, match="not found"):
            router._get("NOPE")

    def test_get_raises_for_not_running_node(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node = AgentNode("DEV")
        node.ctrl = MagicMock()
        node.ctrl.alive = False
        router.add(node)
        with pytest.raises(RuntimeError, match="not running"):
            router._get("DEV")

    def test_start_all_parallel_raises_on_failure(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node1 = AgentNode("A")
        node2 = AgentNode("B")
        node1.start = MagicMock(return_value=True)
        node2.start = MagicMock(return_value=False)
        router.add(node1).add(node2)
        with pytest.raises(RuntimeError, match="Failed to start agent 'B'"):
            router.start_all(parallel=True)

    def test_start_all_serial_raises_on_failure(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node1 = AgentNode("A")
        node1.start = MagicMock(return_value=False)
        router.add(node1)
        with pytest.raises(RuntimeError, match="Failed to start agent 'A'"):
            router.start_all(parallel=False)

    def test_stop_all_stops_and_clears_nodes(self):
        from claude_node.router import AgentNode, MultiAgentRouter
        router = MultiAgentRouter()
        node1 = AgentNode("A")
        node2 = AgentNode("B")
        node1.stop = MagicMock()
        node2.stop = MagicMock()
        router.add(node1).add(node2)
        router.stop_all()
        node1.stop.assert_called_once_with()
        node2.stop.assert_called_once_with()
        assert router._nodes == {}

    def test_context_manager_calls_stop_all(self):
        from claude_node.router import MultiAgentRouter
        router = MultiAgentRouter()
        with patch.object(router, "stop_all") as mock_stop:
            with router as entered:
                assert entered is router
            mock_stop.assert_called_once_with()
