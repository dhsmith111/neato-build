# Pod Design — 3D Printed Electronics Mounts

## Status
SCAD files live in `hardware/` folder of this repo.
Currently iterating on design — not yet printed.

## Three Pod Files

**Dimension key:**
- `pod_width` = across chassis (left-right when mounted) — must fit board width + 2x rail
- `pod_depth` = outward from chassis — must fit board depth + 2x rail
- `pod_height` = up the chassis surface — all pods 66mm
- Rail width: 5mm standard, 10mm on outer left exposed edge
- Board must fit inside rails with ~3mm clearance each side

| File | Component | Board (W×D) | pod_width | pod_depth | Inner space (W×D) |
|------|-----------|-------------|-----------|-----------|-------------------|
| `right_pod.scad` | Pi 5 + AI HAT+ 2 | 85×58mm | 101mm | 70mm | 91×60mm |
| `inner_left_pod.scad` | Relay module | 63×41mm | 75mm | 55mm | 65×45mm |
| `outer_left_pod.scad` | Yahboom PD board | 65×56mm | 86mm | 68mm | 71×58mm |

Note: outer_left inner width = pod_width - outer_rail_w(10) - rail_w(5) = 71mm

## Design Principles

**Orientation:** Bottom face velcros to robot chassis. Print this face flat on the bed.
No supports needed.

**Structure:** Open scaffold — not a box. Each pod has:
- Ribbed bottom face (3 ribs, 12mm wide, aligned to standoff Y positions)
- 4 corner posts + 1 center post per side (6 vertical posts per side wall)
- Mid horizontal rail + top horizontal rail on each side
- Top, front, back: fully open

**Standoffs:** Rise from the ribbed bottom face upward. Board mounts on standoffs
with screws through component mounting holes.
- Height: 18mm
- OD: 6mm
- Ribs are positioned so each standoff lands fully centered on a rib (3mm clearance each side)

## Per-Pod Details

### Right Pod — Pi 5 + AI HAT+ 2
- Hole pattern: 58x49mm, M2.5 (standoff_hole = 2.7mm)
- Pi 5 board: 85x58mm — long axis (85mm) runs horizontally across chassis
- USB/ethernet ports face inward (toward center vent) = right side of pod
- Outer (left) side: full posts + horizontals
- Inner (right/vent) side: corner posts only, no center post — port zone unobstructed

### Inner Left Pod — Relay Module
- Hole pattern: 52.2x36.6mm, M3 (standoff_hole = 3.2mm)
- Width: 70mm (relay is smaller than Pi/Yahboom)
- Adjacent to center vent — inner/protected position
- Both side walls: symmetric

### Outer Left Pod — Yahboom PD Board
- Hole pattern: 58x49mm, M2.5 (standoff_hole = 2.7mm)
- Outer (left) rail: 10mm wide (reinforced — exposed edge of robot)
- Inner (right) rail: 5mm standard
- Battery cable notch: 25x20mm cutout on inner edge of base ribs, for 18AWG wires

## Key Design Decisions (rationale)

- **Three separate pods** (not one unit): smaller prints, independent removal,
  easier iteration if one needs changes
- **Ribbed bottom, not solid**: reduces warping on FDM flat surfaces; enough
  velcro contact area; some flex to conform to curved chassis
- **Center support post on side rails**: 63mm depth is borderline for PLA bridging;
  center post eliminates sag on mid and top horizontal rails
- **Ribs follow standoffs**: standoff positions are fixed by component hole patterns;
  ribs are placed to match, not the other way around
- **Yahboom outer-left**: KF301 screw terminals accessible from exposed outer edge;
  battery cables from right side of chassis reach naturally
- **Relay inner-left**: USB serial cable from chassis center-left is a short run

## SCAD File History (ender3-setup repo, for reference)

Files originated in `ender3-setup` repo and were moved here. Key commits there:
- `0d98ef3` — initial baseline
- `92bfee9` — rib_w widened to 12mm, standoff/rib alignment correct
- `f98b06a` — revert of bad USB gap change (second chat made incorrect edit)
- `b61f88a` — center support posts added to left pod side rails

## Printing Plan

1. Open each `.scad` in OpenSCAD, F6 to render, File → Export → STL
2. Slice in Cura (PLA, no supports, ribbed face on bed)
3. Print `right_pod.scad` first — simplest, good fit test
4. Place Pi 5 on standoffs to verify hole alignment before printing left pods
5. Velcro test fit on chassis rear
6. Print remaining two pods