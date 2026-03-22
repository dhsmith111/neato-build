# Software Setup

## OS & Runtime
- Raspberry Pi OS 64-bit (Bookworm/Trixie)
- Python 3.13
- Venv: `~/neato-build/venv` — created with `--system-site-packages` (required for picamera2 and other system libraries)
- Always activate before working: `source venv/bin/activate`

## GPIO
- **Must use gpiozero + lgpio backend** — RPi.GPIO does NOT support Pi 5
- lgpio is the default backend on Pi 5

## Installed
- pyserial — Neato serial communication
- gpiozero — GPIO control (relay)
- lgpio — Pi 5 GPIO backend
- picamera2 — camera capture (system package via apt: `python3-picamera2`)

## Stage 3 Setup Log

### Camera verification
1. Connected Pi Camera Module 3 Wide to CAM0 via 500mm ribbon cable
2. Verified detection: `rpicam-hello --list-cameras` → `imx708_wide [4608x2592]`
3. Captured test image: `rpicam-still -o test.jpg --width 2304 --height 1296 -t 2000` — 30fps confirmed

### Venv rebuild
The original venv was created without `--system-site-packages`, so picamera2 (installed via apt as `python3-picamera2`) wasn't accessible. Recreated:
```bash
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```
Verified picamera2 works in Python: `Picamera2()` → configure → start → capture_file.

### Hailo-10H driver and runtime install
The AI HAT+ 2 uses a Hailo-10H chip. This needs the `h10-` prefixed packages, NOT the generic `hailo-` ones.

**What didn't work:**
```bash
sudo apt install hailo-all  # Installs hailort 4.23.0 — does NOT support Hailo-10H
```
This installs the Hailo-8/8L runtime. The kernel driver loads but can't bind to the 10H device (`/dev/hailo0` never appears). Even after installing the H10 kernel driver separately (`h10-hailort-pcie-driver`), the 4.x userspace runtime errors with: `Hailo1X Devices are only supported in versions 5.0.0 and above.`

**What works:**
```bash
sudo apt install hailo-h10-all
```
This installs the correct packages:
- `h10-hailort 5.1.1` — runtime library
- `h10-hailort-pcie-driver 5.1.1` — kernel driver
- `python3-h10-hailort 5.1.1` — Python bindings

Reboot required after install. Verify with:
```python
from hailo_platform import VDevice
vdevice = VDevice()  # Should print no errors
print(vdevice.get_physical_devices_ids())  # ['0001:01:00.0']
vdevice.release()
```

### YOLOv8m inference on Hailo-10H

**What didn't work — old `InferVStreams` API:**
```python
from hailo_platform import VDevice, HEF, InferVStreams, InputVStreamParams, OutputVStreamParams
with VDevice() as vdevice:
    network_group = vdevice.configure(hef)[0]  # FAILS: HAILO_NOT_IMPLEMENTED (error 7)
```
The `VDevice.configure()` + `InferVStreams` pattern is the Hailo-8 (hailort 4.x) synchronous API. It is **not implemented** on Hailo-10H (hailort 5.x). The Hailo community forums confirm this is expected — H10 requires the newer async InferModel API.

**What works — `picamera2.devices.Hailo` wrapper:**
```python
from picamera2.devices import Hailo
with Hailo('/usr/share/hailo-models/yolov8m_h10.hef') as hailo:
    model_h, model_w, _ = hailo.get_input_shape()
    results = hailo.run(frame)  # Returns list of 80 arrays, one per COCO class
```
The `Hailo` class (from picamera2) wraps `VDevice.create_infer_model()` + `configured_infer_model.run_async()`. Each array in the result has shape `(N, 5)` where N = detections for that class, and each row is `[y_min, x_min, y_max, x_max, confidence]`.

Under the hood, the correct API path is:
```python
vdevice = VDevice(params)
infer_model = vdevice.create_infer_model(hef_path)
configured = infer_model.configure()
bindings = configured.create_bindings()
bindings.input().set_buffer(input_array)
configured.run_async([bindings], callback)
```

