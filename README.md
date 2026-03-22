# Neato AI Vision Build

AI vision layer on top of a Neato XV Signature Pro's LiDAR navigation. A Raspberry Pi 5 with an AI HAT+ 2 rides on the robot, running real-time object detection and vision-language models to intelligently handle dynamic obstacles — blankets, cat toys, packages, closet floors.

## Hardware

| Component | Detail |
|---|---|
| Robot | Neato XV Signature Pro (Board Rev 64, FW 3.4.24079) |
| Computer | Raspberry Pi 5 8GB |
| AI Accelerator | AI HAT+ 2 (Hailo-10H, 40 TOPS, 8GB) |
| Cameras | 2x Pi Camera Module 3 Wide (one standard, one NoIR) |
| Connection | USB serial via relay power cycle workaround |
| Power | Yahboom PD board (Neato 4S Li-ion battery → 5V/5A Pi) |

## Architecture

**Two-tier inference on the Hailo NPU:**
- **Fast loop** — YOLOv8n at 20-30fps for real-time obstacle detection and reactive avoidance
- **Slow loop** — Vision-language model for strategic scene understanding and cleaning plan generation

**Scout mode** — Pre-clean pass where the robot drives slowly through the home with cameras active, classifies obstacles by type and risk, and generates an optimized cleaning plan before the brush roll activates.

## Documentation

- [docs/BOM.md](docs/BOM.md) — Complete bill of materials and purchase history
- [docs/POWER.md](docs/POWER.md) — Power system design and battery details
- [docs/WIRING.md](docs/WIRING.md) — Relay, serial, and camera wiring reference
- [docs/SETUP.md](docs/SETUP.md) — Software stack, robot config, troubleshooting
- [docs/mounting-layout.svg](docs/mounting-layout.svg) — Physical mounting diagram

## Project Structure

```
neato-build/
├── config/           # Model files, settings
├── neato_serial/     # Neato serial communication library
│   └── neato.py      # Neato class — relay, serial, commands
├── scout/            # Scout mode and reactive behaviors
├── tests/            # Hardware and integration tests
├── vision/           # Camera capture and YOLO detection
├── vlm/              # Vision-language model inference
├── main.py           # Orchestrator (planned)
└── requirements.txt
```

## Development Stages

1. **Mechanical restoration** — Neato disassembled, cleaned, verified ✅
2. **Serial communication** — Pi ↔ Neato via USB relay, command library ✅
3. **Camera + object detection** — picamera2 + YOLOv8n on Hailo HAT+ 2
4. **Reactive behaviors** — Detection → serial commands, first closed-loop AI
5. **VLM + scout mode** — Scene understanding and pre-clean planning
6. **Full integration** — Scout → plan → optimized clean run

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Requires Raspberry Pi 5 with gpiozero + lgpio backend (RPi.GPIO is not supported on Pi 5).

## Usage

```python
from neato_serial.neato import Neato

neato = Neato()
neato.connect()

print(neato.get_version())
print(neato.get_charger())

neato.test_mode(on=True)
neato.set_motor(left_dist=100, right_dist=100, speed=100)
neato.test_mode(on=False)

neato.close()
```
