#!/usr/bin/env python3
"""
协议已通 — 多轮上下文验证
格式: {"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."}]}}
"""

import subprocess, json, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
