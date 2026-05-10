"""drive_daemon.py — Multi-threaded autonomous drive service.

Architecture: each sensor runs in its own thread, writing to shared AtomicState.
The DriveEngine reads from AtomicState and makes decisions at ~3Hz without
waiting for any single sensor. The socket interface accepts high-level commands.

Threads:
  SensorThread   — digital + analog at 5Hz (safety-critical bumpers/cliff)
  LidarThread    — full 360° LDS scan every ~1.5s (always-fresh distances)
  VisionThread   — camera capture + YOLO at ~1-2fps
  DriveEngine    — decision loop at 5Hz, executes moves via serial
  SocketServer   — command/query interface on /tmp/drive.sock

Safety contract:
  Any sensor fault (cliff, wheel-drop) immediately sets emergency_stop flag.
  DriveEngine checks this flag before every motor command.
  SocketServer can set/clear override_stop.
"""

import json
import math
import os
import signal
import socket
import sys
import threading
import time
from collections import deque
from datetime import datetime

# Ensure repo root is on path so vision/neato_serial/scout imports work
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

SOCKET_PATH = '/tmp/drive.sock'
WHEEL_BASE_MM = 240
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'captures')


# ─── Shared atomic state ─────────────────────────────────────────────────────

class AtomicState:
    """Thread-safe shared state between all sensor threads and the drive engine."""

    def __init__(self):
        self._lock = threading.RLock()

        # Sensor snapshots (updated by threads)
        self.digital = {}
        self.analog = {}
        self.accel = {}
        self.lidar = {}          # cardinal distances + raw readings dict
        self.detections = []     # [{label, confidence, bbox, bbox_area, cx}]
        _now = time.time()
        self.lidar_ts = _now     # timestamp of last LiDAR scan
        self.vision_ts = _now    # timestamp of last vision frame
        self.sensor_ts = _now    # timestamp of last sensor poll

        # Derived safety signals (set by SensorThread)
        self.front_bumper = False
        self.side_bumper = False
        self.left_cliff = False
        self.right_cliff = False
        self.wheel_drop = False
        self.any_cliff = False

        # Drive state
        self.emergency_stop = False
        self.override_stop = False   # set by socket command
        self.driving = False         # engine is actively moving
        self.mode = 'idle'           # idle / explore / manual / docking

        # Odometry (cumulative, reset-able)
        self.lw_pos_mm = 0.0
        self.rw_pos_mm = 0.0
        self.lw_pos_ref = None  # baseline for delta
        self.rw_pos_ref = None

        # Running log for analysis
        self.step_log = deque(maxlen=500)
        self.bumper_events = []

        # Tunable parameters (can be adjusted at runtime via socket)
        self.params = {
            'forward_speed': 180,      # was 280 — too fast for blind hits
            'slow_speed': 120,
            'pivot_speed': 110,
            'step_clear_mm': 300,      # was 400
            'step_caution_mm': 150,
            'backup_mm': 250,          # was 180 — agent flagged too short
            'lidar_danger_mm': 250,    # was 180 — earlier slowdown
            'lidar_caution_mm': 600,   # was 350 — much earlier caution
            'bbox_danger': 0.15,
            'bbox_caution': 0.10,
            'wall_close_mm': 120,
            'wall_far_mm': 500,
            'pivot_small': 20,
            'pivot_medium': 45,
            'pivot_large': 90,
        }

    def update_sensors(self, digital, analog, accel):
        with self._lock:
            self.digital = digital
            self.analog = analog
            self.accel = accel
            self.sensor_ts = time.time()

            # Derive safety signals
            self.front_bumper = bool(digital.get('LFRONTBIT', 0) or digital.get('RFRONTBIT', 0))
            self.side_bumper = bool(digital.get('LSIDEBIT', 0) or digital.get('RSIDEBIT', 0))
            ld = analog.get('LeftDropInMM', 60)
            rd = analog.get('RightDropInMM', 60)
            self.left_cliff = isinstance(ld, (int, float)) and ld < 5
            self.right_cliff = isinstance(rd, (int, float)) and rd < 5
            self.wheel_drop = bool(digital.get('SNSR_LEFT_WHEEL_EXTENDED', 0) or
                                   digital.get('SNSR_RIGHT_WHEEL_EXTENDED', 0))
            self.any_cliff = self.left_cliff or self.right_cliff or self.wheel_drop

            if self.any_cliff:
                self.emergency_stop = True

    def update_lidar(self, cardinal, raw_readings):
        with self._lock:
            self.lidar = cardinal
            self.lidar_ts = time.time()

    def update_vision(self, det_list):
        with self._lock:
            self.detections = det_list
            self.vision_ts = time.time()

    def update_odometry(self, motors):
        with self._lock:
            lp = motors.get('LeftWheel_PositionInMM')
            rp = motors.get('RightWheel_PositionInMM')
            if lp is not None:
                if self.lw_pos_ref is None:
                    self.lw_pos_ref = lp
                self.lw_pos_mm = lp - self.lw_pos_ref
            if rp is not None:
                if self.rw_pos_ref is None:
                    self.rw_pos_ref = rp
                self.rw_pos_mm = rp - self.rw_pos_ref

    def snapshot(self):
        with self._lock:
            return {
                'front_bumper': self.front_bumper,
                'side_bumper': self.side_bumper,
                'any_cliff': self.any_cliff,
                'emergency_stop': self.emergency_stop,
                'override_stop': self.override_stop,
                'front_mm': self.lidar.get('front_mm'),
                'front_wide_mm': self.lidar.get('front_wide_mm'),
                'right_mm': self.lidar.get('right_mm'),
                'left_mm': self.lidar.get('left_mm'),
                'wall_mm': self.analog.get('WallSensorInMM'),
                'battery_mv': self.analog.get('BatteryVoltageInmV'),
                'detections': list(self.detections),
                'lidar_age_s': round(time.time() - self.lidar_ts, 1),
                'vision_age_s': round(time.time() - self.vision_ts, 1),
                'sensor_age_s': round(time.time() - self.sensor_ts, 1),
                'mode': self.mode,
                'driving': self.driving,
                'odometry_mm': {'left': round(self.lw_pos_mm, 1), 'right': round(self.rw_pos_mm, 1)},
            }

    def is_blocked(self, direction='forward'):
        with self._lock:
            if self.emergency_stop or self.override_stop:
                return 'emergency_stop'
            if self.any_cliff:
                return 'cliff'
            if direction == 'forward':
                if self.front_bumper:
                    return 'front_bumper'
                if self.side_bumper:
                    return 'side_bumper'
            return None

    def log_step(self, step):
        with self._lock:
            self.step_log.append(step)

    def get_param(self, key):
        with self._lock:
            return self.params.get(key)

    def set_param(self, key, value):
        with self._lock:
            if key in self.params:
                self.params[key] = value
                return True
            return False


