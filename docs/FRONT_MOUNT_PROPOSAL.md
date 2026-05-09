# Front-Mount Proposal

**Status:** Under evaluation. Rear-mount plan in [MOUNTING.md](MOUNTING.md) remains
the documented approach until this proposal is accepted or rejected.

## Motivation

The rear-mount approach (three pods velcroed to the rear chassis, see
[MOUNTING.md](MOUNTING.md)) reached the print-and-fit stage on the `pod-design`
branch. Once the pods were physically present alongside the robot, three issues
became apparent:

1. **Side profile too wide.** Pods extending outward from the rear sides push
   the overall footprint past the vacuum's drive profile. Likely to snag on
   furniture and door frames the bare robot clears.
2. **Dock incompatibility.** Rear-mounted pods block or shift the charging
   contact geometry. Dock would need modification or replacement to make
   contact.
3. **Top-mount remains ruled out** (unchanged from earlier analysis):
   under-furniture clearance and lidar forward arc preclude stacking on top.

Front-mount is proposed as an alternative: **velcro the electronics chassis
directly to the front face of the bumper shell**, in a vertical band that
stays clear of (a) the cliff sensors at the very bottom edge, (b) the lidar
arc at the top, and (c) the bumper sides where the upper case pinches the
shell. The electronics chassis rides *with* the bumper — when the bumper
depresses on contact, the chassis moves with it. The structure also provides
a natural mount point for the forward camera.

## Goals

The front-mount approach must:

- Preserve the dock charging interface (rear stays clean).
- Preserve bumper switch function (bumper still depresses on contact).
- Preserve cliff sensors at the front edge.
- Stay within the lidar's forward FOV (no occlusion of the forward arc).
- Keep the overall footprint within or close to the bare robot's drive profile.
- Provide a logical, short-cabled mount point for the forward-facing camera.
- Not shift center of gravity enough to cause nose-dive, wheel slip on
  thresholds, or false cliff triggers.

## Constraints Inherited from Rear-Mount Plan

These do not change with mount location. Lifted from
[MOUNTING.md](MOUNTING.md) and the existing SCAD work on `pod-design`:

| Component | Board (W×D) | Standoff Pattern | Standoff Type |
|-----------|-------------|------------------|---------------|
| Pi 5 + AI HAT+ 2 (stacked) | 85×58mm | 58×49mm | M2.5 |
| SunFounder 2-ch relay module | 63×41mm | 52.2×36.6mm | M3 |
| Yahboom PD power board | 65×56mm | 58×49mm | M2.5 |

Cable origins (these dictate routing, not mount location):

- **Battery tap** exits chassis right side (per current MOUNTING.md plan).
- **USB serial** to Neato's internal USB port — exits chassis somewhere
  central (exact location TBD on actual robot).
- **GPIO from Pi to relay** — internal to the electronics enclosure.
- **USB-C PD** from Yahboom to Pi — internal to the electronics enclosure.

Front-mount adds length to all chassis-origin cables. Battery cable run grows
the most (right-side rear → around to front).

## Constraints New to Front-Mount

### Bumper is mechanically active, optically irrelevant

Verified 2026-05-09 against the Neato Programmer's Manual sensor enums and
multiple teardowns (RECESSIM, Fictiv, SparkFun): **the XV Signature Pro
front bumper contains only mechanical tactile microswitches — no IR
rangefinders look forward through the bumper face.** An earlier draft of
this doc carried a wrong claim about "4 forward Sharp 0A51SK IR
rangefinders behind the bumper"; that claim conflated the XV-11's *side*
wall sensor with hypothetical front rangefinders. The bumper face is solid
plastic and the owner's external observation of "no IR windows" is correct
and expected.

| Sensor | Count | Where it is | Front-mount implication |
|--------|-------|-------------|-------------------------|
| Bump tactile switches (`LSIDEBIT`, `LFRONTBIT`, `RSIDEBIT`, `RFRONTBIT`) | 4 | Behind bumper, lever arms riding on inner shell face | Bumper must retain full ~2-4mm travel; structure must not bind on bumper sides |
| IR wall sensor (`WallSensorInMM`) | 1 | **Side-facing**, at the **front-right corner** | Pod placement on the bumper face must NOT extend right enough to cover or block the side window where this sensor looks outward |
| Cliff/drop sensors (`LeftDropInMM`, `RightDropInMM`) | 2 | On the **chassis underside**, flanking the brush | Not behind bumper — front-mount pods don't affect them directly, but front-cantilever sag could mistrigger them |
| Magnetic strip sensors (`LeftMagSensor`, `RightMagSensor`) | 2 | On the chassis, near the floor | Pickup is near the floor; pod bottom overhang must not shroud them |

