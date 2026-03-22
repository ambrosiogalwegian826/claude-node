"""
claude_node.exceptions — Typed exception hierarchy for Claude CLI controller.

All exceptions inherit from ClaudeError (which inherits from RuntimeError),
allowing callers to catch all claude-node errors with a single handler
while also catching specific types for granular error handling.
"""


class ClaudeError(RuntimeError):
    """Base exception for all claude-node errors."""

    pass


class ClaudeBinaryNotFound(ClaudeError):
    """Raised when the claude binary cannot be found at the expected path."""

    pass


class ClaudeStartupError(ClaudeError):
    """Raised when the Claude subprocess fails to start or exits unexpectedly."""

    pass


class ClaudeTimeoutError(ClaudeError):
    """Raised when a send() call times out waiting for a result."""

    pass


class ClaudeSendConflictError(ClaudeError):
    """Raised when a send() is attempted while another send is already in-flight."""

    pass
