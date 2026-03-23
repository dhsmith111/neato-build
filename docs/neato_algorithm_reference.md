# Neato XV Algorithm Reference

Research notes from Neato Robotics patents and open-source robotics literature.
This documents the algorithmic strategies used in consumer robot vacuums,
studied as inspiration for our own implementation.

## Patent Sources

| Patent | Title | Key Content |
|--------|-------|-------------|
| US 9,678,509 | SLAM for Mobile Robot | Particle filter, occupancy grid, delocalization detection, dynamic cells |
| US 8,483,881 | Localization and Mapping | Partial map segmentation, particle filter architecture |
| US 8,996,172 | LIDAR Distance Sensor | Laser triangulation, 360° scanning, self-calibration |
| US 10,054,949 | Corner Traversal | Wall following, inside/outside corner strategies |
| US 11,272,823 | Zone Cleaning | Room segmentation, battery-aware multi-zone scheduling |
| US 9,026,302 | Coverage Planning (Evolution/iRobot) | Boustrophedon coverage, perimeter following, frontier exploration |
| US 10,638,906 | Camera-to-Floorplan | Downward camera → bird's-eye view via perspective transform |

All readable at `https://patents.google.com/patent/US_______/en`

---

## 1. SLAM — Simultaneous Localization and Mapping

**Source**: US 9,678,509 / US 8,483,881

### Particle Filter Localization
- Each particle represents a candidate pose (x, y, theta)
- Per iteration: apply odometry motion model → apply noise → evaluate against occupancy grid → compute weight
- Resample particles proportional to weights
- Particles below discard threshold are culled; above clone threshold are duplicated

### Occupancy Grid
- Cell-based grid, each cell stores probability: 0 (empty) to 254 (occupied), initialized at 127 (unknown)
- LIDAR ray update: cells along the ray from robot to wall → decrease probability (empty); cell at the wall endpoint → increase probability (occupied)
- Grid resolution: 1-5 cm per cell

### Dynamic Cell Detection
- If a previously-empty cell suddenly appears occupied (or vice versa), mark it as "dynamic"
- Suspend map updates for dynamic cells until stable
- Handles moving objects (people, pets) without corrupting the map

### Delocalization Detection (Verification Particles)
- Inject deliberately erroneous particles with large angular offsets (30-60°)
- When localized: erroneous particles cluster at bottom of weight distribution (low weights)
- When delocalized: erroneous particles scatter throughout the distribution
- Detection metric: average rank index of erroneous particles
- On delocalization: suspend map updates, attempt relocalization

### Tilt Detection
- Compare first-to-last LIDAR readings in a scan; large differential = tilted
- Also uses accelerometer pitch/roll data
- Discard spatial data collected during tilt (phantom walls from tilted laser plane)

---

## 2. Coverage Planning

**Source**: US 9,026,302 (Evolution Robotics / iRobot, similar to Neato strategy)

### Phase 1 — Boustrophedon Snaking
- Parallel back-and-forth traversal in "ranks" spaced ~28cm apart (brush width)
- Start at origin, go north to Rank 1, traverse east, turn south to Rank 2, traverse west (alternating)
- Obstacle handling: simulate paths both north and south around obstacle, pick shortest route
- Rank extension: if no obstacle ahead, extend current rank by predefined increment

### Phase 2 — Perimeter Following
- Follow edges between explored/unexplored or explored/occupied areas
- Navigate along boundary with tangential bias (approach + retreat pattern)
- Periodically check for new snakeable regions
- Terminate when re-covering already-covered perimeter

### Phase 3 — Frontier Selection
- Frontiers (boundaries between explored and unexplored) ranked by: distance, length (longer preferred), localization quality
- Minimum rank length constraints: ~3x robot diameter for initial region, ~1x for subsequent
- Deferred frontiers: if cost-to-reach is too high relative to length, defer and clean later
- Completion: all frontiers exhausted → navigate to dock/start

---

## 3. Wall Following and Corner Handling

**Source**: US 10,054,949

### Wall Detection
- Line extraction from LIDAR scans detects walls as line segments
- Clustering algorithms group points into wall segments

### Inside Corners
- Detect approaching interior corner from intersecting line segments
- Override obstacle avoidance to allow controlled wall contact
- Back up after contact, pivot into corner
- D-shaped chassis positions brushes at front to minimize unreached area

### Outside Corners
- Detect wall edge disappearance (wall ends)
- Pivot toward the next wall
- Back up to clean area missed by overshooting
- Priority system: complete current corner before detecting next

---

## 4. Zone Cleaning

**Source**: US 11,272,823

### Zone Definition
- User-defined zones (rectangle, L-shape, custom polygons) or auto-detected via room features
- System calculates a "relevancy point" (starting location) guaranteed within zone boundary
- Zones auto-adjusted to align with detected walls

### Multi-Zone Path Planning
- Optimal zone visiting order based on proximity and battery
- Battery-aware: if charge can't complete nearest zone but suffices for a farther one, clean farther first, then recharge
- Directional variation: longitudinal one session, latitudinal the next (cross-hatching for better coverage)

---

## 5. LIDAR Hardware

**Source**: US 8,996,172

- Laser triangulation: `distance = focal_length * baseline / image_plane_offset`
- 360° scanning at 5-10 Hz
- Angular resolution: ~1 degree (360 readings per revolution)
- Range: up to 6 meters, accuracy 1-3 cm
- Self-calibration: analyzes wall straightness across rotation cycles

---

## 6. Open-Source SLAM Implementations

These implement the same or similar algorithms and are available for our use:

| Library | Approach | Notes |
|---------|----------|-------|
| GMapping (ROS) | Rao-Blackwellized particle filter | Proven with Neato LIDAR, 8-100 particles sufficient |
| slam_toolbox (ROS2) | Graph-based SLAM | Default for Nav2, mature and well-tested |
| Google Cartographer | Scan-to-submap matching + loop closure | Tested with Neato Revo LDS, sub-cm accuracy |
| Hector SLAM (ROS) | Scan matching only (no odometry needed) | Good for platforms with poor odometry |

### GMapping Key Innovations
1. **Improved proposal distribution**: uses both odometry AND latest laser scan (scan matching sharpens the proposal before sampling)
2. **Selective resampling**: only resample when effective particle count drops below N/2, preventing particle depletion

### Cartographer Key Details
- Scan-to-submap matching via nonlinear least squares (Ceres solver)
- Loop closure via branch-and-bound scan matching with precomputed multi-resolution grids
- Tested with Neato Revo LDS at ~2 Hz: measurement errors within 0.01-0.11 meters

---

## How This Applies to Our Build

Our Neato XV + Pi 5 + Hailo-10H has everything needed to implement these algorithms:

| Algorithm Component | Our Hardware | Advantage Over Original |
|---------------------|-------------|------------------------|
| LIDAR SLAM | Neato LDS (360°, 5 Hz) | Same sensor, plus camera for visual features |
| Obstacle detection | Camera + YOLOv8m on Hailo | Original had no camera — we can classify objects |
| Coverage planning | Pi 5 compute | More compute for better path optimization |
| Dynamic objects | YOLO detections | Original used cell probability changes; we see what it is |
| Localization | LDS + odometry + camera | Visual landmarks supplement LIDAR scan matching |

### Implementation Path (Stages 5-6)
1. **Stage 5**: SLAM via slam_toolbox or Cartographer (ROS2), overlay YOLO detections as semantic markers
2. **Stage 6**: Coverage planner using boustrophedon + frontier exploration, zone management, dock return
