#!/usr/bin/env python3
"""
测试 2: Skill / Slash Command 调用
测试 3: 交互选择（当 Claude 用 AskUserQuestion 工具提问时如何回应）
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
