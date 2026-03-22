#!/usr/bin/env python3
"""
验证三项能力:
1. Subagent 生成与调用 (Agent tool)
2. Skill 调用 (/brainstorm 等)
3. 交互选择 (AskUserQuestion) — 观察协议格式并尝试程序化回应
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
