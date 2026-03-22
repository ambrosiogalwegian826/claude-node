"""
claude-node — Claude CLI subprocess controller for multi-agent systems

A minimal, well-documented Python library for building Claude-powered agent
systems using the CLI's stream-json persistent mode. No SDK dependency.

Core classes:
    ClaudeController  — manage a single Claude CLI subprocess
    ClaudeMessage     — parsed message from Claude stdout
    MultiAgentRouter  — manage and route between multiple agents

Quick start::

    from claude_node import ClaudeController

    with ClaudeController(skip_permissions=True) as ctrl:
        result = ctrl.send("Hello, Claude")
        print(result.result_text)
"""

from .controller import ClaudeController, ClaudeMessage
from .router import MultiAgentRouter, AgentNode
from .exceptions import (
    ClaudeError,
    ClaudeBinaryNotFound,
    ClaudeStartupError,
    ClaudeTimeoutError,
    ClaudeSendConflictError,
)

__version__ = "0.1.0"
__all__ = [
    "ClaudeController",
    "ClaudeMessage",
    "MultiAgentRouter",
    "AgentNode",
    "ClaudeError",
    "ClaudeBinaryNotFound",
    "ClaudeStartupError",
    "ClaudeTimeoutError",
    "ClaudeSendConflictError",
]
