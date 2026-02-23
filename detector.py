"""
detector.py - Color & Shape Detection Engine
Uses OpenCV HSV color filtering + HoughCircles to locate targets.
"""

import cv2
import numpy as np
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import config


class EmergencyShutdown(Exception):
    """Raised by Detector.process() when an emergency stop has been triggered."""


@dataclass
class Detection:
    """Holds all information about one detected target."""
    # Bounding box (x, y, w, h) in the processed-frame coordinate space
    x: int
    y: int
    w: int
    h: int
    # Center point
    cx: int
    cy: int
    # Circle fit (None if no Hough circle was matched)
    radius: Optional[int] = None
    # Diameter in pixels
    diameter_px: int = 0
    # Estimated real-world diameter in inches
    diameter_in: float = 0.0
    # Confidence score (0-1) based on circularity
    confidence: float = 1.0
    # Label string drawn on the overlay
    label: str = ""
    # Whether a Hough circle was the primary detection method
    is_circle: bool = False

    def __post_init__(self):
        self.diameter_px = self.radius * 2 if self.radius else max(self.w, self.h)
        self.diameter_in = round(self.diameter_px / config.MONITOR_PPI, 2)

        method = "Circle" if self.is_circle else "Contour"
        if config.SHOW_SIZE_LABEL:
            self.label = (
                f"{method} | r={self.radius}px | "
                f"d={self.diameter_px}px ({self.diameter_in}in)"
            )
        else:
            self.label = method

    @property
    def screen_center(self) -> Tuple[int, int]:
        """Return (cx, cy) in original (un-scaled) screen coordinates."""
        scale = config.PROCESS_SCALE if config.PROCESS_SCALE else 1.0
        return (int(self.cx / scale), int(self.cy / scale))


