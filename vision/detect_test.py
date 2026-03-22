"""Quick test: capture a frame, run YOLOv8m on Hailo-10H, print and draw detections."""

import os
import time
from PIL import Image, ImageDraw
from vision.capture import Camera
from vision.detector import Detector

CONFIDENCE_THRESHOLD = 0.3

# Capture
print("Starting camera...")
with Camera() as cam:
    frame = cam.capture()
    print(f"Frame: {frame.shape}")

# Save raw capture
img = Image.fromarray(frame)
img.save("vision/captured.jpg")

# Detect
print("Loading YOLOv8m on Hailo-10H...")
detector = Detector(confidence_threshold=CONFIDENCE_THRESHOLD)
detector.start()

t0 = time.time()
detections = detector.detect(frame)
elapsed = time.time() - t0
print(f"Inference: {elapsed*1000:.0f}ms")

# Print results
print(f"\nDetections (confidence > {CONFIDENCE_THRESHOLD}):")
print("-" * 50)
for d in detections:
    left, top, right, bottom = d.box_pixels(frame.shape[1], frame.shape[0])
    print(f"  {d.label:15s}  {d.confidence:.0%}  ({left},{top})-({right},{bottom})")

if not detections:
    print("  (none)")

# Draw bounding boxes
draw = ImageDraw.Draw(img)
colors = {"cat": "lime", "tv": "cyan", "laptop": "yellow", "cell phone": "magenta",
          "keyboard": "orange", "mouse": "red", "person": "lime", "bottle": "blue",
          "cup": "pink", "book": "white", "chair": "coral", "remote": "magenta"}

for d in detections:
    left, top, right, bottom = d.box_pixels(frame.shape[1], frame.shape[0])
    color = colors.get(d.label, "white")
    draw.rectangle([left, top, right, bottom], outline=color, width=3)
    draw.text((left + 4, top + 4), f"{d.label} {d.confidence:.0%}", fill=color)

img.save("vision/detected.jpg")
print(f"Saved vision/detected.jpg", flush=True)

# Force exit to avoid Hailo cleanup crash (known h10-hailort 5.1.1 issue)
import sys
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)