**Pre-installed models** at `/usr/share/hailo-models/` (H10-compatible):
- `yolov8m_h10.hef` — YOLOv8m object detection (640x640x3 input, 80 COCO classes)
- `yolov11m_h10.hef` — YOLOv11m object detection
- `yolov8m_pose_h10.hef` / `yolov8s_pose_h10.hef` — pose estimation
- `yolov5n_seg_h10.hef` — segmentation
- `resnet_v1_50_h10.hef` — classification

**Performance (YOLOv8m on Hailo-10H, 50-frame benchmark):**
- Inference: 26ms avg (25.7–26.9ms range)
- Camera capture: 21ms avg at 640x640
- End-to-end: 46.7ms avg → **21.4 FPS** sustained

**Hailo tutorials** installed at `/usr/lib/python3/dist-packages/hailo_tutorials/notebooks/`:
- `HRT_0_Async_Inference_Tutorial.ipynb` — async inference API
- `HRT_1_Async_Inference_Multiple_Models_Tutorial.ipynb` — multi-model
- `HRT_3_LLM_Tutorial.ipynb` — LLM on Hailo (relevant for Stage 5)
- `HRT_4_VLM_Tutorial.ipynb` — VLM on Hailo (relevant for Stage 5)
- `HRT_5_Speech2Text_Tutorial.ipynb` — speech-to-text

**Known issue:** Hailo VDevice cleanup can crash with "Resource deadlock avoided" during Python exit. This is a cosmetic issue — inference results are valid. Separating camera and Hailo lifecycles (don't nest them) reduces but doesn't eliminate it.

### Vision modules built
- `vision/capture.py` — `Camera` class wrapping picamera2 (start/capture/stop, context manager)
- `vision/detector.py` — `Detector` class wrapping Hailo inference (start/detect/stop, returns `Detection` objects)
- `vision/detect_test.py` — single-frame test with bounding box overlay
- `vision/benchmark.py` — sustained FPS measurement (50 frames)

### Still to do
- Test at floor level (actual robot use case)
- Continuous streaming mode for reactive behaviors (Stage 4)

## Stage 5 (to install)
- VLM runtime — QWEN2.5-VL-3B or Llama-3.2-3B-Instruct on Hailo HAT+ 2
- Hailo tutorials already installed (see Stage 3 notes above)

## Stage 1 Setup Log — Mechanical Restoration
1. Neato XV Signature Pro acquired, disassembled, cleaned
2. Replaced batteries with NASTIMA 7.2V 5200mAh Li-ion 2-pack
3. Dual battery config — hidden switch in dust bin, flip to ON after new batteries installed
4. Battery initialization: Menu → Support → New Battery
5. Set battery type via serial: `SetConfig BatteryType 3` (lithium mode)
6. LiDAR spinning, motors working, baseline vacuum function verified
7. Brush roll needs cleaning before first vacuum run

## Stage 2 Setup Log — Serial Communication
1. Wired SunFounder relay: Pi Pin 2 → VCC, Pin 6 → GND, Pin 11/GPIO17 → IN1
2. Spliced USB VBUS (red) wire through relay Channel 1 (COM and NO), D+/D-/GND bypass relay
3. Confirmed relay is active HIGH: `OutputDevice(17, active_high=True, initial_value=False)`
4. Verified serial port `/dev/ttyACM0` at 115200 baud after relay power cycle
5. Port re-enumerates after VBUS cycle — must wait for port to disappear then reappear
6. First `GetVersion` response confirmed: ModelID XV28, SW 3.4.24079, Serial KSH34715HH
7. Motor drive commands tested — 100mm forward/backward at 100mm/s
8. Built `neato_serial/neato.py` — reusable class with power cycle, connect, send, and common commands
9. Installed GitHub CLI (`gh`), authenticated, pushed to GitHub

## Neato Robot Reference
- Board Rev 64, Firmware SW 3.4.24079
- Serial: `/dev/ttyACM0` at 115200 baud
- Battery: 4S lithium, 14.8V nominal, 16.8V full, ~12V depleted
- Rev 64 requires USB serial (not hardware UART pins)

## Troubleshooting
- **VSCode SSH connection loop:** From a local terminal, run:
  ```bash
  ssh admin-pi@<pi-ip> "pkill -f vscode-server; rm -rf ~/.vscode-server"
  ```