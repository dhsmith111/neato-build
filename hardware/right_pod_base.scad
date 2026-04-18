// Neato XV Signature Pro - Right Pod BASE
// Print flat (ribbed face down), no supports needed.
// Has 5x5x6mm raised bosses at all 5 post locations.
// Bosses fit into matching sockets in right_pod_sides.scad.
//
// PRINT ORIENTATION: ribbed bottom face flat on bed, standoffs point up.

// ============================================================
// PARAMETERS (must match right_pod_sides.scad)
// ============================================================

pod_width  = 103;
pod_depth  = 70;

rail_w = 5;
rib_w  = 12;

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

// Boss dimensions — raised square pegs on base, fit into sockets in side frame
// 4mm square fits inside 5mm rail with 0.5mm wall each side
boss_size  = 4;   // 4x4mm square
boss_h     = 6;   // 6mm tall

pi_hole_x_span = 58;
pi_hole_y_span = 49;

pi_x_left  = 10;
pi_x_right = pi_x_left + pi_hole_x_span;  // 68mm

pi_y_front = (pod_depth - pi_hole_y_span) / 2;  // 10.5mm
pi_y_rear  = pi_y_front + pi_hole_y_span;        // 59.5mm
pi_y_mid   = (pi_y_front + pi_y_rear) / 2;       // 35mm

rib_positions = [pi_y_front, pi_y_mid, pi_y_rear];

pi_holes = [
    [pi_x_left,  pi_y_front],
    [pi_x_right, pi_y_front],
    [pi_x_left,  pi_y_rear ],
    [pi_x_right, pi_y_rear ],
];

// Boss locations — center of each post footprint
// Outer (left) side: back, front, center
// Inner (right) side: back, front only (no center — port access)
boss_locations = [
    [rail_w/2,              rail_w/2              ],  // outer back
    [rail_w/2,              pod_depth - rail_w/2  ],  // outer front
    [rail_w/2,              pod_depth/2            ],  // outer center
    [pod_width - rail_w/2,  rail_w/2              ],  // inner back
    [pod_width - rail_w/2,  pod_depth - rail_w/2  ],  // inner front
];

// ============================================================
// MODULES
// ============================================================

module ribbed_bottom() {
    // Perimeter rails
    cube([rail_w, pod_depth, rail_w]);
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, pod_depth, rail_w]);
    cube([pod_width, rail_w, rail_w]);
    translate([0, pod_depth - rail_w, 0])
        cube([pod_width, rail_w, rail_w]);

    // Ribs centered on standoff Y positions
    for (y_center = rib_positions) {
        translate([0, y_center - rib_w / 2, 0])
            cube([pod_width, rib_w, rail_w]);
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

    // Raised bosses for side frame alignment
    for (b = boss_locations) {
        translate([b[0] - boss_size/2, b[1] - boss_size/2, rail_w])
            cube([boss_size, boss_size, boss_h]);
    }

    // Standoffs
    for (h = pi_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}