# ─── Sensor thread ───────────────────────────────────────────────────────────

class SensorThread(threading.Thread):
    """Polls digital + analog sensors at ~5Hz. Critical for bumper/cliff safety."""

    def __init__(self, neato, state):
        super().__init__(daemon=True, name='SensorThread')
        self.neato = neato
        self.state = state
        self._stop_event = threading.Event()

    def run(self):
        sys.stdout.write('[sensor] started\n'); sys.stdout.flush()
        cycle = 0
        while not self._stop_event.is_set():
            try:
                digital = self.neato.get_digital_sensors()
                if self._stop_event.is_set(): break
                analog = self.neato.get_analog_sensors()
                # Accel every 5th cycle (not safety-critical)
                accel = {}
                if cycle % 5 == 0:
                    if self._stop_event.is_set(): break
                    try:
                        accel = self.neato.get_accel_parsed()
                    except Exception:
                        pass
                self.state.update_sensors(digital, analog, accel)
                cycle += 1
            except Exception as e:
                sys.stdout.write(f'[sensor] error: {e}\n'); sys.stdout.flush()
            time.sleep(0.18)  # ~5Hz

    def stop(self):
        self._stop_event.set()


# ─── LiDAR thread ────────────────────────────────────────────────────────────

# Angle mapping validated 2026-05-09: 0=rear, 180=front, 90=right, 270=left
LIDAR_FRONT = 180
LIDAR_RIGHT = 90
LIDAR_LEFT = 270

def parse_lidar(raw):
    """Parse GetLDSScan output. Returns (cardinal_dict, raw_readings_dict)."""
    readings = {}
    for line in raw.strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 4:
            try:
                angle = int(parts[0])
                dist = int(parts[1])
                err = int(parts[3])
                if err == 0 and 50 < dist < 6000:
                    readings[angle] = dist
            except (ValueError, IndexError):
                pass

    def arc_min(center, half):
        vals = [readings[a] for a in range(center - half, center + half + 1)
                if a in readings]
        return min(vals) if vals else None

    front_mm = arc_min(LIDAR_FRONT, 20)
    front_wide = arc_min(LIDAR_FRONT, 40)
    right_mm = arc_min(LIDAR_RIGHT, 25)
    left_mm = arc_min(LIDAR_LEFT, 25)

    cardinal = {
        'front_mm': front_mm,
        'front_wide_mm': front_wide,
        'right_mm': right_mm,
        'left_mm': left_mm,
        'n_valid': len(readings),
        'clear_ahead': front_wide is None or front_wide > 500,
    }
    return cardinal, readings


