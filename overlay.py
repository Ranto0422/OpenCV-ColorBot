"""
overlay.py - Real-time Visual Overlay
Draws bounding boxes, circles, labels, crosshair, FPS counter,
and a side-panel with detection stats onto the captured frame.
"""

import time
import cv2
import numpy as np
from typing import List, Optional

import config
from detector import Detection


class Overlay:
    """Renders ML detections onto a frame and displays it in an OpenCV window."""

    def __init__(self):
        self._fps_times: list = []
        cv2.namedWindow(config.OVERLAY_WINDOW_NAME, cv2.WINDOW_NORMAL)

    # ─── Public API ──────────────────────────────────────────────────────────

    def render(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        detections: List[Detection],
        click_count: int = 0,
        clicked_target: Optional[Detection] = None,
    ) -> bool:
        """
        Draw all detections onto `frame`, show it, and return True
        unless the user pressed Q (quit).
        """
        display = frame.copy()

        # Draw each detection
        for det in detections:
            self._draw_detection(display, det, highlight=(det is clicked_target))

        # Heads-up panel (top-left)
        fps = self._update_fps()
        self._draw_hud(display, fps, len(detections), click_count)

        # Optional crosshair
        if config.SHOW_CROSSHAIR:
            self._draw_crosshair(display)

        # Small mask inset (bottom-right corner) for debugging
        self._draw_mask_inset(display, mask)

        cv2.imshow(config.OVERLAY_WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def close(self):
        cv2.destroyAllWindows()

    # ─── Drawing Helpers ─────────────────────────────────────────────────────

    def _draw_detection(
        self, frame: np.ndarray, det: Detection, highlight: bool = False
    ) -> None:
        """Draw bounding box, circle, center dot, size label, confidence."""
        scale = config.PROCESS_SCALE if config.PROCESS_SCALE else 1.0

        # Scale coordinates back to display resolution
        x  = int(det.x  / scale)
        y  = int(det.y  / scale)
        w  = int(det.w  / scale)
        h  = int(det.h  / scale)
        cx = int(det.cx / scale)
        cy = int(det.cy / scale)
        r  = int(det.radius / scale) if det.radius else max(w, h) // 2

        box_color    = (0, 255, 255) if highlight else config.BOX_COLOR
        circle_color = (0, 80, 255)  if highlight else config.CIRCLE_COLOR

        # ── Bounding box ──
        cv2.rectangle(
            frame, (x, y), (x + w, y + h),
            box_color, config.BOX_THICKNESS,
        )

        # ── Circle outline ──
        if det.is_circle or config.USE_HOUGH_CIRCLES:
            cv2.circle(frame, (cx, cy), r, circle_color, config.CIRCLE_THICKNESS)

        # ── Center dot ──
        cv2.circle(frame, (cx, cy), 4, config.CENTER_DOT_COLOR, -1)

        # ── Confidence bar (left edge of box) ──
        bar_h = int(h * det.confidence)
        cv2.rectangle(
            frame,
            (x - 6, y + h - bar_h),
            (x - 2, y + h),
            (0, 200, 0), -1,
        )

        # ── Label above box ──
        label_lines = [
            det.label,
            f"conf={det.confidence:.2f}",
        ]
        for i, line in enumerate(label_lines):
            lx = x
            ly = y - 8 - (len(label_lines) - 1 - i) * 16
            # Shadow
            cv2.putText(
                frame, line, (lx + 1, ly + 1),
                cv2.FONT_HERSHEY_SIMPLEX,
                config.LABEL_FONT_SCALE, (0, 0, 0),
                config.LABEL_THICKNESS + 1, cv2.LINE_AA,
            )
            # Text
            cv2.putText(
                frame, line, (lx, ly),
                cv2.FONT_HERSHEY_SIMPLEX,
                config.LABEL_FONT_SCALE, config.LABEL_COLOR,
                config.LABEL_THICKNESS, cv2.LINE_AA,
            )

    def _draw_hud(
        self, frame: np.ndarray, fps: float, num_detections: int, click_count: int
    ) -> None:
        """Semi-transparent HUD panel in the top-left corner."""
        lines = [
            f"FPS : {fps:.1f}",
            f"Targets : {num_detections}",
            f"Clicks  : {click_count}",
            f"Profile : {config.ACTIVE_PROFILE}",
            f"Mode    : {'AUTO' if config.AUTO_CLICK else 'VIEW'}",
            "Q = quit",
        ]
        panel_w = 210
        panel_h = len(lines) * 20 + 10
        overlay = frame[0:panel_h, 0:panel_w].copy()
        cv2.rectangle(frame, (0, 0), (panel_w, panel_h), (20, 20, 20), -1)
        frame[0:panel_h, 0:panel_w] = cv2.addWeighted(
            overlay, 0.35,
            frame[0:panel_h, 0:panel_w], 0.65,
            0,
        )

        for i, line in enumerate(lines):
            y = 18 + i * 20
            cv2.putText(
                frame, line, (6, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (180, 255, 180), 1, cv2.LINE_AA,
            )

    def _draw_crosshair(self, frame: np.ndarray) -> None:
        """Draw a crosshair at the center of the frame."""
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        size = 15
        color = config.CROSSHAIR_COLOR
        cv2.line(frame, (cx - size, cy), (cx + size, cy), color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - size), (cx, cy + size), color, 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 4, color, 1, cv2.LINE_AA)

    def _draw_mask_inset(self, frame: np.ndarray, mask: np.ndarray) -> None:
        """Show a small color-mask preview in the bottom-right corner."""
        h, w = frame.shape[:2]
        inset_w, inset_h = 220, 135
        mask_rgb  = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_small = cv2.resize(mask_rgb, (inset_w, inset_h))

        # Label
        cv2.putText(
            mask_small, "Color Mask", (4, 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1, cv2.LINE_AA,
        )

        bx = w - inset_w - 4
        by = h - inset_h - 4
        frame[by : by + inset_h, bx : bx + inset_w] = cv2.addWeighted(
            frame[by : by + inset_h, bx : bx + inset_w], 0.2,
            mask_small, 0.8,
            0,
        )
        cv2.rectangle(
            frame, (bx, by), (bx + inset_w, by + inset_h),
            (80, 80, 80), 1,
        )

    # ─── FPS Counter ─────────────────────────────────────────────────────────

    def _update_fps(self) -> float:
        now = time.time()
        self._fps_times.append(now)
        # Keep only last 30 timestamps
        self._fps_times = [t for t in self._fps_times if now - t < 1.0]
        return float(len(self._fps_times))
