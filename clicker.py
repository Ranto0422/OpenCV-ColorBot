"""
clicker.py - Mouse Movement & Click Engine
Finds the best target to click, optionally adds human-like imprecision,
and fires a left-click via SendInput (raw input compatible).
"""

import time
import random
import math
import threading
import ctypes
import ctypes.wintypes
from typing import List, Optional, Tuple

import pyautogui
import config
from detector import Detection


# Prevent pyautogui from throwing FailSafeException by moving to a corner
pyautogui.FAILSAFE = True      # Move mouse to corner to emergency-stop
pyautogui.PAUSE    = 0.0       # We control timing ourselves

# ─── SendInput structures ─────────────────────────────────────────────────────
MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_    = [("type", ctypes.c_ulong), ("_input", _INPUT)]

_SendInput = ctypes.windll.user32.SendInput

def _send_input(*inputs: INPUT) -> None:
    arr = (INPUT * len(inputs))(*inputs)
    _SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

def _make_mouse_input(dx: int = 0, dy: int = 0, flags: int = 0) -> INPUT:
    mi = MOUSEINPUT(dx=dx, dy=dy, mouseData=0, dwFlags=flags, time=0,
                    dwExtraInfo=None)
    inp = INPUT(type=0)
    inp.mi = mi
    return inp


class Clicker:
    """Handles target selection, mouse movement, and clicking."""

    def __init__(self):
        self._last_click_time: float = 0.0
        self._lock = threading.Lock()
        self._click_count: int = 0

    # ─── Public API ──────────────────────────────────────────────────────────

    def try_click(self, detections: List[Detection]) -> Optional[Detection]:
        """
        Given a list of detections, select the best target and click it
        if the click cooldown has elapsed.

        Returns the Detection that was clicked, or None.
        """
        if not config.AUTO_CLICK or not detections:
            return None

        now = time.time()
        if now - self._last_click_time < config.CLICK_DELAY:
            return None

        target = self._select_target(detections)
        if target is None:
            return None

        sx, sy = target.screen_center
        sx, sy = self._humanize(sx, sy)

        with self._lock:
            self._move_and_click(sx, sy)
            self._last_click_time = time.time()
            self._click_count += 1

        return target

    @property
    def click_count(self) -> int:
        return self._click_count

    # ─── Target Selection ─────────────────────────────────────────────────────

    def _select_target(self, detections: List[Detection]) -> Optional[Detection]:
        """
        Choose which target to click.
        - If AIM_NEAREST is True: pick the one closest to the current cursor.
        - Otherwise: pick the highest-confidence detection.
        """
        if not detections:
            return None

        if config.AIM_NEAREST:
            cx, cy = pyautogui.position()
            return min(
                detections,
                key=lambda d: _euclidean(d.screen_center, (cx, cy)),
            )
        else:
            return max(detections, key=lambda d: d.confidence)

    # ─── Mouse Helpers ────────────────────────────────────────────────────────

    def _humanize(self, x: int, y: int) -> Tuple[int, int]:
        """Add slight random offset to simulate imperfect human aim."""
        if not config.HUMANIZE_MOUSE:
            return x, y
        offset = config.HUMANIZE_MAX_PX
        x += random.randint(-offset, offset)
        y += random.randint(-offset, offset)
        return x, y

    def _move_and_click(self, x: int, y: int) -> None:
        """Move the cursor to (x, y) using SendInput (raw-input compatible) and click."""
        cx, cy = pyautogui.position()
        dx = x - cx
        dy = y - cy
        # Relative mouse move — games with raw input respond to this
        _send_input(_make_mouse_input(dx=dx, dy=dy, flags=MOUSEEVENTF_MOVE))
        # Left click down + up
        _send_input(
            _make_mouse_input(flags=MOUSEEVENTF_LEFTDOWN),
            _make_mouse_input(flags=MOUSEEVENTF_LEFTUP),
        )


# ─── Utility ──────────────────────────────────────────────────────────────────

def _euclidean(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
