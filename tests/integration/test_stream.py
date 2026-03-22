#!/usr/bin/env python3
"""
验证 Claude CLI stream-json 双向通信
====================================
只做一件事: 启动 CLI 持久进程, 发消息, 收响应, 发第二条, 看上下文是否连续.

用法:
  python3 test_stream.py
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
