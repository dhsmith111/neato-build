"""pilot.py — interactive vacuum control primitives + autonomous driving daemon.

One-shot subcommands print structured JSON to stdout. The daemon keeps
camera + detector + serial open for low-latency command chains.

Subcommands:
    state                           -- read sensors, print JSON
    look [--save PATH]              -- frame + YOLO + state, print JSON
    forward <mm> [--speed N]        -- drive straight forward
    back <mm> [--speed N]           -- drive straight backward
    pivot <degrees> <left|right> [--speed N]  -- rotate in place
    stop                            -- release motors and exit TestMode
    serve                           -- start unix-socket daemon
    send <action> [args]            -- send one command to running daemon
"""

import argparse
import json
import math
import os
import signal
import sys
import threading
import time

WHEEL_BASE_MM = 240   # Neato XV wheel separation
SERIAL_PORT = '/dev/ttyACM0'
SOCKET_PATH = '/tmp/pilot.sock'

# Driving constants
WALL_TARGET_MM = 300        # ideal distance to right wall
WALL_CLOSE_MM = 150         # wall this close → drift left
WALL_FAR_MM = 500           # wall this far → drift right (if following)
WALL_CLEAR_MM = 1000        # beyond this = open space, ignore wall
WALL_MIN_VALID_MM = 100     # readings below this = pod self-interference, ignore

# Camera is angled ~30° downward, wide-angle lens. Bbox area is not a reliable
# distance metric. These thresholds were calibrated against confirmed cases:
# - Vase at ~70mm (right next to robot): bbox_area ~0.11
# - Couch at ~2m away: bbox_area ~0.03
# Danger = genuinely blocking the path; caution = visible but may not be in path.
BBOX_DANGER = 0.15          # bbox_area > this → very close, likely in path
BBOX_CAUTION = 0.10         # bbox_area > this → close, slow down

FORWARD_SPEED = 250         # mm/s normal
SLOW_SPEED = 150            # mm/s near obstacles
PIVOT_SPEED = 130           # mm/s for turns

STEP_CLEAR_MM = 300         # forward step when clear
STEP_CAUTION_MM = 150       # forward step when cautious
BACKUP_MM = 150             # backup when bumper hit
PIVOT_SMALL = 20            # gentle course correction (degrees)
PIVOT_MEDIUM = 45           # normal turn
PIVOT_LARGE = 90            # corner/dead-end turn


def open_neato():
    """Open serial to Neato, autodetect port (ttyACM0/1 drift after relay)."""
    from neato_serial.neato import Neato
    n = object.__new__(Neato)
    ports = sorted([p for p in os.listdir('/dev') if p.startswith('ttyACM')])
    if not ports:
        raise RuntimeError("no /dev/ttyACM* port present — robot asleep?")
    n.port = '/dev/' + ports[0]
    n.baud = 115200
    n.relay = None
    n.ser = None
    n._lock = threading.Lock()
    n.connect()
    time.sleep(0.3)
    return n


def read_state(neato, motors=True):
    """Return sensor + motor state dict. Pass motors=False to skip GetMotors (faster)."""
    out = {}
    try:
        out['digital'] = neato.get_digital_sensors()
    except Exception as e:
        out['digital_error'] = str(e)
    try:
        out['analog'] = neato.get_analog_sensors()
    except Exception as e:
        out['analog_error'] = str(e)
    try:
        out['accel'] = neato.get_accel_parsed()
    except Exception as e:
        out['accel_error'] = str(e)
    if motors:
        try:
            raw = neato.send('GetMotors', delay=0.3)
            m = {}
            for line in raw.strip().split('\n'):
                if ',' in line and not line.startswith('Parameter'):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            m[parts[0].strip()] = float(parts[1].strip())
                        except ValueError:
                            pass
            out['motors'] = m
        except Exception as e:
            out['motors_error'] = str(e)
    return out


