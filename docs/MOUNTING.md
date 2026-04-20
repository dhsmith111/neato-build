# Electronics Mounting

## Current State

All three pods printed. Boards mounted on standoffs inside pods. Pods not yet
attached to the robot chassis — pending connectivity and functionality checks
before final velcro install.

| Component | Pod | Status |
|-----------|-----|--------|
| Pi 5 + AI HAT+ 2 (stacked) | Right pod | Mounted on standoffs |
| SunFounder 2-ch relay module | Inner left pod | Mounted on standoffs |
| Yahboom PD power board | Outer left pod | Mounted on standoffs |

## Pod Layout (viewed from behind robot)

```
[Outer Left Pod]  [Inner Left Pod]  [Center Vent]  [Right Pod]
  Yahboom            Relay                            Pi 5 + HAT
```

## Pod Specifications (as printed)

| Pod | Component | Dimensions (WxD) | Standoff Holes |
|-----|-----------|------------------|----------------|
| Right pod | Pi 5 + AI HAT+ 2 | 103x70mm | M2.5, 58x49mm pattern |
| Inner left pod | SunFounder 2-ch relay | 55x57mm | M3, 33.5x45mm pattern |
| Outer left pod | Yahboom PD board | 72x71mm | M2.5, 49x58mm pattern |

All pods: standoff height 9mm, rail_w 5mm, pod_height 66mm.
Outer walls 75% height (~50mm), inner walls 50% height (~33mm).
SCAD source files in `hardware/`.

## Chassis Measurements

- Each rear side width (vent edge to curve end): 95mm
- Chassis body height at rear: 66mm
- Center vent width: 137mm

## Cable Routing (planned)

- Battery tap (14.8V) → 18AWG red/black out chassis rear vent → Yahboom KF301 (outer left pod)
- Yahboom USB-C PD out → Pi 5 USB-C power input
- USB serial: Neato USB port → relay Channel 1 (VBUS switched) → Pi 5 USB
- GPIO relay signal: Pi Pin 11 (GPIO17) → relay IN1

## Notes

- Pods are v1 functional prototypes — adequate for development, not final form factor
- All three pods printed in one job on Ender 3 (220x220mm bed), PLA, 0.28mm layers

## TODO

- Velcro pods to rear chassis once connectivity/functionality checks pass