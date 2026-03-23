"""Scout session logging with breadcrumb data for Stage 5."""

import json
import time
from vision.session import Session
from scout.rules import Action


class ScoutLogger:
    """Logs frames, decisions, and breadcrumb data during a scout run."""

    def __init__(self, session_name="scout"):
        self.session = Session(session_name)
        self.log_entries = []
        self._last_action_type = None

    def log_frame(self, frame, snapshot, action, odometry, sensor_state,
                  lidar_scan=None, save_image=False):
        """Record a single decision cycle.

        Args:
            frame: RGB numpy array
            snapshot: Snapshot from perception
            action: Action from rules
            odometry: Odometry from driver
            sensor_state: SensorState from sensors
            lidar_scan: raw LiDAR string (optional, periodic)
            save_image: whether to save annotated frame
        """
        entry = {
            "frame": self.session.frame_num,
            "timestamp": time.time(),
            "action": action.action_type.value,
            "reason": action.reason,
            "odometry": odometry.as_dict(),
            "detections": len(snapshot.obstacles),
            "path_clear": snapshot.path_clear,
            "pet": snapshot.pet_in_frame,
            "overhead": snapshot.overhead_obstruction,
            "tilting": snapshot.tilting,
            "wall_mm": snapshot.wall_distance_mm,
            "battery_mv": sensor_state.battery_voltage_mv if sensor_state else 0,
        }

        if snapshot.closest_obstacle:
            entry["closest"] = {
                "label": snapshot.closest_obstacle.label,
                "zone": snapshot.closest_obstacle.zone.value,
                "bearing": snapshot.closest_obstacle.bearing,
            }

        if lidar_scan:
            entry["lidar_snapshot"] = True

        self.log_entries.append(entry)

        # Save image on interesting events or periodically
        if save_image:
            detections_for_draw = None
            # Convert snapshot obstacles back to something Session.save can draw
            # For now, save raw frame — detection overlay is a nice-to-have
            self.session.save(frame, label=action.action_type.value)

        self._last_action_type = action.action_type

    def should_save_image(self, action, snapshot, frame_count, config):
        """Decide if this frame is worth saving an image for."""
        interval = config.get("log_every_n_frames", 10)

        # Always save on action change
        if action.action_type != self._last_action_type:
            return True
        # Always save on pet
        if snapshot.pet_in_frame:
            return True
        # Always save on overhead / tilt
        if snapshot.overhead_obstruction or snapshot.tilting:
            return True
        # Periodic
        if frame_count % interval == 0:
            return True
        return False

    def save_summary(self):
        """Write JSON log to session directory."""
        path = self.session.summary_path()
        with open(path, 'w') as f:
            json.dump(self.log_entries, f, indent=2)
        return path