def read_lidar_summary(neato):
    """Read LiDAR and return cardinal distances (mm). Returns None on failure.

    LDS scan format: angle,distance_mm,intensity,error_code per line.
    Angle 0 = directly behind robot on XV; adjust offset to match physical front.
    Returns dict: {front, right, left, rear, min_front_arc, clear_ahead}
    """
    # XV Signature Pro: angle 0 = rear (back of robot), 180 = front (bumper direction).
    # 90 = robot's right, 270 = robot's left.
    # Validated by physical compass test 2026-05-09.
    FRONT_ANGLE = 180
    RIGHT_ANGLE = 90
    LEFT_ANGLE = 270
    ARC_HALF = 20      # degrees either side to average

    try:
        raw = neato.send('GetLDSScan', delay=1.2)
        readings = {}
        for line in raw.strip().split('\n'):
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    angle = int(parts[0])
                    dist = int(parts[1])
                    err = int(parts[3]) if len(parts) > 3 else 0
                    if err == 0 and dist > 0:
                        readings[angle] = dist
                except (ValueError, IndexError):
                    pass

        def arc_min(center, half):
            vals = [readings[a] for a in range(center - half, center + half + 1)
                    if a in readings and readings[a] > 0]
            return min(vals) if vals else None

        front_dist = arc_min(FRONT_ANGLE, ARC_HALF)
        right_dist = arc_min(RIGHT_ANGLE, ARC_HALF)
        left_dist  = arc_min(LEFT_ANGLE, ARC_HALF)

        # Wide front arc for "is there anything ahead"
        front_wide = arc_min(FRONT_ANGLE, 40)

        return {
            "front_mm": front_dist,
            "right_mm": right_dist,
            "left_mm": left_dist,
            "front_wide_mm": front_wide,
            "clear_ahead": front_dist is None or front_dist > 500,
            "n_valid": len(readings),
        }
    except Exception as e:
        return {"error": str(e)}


def safety_blocked(state, direction='forward'):
    """Return reason string if a safety sensor is asserted, else None.

    Forward blocks on front bumper + cliff. Backward only blocks on cliff/wheel-drop
    (front bumper is why we're reversing — don't let it trap us).
    """
    d = state.get('digital', {})
    if direction == 'forward':
        if d.get('LFRONTBIT', 0) or d.get('RFRONTBIT', 0):
            return 'front_bumper'
        if d.get('LSIDEBIT', 0) or d.get('RSIDEBIT', 0):
            return 'side_bumper'
    a = state.get('analog', {})
    ld = a.get('LeftDropInMM')
    rd = a.get('RightDropInMM')
    if isinstance(ld, (int, float)) and ld < 5:
        return 'left_cliff'
    if isinstance(rd, (int, float)) and rd < 5:
        return 'right_cliff'
    if d.get('SNSR_LEFT_WHEEL_EXTENDED', 0) or d.get('SNSR_RIGHT_WHEEL_EXTENDED', 0):
        return 'wheel_drop'
    return None


def classify_detections(det_list):
    """Classify detected objects into danger/caution/clear zones.

    Returns (danger_labels, caution_labels, largest_bbox_area).
    Uses bbox_area as a proxy for distance — big box = close obstacle.
    """
    danger = []
    caution = []
    largest = 0.0
    for d in det_list:
        area = d.get('bbox_area', 0)
        label = d.get('label', '?')
        largest = max(largest, area)
        if area >= BBOX_DANGER:
            danger.append(label)
        elif area >= BBOX_CAUTION:
            caution.append(label)
    return danger, caution, largest


def obstacle_side(det_list):
    """Guess which side obstacles are on based on bbox center x.

    Returns 'left', 'right', 'center', or None.
    Only looks at objects in danger/caution range.
    """
    relevant = [d for d in det_list if d.get('bbox_area', 0) >= BBOX_CAUTION]
    if not relevant:
        return None
    centers = []
    for d in relevant:
        bb = d.get('bbox', [0, 0, 1, 1])
        cx = (bb[0] + bb[2]) / 2
        centers.append(cx)
    avg_cx = sum(centers) / len(centers)
    if avg_cx < 0.35:
        return 'left'
    if avg_cx > 0.65:
        return 'right'
    return 'center'


def drive_straight_daemon(neato, distance_mm, speed_mm_s, direction):
    """Drive straight in daemon context — chunked with mid-move safety checks."""
    CHUNK_MM = 150
    remaining = abs(distance_mm)
    sign = 1 if direction > 0 else -1
    abort_reason = None
    moved_mm = 0
    safety_dir = 'forward' if direction > 0 else 'backward'

    while remaining > 0:
        chunk = min(CHUNK_MM, remaining)
        pre = read_state(neato, motors=False)
        block = safety_blocked(pre, safety_dir)
        if block:
            abort_reason = f'pre_{block}'
            break
        signed = sign * chunk
        try:
            neato.send(
                f"SetMotor LWheelDist {signed} RWheelDist {signed} Speed {speed_mm_s}",
                delay=0.05,
            )
        except Exception as e:
            abort_reason = f'serial:{e}'
            break
        wait_s = (chunk / max(speed_mm_s, 1)) + 0.15
        time.sleep(wait_s)
        moved_mm += chunk
        remaining -= chunk
        post = read_state(neato, motors=False)
        block = safety_blocked(post, safety_dir)
        if block:
            abort_reason = f'mid_{block}'
            break

    smooth_stop(neato)
    return moved_mm, abort_reason


