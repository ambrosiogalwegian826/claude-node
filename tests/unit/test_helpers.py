import json


class DummyThread:
    def __init__(self, target=None, args=(), daemon=None, **kwargs):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True


class FakePipe:
    def __init__(self, lines=None):
        self._lines = list(lines or [])

    def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return ""


class FakeStdin:
    def __init__(self):
        self.writes = []
        self.flushed = False
        self.raise_on_write = None

    def write(self, text):
        if self.raise_on_write:
            raise self.raise_on_write
        self.writes.append(text)

    def flush(self):
        self.flushed = True


class FakeProcess:
    def __init__(self, stdout_lines=None, stderr_lines=None, poll_value=None, pid=12345):
        self.stdin = FakeStdin()
        self.stdout = FakePipe(stdout_lines)
        self.stderr = FakePipe(stderr_lines)
        self._poll_value = poll_value
        self.pid = pid
        self.terminated = False
        self.killed = False
        self.wait_calls = []
        self.raise_timeout_once = False

    def poll(self):
        return self._poll_value

    def terminate(self):
        self.terminated = True
        self._poll_value = 0

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.raise_timeout_once:
            self.raise_timeout_once = False
            import subprocess
            raise subprocess.TimeoutExpired(cmd="claude", timeout=timeout)
        return self._poll_value

    def kill(self):
        self.killed = True
        self._poll_value = -9


def make_result_line(result="ok", subtype="success", session_id="sess-1", total_cost_usd=0.1, num_turns=1):
    return json.dumps({
        "type": "result",
        "subtype": subtype,
        "result": result,
        "session_id": session_id,
        "total_cost_usd": total_cost_usd,
        "num_turns": num_turns,
    })


def make_init_line(session_id="sess-1", tools=None, slash_commands=None):
    return json.dumps({
        "type": "system",
        "subtype": "init",
        "session_id": session_id,
        "tools": tools or ["Read", "Write"],
        "slash_commands": slash_commands or ["/memory"],
    })


def make_assistant_line(blocks):
    return json.dumps({
        "type": "assistant",
        "message": {"content": blocks},
    })


def make_tool_result_line(blocks):
    return json.dumps({
        "type": "user",
        "message": {"content": blocks},
    })
