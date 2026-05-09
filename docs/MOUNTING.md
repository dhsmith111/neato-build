# Electronics Mounting

## Current State — Front-Mount Prototype

Electronics mounted to the **front bumper face** of the Neato XV via velcro.
This is a temp prototype using a mix of OEM and existing rear-pod hardware,
sufficient to evaluate front-mounting in real-world operation before
committing to a final design. See [FRONT_MOUNT_PROPOSAL.md](FRONT_MOUNT_PROPOSAL.md)
for design rationale and the bumper-face envelope analysis.

| Component | Mounting |
|-----------|----------|
| Pi 5 + AI HAT+ 2 (stacked) | OEM CanaKit Turbine Case (65×95×46mm), velcro to bumper face |
| Yahboom PD board | Inside the existing `outer_left_pod.scad` print (rear-mount design), velcro to bumper face |
| SunFounder 2-ch relay | Inside the existing `inner_left_pod.scad` print (rear-mount design), velcro to bumper face |
| Camera Module 3 Wide | TBD — small velcro mount or bracket above the Pi case |

The two rear-mount pods are flat-bottomed rectangular boxes (not curved —
they were always designed to mount to flat surfaces). They aren't sized
optimally for the front bumper face dimensions, but they sit flat against
it. The prototype's job is to answer "does front-mounting work at all"
before investing in front-specific pod geometry.

## Bumper-Face Layout

```
[Yahboom pod]   [Pi 5 in OEM case]   [Relay pod]
  outer left          center             inner right
  (~86mm)             (95mm)             (~75mm)
```

Total pod width: ~256mm of usable ~290mm bumper face = ~34mm inter-pod gap budget.

## Cable Routing (front-mount prototype)

- **Battery power:** chassis right rear → around right side → across front of
  bumper → Yahboom KF301 on the outer-left pod. Long route compared to the
  original rear-mount plan; needs adequate 18AWG length.
- **USB-C PD:** Yahboom → Pi 5 USB-C input. Short hop between adjacent pods.
- **USB serial:** Pi 5 USB-A → SunFounder relay (channel 1 switched VBUS) →
  back into chassis to Neato's internal USB port. The relay-to-Neato run
  goes from front-right pod back into the chassis.
- **GPIO relay signal:** Pi GPIO17 (pin 11) → relay IN1. Short hop between
  adjacent pods.
- **Camera CSI:** Pi 5 CSI port → Camera Module 3 Wide. Routing depends on
  camera position.

## Sensor Considerations (front bumper)

Verified on the physical robot (Board Rev 64, FW 3.4.24079) via
`GetAnalogSensors` / `GetDigitalSensors`:

- **Bump switches** (4 mechanical) behind the bumper — pods ride with the
  bumper, switches must still trigger and return.
- **No forward IR sensors through the bumper face** — bumper is solid
  plastic, mechanical only. Pods do not occlude any forward optical sensing.
- **IR wall sensor** (single, side-facing at right-front corner) — pods do
  not extend to the side, so no occlusion.
- **Cliff and magnetic strip sensors** — on chassis, not affected by
  bumper-mounted pods.

## Prototype Observations

- **Charging through dock: works** (verified 2026-05-09). The robot mates
  with the dock and charges normally despite the front-mount payload.
  This was the single biggest functional risk for the rear-mount approach
  the front-mount was chosen to avoid — confirmed solved.
- **Pods sit flat against the bumper face** — outer shells are
  rectangular boxes with flat ribbed bottoms; they mount cleanly with
  full velcro contact area.
- **Battery cabling routed over-the-top** (over the lidar cover) rather
  than around the right side of the chassis. Cleaner than the original
  side-routing plan.
- **Camera is mounted on a separate small bracket** in front of the Pi
  case, lens facing forward. Stands forward of all three pods — the
  camera bracket is now the frontmost point of the robot.

## What's Next

Open prototype tests:
- Whether the bumper still depresses and returns cleanly with payload.
- Whether the robot drives, navigates, and avoids triggering cliff
  sensors with forward CG shift.
- Whether velcro adhesion holds long-term under bump events.

Once evaluated, decisions on whether to:
- Print front-mount-specific pods (designs in [FRONT_MOUNT_PROPOSAL.md](FRONT_MOUNT_PROPOSAL.md)
  with restored 66mm walls, mid beam at Z=32, top/bottom protective walls).
- Move to a different mounting approach if front-mount problems are
  unrecoverable.

## Pod SCAD Files

The rear-mount-design SCAD files in [cad/](../cad/) are the source of truth
for the printed pods now in front-mount prototype service. See
[POD_DESIGN.md](POD_DESIGN.md) for per-pod design details.

Known issues in the printed pods (from the consolidation commit on
`pod-design` branch) — partial USB port blocking on the right pod due to
mid beam at Z=22 instead of Z=32, and reduced wall heights (75% / 50%
instead of 66mm full). These don't affect the prototype because the right
pod isn't in service (Pi is in its OEM case instead). Yahboom and relay
pods don't have port-clearance issues with their cable connections.

## Printer

- Creality Ender 3, calibrated (20mm test cube verified accurate)
- Build volume: 220×220×250mm
- Material: PLA, Slicer: Cura
