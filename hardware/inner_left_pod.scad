// Neato XV Signature Pro - Inner Left Pod
// Mounts: SunFounder 2-channel Relay Module
// Location: inner left (adjacent to center vent), viewed from behind robot
//
// ORIENTATION:
//   Bottom face = velcros to robot chassis (print this face on bed)
//   Posts extend upward (away from chassis)
//   Open: top, front, back
//   Protected: left and right sides with edge rails + center support post
//
// All measurements in mm. Print in PLA, no supports needed.

// ============================================================
// PARAMETERS
// ============================================================

// Relay board: 50.5mm long x 38.5mm wide (walls on long axis).
// Walls on X axis (long board dimension): pod_width = 50.5 + 3 + 3 + 5 + 5 = 67mm
// Open on Y axis (short board dimension): pod_depth = 38.5 + 3 + 3 = 45mm
pod_width  = 67;
pod_depth  = 45;
pod_height = 66;

rail_w = 5;
rib_w  = 12; // wide enough that standoff (6mm dia) sits fully centered with 3mm to spare each side

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 3.2; // M3 for relay

// Relay hole pattern: 45.0mm x 33.5mm (standard 2-ch relay module form factor)
// Standoffs placed at exactly these positions, centered in pod.
// Ribs move to match standoffs.
relay_hole_x_span = 45.0;  // long span — runs along X between walls
relay_hole_y_span = 33.5;  // short span — runs along Y open direction

relay_x_left  = (pod_width - relay_hole_x_span) / 2;  // 8.9mm from left
relay_x_right = relay_x_left + relay_hole_x_span;     // 61.1mm from left

relay_y_front = (pod_depth - relay_hole_y_span) / 2;  // 13.2mm from front
relay_y_rear  = relay_y_front + relay_hole_y_span;    // 49.8mm from front
relay_y_mid   = (relay_y_front + relay_y_rear) / 2;   // 31.5mm — center structural rib

// Ribs centered exactly on standoff Y positions
rib_positions = [relay_y_front, relay_y_mid, relay_y_rear];

relay_holes = [
    [relay_x_left,  relay_y_front],
    [relay_x_right, relay_y_front],
    [relay_x_left,  relay_y_rear ],
    [relay_x_right, relay_y_rear ],
];

// ============================================================
// MODULES
// ============================================================

module ribbed_bottom() {
    // Perimeter rails
    cube([rail_w, pod_depth, rail_w]);                     // left
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, pod_depth, rail_w]);                 // right
    cube([pod_width, rail_w, rail_w]);                     // back
    translate([0, pod_depth - rail_w, 0])
        cube([pod_width, rail_w, rail_w]);                 // front

    // Ribs centered on standoff Y positions
    for (y_center = rib_positions) {
        translate([0, y_center - rib_w / 2, 0])
            cube([pod_width, rib_w, rail_w]);
    }
}

module side_rails() {
    wall_h = pod_height / 2;  // half height — posts + single horizontal beam only

    // Left side
    cube([rail_w, rail_w, wall_h]);                                  // back post
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, wall_h]);                              // front post
    translate([0, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, wall_h]);                              // center post
    translate([0, 0, wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);                           // top horizontal

    // Right side (mirror)
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, wall_h]);                              // back post
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, wall_h]);                              // front post
    translate([pod_width - rail_w, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, wall_h]);                              // center post
    translate([pod_width - rail_w, 0, wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);                           // top horizontal
}

module standoff(h, hole_d) {
    difference() {
        cylinder(h=h, d=standoff_od, $fn=20);
        cylinder(h=h + 0.1, d=hole_d, $fn=20);
    }
}

// ============================================================
// MAIN
// ============================================================

union() {
    ribbed_bottom();
    side_rails();

    for (h = relay_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}