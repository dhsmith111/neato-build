# Wiring Reference

## Relay Wiring (confirmed working)

SunFounder 2-channel relay module (SRD-05VDC-SL-C), active HIGH behavior.

### Pi GPIO → Relay Module
| Pi Pin | Wire Color | Relay Pin | Purpose |
|--------|-----------|-----------|---------|
| Pin 2 (5V) | Red | VCC | Relay power |
| Pin 6 (GND) | Black | GND | Ground |
| Pin 11 (GPIO17) | Yellow | IN1 | Channel 1 control |

### USB Cable → Relay Channel 1
- USB VBUS (red) wire spliced through Channel 1 lower screw terminals (COM and NO)
- D+, D-, GND wires bypass relay — spliced straight through
- `relay.on()` = VBUS connected (Neato powered via USB)
- `relay.off()` = VBUS cut (Neato USB power off)

### GPIO Code
```python
from gpiozero import OutputDevice
relay = OutputDevice(17, active_high=True, initial_value=False)
```

## Battery Power Tap → Yahboom PD Board → Pi 5

### Physical Access
- Neato XV Signature Pro must be partially disassembled to access tap point
- Remove bottom cover (7 screws, Phillips #0)
- Battery harnesses route under mainboard and emerge at upper right of mainboard
- Two-wire connector (red + black) at upper right mainboard corner = combined 14.8V output

### Series Wiring Inside Robot
- Left battery black (negative) → mainboard GND
- Left battery brown (positive) → bridges to right battery connector (series link)
- Right battery red (positive) → mainboard +V
- Combined voltage at mainboard connector: ~14.8V nominal

### Tap Method
- Cut existing red and black wires before the mainboard connector
- Wago 221-413 (3-port lever connector) at each wire:
  - Port 1: battery side of cut wire
  - Port 2: mainboard side of cut wire
  - Port 3: new 18AWG tap wire routed out to Yahboom
- Wagos remain internal to chassis
- New 18AWG red (with inline 5A fuse) and black wires routed out through chassis

### Yahboom KF301 Screw Terminal Connection
- Red 18AWG (via inline 5A fuse) → KF301 + terminal
- Black 18AWG → KF301 - terminal
- Yahboom USB-C PD output → Pi 5 USB-C power input
- No separate ground needed — black wire is ground

## Serial Connection
- Port: `/dev/ttyACM0`
- Baud: 115200
- Board Rev 64 requires USB serial (not hardware UART pins)
- Neato re-enumerates USB after VBUS power cycle — must wait for port to disappear then reappear before opening serial

## Camera Connections
- CAM0: Pi Camera Module 3 Wide (primary, forward-facing)
- CAM1: Pi Camera Module 3 Wide NoIR (secondary, low-light) — future
- Cables: 500mm, 22-pin Pi 5 compatible