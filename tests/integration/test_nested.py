#!/usr/bin/env python3
"""
基于错误信息推断的嵌套格式测试 (不带 --print)
TypeError: Cannot read properties of undefined (reading 'role')
说明 CLI 在访问 obj.message.role → message 字段需要存在
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
