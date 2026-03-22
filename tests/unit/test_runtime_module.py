import subprocess
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestRuntimeDiscovery:
    def test_find_claude_binary_returns_path(self):
        from claude_node.runtime import find_claude_binary
        with patch("claude_node.runtime.shutil.which", return_value="/usr/local/bin/claude") as mock_which:
            assert find_claude_binary("claude") == "/usr/local/bin/claude"
        mock_which.assert_called_once_with("claude")

    def test_find_claude_binary_returns_none(self):
        from claude_node.runtime import find_claude_binary
        with patch("claude_node.runtime.shutil.which", return_value=None):
            assert find_claude_binary("claude") is None

    def test_get_claude_version_success(self):
        from claude_node.runtime import get_claude_version
        cp = subprocess.CompletedProcess(args=["claude", "--version"], returncode=0, stdout="2.1.81\nextra", stderr="")
        with patch("claude_node.runtime.subprocess.run", return_value=cp) as mock_run:
            assert get_claude_version("/bin/claude") == "2.1.81"
        mock_run.assert_called_once()

    def test_get_claude_version_nonzero_returns_none(self):
        from claude_node.runtime import get_claude_version
        cp = subprocess.CompletedProcess(args=["claude"], returncode=1, stdout="", stderr="bad")
        with patch("claude_node.runtime.subprocess.run", return_value=cp):
            assert get_claude_version("/bin/claude") is None

    @pytest.mark.parametrize(
        "exc",
        [FileNotFoundError(), subprocess.TimeoutExpired(cmd="claude", timeout=5), OSError("boom")],
    )
    def test_get_claude_version_handles_exceptions(self, exc):
        from claude_node.runtime import get_claude_version
        with patch("claude_node.runtime.subprocess.run", side_effect=exc):
            assert get_claude_version("/bin/claude") is None

    def test_check_claude_available_success_with_version(self):
        from claude_node.runtime import check_claude_available
        with patch("claude_node.runtime.find_claude_binary", return_value="/usr/bin/claude") as mock_find, \
             patch("claude_node.runtime.get_claude_version", return_value="2.1.81") as mock_version:
            info = check_claude_available()
        assert info.cli_path == "claude"
        assert info.binary_path == "/usr/bin/claude"
        assert info.version == "2.1.81"
        assert info.available is True
        mock_find.assert_called_once_with("claude")
        mock_version.assert_called_once_with("/usr/bin/claude")

    def test_check_claude_available_success_without_version(self):
        from claude_node.runtime import check_claude_available
        with patch("claude_node.runtime.find_claude_binary", return_value="/usr/bin/claude"), \
             patch("claude_node.runtime.get_claude_version", return_value=None):
            info = check_claude_available("my-claude")
        assert info.cli_path == "my-claude"
        assert info.version is None
        assert info.available is True

    def test_check_claude_available_raises_when_missing(self):
        from claude_node.exceptions import ClaudeBinaryNotFound
        from claude_node.runtime import check_claude_available
        with patch("claude_node.runtime.find_claude_binary", return_value=None):
            with pytest.raises(ClaudeBinaryNotFound, match="not found"):
                check_claude_available()

    def test_runtime_info_dataclass_fields(self):
        from claude_node.runtime import ClaudeRuntimeInfo
        info = ClaudeRuntimeInfo(cli_path="claude", binary_path="/bin/claude", version="2.0", available=True)
        assert info.cli_path == "claude"
        assert info.binary_path == "/bin/claude"
        assert info.version == "2.0"
        assert info.available is True
