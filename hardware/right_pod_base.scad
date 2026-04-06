// Neato XV Signature Pro - Right Pod BASE ONLY
// Print this first to verify standoff alignment and velcro fit.
// If base fits, print right_pod_sides.scad separately.
//
// ORIENTATION: print this face down (ribbed bottom on bed), no supports needed.

// ============================================================
// PARAMETERS (must match right_pod_sides.scad)
// ============================================================

pod_width  = 101;
pod_depth  = 70;

rail_w = 5;
rib_w  = 12;

standoff_h    = 18;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

pi_hole_x_span = 58;
pi_hole_y_span = 49;

pi_x_left  = 6;
pi_x_right = pi_x_left + pi_hole_x_span;          // 64mm

pi_y_front = (pod_depth - pi_hole_y_span) / 2;   // 10.5mm — centered on Y
pi_y_rear  = pi_y_front + pi_hole_y_span;         // 59.5mm
pi_y_mid   = (pi_y_front + pi_y_rear) / 2;        // 35mm

rib_positions = [pi_y_front, pi_y_mid, pi_y_rear];

pi_holes = [
    [pi_x_left,  pi_y_front],
    [pi_x_right, pi_y_front],
    [pi_x_left,  pi_y_rear ],
    [pi_x_right, pi_y_rear ],
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

    for (h = pi_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}