class Detector:
    """Main detection pipeline: capture → filter → detect → return detections."""

    def __init__(self):
        # ── Emergency-stop flag ───────────────────────────────────────────────
        self._shutdown_event = threading.Event()

        # ── Enabled flag (starts OFF — press toggle hotkey to activate) ───────
        self._enabled = False

        profile = config.COLOR_PROFILES[config.ACTIVE_PROFILE]
        self.lower_hsv = np.array(profile["lower"], dtype=np.uint8)
        self.upper_hsv = np.array(profile["upper"], dtype=np.uint8)
        self.display_color = profile["display_color"]

        # For red hue which wraps around 0/180 in HSV we need two ranges
        self._dual_range = (
            self.lower_hsv[0] > self.upper_hsv[0]  # lower hue > upper hue
        )
        if self._dual_range:
            # Split into [lower, 179] and [0, upper]
            self._lower2 = np.array([0,              self.lower_hsv[1], self.lower_hsv[2]], dtype=np.uint8)
            self._upper2 = np.array([self.upper_hsv[0], self.upper_hsv[1], self.upper_hsv[2]], dtype=np.uint8)
            self._lower1 = np.array([self.lower_hsv[0], self.lower_hsv[1], self.lower_hsv[2]], dtype=np.uint8)
            self._upper1 = np.array([179,              self.upper_hsv[1], self.upper_hsv[2]], dtype=np.uint8)

        # Morphology kernel for cleaning up the mask
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # ─── Public API ───────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Trigger an emergency stop. The next call to process() will raise EmergencyShutdown."""
        self._shutdown_event.set()

    @property
    def is_shutdown(self) -> bool:
        """True if an emergency stop has been requested."""
        return self._shutdown_event.is_set()

    # ── Enable / disable ──────────────────────────────────────────────────────

    @property
    def is_enabled(self) -> bool:
        """True if detection is currently active."""
        return self._enabled

    def enable(self) -> None:
        """Turn detection on."""
        self._enabled = True

    def disable(self) -> None:
        """Turn detection off (process() returns empty results)."""
        self._enabled = False

    def toggle(self) -> bool:
        """Toggle detection on/off. Returns the new enabled state."""
        self._enabled = not self._enabled
        return self._enabled

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Detection]]:
        """
        Run the full detection pipeline on `frame`.
        Returns:
            mask       – binary mask (for debugging / overlay)
            detections – list of Detection objects
        Raises:
            EmergencyShutdown: if shutdown() was called before this frame.
        """
        if self._shutdown_event.is_set():
            raise EmergencyShutdown("Emergency stop triggered.")

        # Return empty results while paused
        if not self._enabled:
            h, w = frame.shape[:2]
            return np.zeros((h, w), dtype=np.uint8), []

        # Optional downscale for speed
        if config.PROCESS_SCALE and config.PROCESS_SCALE != 1.0:
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (int(w * config.PROCESS_SCALE),
                                       int(h * config.PROCESS_SCALE)))
        else:
            small = frame

        # Blur → HSV → color mask → morphology
        blurred = cv2.GaussianBlur(small, (config.BLUR_KERNEL, config.BLUR_KERNEL), 0)
        hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask    = self._build_mask(hsv)
        mask    = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._kernel, iterations=1)
        mask    = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel, iterations=2)

        detections: List[Detection] = []

        if config.USE_HOUGH_CIRCLES:
            detections = self._detect_hough(small, mask)

        # Fall back to contour detection (or supplement Hough results)
        contour_detections = self._detect_contours(mask)
        detections = self._merge(detections, contour_detections)

        return mask, detections

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _build_mask(self, hsv: np.ndarray) -> np.ndarray:
        """Create a binary mask from the configured HSV range(s)."""
        if self._dual_range:
            m1 = cv2.inRange(hsv, self._lower1, self._upper1)
            m2 = cv2.inRange(hsv, self._lower2, self._upper2)
            return cv2.bitwise_or(m1, m2)
        return cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

    def _detect_hough(self, frame: np.ndarray, mask: np.ndarray) -> List[Detection]:
        """Use HoughCircles on the masked grayscale image to find circular targets."""
        # Apply mask to gray image so only color-matched regions are searched
        gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        masked = cv2.bitwise_and(gray, gray, mask=mask)
        blurred = cv2.GaussianBlur(masked, (9, 9), 2)

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=config.HOUGH_DP,
            minDist=config.HOUGH_MIN_DIST,
            param1=config.HOUGH_PARAM1,
            param2=config.HOUGH_PARAM2,
            minRadius=config.HOUGH_MIN_RADIUS,
            maxRadius=config.HOUGH_MAX_RADIUS,
        )

        detections = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            for (cx, cy, r) in circles:
                x = cx - r
                y = cy - r
                w = h = r * 2
                detections.append(Detection(
                    x=x, y=y, w=w, h=h,
                    cx=cx, cy=cy,
                    radius=int(r),
                    is_circle=True,
                    confidence=0.95,
                ))
        return detections

    def _detect_contours(self, mask: np.ndarray) -> List[Detection]:
        """Detect targets via contour analysis on the color mask."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < config.MIN_CONTOUR_AREA or area > config.MAX_CONTOUR_AREA:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            cx = x + w // 2
            cy = y + h // 2

            # Circularity = 4π·area / perimeter²  (1.0 = perfect circle)
            perimeter = cv2.arcLength(cnt, True)
            circularity = 0.0
            if perimeter > 0:
                circularity = (4 * np.pi * area) / (perimeter ** 2)

            # Fit enclosing circle for radius estimate
            (_, _), radius = cv2.minEnclosingCircle(cnt)
            radius = int(radius)

            detections.append(Detection(
                x=x, y=y, w=w, h=h,
                cx=cx, cy=cy,
                radius=radius,
                is_circle=False,
                confidence=round(circularity, 3),
            ))

        return detections

    def _merge(
        self,
        hough: List[Detection],
        contours: List[Detection],
        iou_threshold: float = 0.3,
    ) -> List[Detection]:
        """
        Combine Hough and contour detections, removing duplicates.
        Hough detections take priority. Contour detections are only added
        if they don't significantly overlap an existing Hough detection.
        """
        merged = list(hough)

        for c in contours:
            duplicate = False
            for h in hough:
                if _iou(c, h) > iou_threshold:
                    duplicate = True
                    break
            if not duplicate:
                merged.append(c)

        return merged


# ─── Utility ──────────────────────────────────────────────────────────────────

def _iou(a: Detection, b: Detection) -> float:
    """Compute Intersection-over-Union for two detections (bounding boxes)."""
    ax1, ay1 = a.x, a.y
    ax2, ay2 = a.x + a.w, a.y + a.h
    bx1, by1 = b.x, b.y
    bx2, by2 = b.x + b.w, b.y + b.h

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union  = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# ─── Entry-point guard ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[detector.py] This file is a module — not an entry point.")
    print("Run the bot with:  python main.py")
