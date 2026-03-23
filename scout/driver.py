"""Motor driver: translates Actions into Neato serial commands + tracks odometry."""

import math
import time
from scout.rules import ActionType


class Odometry:
    """Dead-reckoning position tracker. Approximate only."""

    def __init__(self):
        self.x = 0.0       # mm
        self.y = 0.0       # mm
        self.heading = 0.0  # radians, 0 = initial forward

    def update_forward(self, distance_mm):
        self.x += distance_mm * math.cos(self.heading)
        self.y += distance_mm * math.sin(self.heading)

    def update_turn(self, left_mm, right_mm, wheel_base_mm=240):
        """Update heading from differential wheel distances."""
        delta_heading = (right_mm - left_mm) / wheel_base_mm
        self.heading += delta_heading

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

    def as_dict(self):
        return {
            "x_mm": round(self.x, 1),
            "y_mm": round(self.y, 1),
            "heading_deg": round(math.degrees(self.heading), 1),
        }


class Driver:
    """Translates Action objects into Neato motor commands."""

    WHEEL_BASE_MM = 240  # approximate Neato XV wheel separation

    def __init__(self, neato, config):
        self.neato = neato
        self.config = config
        self.odometry = Odometry()

    def setup(self):
        """Enter TestMode for motor control."""
        self.neato.test_mode(on=True)
        time.sleep(0.5)

    def teardown(self):
        """Exit TestMode."""
        self.neato.test_mode(on=False)

    def execute(self, action):
        """Execute an action. Blocks until movement is complete.

        Returns:
            str: description for logging
        """
        settle = self.config.get("move_settle_time_s", 0.3)
        at = action.action_type

        if at == ActionType.FORWARD or at == ActionType.SLOW_FORWARD:
            dist = action.distance_mm
            speed = action.speed_mm_s
            self.neato.set_motor(left_dist=dist, right_dist=dist, speed=speed)
            self._wait_for_move(dist, speed, settle)
            self.odometry.update_forward(dist)
            return f"forward {dist}mm @ {speed}mm/s"

        elif at == ActionType.BACKUP:
            dist = action.distance_mm
            speed = action.speed_mm_s
            self.neato.set_motor(left_dist=-dist, right_dist=-dist, speed=speed)
            self._wait_for_move(dist, speed, settle)
            self.odometry.update_forward(-dist)
            return f"backup {dist}mm"

        elif at == ActionType.TURN_LEFT:
            turn_dist = action.distance_mm or self.config["turn_distance_mm"]
            speed = action.speed_mm_s or self.config["turn_speed_mm_s"]
            self.neato.set_motor(left_dist=-turn_dist, right_dist=turn_dist, speed=speed)
            self._wait_for_move(turn_dist, speed, settle)
            self.odometry.update_turn(-turn_dist, turn_dist, self.WHEEL_BASE_MM)
            return f"turn left {turn_dist}mm"

        elif at == ActionType.TURN_RIGHT:
            turn_dist = action.distance_mm or self.config["turn_distance_mm"]
            speed = action.speed_mm_s or self.config["turn_speed_mm_s"]
            self.neato.set_motor(left_dist=turn_dist, right_dist=-turn_dist, speed=speed)
            self._wait_for_move(turn_dist, speed, settle)
            self.odometry.update_turn(turn_dist, -turn_dist, self.WHEEL_BASE_MM)
            return f"turn right {turn_dist}mm"

        elif at == ActionType.STOP:
            self.neato.set_motor(left_dist=0, right_dist=0, speed=0)
            time.sleep(settle)
            return "stop"

        elif at == ActionType.WAIT:
            wait_time = self.config.get("pet_wait_seconds", 3.0)
            time.sleep(wait_time)
            return f"wait {wait_time}s"

        return "noop"

    def _wait_for_move(self, distance_mm, speed_mm_s, settle):
        """Block until move is expected to complete."""
        if speed_mm_s > 0:
            move_time = distance_mm / speed_mm_s
            time.sleep(move_time + settle)
        else:
            time.sleep(settle)
