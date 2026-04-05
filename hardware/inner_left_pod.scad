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

// Relay board: 63mm wide x 41mm deep. 3mm clearance each side.
// Inner space = pod_width - rail_w*2 = 75 - 10 = 65mm (1mm each side of 63mm board — tight but ok)
// Inner depth = pod_depth - rail_w*2 = 53 - 10 = 43mm (1mm each side of 41mm board — tight but ok)
// Using 55 and 63 for comfortable clearance
pod_width  = 75;
pod_depth  = 55;
pod_height = 66;

rail_w = 5;
rib_w  = 12; // wide enough that standoff (6mm dia) sits fully centered with 3mm to spare each side

standoff_h    = 18;
standoff_od   = 6;
standoff_hole = 3.2; // M3 for relay

// Relay hole pattern: 52.2mm x 36.6mm
// Standoffs placed at exactly these positions, centered in pod.
// Ribs move to match standoffs.
relay_hole_x_span = 52.2;
relay_hole_y_span = 36.6;

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
    // Left side
    cube([rail_w, rail_w, pod_height]);                              // back post
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);                          // front post
    translate([0, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, pod_height]);                          // center post
    translate([0, 0, pod_height / 2 - rail_w / 2])
        cube([rail_w, pod_depth, rail_w]);                           // mid horizontal
    translate([0, 0, pod_height - rail_w])
        cube([rail_w, pod_depth, rail_w]);                           // top horizontal

    // Right side (mirror)
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, pod_height]);                          // back post
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);                          // front post
    translate([pod_width - rail_w, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, pod_height]);                          // center post
    translate([pod_width - rail_w, 0, pod_height / 2 - rail_w / 2])
        cube([rail_w, pod_depth, rail_w]);                           // mid horizontal
    translate([pod_width - rail_w, 0, pod_height - rail_w])
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