#!/usr/bin/env python3
"""
验证: skill 提问后能否正确回答并继续执行
=============================================
1. 触发 /brainstorm
2. brainstorm 输出方案并提问 "是否按此方案执行"
3. 我们回 "确认"
4. 观察 brainstorm 是否继续多角色并行分析
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
