#!/usr/bin/env python3
"""
Raw output test — no parsing, print every byte from stdout/stderr directly.
"""

import subprocess, threading, time, os, sys
import pytest

pytestmark = pytest.mark.integration