class LidarThread(threading.Thread):
    """Runs GetLDSScan when drive engine is idle (not sending motor commands).

    The LiDAR scan holds the serial lock for ~1.2s, which starves motor commands
    if it runs during a move. drive_idle_event is cleared by DriveEngine before
    sending motor commands and set again after — LiDAR waits for it.
    """

    def __init__(self, neato, state, drive_idle_event):
        super().__init__(daemon=True, name='LidarThread')
        self.neato = neato
        self.state = state
        self.drive_idle = drive_idle_event
        self._stop_event = threading.Event()

    def run(self):
        sys.stdout.write('[lidar] started\n'); sys.stdout.flush()
        while not self._stop_event.is_set():
            # Wait for drive engine to be idle before taking the long scan
            if not self.drive_idle.wait(timeout=3.0):
                continue  # engine busy, try again
            # Re-check stop event after wait (fixes shutdown hang)
            if self._stop_event.is_set():
                break
            # Re-check drive_idle: a motor command may have grabbed it between
            # wait() returning True and us issuing the scan
            if not self.drive_idle.is_set():
                continue
            try:
                raw = self.neato.send('GetLDSScan', delay=1.2)
                cardinal, readings = parse_lidar(raw)
                self.state.update_lidar(cardinal, readings)
                sys.stdout.write(
                    f'[lidar] n={cardinal.get("n_valid")} '
                    f'front={cardinal.get("front_wide_mm")} '
                    f'right={cardinal.get("right_mm")} '
                    f'left={cardinal.get("left_mm")}\n'
                )
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(f'[lidar] error: {e}\n'); sys.stdout.flush()
                time.sleep(1.0)

    def stop(self):
        self._stop_event.set()


# ─── Vision thread ────────────────────────────────────────────────────────────

class VisionThread(threading.Thread):
    """Captures frames and runs YOLO at ~1fps."""

    def __init__(self, cam, det, state):
        super().__init__(daemon=True, name='VisionThread')
        self.cam = cam
        self.det = det
        self.state = state
        self._stop_event = threading.Event()
        self.last_frame = None

    def run(self):
        sys.stdout.write('[vision] started\n'); sys.stdout.flush()
        while not self._stop_event.is_set():
            try:
                frame = self.cam.capture()
                self.last_frame = frame
                detections = self.det.detect(frame)
                det_list = []
                for d in detections:
                    area = round((d.x_max - d.x_min) * (d.y_max - d.y_min), 3)
                    cx = round((d.x_min + d.x_max) / 2, 3)
                    det_list.append({
                        'label': d.label,
                        'confidence': round(d.confidence, 3),
                        'bbox': [round(d.x_min, 3), round(d.y_min, 3),
                                 round(d.x_max, 3), round(d.y_max, 3)],
                        'bbox_area': area,
                        'cx': cx,
                    })
                self.state.update_vision(det_list)
            except Exception as e:
                sys.stdout.write(f'[vision] error: {e}\n'); sys.stdout.flush()
                time.sleep(0.5)

    def stop(self):
        self._stop_event.set()


# ─── Decision logic ───────────────────────────────────────────────────────────

