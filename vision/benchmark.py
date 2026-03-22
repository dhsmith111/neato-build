"""Benchmark: measure sustained FPS for camera capture + YOLO inference on Hailo-10H."""

import os
import sys
import time
from vision.capture import Camera
from vision.detector import Detector

NUM_FRAMES = 50

print(f"Benchmarking {NUM_FRAMES} frames: camera capture + YOLOv8m inference")
print("=" * 60)

# Start camera
cam = Camera()
cam.start(settle_time=2)

# Start detector
detector = Detector(confidence_threshold=0.5)
detector.start()
print(f"Model input: {detector.model_width}x{detector.model_height}")

# Warm up (first inference is slower)
frame = cam.capture()
_ = detector.detect(frame)
print("Warm-up done, starting benchmark...\n")

capture_times = []
inference_times = []
total_detections = 0

for i in range(NUM_FRAMES):
    # Capture
    t0 = time.time()
    frame = cam.capture()
    t1 = time.time()

    # Detect
    detections = detector.detect(frame)
    t2 = time.time()

    cap_ms = (t1 - t0) * 1000
    inf_ms = (t2 - t1) * 1000
    capture_times.append(cap_ms)
    inference_times.append(inf_ms)
    total_detections += len(detections)

    if (i + 1) % 10 == 0:
        print(f"  Frame {i+1}/{NUM_FRAMES}  cap={cap_ms:.0f}ms  inf={inf_ms:.0f}ms  "
              f"total={cap_ms+inf_ms:.0f}ms  det={len(detections)}", flush=True)

cam.stop()

# Stats
avg_cap = sum(capture_times) / len(capture_times)
avg_inf = sum(inference_times) / len(inference_times)
avg_total = avg_cap + avg_inf
fps = 1000 / avg_total

print(f"\n{'Results':=^60}")
print(f"  Frames:     {NUM_FRAMES}")
print(f"  Capture:    {avg_cap:.1f}ms avg  (min={min(capture_times):.1f}, max={max(capture_times):.1f})")
print(f"  Inference:  {avg_inf:.1f}ms avg  (min={min(inference_times):.1f}, max={max(inference_times):.1f})")
print(f"  Total:      {avg_total:.1f}ms avg per frame")
print(f"  FPS:        {fps:.1f}")
print(f"  Detections: {total_detections} total ({total_detections/NUM_FRAMES:.1f} avg/frame)")

sys.stdout.flush()
sys.stderr.flush()
os._exit(0)