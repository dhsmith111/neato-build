"""Analyze firmware Clean mode sensor logs.

Processes JSON logs from log_clean_mode.py runs, extracts key behavioral
metrics, and can compare across multiple sessions.

Usage:
    python analyze_clean_log.py captures/20260322_201514_clean_mode_log/
    python analyze_clean_log.py captures/*_clean_mode_log/     # compare all
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime


def load_log(log_dir):
    """Load sensor_log.json from a capture directory."""
    path = os.path.join(log_dir, "sensor_log.json")
    with open(path) as f:
        return json.load(f)


def analyze_run(data, label=""):
    """Extract behavioral metrics from a single run."""
    if not data:
        return None

    duration = data[-1]["elapsed_s"]
    n_frames = len(data)

    # --- Wheel speeds ---
    speeds = []
    for e in data:
        m = e.get("motors", {})
        speeds.append((m.get("LeftWheel_Speed", 0), m.get("RightWheel_Speed", 0)))

    # --- Behavior classification ---
    behaviors = {"straight": 0, "turn_left": 0, "turn_right": 0,
                 "spin_left": 0, "spin_right": 0, "backing": 0, "stopped": 0}
    for lw, rw in speeds:
        if lw == 0 and rw == 0:
            behaviors["stopped"] += 1
        elif lw < 0 and rw < 0:
            behaviors["backing"] += 1
        elif lw < 0 and rw > 0:
            behaviors["spin_left"] += 1
            behaviors["turn_left"] += 1
        elif lw > 0 and rw < 0:
            behaviors["spin_right"] += 1
            behaviors["turn_right"] += 1
        elif abs(lw - rw) < 30 and lw > 0 and rw > 0:
            behaviors["straight"] += 1
        elif lw > rw:
            behaviors["turn_right"] += 1
        else:
            behaviors["turn_left"] += 1

    # --- Speed stats ---
    lw_moving = [s[0] for s in speeds if s[0] != 0]
    rw_moving = [s[1] for s in speeds if s[1] != 0]
    lw_forward = [s[0] for s in speeds if s[0] > 0]
    rw_forward = [s[1] for s in speeds if s[1] > 0]

    speed_stats = {}
    if lw_forward:
        speed_stats["fwd_left_avg"] = sum(lw_forward) / len(lw_forward)
        speed_stats["fwd_left_max"] = max(lw_forward)
    if rw_forward:
        speed_stats["fwd_right_avg"] = sum(rw_forward) / len(rw_forward)
        speed_stats["fwd_right_max"] = max(rw_forward)
    if lw_moving:
        speed_stats["all_left_min"] = min(lw_moving)
        speed_stats["all_left_max"] = max(lw_moving)
    if rw_moving:
        speed_stats["all_right_min"] = min(rw_moving)
        speed_stats["all_right_max"] = max(rw_moving)

    # --- Wall sensor ---
    walls = [e.get("analog", {}).get("WallSensorInMM", None) for e in data]
    walls = [w for w in walls if w is not None]
    wall_stats = {}
    if walls:
        wall_stats = {
            "min": min(walls),
            "max": max(walls),
            "avg": sum(walls) / len(walls),
            "close_count": sum(1 for w in walls if w < 20),
            "contact_count": sum(1 for w in walls if w < 5),
        }

    # --- Wall following segments (consecutive frames with wall < 20mm) ---
    wall_follow_segments = []
    in_segment = False
    seg_start = 0
    for i, w in enumerate(walls):
        if w < 20 and not in_segment:
            in_segment = True
            seg_start = i
        elif w >= 20 and in_segment:
            in_segment = False
            wall_follow_segments.append((seg_start, i - 1, i - seg_start))
    if in_segment:
        wall_follow_segments.append((seg_start, len(walls) - 1, len(walls) - seg_start))

    # --- Bumpers ---
    bumps_front = 0
    bumps_side = 0
    bump_frames = []
    for i, e in enumerate(data):
        d = e.get("digital", {})
        front = d.get("LFRONTBIT", 0) or d.get("RFRONTBIT", 0)
        side = d.get("LSIDEBIT", 0) or d.get("RSIDEBIT", 0)
        if front:
            bumps_front += 1
            bump_frames.append((i, "front"))
        if side:
            bumps_side += 1
            bump_frames.append((i, "side"))

    # --- Brush/Vacuum ---
    brush_rpms = [e.get("motors", {}).get("Brush_RPM", 0) for e in data]
    vac_rpms = [e.get("motors", {}).get("Vacuum_RPM", 0) for e in data]
    brush_active = [b for b in brush_rpms if b > 0]
    vac_active = [v for v in vac_rpms if v > 0]

    cleaning_stats = {}
    if brush_active:
        cleaning_stats["brush_avg_rpm"] = sum(brush_active) / len(brush_active)
    if vac_active:
        cleaning_stats["vacuum_avg_rpm"] = sum(vac_active) / len(vac_active)

    # --- Odometry ---
    positions = []
    for e in data:
        m = e.get("motors", {})
        lp = m.get("LeftWheel_PositionInMM", 0)
        rp = m.get("RightWheel_PositionInMM", 0)
        if lp != 0 or rp != 0:
            positions.append((lp, rp))

    odo = {}
    if len(positions) >= 2:
        start_l, start_r = positions[0]
        end_l, end_r = positions[-1]
        odo["left_total_mm"] = end_l - start_l
        odo["right_total_mm"] = end_r - start_r
        odo["avg_distance_mm"] = (odo["left_total_mm"] + odo["right_total_mm"]) / 2
        odo["avg_speed_mm_s"] = odo["avg_distance_mm"] / duration if duration > 0 else 0

    # --- Turn sequences (what happens around bumps) ---
    bump_responses = []
    for frame_i, bump_type in bump_frames:
        # Look at 3 frames before and after bump
        window = []
        for j in range(max(0, frame_i - 2), min(len(data), frame_i + 4)):
            e = data[j]
            m = e.get("motors", {})
            w = e.get("analog", {}).get("WallSensorInMM", 0)
            window.append({
                "frame": j,
                "wall_mm": w,
                "left_speed": m.get("LeftWheel_Speed", 0),
                "right_speed": m.get("RightWheel_Speed", 0),
            })
        bump_responses.append({
            "frame": frame_i,
            "type": bump_type,
            "sequence": window,
        })

    # --- Detections ---
    det_labels = []
    for e in data:
        for d in e.get("detections", []):
            det_labels.append(d["label"])

    return {
        "label": label,
        "duration_s": duration,
        "n_frames": n_frames,
        "fps": n_frames / duration if duration > 0 else 0,
        "behaviors": behaviors,
        "speed_stats": speed_stats,
        "wall_stats": wall_stats,
        "wall_follow_segments": wall_follow_segments,
        "bumps_front": bumps_front,
        "bumps_side": bumps_side,
        "bump_responses": bump_responses,
        "cleaning_stats": cleaning_stats,
        "odometry": odo,
        "detections": dict(Counter(det_labels)),
    }


def print_analysis(a):
    """Pretty-print a single run analysis."""
    print(f"\n{'=' * 60}")
    print(f"  RUN: {a['label']}")
    print(f"{'=' * 60}")
    print(f"Duration: {a['duration_s']:.1f}s | Frames: {a['n_frames']} | "
          f"Rate: {a['fps']:.1f} fps")

    print(f"\n--- Behaviors ---")
    b = a["behaviors"]
    total = sum(b.values())
    for key in ["straight", "turn_left", "turn_right", "spin_left", "spin_right", "backing", "stopped"]:
        pct = b[key] / total * 100 if total > 0 else 0
        print(f"  {key:15s}: {b[key]:3d} ({pct:4.1f}%)")

    print(f"\n--- Wheel Speeds (mm/s) ---")
    s = a["speed_stats"]
    if s:
        print(f"  Forward avg:  L={s.get('fwd_left_avg', 0):.0f}  R={s.get('fwd_right_avg', 0):.0f}")
        print(f"  Forward max:  L={s.get('fwd_left_max', 0):.0f}  R={s.get('fwd_right_max', 0):.0f}")
        print(f"  Overall range: L=[{s.get('all_left_min', 0):.0f}, {s.get('all_left_max', 0):.0f}]  "
              f"R=[{s.get('all_right_min', 0):.0f}, {s.get('all_right_max', 0):.0f}]")

    print(f"\n--- Wall Sensor ---")
    w = a["wall_stats"]
    if w:
        print(f"  Range: {w['min']}-{w['max']}mm  Avg: {w['avg']:.0f}mm")
        print(f"  Close (<20mm): {w['close_count']} frames  Contact (<5mm): {w['contact_count']} frames")
        if a["wall_follow_segments"]:
            print(f"  Wall-follow segments: {len(a['wall_follow_segments'])}")
            for start, end, length in a["wall_follow_segments"]:
                print(f"    frames {start}-{end} ({length} frames)")

    print(f"\n--- Bumpers ---")
    print(f"  Front: {a['bumps_front']}  Side: {a['bumps_side']}")
    for br in a["bump_responses"]:
        print(f"  [{br['type']}] at frame {br['frame']}:")
        for step in br["sequence"]:
            print(f"    f{step['frame']:3d}: wall={step['wall_mm']:3d}mm  "
                  f"L={step['left_speed']:4.0f} R={step['right_speed']:4.0f}")

    print(f"\n--- Cleaning Motors ---")
    c = a["cleaning_stats"]
    if c:
        print(f"  Brush: {c.get('brush_avg_rpm', 0):.0f} RPM avg")
        print(f"  Vacuum: {c.get('vacuum_avg_rpm', 0):.0f} RPM avg")

    print(f"\n--- Odometry ---")
    o = a["odometry"]
    if o:
        print(f"  Total: L={o['left_total_mm']:.0f}mm  R={o['right_total_mm']:.0f}mm")
        print(f"  Avg distance: {o['avg_distance_mm']:.0f}mm ({o['avg_distance_mm']/1000:.1f}m)")
        print(f"  Avg speed: {o['avg_speed_mm_s']:.0f} mm/s ({o['avg_speed_mm_s']/1000*60:.1f} m/min)")

    if a["detections"]:
        print(f"\n--- YOLO Detections ---")
        for label, count in sorted(a["detections"].items(), key=lambda x: -x[1]):
            print(f"  {label}: {count}")


def print_comparison(analyses):
    """Compare key metrics across multiple runs."""
    if len(analyses) < 2:
        return

    print(f"\n{'=' * 60}")
    print(f"  COMPARISON ({len(analyses)} runs)")
    print(f"{'=' * 60}")

    # Header
    labels = [a["label"][:20] for a in analyses]
    header = f"{'Metric':30s}" + "".join(f"{l:>15s}" for l in labels)
    print(header)
    print("-" * len(header))

    def row(name, values, fmt=".0f"):
        vals = "".join(f"{v:>15{fmt}}" if v is not None else f"{'n/a':>15s}" for v in values)
        print(f"{name:30s}{vals}")

    row("Duration (s)", [a["duration_s"] for a in analyses], ".1f")
    row("Frames", [a["n_frames"] for a in analyses])
    row("Avg speed (mm/s)", [a["odometry"].get("avg_speed_mm_s", 0) for a in analyses])
    row("Total distance (m)", [a["odometry"].get("avg_distance_mm", 0) / 1000 for a in analyses], ".1f")
    row("Straight %", [a["behaviors"]["straight"] / a["n_frames"] * 100 for a in analyses], ".1f")
    row("Turning %", [(a["behaviors"]["turn_left"] + a["behaviors"]["turn_right"]) / a["n_frames"] * 100 for a in analyses], ".1f")
    row("Wall avg (mm)", [a["wall_stats"].get("avg", 0) for a in analyses])
    row("Wall contacts (<5mm)", [a["wall_stats"].get("contact_count", 0) for a in analyses])
    row("Side bumps", [a["bumps_side"] for a in analyses])
    row("Front bumps", [a["bumps_front"] for a in analyses])
    row("Brush RPM", [a["cleaning_stats"].get("brush_avg_rpm", 0) for a in analyses])
    row("Vacuum RPM", [a["cleaning_stats"].get("vacuum_avg_rpm", 0) for a in analyses])


def save_summary(analyses, out_path="docs/firmware_behavior_summary.json"):
    """Save analysis results to JSON for future reference."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Convert for JSON serialization
    output = {
        "generated": datetime.now().isoformat(),
        "runs": analyses,
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    import glob

    if len(sys.argv) < 2:
        # Auto-find all clean mode logs
        dirs = sorted(glob.glob("captures/*_clean_mode_log"))
    else:
        dirs = []
        for arg in sys.argv[1:]:
            dirs.extend(sorted(glob.glob(arg)))

    if not dirs:
        print("No clean mode log directories found.")
        print("Usage: python analyze_clean_log.py captures/*_clean_mode_log/")
        sys.exit(1)

    analyses = []
    for d in dirs:
        d = d.rstrip("/")
        log_path = os.path.join(d, "sensor_log.json")
        if not os.path.exists(log_path):
            print(f"Skipping {d} — no sensor_log.json")
            continue
        label = os.path.basename(d)
        data = load_log(d)
        a = analyze_run(data, label)
        if a:
            analyses.append(a)
            print_analysis(a)

    if len(analyses) > 1:
        print_comparison(analyses)

    if analyses:
        save_summary(analyses)