**Implications for front-mount design:**

1. **No IR window occlusion problem** on the bumper face itself. A pod can
   sit anywhere across the front face without breaking forward sensing,
   because there is no forward optical sensing through the bumper.
2. **Right-front-corner side window is the one optic to preserve.** The
   single wall sensor on the right corner needs its sideways line-of-sight
   clear. The current layout sketch puts the relay pod near that area —
   need to verify clearance once the side window position is measured.
3. **The bumper is a pure mechanical interface.** Velcro on the bumper
   face works as planned; the only constraints are bumper side pinch
   zones and bumper-travel preservation.

### Verification on actual hardware — ✅ CONFIRMED 2026-05-09

Verified on **Board Rev 64, FW 3.4.24079** via `neato_serial/neato.py`:

```
GetAnalogSensors output (key fields):
  WallSensorInMM,51        ← one side-facing IR only, right-front corner
  LeftDropInMM,60          ← cliff sensors on underside (60mm = floor, normal)
  RightDropInMM,60
  (no forward IR rangefinder fields present)

GetDigitalSensors output:
  LSIDEBIT,0
  LFRONTBIT,0
  RSIDEBIT,0
  RFRONTBIT,0
  (4 mechanical bumper bits only — no forward proximity bits)
```

**Result:** Sensor inventory exactly matches the analysis above. The bumper
face is a pure mechanical interface. No forward IR sensors exist on this unit.
Pods can occupy the full bumper face width without occluding any forward
sensing. Only constraint is preserving line-of-sight for `WallSensorInMM`
at the right-front corner side window.

### Mount approach: velcro on the bumper face, chassis rides with the bumper

The electronics chassis attaches via velcro to the **front face of the bumper
shell itself**, not to the chassis around the bumper. Implication: when the
bumper depresses on contact, the electronics move with it. This is the
intentional design choice — alternatives (mounting above the bumper to the
upper shell, or wrapping around to the chassis sides) introduce worse
problems (lidar clearance loss, side-profile width regression, fussy
clearance geometry to avoid binding bumper travel).

Velcro placement constraints (vertical band on the bumper face only):
- **Not too low** — clear the front cliff sensor area at the chassis bottom
  edge.
- **Not too high** — stay below the lidar's forward arc.
- **Not near the sides** — bumper sides are where the upper case pinches
  the shell; pulling on the velcro there could cause the "stuck bumper"
  failure mode.
- **Don't shroud the right-front-corner side window.** The single
  side-facing IR wall sensor lives there. Velcro patches and pod outer
  shells on the bumper face must not extend right enough to block its
  sideways line-of-sight.

**Pod orientation: same topology as rear pods, rotated 90°.** Each pod's
"bottom" face (the ribbed velcro surface, in rear-pod terms) presses
against the bumper. Each pod's "top" face (open in rear-pod design)
points **forward**, away from the robot. Standoffs stick **forward** from
the bumper, parallel to the floor. Boards mount on the standoffs with
component sides facing forward — meaning the forward-facing camera board's
lens naturally points forward without any bracket re-orientation.

Mapping rear-pod terminology to front-pod orientation:

| Rear pod term | Front pod equivalent |
|---|---|
| Pod "bottom" (ribbed, velcro to chassis rear) | Pod's bumper-facing face (ribbed, velcro to bumper face) |
| Pod "top" (open) | Pod's forward face (open) |
| Pod "depth" (extends rearward from chassis) | Pod's "forward extension" (sticks out from the bumper) |
| Pod "width" (across rear chassis L-R) | Pod's horizontal span on the bumper face |
| Pod "height" (vertical, up the rear chassis) | Pod's vertical extent on the bumper face |
| Standoffs rise rearward from the chassis | Standoffs project forward from the bumper |
| Board's long axis runs L-R across chassis | Board's long axis runs horizontally across bumper face |

**Pods may be taller than the bumper face.** Velcro contact lives within
the bumper-face vertical band, but the pod shell itself can extend above
and below that band — same approach as the rear pods (pod height > velcro
patch height). This lets us size pods around the electronics (Pi+HAT stack
needs ~25mm of internal height alone) rather than cramming everything into
the ~50-60mm bumper face.

