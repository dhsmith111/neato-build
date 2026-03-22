# Neato AI Vision Build

Turning a Neato XV Signature Pro robot vacuum into an AI-powered cleaning machine. A Raspberry Pi 5 with an AI HAT+ 2 (Hailo-10H NPU) rides on top of the robot, running real-time object detection and vision-language models to intelligently navigate a home with dynamic obstacles — blankets off the couch, cat toys, delivered packages, closet floors.

The Neato already has LiDAR-based navigation and mapping. This project adds a vision layer on top: cameras see what the LiDAR can't (soft obstacles, clutter, risk assessment), and the AI decides how to handle each situation before the robot blindly drives into it.

> **A note on component choices:** This is a hobby project built for fun and learning. The Pi 5 8GB and AI HAT+ 2 may be overkill for a robot vacuum — a Pi 4 or Zero 2W with a lighter-weight AI kit would likely work fine for basic obstacle detection. The higher-end hardware was chosen because these components will be reused across future projects, and having the extra headroom makes experimentation easier. This can absolutely be built for less.

## How It Works

**Two-tier AI inference on the Hailo NPU:**

- **Fast loop (20-30fps)** — YOLOv8n detects objects in real time. When the robot sees a cat toy or a shoe, it reacts immediately: slow down, steer around, or skip the area.
- **Slow loop** — A vision-language model (QWEN2.5-VL-3B or similar) looks at the bigger picture. It understands scenes ("this is a cluttered closet floor"), assesses risk, and makes strategic cleaning decisions.

**Scout mode** — Before vacuuming, the robot does a slow pre-clean pass through the whole home with cameras active and brush roll off. The AI classifies every obstacle by type and risk, then generates an optimized room-by-room cleaning plan. Only then does the actual cleaning begin.

## Hardware

| Component | Detail |
|---|---|
| Robot | Neato XV Signature Pro (Board Rev 64, FW 3.4.24079) |
| Computer | Raspberry Pi 5 8GB (CanaKit GenAI Kit) |
| AI Accelerator | AI HAT+ 2 (Hailo-10H, 40 TOPS, 8GB dedicated RAM) |
| Cameras | Pi Camera Module 3 Wide + Camera Module 3 Wide NoIR |
| Serial | USB-A to Mini-USB with relay on VBUS for power cycling |
| Power | Yahboom PD board (Neato 4S Li-ion → 5V/5A to Pi via USB-C PD) |
| Mounting | Velcro for prototyping, 3D printed platform planned |

The Pi + HAT + camera stack mounts on top of the Neato's LiDAR cover. The relay breaks the USB power line so the Pi can hard-reset the Neato's serial interface when needed. See [mounting diagram](docs/mounting-layout.svg).

## Development Stages

### Stage 1 — Mechanical Restoration ✅
Neato disassembled, cleaned, reassembled. LiDAR spinning, motors working, baseline vacuum function verified.

### Stage 2 — Serial Communication ✅
Raspberry Pi talks to the Neato over USB serial. Relay power-cycles the USB connection for clean resets. Built a Python serial library (`neato_serial/neato.py`) wrapping all Neato commands: motor control, LiDAR scans, charger status, configuration. Confirmed motor drive commands, battery set to lithium mode.

### Stage 3 — Camera + Object Detection ← current
Connect Pi Camera Module 3 Wide via picamera2. Get YOLOv8n running on the Hailo HAT+ 2 NPU for real-time obstacle detection at floor level. Target: 20-30fps inference identifying common household objects.

### Stage 4 — Reactive Behaviors
Wire detection output to serial commands. When the camera sees an obstacle, the robot reacts: slow down, steer around, stop, or skip. First closed-loop AI behavior — see something, do something.

### Stage 5 — VLM + Scout Mode
Add a vision-language model for scene understanding. Build scout mode: robot drives slowly through the home pre-clean, AI classifies each area, generates an optimized cleaning plan before the brush roll ever turns on.

### Stage 6 — Full Integration
End-to-end autonomous operation: scout pass, AI-generated plan, optimized clean with reactive obstacle avoidance. Dual camera support (standard + NoIR for low-light areas). Error recovery, persistent state, cleaning history.

## Project Structure

```
neato-build/
├── config/           # Model files, settings
├── docs/             # Hardware docs, diagrams, BOM
├── neato_serial/     # Neato serial communication library
│   └── neato.py      # Neato class — relay, serial, commands
├── scout/            # Scout mode and reactive behaviors
├── tests/            # Hardware and integration tests
├── vision/           # Camera capture and YOLO detection
├── vlm/              # Vision-language model inference
├── main.py           # Orchestrator (planned)
└── requirements.txt
```

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```python
from neato_serial.neato import Neato

neato = Neato()
neato.connect()

print(neato.get_version())
print(neato.get_charger())

# Drive forward 100mm
neato.test_mode(on=True)
neato.set_motor(left_dist=100, right_dist=100, speed=100)
neato.test_mode(on=False)

neato.close()
```

Requires Raspberry Pi 5 with gpiozero + lgpio backend (RPi.GPIO is not supported on Pi 5).

## Docs

- [Bill of Materials](docs/BOM.md) — Complete parts list
- [Power System](docs/POWER.md) — Battery specs, Yahboom PD board, wiring plan
- [Wiring Reference](docs/WIRING.md) — Relay, serial, camera connections
- [Software Setup](docs/SETUP.md) — Stack, robot config, troubleshooting
- [Mounting Layout](docs/mounting-layout.svg) — Physical component placement