def smooth_stop(neato):
    """Two-step deceleration to avoid abrupt forward tilt on stop.

    Firmware tip from clean-run analysis: natural speed increments are ~25mm/s.
    A brief 50mm/s step before zero significantly reduces the jerk.
    """
    try:
        neato.send("SetMotor LWheelDist 8 RWheelDist 8 Speed 60", delay=0.05)
        time.sleep(0.12)
        neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.05)
    except Exception:
        pass


def arc_turn(neato, distance_mm, inner_speed, outer_speed, direction):
    """Curved move: both wheels move but at different speeds.

    Smoother than stop-pivot-go. direction='left' → left wheel slower.
    inner_speed / outer_speed: typical ratio ~25%/100% for gentle curve.
    Returns (moved_mm, error).
    """
    if direction == 'left':
        l_speed, r_speed = inner_speed, outer_speed
    else:
        l_speed, r_speed = outer_speed, inner_speed

    l_dist = int(distance_mm * l_speed / max(outer_speed, 1))
    r_dist = int(distance_mm * r_speed / max(outer_speed, 1))
    max_speed = max(l_speed, r_speed)

    try:
        neato.send(
            f"SetMotor LWheelDist {l_dist} RWheelDist {r_dist} Speed {max_speed}",
            delay=0.05,
        )
        wait_s = distance_mm / max(max_speed, 1) + 0.2
        time.sleep(wait_s)
        smooth_stop(neato)
        return distance_mm, None
    except Exception as e:
        return 0, str(e)


def pivot_daemon(neato, degrees, direction, speed=PIVOT_SPEED):
    """Pivot in place. Returns (arc_mm, error)."""
    arc = int(math.pi * WHEEL_BASE_MM * (degrees / 360.0))
    l_dist, r_dist = (-arc, arc) if direction == 'left' else (arc, -arc)
    try:
        neato.send(f"SetMotor LWheelDist {l_dist} RWheelDist {r_dist} Speed {speed}", delay=0.05)
        time.sleep(arc / max(speed, 1) + 0.3)
        neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.05)
        return arc, None
    except Exception as e:
        return 0, str(e)


