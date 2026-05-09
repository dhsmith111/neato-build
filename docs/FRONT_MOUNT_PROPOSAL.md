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

Front-mount is proposed as an alternative: extend the front bumper area outward
to house the same electronics, with the new structure protecting (not
interfering with) the bumper sensors, and providing a natural mount point for
the forward camera.

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

- **Bumper preservation.** Front bumper is a moving part with switches behind
  it. New structure must attach to the chassis *around* the bumper, leaving
  full bumper travel unobstructed. (To confirm: bumper travel distance, bumper
  face dimensions, attachment points on the chassis around the bumper.)
- **Cliff sensors.** Cliff sensors look down from the front edge. Structure
  must not block their downward view, and front-mounted mass must not cause
  the front to sag enough to mistrigger them.
- **Lidar forward FOV.** Lidar dome sits on top of the robot. Tall front
  structure can occlude the forward sweep. Need maximum allowed front
  structure height vs. lidar dome height.
- **Weight distribution / CG.** Cantilevering ~250-350g forward of the drive
  wheels (estimated: Pi+HAT ~100g, Yahboom ~40g, relay ~20g, camera ~10-20g,
  PLA shells ~80-150g) shifts CG forward. Risks: nose-dive on stops, wheel
  slip on thresholds, cliff sensor false triggers, bumper depression load.
- **Under-furniture clearance.** Front structure adds to overall length and
  potentially height. Must not exceed the bare robot's clearance envelope in
  any dimension that matters for under-couch / under-bed operation.

## Open Questions (resolve before SCAD work)

### Measurements needed (from physical robot or published specs)

1. Overall chassis diameter and footprint outline (XV is D-shaped).
2. Front bumper face: width, height, depth from chassis face.
3. Bumper travel distance (how far it depresses on contact).
4. Drive wheel position relative to chassis center (for moment-arm math).
5. Battery position and mass (for current CG baseline).
6. Lidar dome height above top surface.
7. Cliff sensor positions on the front edge.
8. Front-bumper attachment points or mounting features available on the
   chassis around the bumper.

### Research targets

- Neato XV Signature Pro published spec sheet.
- Service manual (Board Rev 64).
- Hobbyist CAD models on GrabCAD / Thingiverse / xv11hacking.
- Bumper assembly teardown / repair guides (iFixit etc.).

### Design decisions to make

- **Pod count on the front:** three independent pods (preserves modularity),
  two pods (middle ground), or one merged front shell (fewer parts, stiffer)?
- **Layout order across front face:** Pi+HAT centered with Yahboom + relay
  flanking (CG balanced), or order driven by cable-routing realities?
- **Camera mount:** integrated into one of the pods, or a separate fourth
  small pod / bracket?
- **Mounting interface:** velcro to flat bumper-area chassis face (consistent
  with rear-mount approach), or mechanical fasteners into existing chassis
  features?

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

1. Online research pass: pull published specs, find CAD if it exists.
2. Caliper measurements on the robot for the few numbers that matter to ±1mm
   (bumper geometry, wheel position, front edge to wheel distance).
3. iPhone lidar scan only if bumper has curvature calipers can't capture.
4. Weight / CG analysis with measured numbers — go/no-go on front-mount.
5. If go: layout decision → SCAD work, reusing modules from `pod-design`.
6. If no-go: revisit alternatives (low-profile top, integrated rather than
   bolted on, hybrid front-and-rear split).
