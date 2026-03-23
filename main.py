"""Scout main loop — reactive obstacle avoidance on Neato XV + Pi 5 + Hailo-10H.

Usage:
    python main.py              # normal run
    python main.py --dry-run    # no motor commands, just log decisions
"""

import json
import os
import signal
import sys
import time

from neato_serial.neato import Neato
from vision.capture import Camera
from vision.detector import Detector
from scout.perception import perceive
from scout.rules import RuleEngine, ActionType
from scout.driver import Driver
from scout.sensors import SensorMonitor
from scout.feedback import Feedback
from scout.logger import ScoutLogger

CONFIG_PATH = "config/scout.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def run(dry_run=False):
    config = load_config()
    print(f"[scout] config loaded — dry_run={dry_run}")

    # --- Neato ---
    neato = Neato()
    neato.connect()
    print("[scout] neato connected")

    # --- Camera + Detector ---
    camera = Camera(width=640, height=640)
    camera.start(settle_time=2)
    print("[scout] camera started")

    detector = Detector(
        confidence_threshold=config.get("confidence_threshold", 0.4)
    )
    detector.start()
    print("[scout] detector started (Hailo-10H)")

    # --- Scout modules ---
    sensor_monitor = SensorMonitor(
        neato, poll_interval=config.get("sensor_poll_interval_s", 0.15)
    )
    sensor_monitor.start()
    print("[scout] sensor monitor started")

    driver = Driver(neato, config)
    if not dry_run:
        driver.setup()
        print("[scout] driver ready (TestMode on)")

    rules = RuleEngine(config)
    feedback = Feedback(neato, config)
    logger = ScoutLogger("scout")

    feedback.startup()
    print("[scout] ready — press Ctrl+C to stop")

    # LiDAR state
    last_lidar_time = 0
    lidar_scan = None
    lidar_interval = config.get("lidar_interval_s", 30)

    frame_count = 0

    try:
        while True:
            t0 = time.time()

            # 1. Capture + detect
            frame = camera.capture()
            detections = detector.detect(frame)

            # 2. Read sensors (background thread + direct bumper check)
            sensor_state, bumper_hit, cliff, wheel_drop = sensor_monitor.check_and_clear()
            # Direct bumper check — background thread polls too slowly to
            # catch quick taps, so also check here in the main loop
            if not bumper_hit:
                try:
                    digital = neato.get_digital_sensors()
                    if (digital.get('LFRONTBIT', 0) or digital.get('RFRONTBIT', 0) or
                            digital.get('LSIDEBIT', 0) or digital.get('RSIDEBIT', 0)):
                        bumper_hit = True
                except Exception:
                    pass

            # 3. Perceive
            snapshot = perceive(
                detections, sensor_state, config,
                baseline_pitch=sensor_monitor.baseline_pitch,
                baseline_roll=sensor_monitor.baseline_roll,
                lidar_scan=lidar_scan,
            )

            # 4. Decide
            action = rules.decide(snapshot, bumper_hit, cliff, wheel_drop)

            # 5. Log
            save_img = logger.should_save_image(action, snapshot, frame_count, config)
            logger.log_frame(
                frame, snapshot, action, driver.odometry, sensor_state,
                lidar_scan=lidar_scan if lidar_scan else None,
                save_image=save_img,
            )

            # 6. Feedback (LED + sound)
            feedback.signal(action, bumper_hit=bumper_hit, cliff=cliff, wheel_drop=wheel_drop)

            # 7. Execute motor command
            if dry_run:
                desc = f"[dry-run] {action.action_type.value}: {action.reason}"
            else:
                desc = driver.execute(action)

            # 8. Fire LiDAR scan during motor wait (periodic)
            now = time.time()
            if now - last_lidar_time > lidar_interval:
                try:
                    lidar_scan = neato.get_lds_scan()
                    last_lidar_time = now
                except Exception:
                    lidar_scan = None

            elapsed = time.time() - t0
            frame_count += 1

            n_det = len(detections)
            labels = ", ".join(f"{o.label}({o.zone.value})" for o in snapshot.obstacles[:4])
            bumper_str = " BUMP!" if bumper_hit else ""
            print(f"[{frame_count:4d}] {elapsed:.2f}s | {desc} | "
                  f"wall={snapshot.wall_distance_mm}mm [{labels}]{bumper_str}",
                  flush=True)

    except KeyboardInterrupt:
        print("\n[scout] stopping...")

    finally:
        # Graceful shutdown
        sensor_monitor.stop()
        feedback.shutdown()
        if not dry_run:
            driver.teardown()
        camera.stop()

        summary_path = logger.save_summary()
        print(f"[scout] log saved: {summary_path}")

        neato.close()
        print("[scout] done")

        # Hailo cleanup workaround — avoid SIGABRT crash
        os._exit(0)


if __name__ == "__main__":
    # Handle SIGABRT from Hailo cleanup
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))

    dry_run = "--dry-run" in sys.argv
    run(dry_run=dry_run)