def choose_action(det_list, state, recent_bumps=0):
    """Pure decision function: given detections + sensor state, choose next move.

    Returns a dict: {action, params, reason}

    recent_bumps: count of bumpers in recent steps — escalates response.

    Priority:
      1. Bumper hit → backup + pivot away (larger if repeated)
      2. Cliff/wheel-drop → stop (handled upstream by safety_blocked)
      3. Vision danger zone → stop + pivot away from obstacle
      4. Vision caution zone → slow step + gentle correction
      5. Wall sensor tight → go straight (don't nudge if repeatedly bumping)
      6. Wall in range → go straight
      7. Clear → full step forward
    """
    d = state.get('digital', {})
    a = state.get('analog', {})

    front_bump = d.get('LFRONTBIT', 0) or d.get('RFRONTBIT', 0)
    left_front = d.get('LFRONTBIT', 0)
    left_side = d.get('LSIDEBIT', 0)
    right_bump = d.get('RFRONTBIT', 0) or d.get('RSIDEBIT', 0)
    side_bump = d.get('LSIDEBIT', 0) or d.get('RSIDEBIT', 0)
    wall_mm = a.get('WallSensorInMM', 9999)

    danger, caution, largest_area = classify_detections(det_list)
    obs_side = obstacle_side(det_list)

    # Bumper: back up then pivot away — escalate angle with repeated hits
    if front_bump or side_bump:
        # Left hit → pivot right; right hit → pivot left; both → bigger pivot
        if left_front or left_side:
            pivot_dir = 'right'
        elif right_bump:
            pivot_dir = 'left'
        else:
            pivot_dir = 'right'

        # Escalate: first hit=45, second hit=70, third+=90
        pivot_deg = min(PIVOT_LARGE, PIVOT_MEDIUM + recent_bumps * 25)
        backup_mm = BACKUP_MM + recent_bumps * 50  # back more if stuck

        return {
            "action": "sequence",
            "steps": [
                {"action": "back", "mm": backup_mm, "speed": SLOW_SPEED},
                {"action": "pivot", "degrees": pivot_deg, "direction": pivot_dir},
                {"action": "forward", "mm": STEP_CAUTION_MM, "speed": SLOW_SPEED},
            ],
            "reason": (
                f"bumper: front={front_bump} side={side_bump} recent={recent_bumps} "
                f"→ back{backup_mm}+pivot{pivot_deg}_{pivot_dir}"
            ),
        }

    # Vision danger — something very close
    if danger:
        if obs_side == 'left':
            pivot_dir = 'right'
        elif obs_side == 'right':
            pivot_dir = 'left'
        else:
            pivot_dir = 'right'
        return {
            "action": "sequence",
            "steps": [
                {"action": "back", "mm": 80, "speed": SLOW_SPEED},
                {"action": "pivot", "degrees": PIVOT_MEDIUM, "direction": pivot_dir},
            ],
            "reason": f"vision_danger: {danger} ({obs_side}) → back+pivot_{pivot_dir}",
        }

    # Vision caution — obstacle moderately close
    if caution:
        if obs_side == 'left':
            correction = {"action": "pivot", "degrees": PIVOT_SMALL, "direction": "right"}
        elif obs_side == 'right':
            correction = {"action": "pivot", "degrees": PIVOT_SMALL, "direction": "left"}
        else:
            correction = {"action": "pivot", "degrees": PIVOT_MEDIUM, "direction": "right"}
        return {
            "action": "sequence",
            "steps": [
                correction,
                {"action": "forward", "mm": STEP_CAUTION_MM, "speed": SLOW_SPEED},
            ],
            "reason": f"vision_caution: {caution} ({obs_side}) → correct+slow_step",
        }

    # Wall: too close on right → nudge left (but only if not in a bumper streak)
    # Readings below WALL_MIN_VALID_MM are pod self-interference — ignore.
    wall_valid = (
        isinstance(wall_mm, (int, float))
        and WALL_MIN_VALID_MM <= wall_mm < WALL_CLEAR_MM
    )
    if wall_valid:
        if wall_mm < WALL_CLOSE_MM and recent_bumps < 2:
            return {
                "action": "sequence",
                "steps": [
                    {"action": "pivot", "degrees": PIVOT_SMALL, "direction": "left"},
                    {"action": "forward", "mm": STEP_CLEAR_MM, "speed": FORWARD_SPEED},
                ],
                "reason": f"wall_close: {wall_mm}mm recent_bumps={recent_bumps} → nudge_left",
            }
        if wall_mm > WALL_FAR_MM and recent_bumps < 2:
            return {
                "action": "sequence",
                "steps": [
                    {"action": "pivot", "degrees": PIVOT_SMALL, "direction": "right"},
                    {"action": "forward", "mm": STEP_CLEAR_MM, "speed": FORWARD_SPEED},
                ],
                "reason": f"wall_far: {wall_mm}mm → nudge_right",
            }

    # Default: go straight
    return {
        "action": "forward",
        "mm": STEP_CLEAR_MM,
        "speed": FORWARD_SPEED,
        "reason": f"clear: wall={wall_mm}mm no_obstacles",
    }


# ─── one-shot command functions (used without daemon) ────────────────────────

def cmd_state():
    n = open_neato()
    try:
        s = read_state(n)
        s['port'] = n.port
        print(json.dumps(s, indent=2))
    finally:
        n.close()


def cmd_look(save_path=None):
    from vision.capture import Camera
    from vision.detector import Detector
    from PIL import Image

    n = open_neato()
    cam = Camera(width=640, height=640)
    cam.start(settle_time=1)
    det = Detector(confidence_threshold=0.4)
    det.start()

    try:
        frame = cam.capture()
        detections = det.detect(frame)
        det_list = [
            {"label": d.label, "confidence": round(d.confidence, 3),
             "bbox": [round(d.x_min, 3), round(d.y_min, 3),
                      round(d.x_max, 3), round(d.y_max, 3)],
             "bbox_area": round((d.x_max - d.x_min) * (d.y_max - d.y_min), 3)}
            for d in detections
        ]
        state = read_state(n)
        result = {"detections": det_list, "state": state}
        if save_path:
            Image.fromarray(frame).save(save_path, quality=85)
            result["saved_image"] = save_path
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        sys.stdout.flush()
    finally:
        cam.stop()
        n.close()
        os._exit(0)


def _drive_straight_oneshot(neato, distance_mm, speed_mm_s, direction):
    CHUNK_MM = 200
    remaining = abs(distance_mm)
    sign = 1 if direction > 0 else -1
    abort_reason = None
    moved_mm = 0
    safety_dir = 'forward' if direction > 0 else 'backward'

    while remaining > 0:
        chunk = min(CHUNK_MM, remaining)
        pre = read_state(neato, motors=False)
        block = safety_blocked(pre, safety_dir)
        if block:
            abort_reason = f'pre_move_{block}'
            break
        signed = sign * chunk
        try:
            neato.send(f"SetMotor LWheelDist {signed} RWheelDist {signed} Speed {speed_mm_s}", delay=0.1)
        except Exception as e:
            abort_reason = f'serial_error:{e}'
            break
        wait_s = (chunk / max(speed_mm_s, 1)) + 0.4
        time.sleep(wait_s)
        moved_mm += chunk
        remaining -= chunk
        post = read_state(neato, motors=False)
        block = safety_blocked(post, safety_dir)
        if block:
            abort_reason = f'mid_move_{block}'
            break

    return moved_mm, abort_reason


