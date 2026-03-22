#!/usr/bin/env python3
"""
AI ↔ AI 交互测试
================
CLI A (设计师): 提出方案选择，用 AskUserQuestion 问问题
CLI B (决策者): 收到问题，给出选择
Controller: 把 A 的问题转给 B，把 B 的回答喂回 A

流程:
  A 收到任务 → A 用 AskUserQuestion 提问 → Controller 截获
  → Controller 转给 B → B 回答 → Controller 把回答喂回 A
  → A 基于回答继续工作
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
