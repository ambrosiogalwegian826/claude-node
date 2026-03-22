"""
claude_node.runtime — Claude CLI runtime discovery and introspection.

Provides utilities to locate the claude binary, read its version,
and check availability before attempting to start a session.
"""

import shutil
import subprocess
from dataclasses import dataclass

from .exceptions import ClaudeBinaryNotFound


@dataclass
class ClaudeRuntimeInfo:
    """Runtime information about a claude CLI installation."""

    cli_path: str
    binary_path: str | None
    version: str | None
    available: bool


def find_claude_binary(cli_path: str = "claude") -> str | None:
    """
    Resolve the given CLI name to an absolute path using shutil.which.

    Returns the absolute path if the binary is found in PATH,
    or None if no matching binary is found.
    """
    return shutil.which(cli_path)


def get_claude_version(binary_path: str) -> str | None:
    """
    Run `claude --version` and return the version string.

    Returns the first line of stdout on success, or None if the
    command fails or output cannot be read.
    """
    try:
        result = subprocess.run(
            [binary_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def check_claude_available(cli_path: str = "claude") -> ClaudeRuntimeInfo:
    """
    Check whether the claude binary is available and gather runtime info.

    Returns a ClaudeRuntimeInfo with binary_path, version, and availability.
    Raises ClaudeBinaryNotFound if the binary cannot be found at all.
    """
    binary_path = find_claude_binary(cli_path)
    if binary_path is None:
        raise ClaudeBinaryNotFound(
            f"claude binary not found in PATH: {cli_path}"
        )

    version = get_claude_version(binary_path)

    return ClaudeRuntimeInfo(
        cli_path=cli_path,
        binary_path=binary_path,
        version=version,
        available=True,
    )