def cmd_forward(distance_mm, speed_mm_s):
    n = open_neato()
    try:
        n.test_mode(on=True)
        time.sleep(0.3)
        moved, abort = _drive_straight_oneshot(n, distance_mm, speed_mm_s, +1)
        n.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
        end = read_state(n)
        print(json.dumps({
            "command": "forward", "requested_mm": distance_mm, "moved_mm": moved,
            "speed_mm_s": speed_mm_s, "abort_reason": abort,
            "end_state": {"wall_mm": end.get('analog', {}).get('WallSensorInMM'),
                          "battery_mv": end.get('analog', {}).get('BatteryVoltageInmV')},
        }, indent=2))
        sys.exit(1 if abort else 0)
    finally:
        n.close()


def cmd_back(distance_mm, speed_mm_s):
    n = open_neato()
    try:
        n.test_mode(on=True)
        time.sleep(0.3)
        moved, abort = _drive_straight_oneshot(n, distance_mm, speed_mm_s, -1)
        n.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
        end = read_state(n)
        print(json.dumps({
            "command": "back", "requested_mm": distance_mm, "moved_mm": moved,
            "speed_mm_s": speed_mm_s, "abort_reason": abort,
            "end_state": {"wall_mm": end.get('analog', {}).get('WallSensorInMM'),
                          "battery_mv": end.get('analog', {}).get('BatteryVoltageInmV')},
        }, indent=2))
        sys.exit(1 if abort else 0)
    finally:
        n.close()


def cmd_pivot(degrees, direction, speed_mm_s):
    arc = int(math.pi * WHEEL_BASE_MM * (degrees / 360.0))
    l_dist, r_dist = (-arc, arc) if direction == 'left' else (arc, -arc)
    n = open_neato()
    try:
        n.test_mode(on=True)
        time.sleep(0.3)
        pre = read_state(n, motors=False)
        block = safety_blocked(pre)
        if block:
            print(json.dumps({"command": "pivot", "abort_reason": f"pre_move_{block}"}))
            sys.exit(1)
        n.send(f"SetMotor LWheelDist {l_dist} RWheelDist {r_dist} Speed {speed_mm_s}", delay=0.1)
        time.sleep(arc / max(speed_mm_s, 1) + 0.5)
        n.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
        post = read_state(n, motors=False)
        print(json.dumps({"command": "pivot", "degrees": degrees, "direction": direction,
                           "arc_mm": arc, "abort_reason": None,
                           "wall_mm": post.get('analog', {}).get('WallSensorInMM')},
                          indent=2))
    finally:
        n.close()


def cmd_stop():
    n = open_neato()
    try:
        n.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
        n.test_mode(on=False)
        print(json.dumps({"command": "stop", "ok": True}))
    finally:
        n.close()


# ─── Daemon ──────────────────────────────────────────────────────────────────

