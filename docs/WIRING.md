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

## Serial Connection
- Port: `/dev/ttyACM0`
- Baud: 115200
- Board Rev 64 requires USB serial (not hardware UART pins)
- Neato re-enumerates USB after VBUS power cycle — must wait for port to disappear then reappear before opening serial

## Camera Connections
- CAM0: Pi Camera Module 3 Wide (primary, forward-facing)
- CAM1: Pi Camera Module 3 Wide NoIR (secondary, low-light) — future
- Cables: 500mm, 22-pin Pi 5 compatible