def decide(state, recent_bumps=0):
    """Make a drive decision from current AtomicState snapshot.

    Uses LiDAR as primary distance source; camera for obstacle identification.
    Returns a step dict: {action, ...params, reason}.

    Priority:
      1. Cliff / wheel-drop → emergency stop (handled upstream)
      2. Bumper → escalating recovery
      3. LiDAR danger zone → back + pivot away from obstacle
      4. LiDAR caution zone → slow + gentle correction
      5. Vision close object (LiDAR-confirmed) → caution move
      6. Wall sensor → gentle course correction
      7. Clear → full-speed step
    """
    p = state.params
    digital = state.digital
    analog = state.analog
    lidar = state.lidar
    dets = state.detections

    front_bump = state.front_bumper
    left_front = bool(digital.get('LFRONTBIT', 0))
    left_side = bool(digital.get('LSIDEBIT', 0))
    right_bump = bool(digital.get('RFRONTBIT', 0) or digital.get('RSIDEBIT', 0))
    side_bump = state.side_bumper

    front_mm = lidar.get('front_mm')
    front_wide_mm = lidar.get('front_wide_mm')
    right_mm = lidar.get('right_mm')
    left_mm = lidar.get('left_mm')
    lidar_age = time.time() - state.lidar_ts
    wall_mm = analog.get('WallSensorInMM', 9999)

    fwd = p['forward_speed']
    slow = p['slow_speed']
    piv_spd = p['pivot_speed']
    step = p['step_clear_mm']
    step_caut = p['step_caution_mm']
    backup = p['backup_mm']
    lidar_danger = p['lidar_danger_mm']
    lidar_caution = p['lidar_caution_mm']
    pivot_sm = p['pivot_small']
    pivot_md = p['pivot_medium']
    pivot_lg = p['pivot_large']
    bbox_danger = p['bbox_danger']
    bbox_caution = p['bbox_caution']

    # 1. Bumper recovery — escalate with repeated hits
    if front_bump or side_bump:
        if left_front or left_side:
            pivot_dir = 'right'
        elif right_bump:
            pivot_dir = 'left'
        else:
            pivot_dir = 'right'
        pivot_deg = min(pivot_lg, pivot_md + recent_bumps * 25)
        extra_backup = recent_bumps * 60
        return {
            'action': 'sequence',
            'steps': [
                {'action': 'back', 'mm': backup + extra_backup, 'speed': slow},
                {'action': 'pivot', 'degrees': pivot_deg, 'direction': pivot_dir, 'speed': piv_spd},
                {'action': 'forward', 'mm': step_caut, 'speed': slow},
            ],
            'reason': f'bumper: L={int(left_front)}R={int(right_bump)} side={int(side_bump)} '
                      f'recent={recent_bumps} → back{backup+extra_backup}+piv{pivot_deg}_{pivot_dir}',
            'is_recovery': True,
        }

    # 2. LiDAR danger — clear path is blocked
    lidar_fresh = lidar_age < 3.0 and front_wide_mm is not None
    if lidar_fresh and front_wide_mm < lidar_danger:
        # Determine which side is more open
        r = right_mm or 9999
        l = left_mm or 9999
        pivot_dir = 'right' if r > l else 'left'
        return {
            'action': 'sequence',
            'steps': [
                {'action': 'back', 'mm': backup, 'speed': slow},
                {'action': 'pivot', 'degrees': pivot_md, 'direction': pivot_dir, 'speed': piv_spd},
            ],
            'reason': f'lidar_danger: front={front_wide_mm}mm R={right_mm} L={left_mm} → piv_{pivot_dir}',
        }

    # 3. LiDAR caution — something ahead, slow down and maybe correct
    if lidar_fresh and front_wide_mm < lidar_caution:
        # Gentle correction toward open side
        r = right_mm or 9999
        l = left_mm or 9999
        if r > l + 300:
            correction = {'action': 'pivot', 'degrees': pivot_sm, 'direction': 'right', 'speed': piv_spd}
        elif l > r + 300:
            correction = {'action': 'pivot', 'degrees': pivot_sm, 'direction': 'left', 'speed': piv_spd}
        else:
            correction = None
        steps = []
        if correction:
            steps.append(correction)
        steps.append({'action': 'forward', 'mm': step_caut, 'speed': slow})
        return {
            'action': 'sequence',
            'steps': steps,
            'reason': f'lidar_caution: front={front_wide_mm}mm R={right_mm} L={left_mm}',
        }

    # 4. Vision close objects (camera-confirmed, LiDAR says path somewhat clear)
    close_dets = [d for d in dets if d.get('bbox_area', 0) >= bbox_danger]
    if close_dets:
        # Find which side they're on
        left_obs = [d for d in close_dets if d.get('cx', 0.5) < 0.4]
        right_obs = [d for d in close_dets if d.get('cx', 0.5) > 0.6]
        if left_obs and not right_obs:
            pivot_dir = 'right'
        elif right_obs and not left_obs:
            pivot_dir = 'left'
        else:
            pivot_dir = 'right'
        labels = [d['label'] for d in close_dets]
        return {
            'action': 'sequence',
            'steps': [
                {'action': 'pivot', 'degrees': pivot_sm, 'direction': pivot_dir, 'speed': piv_spd},
                {'action': 'forward', 'mm': step_caut, 'speed': slow},
            ],
            'reason': f'vision_close: {labels} → dodge_{pivot_dir}',
        }

    # 5. Wall sensor correction (right side IR)
    wall_valid = isinstance(wall_mm, (int, float)) and 100 <= wall_mm < 1000
    if wall_valid and wall_mm < p['wall_close_mm'] and recent_bumps < 2:
        return {
            'action': 'sequence',
            'steps': [
                {'action': 'arc', 'mm': step, 'direction': 'left',
                 'inner_speed': 60, 'outer_speed': fwd},
            ],
            'reason': f'wall_close: {wall_mm}mm → arc_left',
        }
    if wall_valid and wall_mm > p['wall_far_mm'] and recent_bumps < 2:
        return {
            'action': 'sequence',
            'steps': [
                {'action': 'arc', 'mm': step, 'direction': 'right',
                 'inner_speed': 80, 'outer_speed': fwd},
            ],
            'reason': f'wall_far: {wall_mm}mm → arc_right',
        }

    # 6. Clear — full-speed forward
    front_info = f'{front_wide_mm}mm' if front_wide_mm else 'unknown'
    return {
        'action': 'forward',
        'mm': step,
        'speed': fwd,
        'reason': f'clear: front={front_info} wall={wall_mm}',
    }


