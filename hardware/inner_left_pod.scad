// Neato XV Signature Pro - Inner Left Pod
// Mounts: SunFounder 2-channel Relay Module
// Location: inner left (adjacent to center vent), viewed from behind robot
// One-piece print — flat on bed, no supports needed.
//
// ORIENTATION (as mounted on robot):
//   Bottom face = velcros to robot chassis
//   Walls on long board axis (50.5mm), open on short axis (38.5mm)
//   Both walls half height (~33mm)

// ============================================================
// PARAMETERS
// ============================================================

pod_width  = 55;
pod_depth  = 57;
pod_height = 66;

rail_w = 5;
rib_w  = 12;

wall_h = pod_height * 0.50;  // ~33mm half height

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 3.2; // M3 for relay

relay_hole_x_span = 33.5;
relay_hole_y_span = 45.0;

relay_x_left  = (pod_width - relay_hole_x_span) / 2;
relay_x_right = relay_x_left + relay_hole_x_span;

relay_y_front = (pod_depth - relay_hole_y_span) / 2;
relay_y_rear  = relay_y_front + relay_hole_y_span;
relay_y_mid   = (relay_y_front + relay_y_rear) / 2;

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
    cube([rail_w, pod_depth, rail_w]);
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, pod_depth, rail_w]);
    cube([pod_width, rail_w, rail_w]);
    translate([0, pod_depth - rail_w, 0])
        cube([pod_width, rail_w, rail_w]);
    for (y_center = rib_positions) {
        translate([0, y_center - rib_w / 2, 0])
            cube([pod_width, rib_w, rail_w]);
    }
}

module side_wall(x_pos) {
    translate([x_pos, 0, 0]) {
        cube([rail_w, rail_w, wall_h]);
        translate([0, pod_depth - rail_w, 0])
            cube([rail_w, rail_w, wall_h]);
        translate([0, pod_depth / 2 - rail_w / 2, 0])
            cube([rail_w, rail_w, wall_h]);
        translate([0, 0, wall_h - rail_w])
            cube([rail_w, pod_depth, rail_w]);
    }
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
    side_wall(0);
    side_wall(pod_width - rail_w);

    for (h = relay_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}