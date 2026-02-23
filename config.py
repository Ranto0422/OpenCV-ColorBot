"""
config.py - AimLab ColorBot Configuration
All tunable parameters in one place for easy adjustment.
"""

# ─── Screen Capture ───────────────────────────────────────────────────────────
# Set to None to auto-detect the primary monitor, or set a specific region:
# CAPTURE_REGION = {"top": 0, "left": 0, "width": 1920, "height": 1080}
CAPTURE_REGION = None          # None = full primary monitor

# ─── Target Color Profiles ────────────────────────────────────────────────────
# Define named HSV color ranges for targets.
# Hue: 0-179, Saturation: 0-255, Value: 0-255
# Add / remove profiles as needed, then pick the active one below.
COLOR_PROFILES = {
    # AimLab default targets (white/bright orbs)
    "aimlab_white": {
        "lower": (0,   0,  200),
        "upper": (180, 40, 255),
        "display_color": (255, 255, 255),   # BGR color for overlay boxes
    },
    # Orange/red targets (e.g. Gridshot)
    "orange": {
        "lower": (0,  120, 150),
        "upper": (20, 255, 255),
        "display_color": (0, 130, 255),
    },
    # Blue targets
    "blue": {
        "lower": (100, 120, 100),
        "upper": (130, 255, 255),
        "display_color": (255, 100,   0),
    },
    # Cyan targets
    "cyan": {
        "lower": (75,  80,  80),
        "upper": (105, 255, 255),
        "display_color": (255, 255, 0),
    },
}

# Which profile to use (must be a key in COLOR_PROFILES)
ACTIVE_PROFILE = "cyan"

# ─── Detection Settings ───────────────────────────────────────────────────────
# Gaussian blur kernel before color filtering (must be odd)
BLUR_KERNEL = 5

# Minimum contour area (px²) to be considered a target (filters noise)
MIN_CONTOUR_AREA = 300

# Maximum contour area (px²) — ignores giant blobs
MAX_CONTOUR_AREA = 50_000

# ─── Circle (Hough) Detection ─────────────────────────────────────────────────
USE_HOUGH_CIRCLES = True       # Enable HoughCircles on masked regions
HOUGH_DP          = 1.2        # Inverse ratio of accumulator resolution
HOUGH_MIN_DIST    = 30         # Minimum distance between circle centers (px)
HOUGH_PARAM1      = 100        # Canny high threshold
HOUGH_PARAM2      = 30         # Accumulator threshold (lower = more circles)
HOUGH_MIN_RADIUS  = 10         # Minimum circle radius (px)
HOUGH_MAX_RADIUS  = 120        # Maximum circle radius (px)

# ─── OCR / Size Measurement ───────────────────────────────────────────────────
SHOW_SIZE_LABEL   = True       # Draw diameter label on each detected target
# Pixels-per-inch for real-world size estimate (set to your monitor's PPI)
MONITOR_PPI       = 96
# Whether to attempt pytesseract OCR on the overlay label region (advanced)
USE_OCR           = False      # Requires tesseract installed separately

# ─── Auto-Click Settings ──────────────────────────────────────────────────────
AUTO_CLICK        = True        # Set False to run in detection-only mode
CLICK_DELAY       = 0.05        # Seconds between clicks (lower = faster)
# Aim at the nearest target to the current cursor position
AIM_NEAREST       = True

# Human-like mouse movement (adds slight random offset)
HUMANIZE_MOUSE    = True
HUMANIZE_MAX_PX   = 3          # Max random offset in pixels

# ─── Overlay Window ───────────────────────────────────────────────────────────
OVERLAY_WINDOW_NAME = "AimBot Overlay - Press Q to quit"
OVERLAY_ALPHA       = 0.6      # Transparency of detection overlay (0-1)
SHOW_FPS            = True
SHOW_CROSSHAIR      = True
CROSSHAIR_COLOR     = (0, 255, 0)  # BGR green

# Box / circle outline colors (BGR)
BOX_COLOR           = (0, 255,   0)   # green bounding box
CIRCLE_COLOR        = (0, 0,   255)   # red circle outline
CENTER_DOT_COLOR    = (0, 255, 255)   # cyan center dot
LABEL_COLOR         = (255, 255, 255) # white text
BOX_THICKNESS       = 2
CIRCLE_THICKNESS    = 2
LABEL_FONT_SCALE    = 0.5
LABEL_THICKNESS     = 1

# ─── Performance ──────────────────────────────────────────────────────────────
# Process every Nth frame (1 = every frame, 2 = every other, etc.)
FRAME_SKIP         = 1
# Resize captured frame before processing to speed things up (None = no resize)
PROCESS_SCALE      = 0.75      # 0.75 = 75% of original size