# ─── Drive engine ─────────────────────────────────────────────────────────────

class DriveEngine:
    """Executes drive steps via serial. Called synchronously from explore loop.

    Sets drive_idle_event.clear() before motor commands so LidarThread waits,
    then set() after so LiDAR can scan between moves.
    """

    def __init__(self, neato, state, drive_idle_event=None):
        self.neato = neato
        self.state = state
        self.drive_idle = drive_idle_event or threading.Event()
        self.drive_idle.set()  # start idle

    def _send(self, cmd, delay=0.05):
        return self.neato.send(cmd, delay=delay)

    def _motor_send(self, cmd, delay=0.05):
        """Send a motor command — signals LiDAR thread to wait."""
        self.drive_idle.clear()
        try:
            return self.neato.send(cmd, delay=delay)
        finally:
            self.drive_idle.set()

    def smooth_stop(self, direction=1):
        """Issue a final very-slow micro-move to bleed momentum, then zero.

        NOTE: this only works if called BEFORE the cruise has stopped. If the
        previous SetMotor distance has already completed, the robot is already
        at rest and no smoothing is possible. The proper smooth-stop happens
        inside forward()/back() by reserving a tail distance for slow speed.
        """
        try:
            self.neato.send('SetMotor LWheelDist 0 RWheelDist 0 Speed 0', delay=0.05)
        except Exception:
            pass

    def _drive_linear(self, mm, speed, sign):
        """Single SetMotor command for the full distance, monitor sensors during.

        Letting the firmware handle the FULL distance in one command lets its
        built-in trapezoidal speed profile work — accel ramp + cruise + decel
        ramp. Chunking forced abrupt stops because each chunk hit Distance=0
        before the firmware could decelerate.

        Safety: SensorThread polls at 5Hz, AtomicState.is_blocked checks each
        loop iteration. On bumper/cliff we send Speed 0 to abort the move.
        """
        if mm <= 0:
            return 0, None
        signed = sign * mm
        cmd_dir = 'forward' if sign > 0 else 'backward'
        self.drive_idle.clear()
        moved = 0
        abort = None
        t_start = time.time()
        # Estimated travel time + 30% slack for accel/decel ramps
        travel_s = (mm / max(speed, 1)) * 1.30 + 0.4
        try:
            try:
                self.neato.send(
                    f'SetMotor LWheelDist {signed} RWheelDist {signed} Speed {speed}',
                    delay=0.05,
                )
            except Exception as e:
                return 0, f'serial:{e}'
            # Monitor while firmware drives
            while True:
                elapsed = time.time() - t_start
                if elapsed >= travel_s:
                    moved = mm
                    break
                block = self.state.is_blocked(cmd_dir)
                if block:
                    # Abort: cancel by sending Speed 0
                    try:
                        self.neato.send('SetMotor LWheelDist 0 RWheelDist 0 Speed 0', delay=0.05)
                    except Exception:
                        pass
                    abort = block
                    # estimate distance moved from elapsed time at requested speed
                    moved = int(min(mm, elapsed * speed))
                    break
                time.sleep(0.05)  # 20Hz check loop
        finally:
            self.drive_idle.set()
        return moved, abort

    def forward(self, mm, speed):
        return self._drive_linear(mm, speed, sign=1)

    def back(self, mm, speed):
        return self._drive_linear(mm, speed, sign=-1)

    def pivot(self, degrees, direction, speed):
        """Rotate in place. Single SetMotor command lets firmware run trapezoid."""
        arc = int(math.pi * WHEEL_BASE_MM * (degrees / 360.0))
        l_dist, r_dist = (-arc, arc) if direction == 'left' else (arc, -arc)
        self.drive_idle.clear()
        err = None
        try:
            self.neato.send(f'SetMotor LWheelDist {l_dist} RWheelDist {r_dist} Speed {speed}',
                            delay=0.05)
            # firmware does the move; wait based on distance + ramp slack
            time.sleep(arc / max(speed, 1) * 1.25 + 0.3)
        except Exception as e:
            err = str(e)
        finally:
            # Always send a zero-motor frame to ensure stop, even on exception
            try:
                self.neato.send('SetMotor LWheelDist 0 RWheelDist 0 Speed 0', delay=0.05)
            except Exception:
                pass
            self.drive_idle.set()
        return arc, err

    def arc(self, mm, direction, inner_speed, outer_speed):
        """Curved move: differential wheel speeds, smoother than stop-pivot-go."""
        l_speed = inner_speed if direction == 'left' else outer_speed
        r_speed = outer_speed if direction == 'left' else inner_speed
        l_dist = int(mm * l_speed / max(outer_speed, 1))
        r_dist = int(mm * r_speed / max(outer_speed, 1))
        max_spd = max(l_speed, r_speed)
        self.drive_idle.clear()
        err = None
        try:
            self.neato.send(f'SetMotor LWheelDist {l_dist} RWheelDist {r_dist} Speed {max_spd}',
                            delay=0.05)
            time.sleep(mm / max(max_spd, 1) * 1.25 + 0.2)
        except Exception as e:
            err = str(e)
        finally:
            try:
                self.neato.send('SetMotor LWheelDist 0 RWheelDist 0 Speed 0', delay=0.05)
            except Exception:
                pass
            self.drive_idle.set()
        return mm, err

    def stop(self):
        try:
            self.neato.send('SetMotor LWheelDist 0 RWheelDist 0 Speed 0', delay=0.05)
        except Exception:
            pass

    def execute_step(self, step):
        """Execute one step dict. Returns result dict."""
        act = step.get('action')
        if act == 'forward':
            moved, abort = self.forward(step.get('mm', 300), step.get('speed', 250))
            return {'action': 'forward', 'moved_mm': moved, 'abort': abort}
        elif act == 'back':
            moved, abort = self.back(step.get('mm', 160), step.get('speed', 130))
            return {'action': 'back', 'moved_mm': moved, 'abort': abort}
        elif act == 'pivot':
            arc, err = self.pivot(step.get('degrees', 45), step.get('direction', 'right'),
                                  step.get('speed', 120))
            return {'action': 'pivot', 'degrees': step.get('degrees'), 'error': err}
        elif act == 'arc':
            moved, err = self.arc(step.get('mm', 300), step.get('direction', 'left'),
                                  step.get('inner_speed', 60), step.get('outer_speed', 250))
            return {'action': 'arc', 'moved_mm': moved, 'error': err}
        return {'action': act, 'error': 'unknown'}

    def execute_decision(self, decision):
        """Execute a full decision (possibly a sequence). Returns list of results."""
        results = []
        if decision['action'] == 'sequence':
            for step in decision['steps']:
                r = self.execute_step(step)
                results.append(r)
                # Stop sequence on cliff abort
                if r.get('abort') in ('cliff', 'left_cliff', 'right_cliff', 'emergency_stop'):
                    break
        elif decision['action'] in ('forward', 'back', 'pivot', 'arc'):
            results.append(self.execute_step(decision))
        return results


