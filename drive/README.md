# drive/ — Autonomous driving subsystem

Multi-threaded daemon that fuses LiDAR + camera + onboard sensors to drive the
Neato XV chassis. One piece of the broader Pi+Hailo+Neato build.

## Architecture

```
                 /tmp/drive.sock
                       │
                       ▼
                ┌──────────────┐         shared
                │ SocketServer │──────►  AtomicState  ◄─────────┐
                └──────────────┘         (locked)               │
                       │                  ▲                     │
                       │ commands         │ writes              │
                       ▼                  │                     │
                ┌──────────────┐    ┌─────┴────┐   ┌───────┐    │
                │ DriveEngine  │    │ Sensor   │   │ Lidar │    │
                │  forward     │    │  thread  │   │ thread│    │
                │  pivot/arc   │    │  (5Hz)   │   │ (~1Hz)│    │
                │  smooth_stop │    └──────────┘   └───────┘    │
                └──────────────┘            │           │       │
                       │                    │           │       │
                       │   drive_idle.clear/set         │       │
                       └────────────────────┴───────────┘       │
                                                                │
                                            ┌───────────────────┘
                                            │
                                       ┌────┴─────┐
                                       │  Vision  │
                                       │  thread  │
                                       │  (~1Hz)  │
                                       └──────────┘
```

### Threads

- **SensorThread** — `GetDigitalSensors` + `GetAnalogSensors` at ~5Hz. Bumpers
  and cliff sensors are checked here; emergency_stop is set from this thread.
- **LidarThread** — `GetLDSScan` whenever drive engine is idle (1.2s per scan).
  Yields the serial port to motor commands via `drive_idle` event.
- **VisionThread** — Camera capture + Hailo YOLO at ~1-2Hz.
- **DriveEngine** — synchronous motor primitives, called from socket handler or
  ExploreLoop. Single SetMotor command per move (firmware does the trapezoid).
- **ExploreLoop** — autonomous loop reading AtomicState + calling DriveEngine.

### Single half-duplex serial port

The Neato has one USB serial port for everything (sensors, LiDAR, motors).
Three threads compete; coordination is via:

1. `neato._lock` — atomic command-response inside `Neato.send()`.
2. `drive_idle: threading.Event` — LidarThread waits while motor commands run
   (the 1.2s LiDAR scan would starve the 0.05s motor command otherwise).

### Important firmware quirks

- `SetLDSRotation On` MUST be called after `TestMode On` or LiDAR returns
  frozen scans.
- `SetMotor LWheelDist N RWheelDist N Speed S` runs the firmware's built-in
  trapezoidal speed profile (accel + cruise + decel). **Don't chunk** — the
  firmware can't decelerate within a tiny chunk, so it slams to a stop.
- LiDAR angle map: `0` = rear, `90` = right, `180` = front, `270` = left.

## Files

- `daemon.py` — main multi-threaded daemon
- `client.py` — thin command-line client (`python drive/client.py status`)
- `pilot.py` — legacy single-threaded version (kept for reference)

## Running

```bash
# from repo root
./start_drive.sh                        # starts daemon, waits for ready

python drive/client.py status           # snapshot
python drive/client.py forward 300      # move 300mm
python drive/client.py explore --duration 600  # 10min autonomous run
python drive/client.py shutdown
```

## Tunable parameters (live, via socket)

```bash
python drive/client.py get_params
python drive/client.py set_param forward_speed 200
```

Defaults are conservative because the camera is mounted at a downward tilt
(~30°) and the LiDAR plane misses low/thin obstacles, so we drive slowly enough
that bumper aborts don't tip the robot.

## Logs

- `/tmp/drive.log` — daemon stdout (sensor/lidar/vision events + step decisions)
- `captures/<timestamp>_drive_explore.json` — per-step decision log

## Open issues

- Camera mount angle (~30° down) — bbox_area is unreliable for distance
- No spatial memory between runs — can't return to dock without manual placement
- Odometry exists in AtomicState but isn't being populated (GetMotors not in
  SensorThread loop)
