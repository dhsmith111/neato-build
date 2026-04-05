# Electronics Mounting

## Current State
- Pi 5 + AI HAT+ 2 stack: temporarily mounted on top of Neato LIDAR cover
- Yahboom PD board: temporarily external, velcro planned
- Relay module: temporarily mounted
- Goal: 3D printed pod on right rear curved section of Neato chassis

## 3D Printed Pod Plan

### Concept
- Curved shell extension mounting to the right rounded rear of the Neato XV chassis
- Avoids: power/USB ports, ventilation, left side (battery wire exit point)
- Extends ~2-3 inches outward, reproducing existing chassis curvature
- Electronics housed inside the pod
- Velcro attachment to chassis curved surface

### Neato XV Chassis Reference Dimensions
- Robot width: 330mm
- Robot depth: 318mm  
- Robot body height: 102mm (excluding LIDAR turret)
- Rear curve radius: ~165mm (estimated)
- Exact rear arc measurements: **TODO — measure physically with tape measure**

### Components to Mount in Pod
| Component | Footprint | Mounting | Notes |
|-----------|-----------|----------|-------|
| Pi 5 + AI HAT+ 2 (stacked) | 85 x 58mm | M2.5 standoffs | Stay together as one unit |
| Yahboom PD board | 65 x 56mm | M2.5 standoffs | Needs accessible KF301 + USB-C |
| Relay module | 63 x 41mm | 3mm holes, 52.2 x 36.6mm spacing | Smaller hole pattern than Pi stack |

### Printer
- Creality Ender 3
- Build volume: 220 x 220 x 250mm
- Material: PLA (preferred) or PETG (more heat resistant)
- Slicer: Cura
- Status: assembled, test printed, needs re-leveling and calibration after long idle

### Design Tools
- FreeCAD (free, open source) or Fusion 360 (free tier)
- Need physical measurement of Neato rear arc before modeling

### Design Notes
- Pod may need to be split into two pieces if arc spans >220mm
- Curved backing face must match Neato chassis curve exactly — trace from physical robot
- Leave access holes for: KF301 terminals, USB-C port on Yahboom, relay terminals
- PETG preferred over PLA if pod gets warm during operation

### TODO Before Designing
1. Measure right rear arc width and height on physical robot
2. Calibrate and test Ender 3
3. Install OpenSCAD (free — openscad.org) — Claude will write the design as code, no CAD skills needed
4. Claude generates OpenSCAD file from measurements
5. Render → export STL → slice in Cura → print test fit in PLA
6. Iterate based on fit