# ─── Explore loop (runs in a thread) ─────────────────────────────────────────

class ExploreLoop(threading.Thread):
    """Autonomous exploration using AtomicState for real-time sensor fusion."""

    def __init__(self, state, engine, duration_s, log_path):
        super().__init__(daemon=True, name='ExploreLoop')
        self.state = state
        self.engine = engine
        self.duration_s = duration_s
        self.log_path = log_path
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        t_start = time.time()
        step_num = 0
        recent_bumps = 0
        consecutive_aborts = 0
        history = []

        sys.stdout.write(f'[explore] starting {self.duration_s}s run\n')
        sys.stdout.flush()

        with self.state._lock:
            self.state.mode = 'explore'

        while not self._stop.is_set():
            elapsed = time.time() - t_start
            if elapsed >= self.duration_s:
                break

            # Safety check
            if self.state.emergency_stop or self.state.override_stop:
                sys.stdout.write('[explore] STOPPED: emergency/override\n')
                sys.stdout.flush()
                break

            # Wait briefly for sensor data to be fresh
            if (time.time() - self.state.sensor_ts) > 1.0:
                time.sleep(0.1)
                continue

            # Snapshot current state for decision
            snap = self.state.snapshot()
            decision = decide(self.state, recent_bumps)
            reason = decision.get('reason', '')

            # Console status line
            det_labels = [d['label'] for d in snap['detections']]
            lidar_str = (f"f={snap.get('front_wide_mm')}mm "
                         f"r={snap.get('right_mm')}mm "
                         f"l={snap.get('left_mm')}mm")
            sys.stdout.write(
                f'[ex #{step_num:3d} {elapsed:5.1f}s] '
                f'wall={snap.get("wall_mm")}mm {lidar_str} | '
                f'det={det_labels} | {reason}\n'
            )
            sys.stdout.flush()

            # Execute
            results = self.engine.execute_decision(decision)

            # Track bumper streak
            is_recovery = decision.get('is_recovery', False)
            if is_recovery:
                recent_bumps += 1
                with self.state._lock:
                    self.state.bumper_events.append({
                        'step': step_num, 'elapsed_s': round(elapsed, 1),
                        'reason': reason,
                    })
            else:
                recent_bumps = max(0, recent_bumps - 1)

            # Stuck detection: all moves aborted
            any_abort = any(r.get('abort') for r in results if 'abort' in r)
            if any_abort and results:
                consecutive_aborts += 1
                if consecutive_aborts >= 3:
                    sys.stdout.write(f'[explore] STUCK {consecutive_aborts}x — big pivot\n')
                    sys.stdout.flush()
                    # Find most open direction from LiDAR
                    r_mm = snap.get('right_mm') or 0
                    l_mm = snap.get('left_mm') or 0
                    big_dir = 'right' if r_mm > l_mm else 'left'
                    self.engine.back(self.state.params['backup_mm'] * 2,
                                     self.state.params['slow_speed'])
                    self.engine.pivot(self.state.params['pivot_large'], big_dir,
                                      self.state.params['pivot_speed'])
                    consecutive_aborts = 0
                    recent_bumps = 0
            else:
                consecutive_aborts = 0

            # Log
            log_entry = {
                'step': step_num, 'elapsed_s': round(elapsed, 1),
                'snap': snap, 'decision': decision, 'results': results,
            }
            history.append(log_entry)
            self.state.log_step(log_entry)
            step_num += 1

        self.engine.stop()
        with self.state._lock:
            self.state.mode = 'idle'
            self.state.driving = False

        duration_actual = round(time.time() - t_start, 1)
        sys.stdout.write(f'[explore] done — {step_num} steps in {duration_actual}s\n')
        sys.stdout.flush()

        # Save log
        if self.log_path and history:
            try:
                os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
                with open(self.log_path, 'w') as f:
                    json.dump(history, f, indent=2)
                sys.stdout.write(f'[explore] log → {self.log_path}\n')
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(f'[explore] log save error: {e}\n')
                sys.stdout.flush()


