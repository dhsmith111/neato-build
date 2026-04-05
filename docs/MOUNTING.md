# Electronics Mounting

## Current State (Temporary — Functional for Development)

All components are temporarily mounted and fully operational. Sufficient to
continue software and AI development without the permanent pod install.

| Component | Current Mounting |
|-----------|-----------------|
| Pi 5 + AI HAT+ 2 (stacked) | Velcro on top of Neato LIDAR cover |
| Yahboom PD board | External, velcro |
| Relay module | External, velcro |

## Planned Permanent Install — Three 3D Printed Pods

Three independent open-frame pods velcroed to the rear chassis of the Neato XV.

### Pod Layout (viewed from behind robot)

```
[Outer Left Pod]  [Inner Left Pod]  [Center Vent]  [Right Pod]
  Yahboom            Relay                            Pi 5 + HAT
```

| Pod | Component | Width | Standoff Holes |
|-----|-----------|-------|----------------|
| Right pod | Pi 5 + AI HAT+ 2 (pre-stacked) | 95mm | M2.5, 58x49mm pattern |
| Inner left pod | SunFounder 2-ch relay module | 70mm | M3, 52.2x36.6mm pattern |
| Outer left pod | Yahboom PD power board | 95mm | M2.5, 58x49mm pattern |

### Chassis Measurements (taken from physical robot)

- Each rear side width (vent edge to curve end): 95mm (3.75 in)
- Chassis body height at rear: 66mm (2.6 in)
- Pod depth (extension outward from chassis): 63mm
- Center vent width: 137mm (5.375 in)
- Total rear check: 137 + 95 + 95 = 327mm ≈ 330mm chassis width ✓

### Pod Design (planned)

- Bottom face: ribbed, velcros to chassis — print flat on bed, no supports
- Side walls: open scaffold — corner posts + center post + horizontal rails
- Top, front, back: open for airflow and cable access
- Standoff height: 18mm
- Outer left pod: reinforced outer rail, battery cable notch on inner edge

### Cable Routing (permanent install)

- Battery power: exits chassis right side → runs across rear → Yahboom KF301 (outer left)
- USB-C PD: Yahboom → Pi 5 (outer left to right)
- USB serial: chassis center-left → relay (inner left, short run)
- GPIO relay signal: relay → Pi (inner left to right)

### Printer

- Creality Ender 3, calibrated (20mm test cube verified accurate)
- Build volume: 220x220x250mm — all three pods fit individually
- Material: PLA, Slicer: Cura

### TODO

- Design and iterate SCAD files (tracked separately)
- Test fit prints before final install