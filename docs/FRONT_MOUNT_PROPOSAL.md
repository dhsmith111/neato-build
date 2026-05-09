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

### The bumper is a sensor array, not just a bump panel

The single most important finding from the chassis research: **all of the
robot's forward environment sensing lives in the front bumper / front edge.
There is no rear or side cliff sensing.** Any front-mount structure has to
preserve every one of these:

| Sensor | Count | What it does | Front-mount implication |
|--------|-------|--------------|-------------------------|
| Bump switches | 4 (L-side, top-L, top-R, R-side) | Detect physical contact | Bumper must retain full ~2-4mm travel; structure must not bind on bumper sides |
| Sharp 0A51SK IR rangefinders | 4 | Look **forward** through the bumper face | Their forward line-of-sight must stay clear |
| Cliff/drop sensors (optical, downward) | 2 | Look **down** from the front edge | Structure must not block their downward view |
| Magnetic strip sensors | up to 4 | Detect floor boundary markers | Structure must not block their pickup near the floor |

In short: the bumper face is full of forward-looking optics, not just a
mechanical bump panel. Any "pod stuck on the front" risks occluding multiple
sensors at once. This materially changes the design problem from what was
assumed at the start of this proposal — the front is the robot's eyes, not a
blank wall.

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
- **Avoid the IR rangefinder windows** — 4 Sharp 0A51SK sensors look forward
  through the bumper face. Velcro patches and the chassis itself must not
  cover them or block their forward line-of-sight.

### Other new constraints

- **Bump-switch activation force vs. added mass.** Bumper switches activate
  at ~170gf each. With ~250-350g of electronics velcro'd to the bumper
  face, the bumper is now a "bumper plus payload" — the switches still need
  to trigger cleanly on contact, and the bumper return spring needs to pop
  the bumper back out fully against the added inertia. **This is the
  critical feasibility question for the velcro-on-bumper approach** and
  needs physical testing once a prototype exists.
- **Cliff sensor downward FOV.** Cliff sensors live on the chassis front
  edge (not on the bumper) and look down. Structure must stay clear of
  their downward cone. Front-mounted mass must not sag the chassis enough
  to mistrigger them.
- **Lidar forward FOV.** Lidar dome sits ~30-35mm above the main top
  surface, centered left-right and offset toward the rear ~3rd of the
  chassis. Front structure must stay below the dome's lower edge.
- **Weight distribution / CG.** Cantilevering ~250-350g forward of the
  drive wheels (Pi+HAT ~100g, Yahboom ~40g, relay ~20g, camera ~10-20g,
  PLA shells ~80-150g) shifts CG forward. Mitigated somewhat by the fact
  that **the battery sits in the rear** (two packs in the rear quarters,
  ~320g each), so stock CG is rear-biased and there's some headroom.
  Still: risk of nose-dive on stops, wheel slip on thresholds, cliff sensor
  false triggers if front sags.
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

## Measurements still needed (caliper on actual robot)

These drive the front-mount geometry and are not reliably available online:

1. Bumper face exact width and height (the molded shell only).
2. Bumper free-state stand-off from chassis face.
3. Bumper travel distance before switches click.
4. Front cliff-sensor window positions on the chassis underside.
5. Front IR rangefinder window positions on the bumper face (Sharp 0A51SK x4).
6. Front magnetic strip sensor positions.
7. Drive-wheel axis distance from the flat front edge.
8. Any mounting boss / threaded inserts on the upper shell near the front
   (preferred over gluing/strapping to the bumper, since the bumper moves).

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