# ─── Socket command server ────────────────────────────────────────────────────

def handle_command(cmd, state, engine, explore_ref):
    """Handle one command dict. Returns response dict."""
    action = cmd.get('action')

    if action == 'status':
        return state.snapshot()

    if action == 'forward':
        moved, abort = engine.forward(int(cmd.get('mm', 300)), int(cmd.get('speed', state.params['forward_speed'])))
        return {'action': 'forward', 'moved_mm': moved, 'abort': abort}

    if action == 'back':
        moved, abort = engine.back(int(cmd.get('mm', 160)), int(cmd.get('speed', state.params['slow_speed'])))
        return {'action': 'back', 'moved_mm': moved, 'abort': abort}

    if action == 'pivot':
        arc, err = engine.pivot(int(cmd.get('degrees', 45)), cmd.get('direction', 'right'),
                                int(cmd.get('speed', state.params['pivot_speed'])))
        return {'action': 'pivot', 'arc_mm': arc, 'error': err}

    if action == 'arc':
        moved, err = engine.arc(int(cmd.get('mm', 300)), cmd.get('direction', 'left'),
                                int(cmd.get('inner_speed', 60)),
                                int(cmd.get('outer_speed', state.params['forward_speed'])))
        return {'action': 'arc', 'moved_mm': moved, 'error': err}

    if action == 'stop':
        engine.stop()
        state.override_stop = True
        return {'action': 'stop', 'ok': True}

    if action == 'resume':
        with state._lock:
            state.override_stop = False
            state.emergency_stop = False
        return {'action': 'resume', 'ok': True}

    if action == 'explore':
        if explore_ref[0] and explore_ref[0].is_alive():
            return {'error': 'already exploring'}
        duration_s = int(cmd.get('duration_s', 300))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = cmd.get('log_path', f'{LOG_DIR}/{ts}_drive_explore.json')
        with state._lock:
            state.override_stop = False
        loop = ExploreLoop(state, engine, duration_s, log_path)
        explore_ref[0] = loop
        loop.start()
        return {'action': 'explore', 'started': True, 'duration_s': duration_s, 'log': log_path}

    if action == 'stop_explore':
        if explore_ref[0]:
            explore_ref[0].stop()
        engine.stop()
        with state._lock:
            state.mode = 'idle'
        return {'action': 'stop_explore', 'ok': True}

    if action == 'set_param':
        key = cmd.get('key')
        val = cmd.get('value')
        if key and val is not None:
            ok = state.set_param(key, val)
            return {'action': 'set_param', 'key': key, 'value': val, 'ok': ok}
        return {'error': 'key and value required'}

    if action == 'get_params':
        with state._lock:
            return dict(state.params)

    if action == 'bumper_events':
        with state._lock:
            return {'events': list(state.bumper_events)}

    if action == 'step_log':
        n = int(cmd.get('n', 20))
        with state._lock:
            return {'log': list(state.step_log)[-n:]}

    if action == 'decide':
        snap = state.snapshot()
        d = decide(state)
        return {'snap': snap, 'decision': d}

    if action == 'shutdown':
        return {'action': 'shutdown', 'ok': True, 'exit': True}

    return {'error': f'unknown action: {action}'}


