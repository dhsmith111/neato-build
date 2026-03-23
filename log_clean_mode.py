"""Log all Neato sensors + camera/YOLO during a firmware Clean mode run.

Uses the relay to drop USB so Clean mode starts without the
"unplug USB" complaint, then reconnects to log everything.

Usage:
    python log_clean_mode.py [duration_seconds]
    Default: 120 seconds (2 minutes)
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from gpiozero import OutputDevice

RELAY_PIN = 17
SERIAL_PORT = '/dev/ttyACM0'


def wait_for_port(present=True, timeout=30):
    """Wait for serial port to appear or disappear."""
    elapsed = 0
    while elapsed < timeout:
        exists = os.path.exists(SERIAL_PORT)
        if present and exists:
            return True
        if not present and not exists:
            return True
        time.sleep(0.5)
        elapsed += 0.5
    return False


def log_clean_run(duration_s=120):
    relay = OutputDevice(RELAY_PIN, active_high=True, initial_value=True)

    # --- Phase 1: Drop USB so Clean mode will start ---
    print("[log] cutting USB (relay off)...", flush=True)
    relay.off()

    if not wait_for_port(present=False, timeout=10):
        print("[log] WARNING: serial port didn't disappear, trying anyway", flush=True)

    print("", flush=True)
    print("=" * 50, flush=True)
    print("  >>> PRESS THE CLEAN BUTTON ON THE NEATO <<<", flush=True)
    print("=" * 50, flush=True)
    print("", flush=True)
    print("[log] waiting 10 seconds for cleaning to start...", flush=True)
    time.sleep(10)

    # --- Phase 2: Restore USB mid-clean ---
    print("[log] restoring USB (relay on)...", flush=True)
    relay.on()

    print("[log] waiting for serial port...", flush=True)
    if not wait_for_port(present=True, timeout=15):
        print("[log] ERROR: serial port never reappeared!", flush=True)
        return

    print("[log] serial port found, waiting for settle...", flush=True)
    time.sleep(2)

    # --- Phase 3: Connect and log ---
    import serial as pyserial
    import threading
    from neato_serial.neato import Neato
    from vision.capture import Camera
    from vision.detector import Detector

    # Build Neato object without re-creating the relay
    neato = object.__new__(Neato)
    neato.port = SERIAL_PORT
    neato.baud = 115200
    neato.relay = relay
    neato.ser = None
    neato._lock = threading.Lock()
    neato.connect()
    print("[log] connected to Neato", flush=True)

    camera = Camera(width=640, height=640)
    camera.start(settle_time=2)
    print("[log] camera started", flush=True)

    detector = Detector(confidence_threshold=0.4)
    detector.start()
    print("[log] detector started (Hailo-10H)", flush=True)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"captures/{timestamp}_clean_mode_log"
    os.makedirs(out_dir, exist_ok=True)

    entries = []
    frame = 0
    t_start = time.time()

    print(f"[log] logging for {duration_s}s — press Ctrl+C to stop early", flush=True)

    try:
        while time.time() - t_start < duration_s:
            t0 = time.time()
            entry = {"frame": frame, "timestamp": t0, "elapsed_s": round(t0 - t_start, 2)}

            # --- Camera + YOLO ---
            try:
                img = camera.capture()
                detections = detector.detect(img)
                det_list = [{"label": d.label, "confidence": round(d.confidence, 2),
                             "bbox": [round(d.x_min, 3), round(d.y_min, 3),
                                      round(d.x_max, 3), round(d.y_max, 3)]}
                            for d in detections]
                entry["detections"] = det_list

                # Save image every 10 frames or on detection
                if frame % 10 == 0 or len(detections) > 0:
                    from PIL import Image
                    img_pil = Image.fromarray(img)
                    img_pil.save(f"{out_dir}/frame_{frame:04d}.jpg", quality=85)
            except Exception as e:
                entry["vision_error"] = str(e)
                det_list = []

            # --- Sensors ---
            digital = {}
            analog = {}
            motors = {}
            accel = {}

            try:
                digital = neato.get_digital_sensors()
                entry["digital"] = digital
            except Exception as e:
                entry["digital_error"] = str(e)

            try:
                analog = neato.get_analog_sensors()
                entry["analog"] = analog
            except Exception as e:
                entry["analog_error"] = str(e)

            try:
                raw = neato.send("GetMotors", delay=0.3)
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
                accel = neato.get_accel_parsed()
                entry["accel"] = accel
            except Exception as e:
                entry["accel_error"] = str(e)

            # Periodic LiDAR (every ~30s)
            if frame > 0 and frame % 30 == 0:
                try:
                    lidar_raw = neato.send("GetLDSScan", delay=1.5)
                    entry["lidar_scan"] = True
                    with open(f"{out_dir}/lidar_frame_{frame:04d}.txt", 'w') as f:
                        f.write(lidar_raw)
                except Exception:
                    pass

            entries.append(entry)

            # --- Console output ---
            bumpers = ""
            if digital.get('LFRONTBIT', 0) or digital.get('RFRONTBIT', 0):
                bumpers = " BUMP!"
            if digital.get('LSIDEBIT', 0) or digital.get('RSIDEBIT', 0):
                bumpers += " SIDE!"

            wall = analog.get('WallSensorInMM', '?')
            lw_speed = motors.get('LeftWheel_Speed', 0)
            rw_speed = motors.get('RightWheel_Speed', 0)
            brush = motors.get('Brush_RPM', 0)
            vacuum = motors.get('Vacuum_RPM', 0)
            lw_pos = motors.get('LeftWheel_PositionInMM', 0)
            rw_pos = motors.get('RightWheel_PositionInMM', 0)

            n_det = len(det_list)
            labels = ", ".join(d["label"] for d in det_list[:3]) if n_det > 0 else ""

            elapsed = entry["elapsed_s"]
            print(f"[{frame:4d}] {elapsed:5.1f}s | "
                  f"wall={wall}mm L={lw_speed:.0f} R={rw_speed:.0f} | "
                  f"pos L={lw_pos:.0f} R={rw_pos:.0f} | "
                  f"brush={brush:.0f} vac={vacuum:.0f} | "
                  f"det={n_det} [{labels}]{bumpers}",
                  flush=True)

            frame += 1

    except KeyboardInterrupt:
        print("\n[log] stopped early", flush=True)

    # Stop camera
    camera.stop()
    print("[log] camera stopped", flush=True)

    # Save log
    log_path = f"{out_dir}/sensor_log.json"
    with open(log_path, 'w') as f:
        json.dump(entries, f, indent=2)

    print(f"[log] saved {len(entries)} frames to {log_path}", flush=True)

    # Don't try to stop cleaning — let it finish or user presses button
    neato.close()
    print("[log] done — press button on Neato to stop cleaning", flush=True)

    # Hailo cleanup workaround
    os._exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    log_clean_run(duration)
