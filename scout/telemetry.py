"""Telemetry helpers for firmware-observation runs.

Used by log_clean_mode.py to:
- Collect run metadata interactively at start
- Auto-write a per-run summary.json after capture
- Maintain a top-level captures/runs.json index of all runs
"""

import json
import os
from collections import Counter
from datetime import datetime


CAPTURES_DIR = "captures"
RUNS_INDEX = os.path.join(CAPTURES_DIR, "runs.json")


def collect_metadata(duration_s):
    """Interactive prompt for run metadata. Returns a dict.

    All fields optional — empty input becomes None. Goal is to capture
    *context* the data file alone can't tell us later (room, lighting,
    what was on the floor, anything unusual).
    """
    print("", flush=True)
    print("=" * 50, flush=True)
    print("  RUN METADATA (press Enter to skip a field)", flush=True)
    print("=" * 50, flush=True)

    def ask(prompt):
        try:
            v = input(f"  {prompt}: ").strip()
            return v if v else None
        except EOFError:
            return None

    meta = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "duration_s_planned": duration_s,
        "room": ask("Room (e.g. kitchen, hallway, living)"),
        "starting_position": ask("Starting position (e.g. on dock, mid-floor)"),
        "lighting": ask("Lighting (e.g. daylight, lamp, dark)"),
        "obstacles": ask("Obstacles present (e.g. rug, cable, cat)"),
        "mode": ask("Cleaning mode (e.g. Clean, Spot)") or "Clean",
        "notes": ask("Notes (anything to remember)"),
    }
    print("=" * 50, flush=True)
    print("", flush=True)
    return meta


def classify_motion(lw_speed, rw_speed):
    """Crude motion classifier for a single frame.

    Not a behavior classifier — just a coarse bucket so summary stats can
    show "robot was moving forward 60% of the time" etc. Real behavior
    inspection is human-in-the-loop.
    """
    if lw_speed == 0 and rw_speed == 0:
        return "stopped"
    if lw_speed < 0 and rw_speed < 0:
        return "backing"
    if lw_speed > 0 and rw_speed < 0:
        return "spin_right"
    if lw_speed < 0 and rw_speed > 0:
        return "spin_left"
    if abs(lw_speed - rw_speed) < 30 and lw_speed > 0:
        return "straight"
    return "turn_right" if lw_speed > rw_speed else "turn_left"


def compute_summary(entries, metadata):
    """Build a summary.json dict from raw frame entries.

    Stats are intentionally simple — total distance from wheel odometry,
    bumper events, wall-sensor distribution, motion bucket breakdown,
    YOLO detection counts. Just enough to skim a run at a glance.
    """
    if not entries:
        return {"frames": 0, "metadata": metadata}

    motion_counts = Counter()
    bumper_front_hits = 0
    bumper_side_hits = 0
    wall_readings = []
    det_counts = Counter()
    pitch_max = 0.0
    roll_max = 0.0
    battery_start_mv = None
    battery_end_mv = None

    lw_pos_first = None
    lw_pos_last = None
    rw_pos_first = None
    rw_pos_last = None

    prev_front = 0
    prev_side = 0

    for e in entries:
        m = e.get("motors", {})
        lw = m.get("LeftWheel_Speed", 0)
        rw = m.get("RightWheel_Speed", 0)
        motion_counts[classify_motion(lw, rw)] += 1

        lp = m.get("LeftWheel_PositionInMM")
        rp = m.get("RightWheel_PositionInMM")
        if lp is not None:
            if lw_pos_first is None:
                lw_pos_first = lp
            lw_pos_last = lp
        if rp is not None:
            if rw_pos_first is None:
                rw_pos_first = rp
            rw_pos_last = rp

        d = e.get("digital", {})
        front = d.get("LFRONTBIT", 0) or d.get("RFRONTBIT", 0)
        side = d.get("LSIDEBIT", 0) or d.get("RSIDEBIT", 0)
        if front and not prev_front:
            bumper_front_hits += 1
        if side and not prev_side:
            bumper_side_hits += 1
        prev_front, prev_side = front, side

        a = e.get("analog", {})
        wall = a.get("WallSensorInMM")
        if isinstance(wall, (int, float)):
            wall_readings.append(wall)
        bv = a.get("BatteryVoltageInmV")
        if isinstance(bv, (int, float)):
            if battery_start_mv is None:
                battery_start_mv = bv
            battery_end_mv = bv

        ac = e.get("accel", {})
        if isinstance(ac, dict):
            try:
                pitch_max = max(pitch_max, abs(float(ac.get("PitchInDegrees", 0))))
                roll_max = max(roll_max, abs(float(ac.get("RollInDegrees", 0))))
            except (TypeError, ValueError):
                pass

        for det in e.get("detections", []):
            det_counts[det.get("label", "?")] += 1

    distance_l_mm = (lw_pos_last - lw_pos_first) if lw_pos_first is not None else 0
    distance_r_mm = (rw_pos_last - rw_pos_first) if rw_pos_first is not None else 0
    distance_avg_mm = (distance_l_mm + distance_r_mm) / 2

    return {
        "metadata": metadata,
        "frames": len(entries),
        "duration_s_actual": entries[-1].get("elapsed_s"),
        "distance_mm": {
            "left": distance_l_mm,
            "right": distance_r_mm,
            "avg": round(distance_avg_mm, 1),
        },
        "bumper_events": {
            "front_hits": bumper_front_hits,
            "side_hits": bumper_side_hits,
        },
        "wall_sensor_mm": {
            "min": min(wall_readings) if wall_readings else None,
            "max": max(wall_readings) if wall_readings else None,
            "avg": round(sum(wall_readings) / len(wall_readings), 1) if wall_readings else None,
            "samples": len(wall_readings),
        },
        "motion_breakdown": dict(motion_counts),
        "yolo_detections": dict(det_counts.most_common()),
        "tilt_max_degrees": {
            "pitch_abs_max": round(pitch_max, 2),
            "roll_abs_max": round(roll_max, 2),
        },
        "battery_mv": {
            "start": battery_start_mv,
            "end": battery_end_mv,
            "delta": (battery_end_mv - battery_start_mv) if battery_start_mv and battery_end_mv else None,
        },
    }


def update_runs_index(run_dir, summary):
    """Append/update a single run's entry in captures/runs.json.

    The index is a list of compact records — one per run — so we can scan
    all runs at a glance without loading every sensor_log.json.
    """
    index = []
    if os.path.exists(RUNS_INDEX):
        try:
            with open(RUNS_INDEX) as f:
                index = json.load(f)
        except (json.JSONDecodeError, ValueError):
            index = []

    rel_dir = os.path.relpath(run_dir, CAPTURES_DIR)
    record = {
        "dir": rel_dir,
        "started_at": summary.get("metadata", {}).get("started_at"),
        "room": summary.get("metadata", {}).get("room"),
        "obstacles": summary.get("metadata", {}).get("obstacles"),
        "frames": summary.get("frames"),
        "duration_s": summary.get("duration_s_actual"),
        "distance_mm_avg": summary.get("distance_mm", {}).get("avg"),
        "front_bumps": summary.get("bumper_events", {}).get("front_hits"),
        "side_bumps": summary.get("bumper_events", {}).get("side_hits"),
        "battery_delta_mv": summary.get("battery_mv", {}).get("delta"),
    }

    index = [r for r in index if r.get("dir") != rel_dir]
    index.append(record)
    index.sort(key=lambda r: r.get("started_at") or "")

    with open(RUNS_INDEX, "w") as f:
        json.dump(index, f, indent=2)
