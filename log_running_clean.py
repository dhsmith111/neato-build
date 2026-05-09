"""Attach the logger to a Clean run that's already in progress.

Skips the relay/start-button dance — assumes Clean mode is already
running and the USB is connected. Just opens serial + camera and logs
for the requested duration.
"""

import json
import os
import signal
import sys
import threading
import time
from datetime import datetime

from scout.telemetry import collect_metadata, compute_summary, update_runs_index
from neato_serial.neato import Neato
from vision.capture import Camera
from vision.detector import Detector

SERIAL_PORT = '/dev/ttyACM0'


def attach_and_log(duration_s=120, metadata=None):
    if metadata is None:
        metadata = collect_metadata(duration_s)
    metadata["watch_mode"] = "attached_to_running_clean"

    n = object.__new__(Neato)
    n.port = SERIAL_PORT
    n.baud = 115200
    n.relay = None
    n.ser = None
    n._lock = threading.Lock()
    n.connect()
    print("[log] connected to Neato", flush=True)

    camera = Camera(width=640, height=640)
    camera.start(settle_time=2)
    print("[log] camera started", flush=True)

    detector = Detector(confidence_threshold=0.4)
    detector.start()
    print("[log] detector started (Hailo-10H)", flush=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"captures/{timestamp}_clean_mode_log"
    os.makedirs(out_dir, exist_ok=True)

    entries = []
    frame = 0
    t_start = time.time()
    print(f"[log] logging for {duration_s}s — Ctrl+C to stop early", flush=True)

    try:
        while time.time() - t_start < duration_s:
            t0 = time.time()
            entry = {"frame": frame, "timestamp": t0, "elapsed_s": round(t0 - t_start, 2)}

            try:
                img = camera.capture()
                detections = detector.detect(img)
                det_list = [{"label": d.label, "confidence": round(d.confidence, 2),
                             "bbox": [round(d.x_min, 3), round(d.y_min, 3),
                                      round(d.x_max, 3), round(d.y_max, 3)]}
                            for d in detections]
                entry["detections"] = det_list
                if frame % 10 == 0 or len(detections) > 0:
                    from PIL import Image
                    Image.fromarray(img).save(f"{out_dir}/frame_{frame:04d}.jpg", quality=85)
            except Exception as e:
                entry["vision_error"] = str(e)
                det_list = []

            digital = motors = analog = accel = {}
            try:
                digital = n.get_digital_sensors(); entry["digital"] = digital
            except Exception as e:
                entry["digital_error"] = str(e)
            try:
                analog = n.get_analog_sensors(); entry["analog"] = analog
            except Exception as e:
                entry["analog_error"] = str(e)
            try:
                raw = n.send("GetMotors", delay=0.3)
                motors = {}
                for line in raw.strip().split('\n'):
                    if ',' in line and not line.startswith('Parameter'):
                        parts = line.split(',')
                        if len(parts) >= 2:
                            try:
                                motors[parts[0].strip()] = float(parts[1].strip())
                            except ValueError:
                                pass
                entry["motors"] = motors
            except Exception as e:
                entry["motors_error"] = str(e)
            try:
                accel = n.get_accel_parsed(); entry["accel"] = accel
            except Exception as e:
                entry["accel_error"] = str(e)

            entries.append(entry)

            wall = analog.get('WallSensorInMM', '?')
            lw = motors.get('LeftWheel_Speed', 0)
            rw = motors.get('RightWheel_Speed', 0)
            brush = motors.get('Brush_RPM', 0)
            vac = motors.get('Vacuum_RPM', 0)
            n_det = len(det_list)
            labels = ", ".join(d["label"] for d in det_list[:3]) if n_det else ""
            bumps = ""
            if digital.get('LFRONTBIT', 0) or digital.get('RFRONTBIT', 0):
                bumps += " BUMP!"
            if digital.get('LSIDEBIT', 0) or digital.get('RSIDEBIT', 0):
                bumps += " SIDE!"
            print(f"[{frame:4d}] {entry['elapsed_s']:5.1f}s | wall={wall}mm L={lw:.0f} R={rw:.0f} | brush={brush:.0f} vac={vac:.0f} | det={n_det} [{labels}]{bumps}", flush=True)
            frame += 1
    except KeyboardInterrupt:
        print("\n[log] stopped early", flush=True)

    camera.stop()
    print("[log] camera stopped", flush=True)

    with open(f"{out_dir}/sensor_log.json", 'w') as f:
        json.dump(entries, f, indent=2)
    print(f"[log] saved {len(entries)} frames", flush=True)

    with open(f"{out_dir}/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    summary = compute_summary(entries, metadata)
    with open(f"{out_dir}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    update_runs_index(out_dir, summary)
    print(f"[log] summary + index updated", flush=True)

    n.close()
    os._exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    # baked-in metadata since this is a recovery/attach scenario
    metadata = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "duration_s_planned": duration,
        "room": "watch_test_attach",
        "starting_position": None,
        "lighting": None,
        "obstacles": None,
        "mode": "Clean",
        "notes": "Attached mid-run after watch-mode test; firmware was in 'please unplug' state, manually bounced relay to release.",
    }
    attach_and_log(duration, metadata)
