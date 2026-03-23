"""Reactive decision engine: Snapshot → Action."""

from enum import Enum
from dataclasses import dataclass
from scout.perception import Zone


class ActionType(Enum):
    FORWARD = "forward"
    SLOW_FORWARD = "slow_forward"
    STOP = "stop"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    BACKUP = "backup"
    WAIT = "wait"


@dataclass
class Action:
    action_type: ActionType
    reason: str
    distance_mm: int = 0
    speed_mm_s: int = 0


class RuleEngine:
    """Prioritized reactive rules. Takes a Snapshot, returns an Action."""

    def __init__(self, config):
        self.config = config
        self.consecutive_clear = 0
        self._last_turn = "left"  # alternate backup turns
        self._straight_distance_mm = 0  # track straight-line travel

    def decide(self, snapshot, bumper_hit, cliff, wheel_drop):
        """Apply rules in priority order.

        Args:
            snapshot: Snapshot from perception
            bumper_hit: bool from sensor monitor
            cliff: bool from sensor monitor
            wheel_drop: bool from sensor monitor

        Returns:
            Action
        """
        cfg = self.config

        # --- Priority 1: Cliff (stairs) ---
        if cliff:
            return self._reactive(ActionType.STOP, "cliff detected — stairs?")

        # --- Priority 2: Wheel drop (robot lifted) ---
        if wheel_drop:
            return self._reactive(ActionType.STOP, "wheel drop — robot lifted")

        # --- Priority 3: Bumper hit ---
        if bumper_hit:
            turn = self._alternate_turn()
            return self._reactive(ActionType.BACKUP,
                                  f"bumper hit — backup then {turn}",
                                  cfg["backup_distance_mm"], cfg["backup_speed_mm_s"])

        # --- Priority 4: Wall sensor too close ---
        wall_mm = snapshot.wall_distance_mm
        if wall_mm < cfg["wall_stop_mm"]:
            turn = self._turn_from_snapshot(snapshot)
            return self._reactive(turn, f"wall at {wall_mm}mm — turning",
                                  cfg["turn_distance_mm"], cfg["turn_speed_mm_s"])

        if wall_mm < cfg["wall_slow_mm"]:
            return self._reactive(ActionType.SLOW_FORWARD,
                                  f"wall at {wall_mm}mm — slowing",
                                  cfg["step_distance_mm"] // 2,
                                  cfg["step_speed_mm_s"] // 2)

        # --- Priority 5: Pet in close/danger zone ---
        if snapshot.pet_in_frame:
            pets = [o for o in snapshot.obstacles
                    if o.is_pet and o.zone in (Zone.CLOSE, Zone.DANGER)]
            if pets:
                return self._reactive(ActionType.WAIT,
                                      f"pet ({pets[0].label}) nearby — waiting")

        # --- Priority 6: Obstacle in DANGER zone center ---
        danger_center = [o for o in snapshot.obstacles
                         if o.zone == Zone.DANGER and o.bearing == "center"
                         and not o.is_pet]
        if danger_center:
            return self._reactive(ActionType.BACKUP,
                                  f"DANGER: {danger_center[0].label} dead ahead",
                                  cfg["backup_distance_mm"], cfg["backup_speed_mm_s"])

        # --- Priority 7: Obstacle in CLOSE zone center ---
        close_center = [o for o in snapshot.obstacles
                        if o.zone == Zone.CLOSE and o.bearing == "center"
                        and not o.is_pet]
        if close_center:
            obs = close_center[0]
            turn = self._turn_away_from(obs)
            return self._reactive(turn, f"CLOSE: {obs.label} center — turning",
                                  cfg["turn_distance_mm"], cfg["turn_speed_mm_s"])

        # --- Priority 8: Obstacle in NEAR zone center ---
        near_center = [o for o in snapshot.obstacles
                       if o.zone == Zone.NEAR and o.bearing == "center"]
        if near_center:
            return self._reactive(ActionType.SLOW_FORWARD,
                                  f"NEAR: {near_center[0].label} ahead — slowing",
                                  cfg["step_distance_mm"] // 2,
                                  cfg["step_speed_mm_s"] // 2)

        # --- Priority 9: Overhead obstruction ---
        if snapshot.overhead_obstruction:
            return self._reactive(ActionType.BACKUP,
                                  "overhead obstruction — backing up",
                                  cfg["backup_distance_mm"], cfg["backup_speed_mm_s"])

        # --- Priority 10: Tilt ---
        if snapshot.tilting:
            return self._reactive(ActionType.BACKUP,
                                  "tilting — wedging under something",
                                  cfg["backup_distance_mm"], cfg["backup_speed_mm_s"])

        # --- Priority 11: Exploration turn (don't drive straight too long) ---
        max_straight = cfg.get("max_straight_mm", 900)
        if self._straight_distance_mm >= max_straight:
            self._straight_distance_mm = 0
            turn = self._alternate_turn()
            return Action(turn, f"exploration turn after {max_straight}mm straight",
                          distance_mm=cfg["turn_distance_mm"],
                          speed_mm_s=cfg["turn_speed_mm_s"])

        # --- Priority 12: Path clear ---
        self.consecutive_clear += 1
        step = cfg["step_distance_mm"]
        if self.consecutive_clear >= cfg["clear_frames_before_speedup"]:
            step = min(step * 2, cfg["max_step_distance_mm"])

        self._straight_distance_mm += step
        return Action(ActionType.FORWARD, "path clear",
                      distance_mm=step,
                      speed_mm_s=cfg["step_speed_mm_s"])

    def _reactive(self, action_type, reason, distance_mm=0, speed_mm_s=0):
        """Return an action and reset forward-tracking state."""
        self.consecutive_clear = 0
        self._straight_distance_mm = 0
        return Action(action_type, reason, distance_mm, speed_mm_s)

    def _alternate_turn(self):
        """Alternate left/right on backup turns."""
        if self._last_turn == "left":
            self._last_turn = "right"
            return ActionType.TURN_RIGHT
        else:
            self._last_turn = "left"
            return ActionType.TURN_LEFT

    def _turn_away_from(self, obstacle):
        """Turn away from obstacle based on its bearing."""
        if obstacle.x_center < 0.5:
            return ActionType.TURN_RIGHT
        return ActionType.TURN_LEFT

    def _turn_from_snapshot(self, snapshot):
        """Pick turn direction based on obstacles — away from the densest side."""
        left_count = sum(1 for o in snapshot.obstacles if o.bearing == "left")
        right_count = sum(1 for o in snapshot.obstacles if o.bearing == "right")
        if left_count > right_count:
            return ActionType.TURN_RIGHT
        return ActionType.TURN_LEFT
