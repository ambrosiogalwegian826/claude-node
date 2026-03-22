#!/usr/bin/env python3
"""
关键测试: --print + stream-json + stdin 保持打开
================================================
帮助文本说 --input-format "only works with --print"
之前测试 --print 失败是因为 echo pipe 立即关闭了 stdin
这次用 subprocess.PIPE 保持 stdin 打开
"""

import subprocess, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
