import os
import tempfile

import pytest

# Isolate all app data for tests.
_tmp = tempfile.mkdtemp(prefix="claude-agent-test-")
os.environ["CLAUDE_AGENT_HOME"] = _tmp


@pytest.fixture
def brain(tmp_path):
    from claude_agent.memory.db import Brain
    b = Brain(tmp_path / "t.sqlite3")
    yield b
    b.close()


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


@pytest.fixture
def clock():
    return Clock()
