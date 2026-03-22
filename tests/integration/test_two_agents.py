#!/usr/bin/env python3
"""
两个 Claude CLI 互相聊天
========================
Agent A (产品经理): 提出需求
Agent B (工程师): 回应并反问
Controller 在中间翻译和路由

架构:
  Agent A (CLI进程) ←→ Controller ←→ Agent B (CLI进程)
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