**Standoff loading is worse than rear-pod orientation.** In rear pods,
standoffs carry board weight in compression (gravity pulls board onto
standoffs). In front pods, standoffs carry board weight in cantilever
shear (gravity pulls board perpendicular to the standoff axis). At Pi+HAT
~100g on 18mm M2.5 brass standoffs the load is fine for steady state, but
bump events add inertial load. Worth confirming during prototype testing;
unlikely to require redesign.

Two new constraints from pod overhang above/below the bumper:
- **Bottom overhang must clear the floor under the bumper.** Pods ride with
  the bumper; when the bumper depresses, the bottom of the pod also drops.
  Pod bottom must stay above the floor (and above the chassis cliff-sensor
  view) through full bumper travel.
- **Top overhang must clear the upper chassis above the bumper.** Likewise,
  pod top must not hit the upper case during bumper compression, or it
  binds the bumper before the switches trigger.

### Other new constraints

- **Bump-switch activation force vs. added mass.** Bumper switches activate
  at ~170gf each. Total front-mount payload is ~250g electronics + wiring +
  TBD PLA shells. The bumper is now a "bumper plus payload" — the switches
  still need to trigger cleanly on contact, and the bumper return spring
  needs to pop the bumper back out fully against the added inertia. **This
  is the critical feasibility question for the velcro-on-bumper approach**
  and needs physical testing once a prototype exists.
- **Cliff sensor downward FOV.** Cliff sensors live on the chassis front
  edge (not on the bumper) and look down. Structure must stay clear of
  their downward cone. Front-mounted mass must not sag the chassis enough
  to mistrigger them.
- **Lidar forward FOV.** Lidar dome sits ~30-35mm above the main top
  surface, centered left-right and offset toward the rear ~3rd of the
  chassis. Front structure must stay below the dome's lower edge.
- **Weight distribution / CG.** Cantilevering electronics + shells forward
  of the drive wheels shifts CG forward. Component weights (researched
  2026-05-09, no plastic chassis on Pi+HAT, heatsink only — no active
  cooler):

  | Item | Weight (g) | Confidence |
  |------|-----------:|------------|
  | Pi 5 (8GB), bare board | 46 | High (RPi spec) |
  | AI HAT+ 2 board (Hailo-10H, 8GB) | 50 | Medium (Waveshare listing) |
  | AI HAT+ 2 heatsink | ~15 | Low (inferred from dimensions) |
  | Pi Camera Module 3 Wide | ~4 | Low (published 14-15g is shipping wt) |
  | Pi Camera 500mm cable | ~5 | Medium |
  | Yahboom PD board | ~60 | Medium (inferred from 52Pi sibling product) |
  | SunFounder 2ch relay | 31 | High (SunFounder spec) |
  | M2.5 standoffs + screws (×4 each pod, 2 pods) | ~6 each | Low |
  | M3 standoffs + screws (×4) | ~8 | Medium |
  | **Electronics + standoffs subtotal** | **~225** | |
  | Wires, heat shrink, jumpers, zip ties | ~25-30 | Low (envelope) |
  | PLA pod shells | TBD — weigh first printed front pods | unknown |

  Mitigated somewhat by the fact that **the battery sits in the rear**
  (two packs in the rear quarters, ~320g each), so stock CG is rear-biased
  and there's some headroom. Still: risk of nose-dive on stops, wheel slip
  on thresholds, cliff sensor false triggers if front sags.

  Front-pod shell weight will be measured directly from the first printed
  front pods. The rear pods are a different shell shape and not worth
  weighing for this purpose.
- **Under-furniture clearance.** Front structure adds to overall length and
  potentially height. Must not exceed the bare robot's clearance envelope.

## Specs gathered from online research (2026-05-09)

These are sourced from published retailer specs, the xv11hacking wiki, the
RECESSIM XV-11 archive, and forum measurements. Numbers marked **[MEASURE]**
were not findable online and need calipers on the actual robot.

### Chassis and drive

