# Software Setup

## OS & Runtime
- Raspberry Pi OS 64-bit (Bookworm/Trixie)
- Python 3.13
- Venv: `~/neato-build/venv` — always activate before working

## GPIO
- **Must use gpiozero + lgpio backend** — RPi.GPIO does NOT support Pi 5
- lgpio is the default backend on Pi 5

## Installed
- pyserial — Neato serial communication
- gpiozero — GPIO control (relay)
- lgpio — Pi 5 GPIO backend

## Stage 3 (to install)
- picamera2 — camera capture
- Hailo runtime (HailoRT) — NPU inference
- YOLOv8n HEF model — object detection on Hailo

## Stage 5 (to install)
- VLM runtime — QWEN2.5-VL-3B or Llama-3.2-3B-Instruct on Hailo HAT+ 2

## Neato Robot Setup
- Board Rev 64, Firmware SW 3.4.24079
- Serial: `/dev/ttyACM0` at 115200 baud
- After lithium battery install: `SetConfig BatteryType 3`
- Battery initialization: Menu → Support → New Battery
- Dual battery config — hidden switch in dust bin (flip to ON after new batteries installed)
- Brush roll needs cleaning before first vacuum run

## Troubleshooting
- **VSCode SSH connection loop:** From a local terminal, run:
  ```bash
  ssh admin-pi@<pi-ip> "pkill -f vscode-server; rm -rf ~/.vscode-server"
  ```