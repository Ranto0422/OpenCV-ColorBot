"""
main.py - AimLab ColorBot Entry Point
School project demonstrating:
  • Real-time screen capture (mss)
  • HSV color-space filtering (OpenCV)
  • Circle detection via HoughCircles (OpenCV)
  • Contour-based shape detection (OpenCV)
  • Size measurement in pixels + inches
  • Auto-click with human-like imprecision (pyautogui)
  • Live detection overlay with stats (OpenCV)

Usage:
    python main.py [--profile <name>] [--no-click] [--no-hough]

Controls (while overlay window is focused):
    Q  – quit
    Mouse to top-left corner – emergency stop (pyautogui failsafe)
"""

import sys
import time
import argparse
import cv2
import numpy as np
import mss

import keyboard

import config
from detector import Detector, EmergencyShutdown
from clicker  import Clicker
from overlay  import Overlay

# ─── Hotkeys ─────────────────────────────────────────────────────────────────
# * – toggle detection on/off  (starts OFF on launch)
# - – emergency stop (kills the loop entirely)
TOGGLE_HOTKEY    = "*"
EMERGENCY_HOTKEY = "-"


# ─── CLI Arguments ────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AimLab ColorBot - OpenCV school project"
    )
    parser.add_argument(
        "--profile",
        choices=list(config.COLOR_PROFILES.keys()),
        default=config.ACTIVE_PROFILE,
        help="Color profile to use for target detection",
    )
    parser.add_argument(
        "--no-click",
        action="store_true",
        help="Run in detection-only mode (no auto-clicking)",
    )
    parser.add_argument(
        "--no-hough",
        action="store_true",
        help="Disable HoughCircles, use contour-only detection",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=config.PROCESS_SCALE,
        help="Downscale factor for processing (e.g. 0.75 = 75%%)",
    )
    return parser.parse_args()


# ─── Main Loop ────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # Apply CLI overrides to config
    config.ACTIVE_PROFILE    = args.profile
    config.AUTO_CLICK        = not args.no_click
    config.USE_HOUGH_CIRCLES = not args.no_hough
    config.PROCESS_SCALE     = args.scale

    print(f"[ColorBot] Starting — profile={config.ACTIVE_PROFILE}, "
          f"auto_click={config.AUTO_CLICK}, hough={config.USE_HOUGH_CIRCLES}")
    print("[ColorBot] Focus the AimLab window, then switch to overlay to see detections.")
    print(f"[ColorBot] Detection starts PAUSED — press {TOGGLE_HOTKEY} to enable.")
    print(f"[ColorBot] {EMERGENCY_HOTKEY} = emergency stop | Q in overlay = quit.\n")

    detector = Detector()
    clicker  = Clicker()
    overlay  = Overlay()

    # Register global hotkeys (work even when overlay window is not focused)
    def _on_toggle():
        state = detector.toggle()
        print(f"[ColorBot] Detection {'ENABLED' if state else 'DISABLED'} ({TOGGLE_HOTKEY})")

    keyboard.add_hotkey(TOGGLE_HOTKEY,    _on_toggle)
    keyboard.add_hotkey(EMERGENCY_HOTKEY, detector.shutdown)
    print(f"[ColorBot] {TOGGLE_HOTKEY} = toggle detection | {EMERGENCY_HOTKEY} = emergency stop")

    frame_idx = 0

    with mss.mss() as sct:
        # Determine capture region
        if config.CAPTURE_REGION:
            monitor = config.CAPTURE_REGION
        else:
            monitor = sct.monitors[1]   # monitors[0] = all screens; [1] = primary

        print(f"[ColorBot] Capture region: {monitor}")

        try:
            while True:
                frame_idx += 1

                # ── Capture ──────────────────────────────────────────────────
                raw  = sct.grab(monitor)
                frame = np.array(raw)
                # mss gives BGRA; convert to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                # ── Skip frames for performance ───────────────────────────────
                if frame_idx % config.FRAME_SKIP != 0:
                    continue

                # ── Detect ───────────────────────────────────────────────────
                try:
                    mask, detections = detector.process(frame)
                except EmergencyShutdown:
                    print(f"[ColorBot] EMERGENCY STOP — {EMERGENCY_HOTKEY} pressed. Shutting down.")
                    break

                # ── Click ────────────────────────────────────────────────────
                clicked = clicker.try_click(detections)

                # ── Render overlay ───────────────────────────────────────────
                keep_running = overlay.render(
                    frame, mask, detections,
                    click_count=clicker.click_count,
                    clicked_target=clicked,
                )

                if not keep_running:
                    print("[ColorBot] Q pressed — exiting.")
                    break

        except KeyboardInterrupt:
            print("[ColorBot] Interrupted by user.")
        finally:
            keyboard.remove_all_hotkeys()
            overlay.close()
            print(f"[ColorBot] Session ended. Total clicks: {clicker.click_count}")


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