class PilotDaemon:
    """Long-running daemon. Keeps camera + detector + serial open.

    Handles JSON-line commands over a unix socket. Includes an autonomous
    explore loop that runs inside the daemon for minimum latency.
    """

    def __init__(self):
        self.neato = None
        self.cam = None
        self.det = None
        self._exploring = False
        self._explore_thread = None

    def start(self):
        from vision.capture import Camera
        from vision.detector import Detector

        self.neato = open_neato()
        self.neato.test_mode(on=True)
        time.sleep(0.3)

        self.cam = Camera(width=640, height=640)
        self.cam.start(settle_time=1)

        self.det = Detector(confidence_threshold=0.35)
        self.det.start()

        sys.stdout.write("[daemon] ready on " + SOCKET_PATH + "\n")
        sys.stdout.flush()

    def stop(self):
        self._exploring = False
        try:
            if self.neato:
                self.neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
                self.neato.test_mode(on=False)
                self.neato.close()
        except Exception:
            pass
        try:
            if self.cam:
                self.cam.stop()
        except Exception:
            pass

    def _execute_step(self, step):
        """Execute a single step dict, return result dict."""
        act = step.get('action')
        if act == 'forward':
            mm = int(step.get('mm', STEP_CLEAR_MM))
            speed = int(step.get('speed', FORWARD_SPEED))
            moved, abort = drive_straight_daemon(self.neato, mm, speed, +1)
            return {"action": "forward", "moved_mm": moved, "abort": abort}
        elif act == 'back':
            mm = int(step.get('mm', BACKUP_MM))
            speed = int(step.get('speed', SLOW_SPEED))
            moved, abort = drive_straight_daemon(self.neato, mm, speed, -1)
            return {"action": "back", "moved_mm": moved, "abort": abort}
        elif act == 'pivot':
            deg = int(step.get('degrees', PIVOT_MEDIUM))
            direction = step.get('direction', 'right')
            speed = int(step.get('speed', PIVOT_SPEED))
            arc, err = pivot_daemon(self.neato, deg, direction, speed)
            return {"action": "pivot", "degrees": deg, "direction": direction, "error": err}
        return {"action": act, "error": "unknown step action"}

    def _look(self):
        """Capture frame + run YOLO + read fast sensor state. Returns (det_list, state)."""
        frame = self.cam.capture()
        detections = self.det.detect(frame)
        det_list = [
            {"label": d.label, "confidence": round(d.confidence, 3),
             "bbox": [round(d.x_min, 3), round(d.y_min, 3),
                      round(d.x_max, 3), round(d.y_max, 3)],
             "bbox_area": round((d.x_max - d.x_min) * (d.y_max - d.y_min), 3)}
            for d in detections
        ]
        state = read_state(self.neato, motors=False)
        return det_list, state

    def _explore_loop(self, duration_s, log_path):
        """Autonomous explore loop. Runs in a thread; sets self._exploring=False when done."""
        t_start = time.time()
        step_num = 0
        history = []  # for log

        sys.stdout.write(f"[explore] starting {duration_s}s exploration\n")
        sys.stdout.flush()

        consecutive_blocks = 0
        recent_bumps = 0  # track bumper streak for escalating recovery
        lidar_front_mm = None  # updated every 5 steps

        while self._exploring and (time.time() - t_start) < duration_s:
            try:
                det_list, state = self._look()

                # Pre-check cliffs before anything
                cliff = safety_blocked(state, 'forward')
                if cliff in ('left_cliff', 'right_cliff', 'wheel_drop'):
                    sys.stdout.write(f"[explore] SAFETY: {cliff} — stopping!\n")
                    sys.stdout.flush()
                    self.neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.05)
                    self._exploring = False
                    break

                # Periodic LiDAR check for ground-truth forward distance
                if step_num % 5 == 0:
                    ld = read_lidar_summary(self.neato)
                    lidar_front_mm = ld.get('front_wide_mm')
                    if lidar_front_mm:
                        sys.stdout.write(
                            f"[explore] LiDAR: front={lidar_front_mm}mm "
                            f"right={ld.get('right_mm')}mm "
                            f"left={ld.get('left_mm')}mm\n"
                        )
                        sys.stdout.flush()

                # Override vision danger if LiDAR says path is actually clear
                # (camera tilt causes false close detections for distant objects)
                if lidar_front_mm and lidar_front_mm > 400:
                    det_list_filtered = [d for d in det_list if d.get('bbox_area', 0) < BBOX_DANGER]
                else:
                    det_list_filtered = det_list

                decision = choose_action(det_list_filtered, state, recent_bumps=recent_bumps)
                reason = decision.get('reason', '')
                elapsed = round(time.time() - t_start, 1)

                # Summarize what we see
                labels = [d['label'] for d in det_list]
                wall_mm = state.get('analog', {}).get('WallSensorInMM', '?')
                sys.stdout.write(
                    f"[explore #{step_num:3d} {elapsed:5.1f}s] "
                    f"wall={wall_mm}mm det={labels} → {reason}\n"
                )
                sys.stdout.flush()

                # Execute decision
                results = []
                if decision['action'] == 'sequence':
                    for step in decision['steps']:
                        r = self._execute_step(step)
                        results.append(r)
                        if r.get('abort') and 'cliff' in str(r.get('abort', '')):
                            self._exploring = False
                            break
                elif decision['action'] in ('forward', 'back', 'pivot'):
                    results.append(self._execute_step(decision))

                # Track bumper events and consecutive blocks
                was_bumper = 'bumper' in reason
                if was_bumper:
                    recent_bumps += 1
                else:
                    recent_bumps = max(0, recent_bumps - 1)  # decay

                all_aborted = all(r.get('abort') for r in results if 'abort' in r)
                if all_aborted and results:
                    consecutive_blocks += 1
                    if consecutive_blocks >= 4:
                        sys.stdout.write(f"[explore] STUCK {consecutive_blocks}x — big pivot right\n")
                        sys.stdout.flush()
                        pivot_daemon(self.neato, PIVOT_LARGE, 'right', PIVOT_SPEED)
                        consecutive_blocks = 0
                        recent_bumps = 0
                else:
                    consecutive_blocks = 0

                log_entry = {
                    "step": step_num,
                    "elapsed_s": elapsed,
                    "detections": det_list,
                    "wall_mm": wall_mm,
                    "reason": reason,
                    "results": results,
                }
                history.append(log_entry)
                step_num += 1

            except Exception as e:
                sys.stdout.write(f"[explore] step error: {e}\n")
                sys.stdout.flush()
                time.sleep(0.5)

        self.neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
        self._exploring = False
        duration_actual = round(time.time() - t_start, 1)
        sys.stdout.write(f"[explore] done — {step_num} steps in {duration_actual}s\n")
        sys.stdout.flush()

        if log_path and history:
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, 'w') as f:
                    json.dump(history, f, indent=2)
                sys.stdout.write(f"[explore] log saved: {log_path}\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(f"[explore] log save failed: {e}\n")
                sys.stdout.flush()

    def handle(self, cmd):
        action = cmd.get('action')

        if action == 'state':
            return read_state(self.neato)

        if action == 'look':
            from PIL import Image
            det_list, state = self._look()
            result = {"detections": det_list, "state": state}
            save = cmd.get('save')
            if save:
                frame = self.cam.capture()
                Image.fromarray(frame).save(save, quality=85)
                result['saved_image'] = save
            return result

        if action == 'forward':
            mm = int(cmd.get('mm', 100))
            speed = int(cmd.get('speed', FORWARD_SPEED))
            moved, abort = drive_straight_daemon(self.neato, mm, speed, +1)
            return {"command": "forward", "requested_mm": mm, "moved_mm": moved,
                    "abort_reason": abort, "end_state": read_state(self.neato, motors=False)}

        if action == 'back':
            mm = int(cmd.get('mm', BACKUP_MM))
            speed = int(cmd.get('speed', SLOW_SPEED))
            moved, abort = drive_straight_daemon(self.neato, mm, speed, -1)
            return {"command": "back", "requested_mm": mm, "moved_mm": moved,
                    "abort_reason": abort, "end_state": read_state(self.neato, motors=False)}

        if action == 'pivot':
            deg = int(cmd.get('degrees', PIVOT_MEDIUM))
            direction = cmd.get('direction', 'right')
            speed = int(cmd.get('speed', PIVOT_SPEED))
            arc, err = pivot_daemon(self.neato, deg, direction, speed)
            return {"command": "pivot", "degrees": deg, "direction": direction,
                    "arc_mm": arc, "error": err,
                    "end_state": read_state(self.neato, motors=False)}

        if action == 'lidar':
            return read_lidar_summary(self.neato)

        if action == 'arc':
            distance_mm = int(cmd.get('mm', 400))
            inner = int(cmd.get('inner_speed', 60))
            outer = int(cmd.get('outer_speed', FORWARD_SPEED))
            direction = cmd.get('direction', 'left')
            moved, err = arc_turn(self.neato, distance_mm, inner, outer, direction)
            return {"command": "arc", "mm": distance_mm, "direction": direction,
                    "moved_mm": moved, "error": err,
                    "end_state": read_state(self.neato, motors=False)}

        if action == 'decide':
            # Look + return the decision without executing (for inspection)
            det_list, state = self._look()
            decision = choose_action(det_list, state)
            return {"detections": det_list, "decision": decision,
                    "wall_mm": state.get('analog', {}).get('WallSensorInMM')}

        if action == 'step':
            # Look + decide + execute one step
            det_list, state = self._look()
            decision = choose_action(det_list, state)
            results = []
            if decision['action'] == 'sequence':
                for s in decision['steps']:
                    results.append(self._execute_step(s))
            elif decision['action'] in ('forward', 'back', 'pivot'):
                results.append(self._execute_step(decision))
            return {"detections": det_list, "decision": decision, "results": results,
                    "wall_mm": state.get('analog', {}).get('WallSensorInMM')}

        if action == 'explore':
            if self._exploring:
                return {"error": "already exploring — send stop_explore first"}
            duration_s = int(cmd.get('duration_s', 300))
            ts = time.strftime("%Y%m%d_%H%M%S")
            log_path = cmd.get('log_path', f"captures/{ts}_explore_log.json")
            self._exploring = True
            self._explore_thread = threading.Thread(
                target=self._explore_loop,
                args=(duration_s, log_path),
                daemon=True,
            )
            self._explore_thread.start()
            return {"command": "explore", "started": True,
                    "duration_s": duration_s, "log_path": log_path}

        if action == 'stop_explore':
            self._exploring = False
            self.neato.send("SetMotor LWheelDist 0 RWheelDist 0 Speed 0", delay=0.1)
            return {"command": "stop_explore", "ok": True}

        if action == 'shutdown':
            self.stop()
            return {"command": "shutdown", "ok": True, "exit": True}

        return {"error": f"unknown action: {action}"}


# ─── Server loop ─────────────────────────────────────────────────────────────

def cmd_serve():
    import socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(5)
    os.chmod(SOCKET_PATH, 0o666)

    daemon = PilotDaemon()
    daemon.start()

    try:
        while True:
            conn, _ = server.accept()
            try:
                data = b''
                while not data.endswith(b'\n'):
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                if not data:
                    continue
                cmd = json.loads(data.decode().strip())
                result = daemon.handle(cmd)
                conn.sendall((json.dumps(result) + '\n').encode())
                if result.get('exit'):
                    break
            except Exception as e:
                err = {"error": str(e)}
                try:
                    conn.sendall((json.dumps(err) + '\n').encode())
                except Exception:
                    pass
            finally:
                conn.close()
    finally:
        daemon.stop()
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        os._exit(0)


def cmd_send(args):
    """Client: send one command to running daemon."""
    import socket
    payload = {"action": args.action}
    for k, v in vars(args).items():
        if k in ('action', 'cmd', 'func'):
            continue
        if v is not None:
            payload[k] = v
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(90)
        s.connect(SOCKET_PATH)
        s.sendall((json.dumps(payload) + '\n').encode())
        data = b''
        while not data.endswith(b'\n'):
            chunk = s.recv(8192)
            if not chunk:
                break
            data += chunk
        s.close()
        sys.stdout.write(data.decode())
        sys.stdout.flush()
    except FileNotFoundError:
        print(json.dumps({"error": "daemon not running — start with: python pilot.py serve"}))
        sys.exit(2)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))

    p = argparse.ArgumentParser(description="Vacuum pilot")
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('serve')
    sub.add_parser('state')
    sub.add_parser('stop')

    p_look = sub.add_parser('look')
    p_look.add_argument('--save', default=None)

    p_fwd = sub.add_parser('forward')
    p_fwd.add_argument('mm', type=int)
    p_fwd.add_argument('--speed', type=int, default=FORWARD_SPEED)

    p_back = sub.add_parser('back')
    p_back.add_argument('mm', type=int)
    p_back.add_argument('--speed', type=int, default=SLOW_SPEED)

    p_piv = sub.add_parser('pivot')
    p_piv.add_argument('degrees', type=int)
    p_piv.add_argument('direction', choices=['left', 'right'])
    p_piv.add_argument('--speed', type=int, default=PIVOT_SPEED)

    # send subcommand (daemon client)
    p_send = sub.add_parser('send')
    send_sub = p_send.add_subparsers(dest='action', required=True)
    send_sub.add_parser('state')
    sl = send_sub.add_parser('look')
    sl.add_argument('--save', default=None)
    sf = send_sub.add_parser('forward')
    sf.add_argument('mm', type=int)
    sf.add_argument('--speed', type=int, default=FORWARD_SPEED)
    sb = send_sub.add_parser('back')
    sb.add_argument('mm', type=int)
    sb.add_argument('--speed', type=int, default=SLOW_SPEED)
    sp = send_sub.add_parser('pivot')
    sp.add_argument('degrees', type=int)
    sp.add_argument('direction', choices=['left', 'right'])
    sp.add_argument('--speed', type=int, default=PIVOT_SPEED)
    send_sub.add_parser('lidar')
    sa = send_sub.add_parser('arc')
    sa.add_argument('mm', type=int)
    sa.add_argument('direction', choices=['left', 'right'])
    sa.add_argument('--inner', type=int, default=60, dest='inner_speed')
    sa.add_argument('--outer', type=int, default=FORWARD_SPEED, dest='outer_speed')
    send_sub.add_parser('decide')
    send_sub.add_parser('step')
    se = send_sub.add_parser('explore')
    se.add_argument('--duration', type=int, default=300, dest='duration_s')
    se.add_argument('--log', default=None, dest='log_path')
    send_sub.add_parser('stop_explore')
    send_sub.add_parser('shutdown')

    args = p.parse_args()

    if args.cmd == 'serve':
        cmd_serve()
    elif args.cmd == 'send':
        cmd_send(args)
    elif args.cmd == 'state':
        cmd_state()
    elif args.cmd == 'look':
        cmd_look(args.save)
    elif args.cmd == 'forward':
        cmd_forward(args.mm, args.speed)
    elif args.cmd == 'back':
        cmd_back(args.mm, args.speed)
    elif args.cmd == 'pivot':
        cmd_pivot(args.degrees, args.direction, args.speed)
    elif args.cmd == 'stop':
        cmd_stop()


if __name__ == '__main__':
    main()
