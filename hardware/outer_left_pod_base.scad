// Neato XV Signature Pro - Outer Left Pod BASE
// Print flat (ribbed face down), no supports needed.
// Has 4x4x6mm raised bosses at all 4 post locations.
// Bosses fit into matching sockets in outer_left_pod_sides.scad.
//
// PRINT ORIENTATION: ribbed bottom face flat on bed, standoffs point up.

// ============================================================
// PARAMETERS (must match outer_left_pod_sides.scad)
// ============================================================

pod_width  = 77;
pod_depth  = 71;

rail_w       = 5;
outer_rail_w = 10;
rib_w        = 12;

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

cable_notch_w = 25;
cable_notch_d = 20;

boss_size = 4;
boss_h    = 6;

yahboom_hole_x_span = 49;
yahboom_hole_y_span = 58;

yahboom_x_left  = (pod_width - yahboom_hole_x_span) / 2;
yahboom_x_right = yahboom_x_left + yahboom_hole_x_span;

yahboom_y_front = (pod_depth - yahboom_hole_y_span) / 2;
yahboom_y_rear  = yahboom_y_front + yahboom_hole_y_span;
yahboom_y_mid   = (yahboom_y_front + yahboom_y_rear) / 2;

rib_positions = [yahboom_y_front, yahboom_y_mid, yahboom_y_rear];

yahboom_holes = [
    [yahboom_x_left,  yahboom_y_front],
    [yahboom_x_right, yahboom_y_front],
    [yahboom_x_left,  yahboom_y_rear ],
    [yahboom_x_right, yahboom_y_rear ],
];

// Boss locations — center of each post footprint
// Outer (left) side: back, front
// Inner (right) side: back, front
boss_locations = [
    [outer_rail_w/2,          rail_w/2              ],  // outer back
    [outer_rail_w/2,          pod_depth - rail_w/2  ],  // outer front
    [pod_width - rail_w/2,    rail_w/2              ],  // inner back
    [pod_width - rail_w/2,    pod_depth - rail_w/2  ],  // inner front
];

// ============================================================
// MODULES
// ============================================================

module ribbed_bottom() {
    // Outer (left) edge — extra thick
    cube([outer_rail_w, pod_depth, rail_w]);
    // Inner (right) edge
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, pod_depth, rail_w]);
    // Back edge
    cube([pod_width, rail_w, rail_w]);
    // Front edge
    translate([0, pod_depth - rail_w, 0])
        cube([pod_width, rail_w, rail_w]);

    // Ribs with battery cable notch on inner (right) edge
    for (y_center = rib_positions) {
        y = y_center - rib_w / 2;
        difference() {
            translate([0, y, 0])
                cube([pod_width, rib_w, rail_w]);
            translate([pod_width - cable_notch_w, y - 0.1, -0.1])
                cube([cable_notch_w + 0.1, rib_w + 0.2, rail_w + 0.2]);
        }
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

    for (b = boss_locations) {
        translate([b[0] - boss_size/2, b[1] - boss_size/2, rail_w])
            cube([boss_size, boss_size, boss_h]);
    }

    for (h = yahboom_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}