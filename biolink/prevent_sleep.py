"""Prevent system sleep during experiments (Windows); no-op elsewhere."""

import ctypes
import sys


def prevent_sleep():
    if sys.platform != "win32":
        return
    try:
        print("preventSleep")
        es_continuous = 0x80000000
        es_system_required = 0x00000001
        es_display_required = 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(
            es_continuous | es_system_required | es_display_required
        )
    except Exception as e:
        print("preventSleep Error: " + str(e))


def allow_sleep():
    if sys.platform != "win32":
        return
    try:
        es_continuous = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(es_continuous)
    except Exception as e:
        print("allowSleep Error: " + str(e))
