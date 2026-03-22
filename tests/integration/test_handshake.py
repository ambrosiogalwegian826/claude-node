#!/usr/bin/env python3
"""
正确协议测试: --print + stream-json + initialize 握手
=====================================================
发现: SDK 不是直接发 user message, 而是先发 initialize 握手
Go SDK 确认启动命令是: claude --print --input-format stream-json --output-format stream-json

协议流程:
  1. 启动 CLI (--print --input-format stream-json --output-format stream-json)
  2. 发送 initialize 消息 (握手)
  3. 收到初始化响应
  4. 发送 user message
  5. 收到 assistant response
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