# ─── Main ─────────────────────────────────────────────────────────────────────

def open_neato():
    from neato_serial.neato import Neato
    n = object.__new__(Neato)
    ports = sorted([p for p in os.listdir('/dev') if p.startswith('ttyACM')])
    if not ports:
        raise RuntimeError('no ttyACM port')
    n.port = '/dev/' + ports[0]
    n.baud = 115200
    n.relay = None
    n.ser = None
    n._lock = threading.Lock()
    n.connect()
    time.sleep(0.3)
    return n


def main():
    signal.signal(signal.SIGABRT, lambda *a: sys.exit(0))

    from vision.capture import Camera
    from vision.detector import Detector

    sys.stdout.write('[drive_daemon] starting up\n'); sys.stdout.flush()

    neato = open_neato()
    neato.test_mode(on=True)
    time.sleep(0.3)
    # LDS (laser scanner) defaults to Off in TestMode — must enable explicitly
    neato.set_lds_rotation(on=True)
    time.sleep(1.0)  # let it spin up to speed
    sys.stdout.write(f'[drive_daemon] serial: {neato.port}, LDS rotation ON\n'); sys.stdout.flush()

    cam = Camera(width=640, height=640)
    cam.start(settle_time=1)

    det = Detector(confidence_threshold=0.35)
    det.start()

    state = AtomicState()
    drive_idle = threading.Event()
    drive_idle.set()  # initially idle
    engine = DriveEngine(neato, state, drive_idle)

    # Start background threads
    sensor_t = SensorThread(neato, state)
    lidar_t = LidarThread(neato, state, drive_idle)
    vision_t = VisionThread(cam, det, state)

    sensor_t.start()
    lidar_t.start()
    vision_t.start()

    # Give sensors a moment to populate
    time.sleep(2.0)
    sys.stdout.write('[drive_daemon] sensors warm, ready\n'); sys.stdout.flush()

    # Socket server
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCKET_PATH)
    srv.listen(5)
    os.chmod(SOCKET_PATH, 0o666)

    explore_ref = [None]  # mutable container for current ExploreLoop

    sys.stdout.write(f'[drive_daemon] ready on {SOCKET_PATH}\n'); sys.stdout.flush()

    try:
        while True:
            conn, _ = srv.accept()
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
                resp = handle_command(cmd, state, engine, explore_ref)
                conn.sendall((json.dumps(resp) + '\n').encode())
                if resp.get('exit'):
                    break
            except Exception as e:
                try:
                    conn.sendall((json.dumps({'error': str(e)}) + '\n').encode())
                except Exception:
                    pass
            finally:
                conn.close()
    finally:
        if explore_ref[0]:
            explore_ref[0].stop()
        sensor_t.stop()
        lidar_t.stop()
        vision_t.stop()
        try:
            engine.stop()
            neato.set_lds_rotation(on=False)
            neato.test_mode(on=False)
            neato.close()
        except Exception:
            pass
        try:
            cam.stop()
        except Exception:
            pass
        srv.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        os._exit(0)


if __name__ == '__main__':
    main()
