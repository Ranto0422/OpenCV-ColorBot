# AimLab ColorBot — OpenCV School Project

A real-time **color detection bot** for AimLab built with Python and OpenCV.
Demonstrates computer vision concepts for a school project:

| Concept | Implementation |
|---|---|
| Screen capture | `mss` (fast pixel-perfect grab) |
| HSV color filtering | `cv2.inRange` on each frame |
| Circle detection | `cv2.HoughCircles` (Hough Transform) |
| Shape detection | `cv2.findContours` + circularity metric |
| Size measurement | Pixel radius → inch conversion via monitor PPI |
| Auto-clicking | `pyautogui.click` with nearest-target selection |
| Live overlay | OpenCV window with bounding boxes, labels, FPS HUD |

---

## Project Structure

```
OpenCV-ColorBot/
├── main.py          # Entry point & main loop
├── config.py        # All tunable parameters
├── detector.py      # Color + circle + contour detection engine
├── clicker.py       # Target selection & mouse clicking
├── overlay.py       # Real-time visual overlay renderer
└── requirements.txt
```

---

## How It Works

### 1. Screen Capture
Every frame the bot grabs a screenshot using `mss`, which is much faster than
`PIL.ImageGrab` because it calls native OS APIs directly.

### 2. HSV Color Filtering
The captured BGR frame is converted to **HSV** (Hue-Saturation-Value) color
space. HSV is preferred over RGB for color detection because the hue channel is
independent of lighting changes.

A binary mask is created with `cv2.inRange`, leaving only pixels that match the
target color range (configurable in `config.py`).

```
BGR frame → GaussianBlur → HSV → inRange mask → morphological cleanup
```

### 3. Circle Detection (Hough Transform)
`cv2.HoughCircles` uses the **Hough Circle Transform** to find circular shapes
in the masked grayscale image. This is the primary method for AimLab targets
because targets are round orbs.

Parameters tunable in `config.py`:
- `HOUGH_DP` — accumulator resolution
- `HOUGH_PARAM2` — sensitivity (lower → more circles found)
- `HOUGH_MIN/MAX_RADIUS` — expected target size range

### 4. Contour-based Shape Detection
As a fallback (and to catch non-circular or partially occluded targets),
`cv2.findContours` extracts all connected blobs from the mask. Each contour's
**circularity** is computed:

$$\text{circularity} = \frac{4\pi \cdot \text{area}}{\text{perimeter}^2}$$

A perfect circle has circularity = 1.0. This score is used as the confidence
value displayed in the overlay.

### 5. Size Measurement
Each detected target's radius (in pixels) is converted to a real-world diameter:

$$\text{diameter (in)} = \frac{\text{diameter (px)}}{\text{monitor PPI}}$$

The label is drawn above each bounding box:
```
Circle | r=32px | d=64px (0.67in)
```

### 6. Auto-Click
The `Clicker` selects the target whose center is **nearest to the current cursor
position** (configurable) and fires `pyautogui.click()`. A configurable delay
prevents spam-clicking. Optional humanization adds a small random pixel offset.

### 7. Live Overlay
An OpenCV window shows:
- **Green bounding box** around each detected target
- **Red circle outline** from HoughCircles
- **Cyan center dot**
- **Confidence bar** along the left edge of each box
- **Label** with method, radius, diameter
- **HUD panel** with FPS, detection count, click count, active mode
- **Color mask inset** (bottom-right) showing what the bot "sees" after filtering

---

## Installation

```bash
pip install -r requirements.txt
```

> **Tesseract (optional):** If you enable `USE_OCR = True` in `config.py`,
> install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and
> `pip install pytesseract`.

---

## Usage

```bash
# Default (auto-click enabled, aimlab_white profile)
python main.py

# Detection-only mode (no clicking)
python main.py --no-click

# Use a different color profile
python main.py --profile orange

# Disable HoughCircles, use contour detection only
python main.py --no-hough

# Process at 50% scale for lower-end PCs
python main.py --scale 0.5
```

**Controls:**
| Key | Action |
|---|---|
| `Q` | Quit cleanly |
| Mouse → top-left corner | Emergency stop (pyautogui failsafe) |

---

## Tuning Color Profiles

Open `config.py` and adjust the `COLOR_PROFILES` dictionary.
Use the mask inset in the overlay to verify your color range is isolating targets.

AimLab default targets appear **white** — the `aimlab_white` profile works for
most tasks. Use `orange` for Gridshot if your settings use colored targets.

To find the right HSV range:
1. Screenshot a target
2. Open it in the HSV tuner below (or use GIMP/Photoshop color picker)
3. Adjust `lower`/`upper` in the profile

---

## Key Computer Vision Concepts (for the report)

| Term | Meaning |
|---|---|
| **HSV** | Color model where Hue is separated from brightness |
| **Gaussian Blur** | Smooths image to reduce noise before processing |
| **Binary mask** | Black/white image where white = target color |
| **Morphological opening** | Removes small noise blobs from the mask |
| **Morphological closing** | Fills small holes inside detected blobs |
| **Hough Transform** | Votes-based algorithm for detecting geometric shapes |
| **Contour** | Outline of a connected region in a binary image |
| **Circularity** | Ratio measuring how close a shape is to a perfect circle |
| **IoU** | Intersection-over-Union — metric for overlap between two boxes |
| **PPI** | Pixels Per Inch — used to convert pixel measurements to real units |
