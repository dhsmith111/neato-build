# Power System

## Battery
- Neato battery is 4S lithium: 14.8V nominal, 16.8V fully charged, ~12V depleted
- `VBattV` in GetCharger reports actual battery voltage (not 24V — that's charger voltage `VExtV`)
- Must set `SetConfig BatteryType 3` via serial for lithium mode (LIION_4CELL)
- Menu → Support → New Battery for initial battery initialization

## Power Supply: Yahboom PD Expansion Board
- Input: 6-24V (battery range 12-17V fits perfectly)
- Output: 5V/5A with Raspberry Pi 5 PD protocol — no EEPROM config needed
- Three input connectors on board: KF301 screw terminals, XH2.54, DC5.5x2.5
- Plan: use KF301 screw terminals for battery tap wires
- Includes dual Type-C PD adapter to connect directly to Pi 5
- Board: 65x56mm, matches Pi 5 footprint, has on/off switch
- Stacks above or below Pi 5

## Why Not LM2596
- The Seloky LM2596 buck converters (already owned) are rated 3A max, recommended under 2A
- Pi 5 + AI HAT+ 2 can draw 4-5A peak during inference — brownout risk

## Power Draw from Battery
- At 5V/5A output with ~90% efficiency, draws ~1.9A from the Neato battery
- Neato motors draw more — this is a reasonable additional load

## Wiring Plan
1. Tap Neato battery leads (18 AWG wire)
2. Inline 5A blade fuse for short-circuit protection
3. Wire to Yahboom board KF301 screw terminals
4. Yahboom USB-C PD → Pi 5 USB-C power input