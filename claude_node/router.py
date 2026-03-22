#!/usr/bin/env python3
"""
多 Agent 消息路由器
管理多个 Claude CLI 进程的生命周期和消息路由
"""

from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from .controller import ClaudeController, ClaudeMessage


class AgentNode:
    """单个 Agent 节点配置"""
    def __init__(
        self,
        name: str,
        system_prompt: str = "",
        append_system_prompt: str = "",
        tools: list[str] = None,
        allowed_tools: list[str] = None,
        disallowed_tools: list[str] = None,
        skip_permissions: bool = True,
        bare: bool = False,
        cwd: str = None,
        on_message: Callable[[ClaudeMessage], None] = None,
    ):
        self.name = name
        self._ctrl_kwargs = dict(
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            tools=tools,
            allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools,
            skip_permissions=skip_permissions,
            bare=bare,  # 见 ClaudeController 注释：OAuth 用户应使用 tools=[...] 替代
            cwd=cwd,
            on_message=on_message,
        )
        self.ctrl: Optional[ClaudeController] = None

    def start(self) -> bool:
        self.ctrl = ClaudeController(**self._ctrl_kwargs)
        return self.ctrl.start()

    def stop(self):
        if self.ctrl:
            self.ctrl.stop()

    @property
    def alive(self) -> bool:
        return self.ctrl is not None and self.ctrl.alive

    def send(self, text: str, timeout: float = 60) -> Optional[str]:
        if not self.ctrl:
            raise RuntimeError(f"Agent '{self.name}' not started")
        result = self.ctrl.send(text, timeout=timeout)
        return result.result_text if result else None


class MultiAgentRouter:
    """
    多 Agent 消息路由器

    用法：
        router = MultiAgentRouter()
        router.add(AgentNode("PM", system_prompt="你是产品经理"))
        router.add(AgentNode("DEV", system_prompt="你是工程师"))
        router.start_all()

        # 直接发消息
        resp = router.send("PM", "提出需求")

        # A2A 路由
        resp = router.route("PM", resp, "DEV", wrap="PM说：{message}\n你怎么看？")

        router.stop_all()

    或使用 context manager：
        with MultiAgentRouter() as router:
            router.add(AgentNode("PM", ...))
            router.add(AgentNode("DEV", ...))
            router.start_all()
            ...
    """

    def __init__(self):
        self._nodes: dict[str, AgentNode] = {}

    def add(self, node: AgentNode) -> "MultiAgentRouter":
        """添加 Agent 节点（链式调用）"""
        self._nodes[node.name] = node
        return self

    def start_all(self, parallel: bool = True):
        """启动所有 Agent"""
        if parallel:
            def start_one(node):
                ok = node.start()
                return node.name, ok

            with ThreadPoolExecutor(max_workers=len(self._nodes)) as ex:
                futures = {ex.submit(start_one, n): n for n in self._nodes.values()}
                for f in as_completed(futures):
                    name, ok = f.result()
                    if not ok:
                        raise RuntimeError(f"Failed to start agent '{name}'")
        else:
            for node in self._nodes.values():
                if not node.start():
                    raise RuntimeError(f"Failed to start agent '{node.name}'")

    def stop_all(self):
        """停止所有 Agent"""
        for node in self._nodes.values():
            node.stop()
        self._nodes.clear()

    def send(self, agent_name: str, message: str, timeout: float = 60) -> Optional[str]:
        """向指定 Agent 发消息，返回 result text"""
        node = self._get(agent_name)
        return node.send(message, timeout=timeout)

    def route(
        self,
        message: str,
        to: str,
        wrap: str = "{message}",
        timeout: float = 60,
    ) -> Optional[str]:
        """
        把消息路由到目标 Agent。

        wrap 是包装模板，{message} 会被替换为实际消息内容。

        示例：
            router.route(pm_reply, to="DEV", wrap="PM说：{message}\n你的技术意见？")
        """
        wrapped = wrap.format(message=message)
        return self.send(to, wrapped, timeout=timeout)

    def parallel_send(
        self,
        message: str,
        agent_names: list[str],
        timeout: float = 90,
    ) -> dict[str, str]:
        """
        向多个 Agent 并行发送相同消息，返回 {agent_name: result_text}。
        """
        results = {}

        def send_one(name):
            r = self.send(name, message, timeout=timeout)
            return name, r or ""

        with ThreadPoolExecutor(max_workers=len(agent_names)) as ex:
            futures = [ex.submit(send_one, n) for n in agent_names]
            for f in as_completed(futures):
                name, result = f.result()
                results[name] = result

        return results

    def get_ctrl(self, agent_name: str) -> ClaudeController:
        """获取指定 Agent 的 Controller（用于高级操作）"""
        return self._get(agent_name).ctrl

    def _get(self, name: str) -> AgentNode:
        node = self._nodes.get(name)
        if not node:
            raise ValueError(f"Agent '{name}' not found. Available: {list(self._nodes)}")
        if not node.alive:
            raise RuntimeError(f"Agent '{name}' is not running")
        return node

    def __enter__(self) -> "MultiAgentRouter":
        return self

    def __exit__(self, *args):
        self.stop_all()
