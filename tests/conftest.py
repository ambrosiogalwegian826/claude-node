"""
Shared pytest fixtures for claude-node tests.
"""

import pytest
import shutil


@pytest.fixture
def claude_required():
    """
    Fixture that skips the test if the `claude` binary is not available.

    Usage:
        def test_something(claude_required):
            # test code here
            pass
    """
    if shutil.which("claude") is None:
        pytest.skip("claude binary not found in PATH")
    return True