| Item | Value | Source |
|------|-------|--------|
| Width (flat-front edge) | ~330mm (13.0") | retailer specs |
| Depth (front-to-back) | ~318mm (12.5") | retailer specs |
| Height (top of dome) | ~102mm (4.0") | retailer specs |
| Weight (with stock NiMH) | ~3.9kg (8.6 lb) | retailer specs |
| Footprint | D-shape, flat front, semicircular rear | universal |
| Wheelbase (track width) | ~248mm | xv11hacking / RECESSIM |
| Wheel diameter | ~76mm (3 in) | forum consensus |
| Wheel position front-to-back | Slightly behind chassis center, biased toward front of round rear half (under LDS axis) | inferred from teardown photos |
| Distance wheel axis → flat front edge | **[MEASURE]** (~150-170mm estimated) | needs calipers |

### Lidar (LDS) module

| Item | Value | Source |
|------|-------|--------|
| LDS module weight | ~195g | xv11hacking |
| Dome external diameter | ~95-100mm | inferred from belt + photos |
| Dome height above main top surface | ~30-35mm | inferred (102mm total - chassis body) |
| Position | Centered L-R, offset toward rear ~3rd of chassis | photos |
| Authoritative CAD | Available — SLDPRT/STL/IGS at xv11hacking | http://xv11hacking.rohbotics.com/mainSpace/LIDAR%20Mechanical%20Info.html |

### Battery

- Stock: NiMH 7.2V, ~320g per pack, **two packs**, one in each rear quarter
  (left + right of dust bin). Rear-biased CG by design.
- Pack outer dim: ~67.8 × 32.3 × 59.2mm.
- Front bumper area is uncluttered by battery hardware.

### Front bumper geometry — mostly unknown

| Item | Status |
|------|--------|
| Bumper face width | ~330mm (full flat front) [INFER] |
| Bumper face height | ~50-60mm [INFER from photos] — **[MEASURE]** for design |
| Bumper free-state stand-off from chassis | ~5-10mm air gap [INFER] — **[MEASURE]** |
| Bumper travel (depression before switches click) | ~2-4mm estimated [INFER] — **[MEASURE]** |
| Bumper attachment | Held by upper case half, NO external screws on the bumper itself; loose front screws cause "stuck bumper" failure mode |
| Bump switch type | Tactile micro-switches, ~170gf activation, board ~11.8 × 21.4mm |

### No published full chassis or bumper CAD

Hobbyists have modeled wheels, axles, dust bin parts, and the LDS module. **No
one has published a chassis or bumper STL/STEP.** A Neato D5 bumper scan exists
on Printables but the D5 is a different chassis — not transferable. We will
have to model the bumper area from caliper measurements ourselves.

### Useful references

- **xv11hacking wiki**: http://xv11hacking.rohbotics.com/ — LIDAR CAD, PCB Rev 64 pinouts, programmer's manual mirror.
- **RECESSIM XV-11 archive**: https://wiki.recessim.com/view/Neato_XV-11 — best single page of internal measurements (wheelbase, LDS weight, sensor connector pinouts, bump switch map).
- **iFixit Neato XV**: https://www.ifixit.com/Device/Neato_XV — disassembly guides per model.
- **RobotShop teardown video**: https://www.youtube.com/watch?v=G8G72NAppKY
- **Neato Programmer's Manual**: https://help.neatorobotics.com/wp-content/uploads/2020/07/XV-ProgrammersManual-3_1.pdf

## Measurements (caliper on actual robot, Pi-side)

PLA shell weights will be measured directly from the first printed front
pods. Rear-pod weighing skipped — shells are different shape and not
directly informative.

### A. Bumper face geometry

| # | Item | Value | Notes |
|---|------|-------|-------|
| A1 | Bumper face width | ~330mm (estimated) | No caliper long enough; visual confirmation against estimate |
| A2 | Bumper face height | **61mm** (measured) | Pod outer shell may extend above/below this |
| A3 | Bumper-side pinch zone inset | unknown — using estimate ~20mm | Sides are smooth; no visible seam to measure from |

### B. Bumper kinematics — pending

- B1. Bumper free-state stand-off from chassis face.
- B2. Bumper travel distance before switches click.

### C. Sensor positions — pending

- C1. Right-front-corner side window for `WallSensorInMM`.
- C2. Cliff sensor positions (left and right) on chassis underside.
- C3. Magnetic strip sensor positions.

### D. Vertical clearances above and below bumper face

| # | Item | Value | Notes |
|---|------|-------|-------|
| D1 | Floor clearance below bumper face | ~5mm at rest, with ~5mm additional margin during depression (assumed) | Not directly measured — assumption pending physical check. Pod bottom overhang must respect both numbers. |
| D2 | Upper-chassis clearance above bumper face | pending | At rest and at full depression. |

### E. Drive geometry — pending

- E1. Drive-wheel axis distance from the flat front edge.

### Layout: separate pod chassis along the front bumper

Same modularity philosophy as the rear-pod plan: **separate pod chassis per
component**, each individually velcro'd to the bumper face along a
horizontal band. Likely three pods (Pi+HAT, Yahboom, relay) plus a camera
mount, but exact count and layout to be determined.

Reasons to keep the pod-level modularity:
- Reprint one pod when its design changes, not the whole front.
- Iteration on camera mount geometry is independent of the heavier pods.
- Failure of one velcro attachment doesn't cascade.
- Reuses the existing per-pod SCAD module structure from `pod-design`.

### Design decisions to make

- **Pod count on the front:** three (Pi+HAT, Yahboom, relay) plus a
  separate camera pod/bracket, or fewer with the camera integrated into
  one of the existing pods?
- **Layout order across the front face:** Pi+HAT centered with Yahboom +
  relay flanking (CG balanced left-right), or order driven by cable
  routing? Camera position is its own decision — likely centered or
  high-on-Pi-pod for forward FOV.
- **Velcro patch layout per pod.** Where on the bumper face does each
  pod's velcro footprint go to (a) avoid IR rangefinder windows, (b)
  stay clear of the bumper sides, (c) provide enough surface area to
  hold the pod's mass through bump events. Driven by sensor window
  positions, which still need measuring.
- **Pod outer shell shape.** Rear pods on `pod-design` are shaped to wrap
  around the curved rear chassis. Front pods sit against a flat bumper
  face — outer shell is simpler. The "pod-side velcro face" replaces
  the "rear-chassis-side velcro face" of the rear pods, but it's the
  same idea, just on a flat instead of curved surface.

## What Carries Over from `pod-design`

- Standoff geometry per board (M2.5 58×49mm, M3 33.5×45mm — the hard-won part).
- Rib-to-standoff alignment math.
- "Open scaffold, not a box" structural philosophy.
- Print-flat-on-the-ribbed-face print orientation.
- Three-pod modularity (probable — see open question above).
- Combined-print SCAD pattern (`all_pods.scad` style for printing efficiency).

## What Changes from `pod-design`

- **Outer shell shape.** Rear pods are shaped to match the curved rear
  chassis with a center vent split. Front bumper is flat — outer shell
  becomes simpler geometry.
- **Mounting interface.** Velcro to a flat bumper-area face vs. velcro to
  the curved rear.
- **Pod arrangement.** No center-vent split on the front, so pods sit
  linearly across the flat face. Order is a layout decision, not forced
  by chassis geometry.
- **Cable routing.** Battery cable run grows substantially (rear-right
  origin → forward).
- **New mount considerations:** bumper preservation, cliff sensor
  preservation, lidar FOV, forward-cantilever CG impact. None of these
  applied to rear-mount.

## Decision Path

1. ~~Online research pass: pull published specs, find CAD if it exists.~~
   **Done 2026-05-09.** Findings folded into this doc above. Notable result:
   the front bumper is the robot's entire forward perception array (4 IR
   rangefinders + 4 bump switches + 2 cliff sensors + magnetic strip pickups)
   — front-mount is not a blank-wall problem. No published chassis/bumper
   CAD exists; we'll model the bumper area from our own caliper measurements.
2. **Caliper measurements on the robot** (next — Pi-side / physical-access
   task; this chat can't do it). Targets listed under "Measurements still
   needed" above. Most critical: sensor window positions, bumper travel,
   bumper attachment / chassis features above the bumper.
3. iPhone lidar scan only if bumper has curvature calipers can't capture.
4. **Sensor-occlusion analysis** with measured numbers. Can a front structure
   actually clear all forward IR rangefinder lines-of-sight, all cliff
   sensor downward cones, the bumper's full travel, and stay below the
   lidar dome? This is the dominant feasibility question now.
5. **Weight / CG analysis** with measured numbers — go/no-go on front-mount.
   Battery is rear, which gives some headroom; quantify.
6. If go: layout decision → SCAD work, reusing modules from `pod-design`.
7. If no-go: revisit alternatives. Possibilities: structure *above* the
   bumper (clear of forward sensors), low-profile top behind the lidar,
   integrated rather than bolted on, hybrid front-and-rear split.
