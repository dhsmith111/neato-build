"""Log all Neato sensors + camera/YOLO during a firmware Clean mode run.

Two modes for getting Clean mode to start despite USB being plugged in:

  - default ("blind") mode: drop USB first, prompt user to press button
    during a 10s window, restore USB, log.

  - --watch mode: keep USB connected, poll GetButtons until user presses
    Start, then drop USB briefly so firmware can begin cleaning, restore
    USB, log. User only has to press the button once.

End condition for the logging loop:
  - if a positive duration is given, log for that many seconds (default 120)
  - if --until-stopped is given, log until either: motors stay idle for
    IDLE_STOP_FRAMES consecutive frames, ChargingActive=1 (docked), or a
    hard safety cap of MAX_RUN_SECONDS is reached

Usage:
    python log_clean_mode.py [--watch] [--until-stopped] [duration_seconds]
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from gpiozero import OutputDevice

from scout.telemetry import collect_metadata, compute_summary, update_runs_index

RELAY_PIN = 17
SERIAL_PORT = '/dev/ttyACM0'

# --until-stopped tuning
IDLE_STOP_FRAMES = 30      # ~30s of all-zero motors = cleaning ended
MAX_RUN_SECONDS = 1800     # 30min safety cap regardless of mode


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


def watch_for_start_press(timeout_s=300):
    """Poll GetButtons over USB until BTN_START is pressed.

    Returns True if pressed within timeout, False otherwise. Robot must
    be awake and USB connected. Polls roughly every 0.5s.
    """
    import threading
    from neato_serial.neato import Neato

    n = object.__new__(Neato)
    n.port = SERIAL_PORT
    n.baud = 115200
    n.relay = None
    n.ser = None
    n._lock = threading.Lock()
    n.connect()

    print("[watch] polling GetButtons — press Start on the Neato...", flush=True)
    pressed = False
    t0 = time.time()
    try:
        while time.time() - t0 < timeout_s:
            try:
                raw = n.send("GetButtons", delay=0.2)
                # firmware returns "BTN_START,1" when held down
                if "BTN_START,1" in raw:
                    pressed = True
                    break
            except Exception:
                pass
            time.sleep(0.3)
    finally:
        n.close()
    return pressed


def is_idle(motors):
    """Return True when all relevant motors are at zero (no cleaning happening)."""
    if not motors:
        return False
    return (motors.get('Brush_RPM', 0) == 0
            and motors.get('Vacuum_RPM', 0) == 0
            and motors.get('LeftWheel_Speed', 0) == 0
            and motors.get('RightWheel_Speed', 0) == 0)


def is_charging(neato):
    """Quick non-blocking check: is the robot docked and charging?"""
    try:
        raw = neato.send('GetCharger', delay=0.3)
        return 'ChargingActive,1' in raw
    except Exception:
        return False


def auto_start_via_serial():
    """Send Clean command via serial, then immediately drop+restore USB.

    Bet: firmware queues the start request and begins cleaning when USB drops.
    Returns True if cleaning appears to be running afterward, False otherwise.
    """
    import threading
    from neato_serial.neato import Neato

    n = object.__new__(Neato)
    n.port = SERIAL_PORT
    n.baud = 115200
    n.relay = None
    n.ser = None
    n._lock = threading.Lock()
    n.connect()
    print("[auto-start] sending 'Clean' command...", flush=True)
    try:
        n.send("Clean", delay=0.5)
    except Exception as e:
        print(f"[auto-start] Clean send failed: {e}", flush=True)
    finally:
        n.close()
    return True


def log_clean_run(duration_s=120, watch=False, until_stopped=False, auto_start=False):
    # --- Phase 0: Collect metadata before any USB juggling ---
    metadata = collect_metadata(duration_s)
    metadata["watch_mode"] = watch
    metadata["until_stopped"] = until_stopped
    metadata["auto_start"] = auto_start

    relay = OutputDevice(RELAY_PIN, active_high=True, initial_value=True)

    if auto_start:
        # --- Auto-start flow: send Clean over serial, then bounce USB ---
        print("[log] auto-start mode — sending Clean via serial then dropping USB", flush=True)
        auto_start_via_serial()
        time.sleep(0.3)
        relay.off()
        if not wait_for_port(present=False, timeout=5):
            print("[log] WARNING: port didn't drop after relay off", flush=True)
        time.sleep(5)
        relay.on()
    elif watch:
        # --- Watch flow: USB stays on; we wait for the button, then bounce USB ---
        print("[log] watch mode — USB stays connected, waiting for Start press", flush=True)
        if not watch_for_start_press(timeout_s=300):
            print("[log] no Start press in 5 minutes — aborting", flush=True)
            return

        # User pressed Start. Firmware is showing "please unplug." Drop USB
        # so it processes the (queued) start command, then restore.
        print("[log] Start detected — bouncing USB to release the firmware", flush=True)
        relay.off()
        if not wait_for_port(present=False, timeout=5):
            print("[log] WARNING: port didn't drop after relay off", flush=True)
        time.sleep(5)  # give firmware time to begin cleaning
        relay.on()
    else:
        # --- Blind flow: drop USB first, user presses button during the window ---
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

        print("[log] restoring USB (relay on)...", flush=True)
        relay.on()

    # --- Common: wait for port + settle ---
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
    idle_streak = 0
    stop_reason = "duration_reached"

    if until_stopped:
        print(f"[log] until-stopped mode — capping at {MAX_RUN_SECONDS}s safety, idle stop after {IDLE_STOP_FRAMES} idle frames", flush=True)
    else:
        print(f"[log] logging for {duration_s}s — press Ctrl+C to stop early", flush=True)

    try:
        while True:
            elapsed = time.time() - t_start
            if until_stopped:
                if elapsed >= MAX_RUN_SECONDS:
                    stop_reason = "max_run_seconds_cap"
                    break
            else:
                if elapsed >= duration_s:
                    stop_reason = "duration_reached"
                    break
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

            # --- Stop-condition tracking when --until-stopped ---
            if until_stopped:
                if is_idle(motors):
                    idle_streak += 1
                    if idle_streak == 5:
                        print(f"[log] motors idle for 5 frames — verifying with charger check", flush=True)
                    if idle_streak >= IDLE_STOP_FRAMES:
                        if is_charging(neato):
                            stop_reason = "docked_and_charging"
                        else:
                            stop_reason = "motors_idle_timeout"
                        print(f"[log] stop condition: {stop_reason}", flush=True)
                        frame += 1
                        break
                else:
                    if idle_streak >= 5:
                        print(f"[log] motors active again — resetting idle streak", flush=True)
                    idle_streak = 0

            frame += 1

    except KeyboardInterrupt:
        print("\n[log] stopped early", flush=True)

    # Stop camera
    camera.stop()
    print("[log] camera stopped", flush=True)

    # Save raw log
    log_path = f"{out_dir}/sensor_log.json"
    with open(log_path, 'w') as f:
        json.dump(entries, f, indent=2)
    print(f"[log] saved {len(entries)} frames to {log_path} (stop_reason={stop_reason})", flush=True)

    # Save metadata
    metadata["stop_reason"] = stop_reason
    with open(f"{out_dir}/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    # Compute and save summary; update runs.json index
    summary = compute_summary(entries, metadata)
    summary["stop_reason"] = stop_reason
    with open(f"{out_dir}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    update_runs_index(out_dir, summary)
    print(f"[log] summary written + runs index updated", flush=True)

    # Don't try to stop cleaning — let it finish or user presses button
    neato.close()
    print("[log] done — press button on Neato to stop cleaning", flush=True)

    # Hailo cleanup workaround
    os._exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))
    args = [a for a in sys.argv[1:] if a]
    watch = "--watch" in args
    until_stopped = "--until-stopped" in args
    auto_start = "--auto-start" in args
    args = [a for a in args if not a.startswith("--")]
    duration = int(args[0]) if args else 120
    log_clean_run(duration, watch=watch, until_stopped=until_stopped, auto_start=auto_start)
