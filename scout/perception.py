"""Perception: fuse vision detections + hardware sensors into a world snapshot."""

import time
from enum import Enum
from dataclasses import dataclass, field


class Zone(Enum):
    """Distance zone based on bounding box area in frame."""
    FAR = "far"        # < near threshold
    NEAR = "near"      # near..close
    CLOSE = "close"    # close..danger
    DANGER = "danger"  # > danger threshold


@dataclass
class Obstacle:
    """A detected object with spatial classification."""
    label: str
    confidence: float
    zone: Zone
    bearing: str          # "left", "center", "right"
    bbox_area: float      # normalized area 0-1
    is_pet: bool
    x_center: float       # normalized, 0=left, 1=right
    y_min: float          # normalized top of bbox


@dataclass
class Snapshot:
    """World state from a single perception cycle."""
    obstacles: list = field(default_factory=list)
    path_clear: bool = True
    closest_obstacle: object = None
    pet_in_frame: bool = False
    overhead_obstruction: bool = False
    tilting: bool = False
    wall_distance_mm: int = 9999
    timestamp: float = 0.0


def perceive(detections, sensor_state, config, baseline_pitch=0.0, baseline_roll=0.0,
             lidar_scan=None):
    """Convert raw detections + sensor state into a world snapshot.

    Args:
        detections: list[Detection] from vision.detector
        sensor_state: SensorState from scout.sensors
        config: dict from config/scout.json
        baseline_pitch: calibrated pitch at startup
        baseline_roll: calibrated roll at startup
        lidar_scan: raw LiDAR scan string (optional, for trailing clearance)

    Returns:
        Snapshot
    """
    zone_thresholds = config["zone_thresholds"]
    pet_labels = set(config["pet_labels"])
    ignore_labels = set(config["ignore_labels"])
    overhead_top = config.get("overhead_top_fraction", 0.10)
    overhead_area = config.get("overhead_min_area", 0.15)
    tilt_threshold = config.get("tilt_threshold_degrees", 5.0)

    obstacles = []
    pet_in_frame = False
    overhead = False

    for det in detections:
        if det.label in ignore_labels:
            continue

        # Bbox area as fraction of frame
        area = (det.x_max - det.x_min) * (det.y_max - det.y_min)

        # Zone from area
        if area >= zone_thresholds["danger"]:
            zone = Zone.DANGER
        elif area >= zone_thresholds["close"]:
            zone = Zone.CLOSE
        elif area >= zone_thresholds["near"]:
            zone = Zone.NEAR
        else:
            zone = Zone.FAR

        # Bearing from x-center
        x_center = (det.x_min + det.x_max) / 2
        if x_center < 0.33:
            bearing = "left"
        elif x_center > 0.67:
            bearing = "right"
        else:
            bearing = "center"

        is_pet = det.label in pet_labels
        if is_pet:
            pet_in_frame = True

        # Overhead detection: large object in top of frame
        if det.y_min < overhead_top and area > overhead_area:
            overhead = True

        obstacles.append(Obstacle(
            label=det.label,
            confidence=det.confidence,
            zone=zone,
            bearing=bearing,
            bbox_area=area,
            is_pet=is_pet,
            x_center=x_center,
            y_min=det.y_min,
        ))

    # Path clear = no center obstacles in CLOSE or DANGER
    center_threats = [o for o in obstacles
                      if o.bearing == "center" and o.zone in (Zone.CLOSE, Zone.DANGER)]
    path_clear = len(center_threats) == 0

    # Closest obstacle by bbox area (larger = closer)
    closest = max(obstacles, key=lambda o: o.bbox_area) if obstacles else None

    # Tilt detection from accelerometer
    tilting = False
    if sensor_state:
        pitch_delta = abs(sensor_state.pitch_degrees - baseline_pitch)
        roll_delta = abs(sensor_state.roll_degrees - baseline_roll)
        tilting = pitch_delta > tilt_threshold or roll_delta > tilt_threshold

    # LiDAR trailing clearance check
    if lidar_scan and not overhead:
        overhead = _check_lidar_trailing_clearance(lidar_scan)

    wall_dist = sensor_state.wall_distance_mm if sensor_state else 9999

    return Snapshot(
        obstacles=obstacles,
        path_clear=path_clear,
        closest_obstacle=closest,
        pet_in_frame=pet_in_frame,
        overhead_obstruction=overhead,
        tilting=tilting,
        wall_distance_mm=wall_dist,
        timestamp=time.time(),
    )


def _check_lidar_trailing_clearance(lidar_scan):
    """Check if rear LiDAR readings suggest overhead obstruction.

    If front is clear but rear (90-270°) has close readings,
    we may be driving under something our tall rear won't fit under.

    Returns True if trailing clearance issue detected.
    """
    # Parse LiDAR scan into angle:distance dict
    readings = _parse_lidar(lidar_scan)
    if not readings:
        return False

    # Average front distances (330-30°)
    front = [d for a, d in readings.items() if (a >= 330 or a <= 30) and d > 0]
    # Average rear distances (150-210°)
    rear = [d for a, d in readings.items() if 150 <= a <= 210 and d > 0]

    if not front or not rear:
        return False

    avg_front = sum(front) / len(front)
    avg_rear = sum(rear) / len(rear)

    # If front is clear (>500mm) but rear is close (<200mm), something overhead
    return avg_front > 500 and avg_rear < 200


def _parse_lidar(raw):
    """Parse GetLDSScan response into {angle: distance_mm} dict."""
    readings = {}
    for line in raw.strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                angle = int(parts[0].strip())
                dist = int(parts[1].strip())
                readings[angle] = dist
            except ValueError:
                continue
    return readings
