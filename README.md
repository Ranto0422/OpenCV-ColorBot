# OpenCV ColorBot

A real-time computer vision program that captures the screen, finds round color targets in the aim-trainer game AimLab, measures them, and clicks the nearest one. Built for a Graphics and Visual Computing course to apply color-space filtering, the Hough transform and contour analysis to a live video feed.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)

| | |
|---|---|
| **Stack** | Python, OpenCV, NumPy, mss (screen capture), pyautogui, keyboard |
| **Pipeline** | Capture → blur → HSV mask → morphology → HoughCircles + contours → merge by IoU → pick target → click |
| **Highlights** | Two detection methods combined, live debug overlay with FPS and mask view, CLI flags, hotkeys and failsafe |

## Pipeline

```
screen frame (mss)
  → Gaussian blur
  → BGR to HSV, cv2.inRange mask for the chosen color profile
  → morphological open (remove specks) and close (fill holes)
  → cv2.HoughCircles            primary: finds round targets
  → cv2.findContours            fallback: catches partly hidden targets, scores circularity
  → merge duplicates by IoU
  → choose the target nearest the cursor, click with a small random offset
  → draw overlay
```

| Concept | Where |
|---|---|
| HSV color filtering | `detector.py` |
| Hough Circle Transform | `detector.py` |
| Contours and circularity, `4π·area / perimeter²` | `detector.py` |
| IoU de-duplication of the two detectors | `detector.py` |
| Pixel to inch size (`diameter_px / monitor PPI`) | `detector.py`, `config.py` |
| Target selection and click rate limiting | `clicker.py` |
| Overlay: boxes, labels, confidence bars, FPS HUD, mask inset | `overlay.py` |

## Project structure

```
OpenCV-ColorBot/
├── main.py          entry point, CLI arguments, main loop, hotkeys
├── config.py        all tunable values: color profiles, Hough settings, click delay, PPI
├── detector.py      color, circle and contour detection
├── clicker.py       target selection and clicking
├── overlay.py       live debug overlay
└── requirements.txt
```

## Running it

Requires Python 3.10+. Written for Windows; on macOS and Linux the `keyboard` hotkey library needs root.

```bash
pip install -r requirements.txt
python main.py --no-click        # detection and overlay only, no clicking
python main.py                   # detection + auto-click, default profile
python main.py --profile orange  # other profiles: aimlab_white, orange, blue, cyan
python main.py --no-hough        # contour detection only
python main.py --scale 0.5       # process at half resolution on slower PCs
```

| Control | Action |
|---|---|
| `*` | Turn detection on or off |
| `-` | Emergency stop |
| `Q` (overlay focused) | Quit |
| Move mouse to the top-left corner | pyautogui failsafe stop |

## Tuning

Color ranges live in `COLOR_PROFILES` in `config.py`. Use the mask inset in the bottom-right of the overlay to check that only the targets show up white, then adjust the HSV `lower` and `upper` bounds.

## Note

This is a school project for learning computer vision, run against AimLab's single-player training modes. It is not meant for use in online multiplayer games.
