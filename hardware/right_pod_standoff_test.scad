// Neato XV Signature Pro - Right Pod STANDOFF ALIGNMENT TEST
// Minimal print — just standoffs connected by thin rails.
// Verifies Pi 5 hole pattern alignment only.
// Print in ~20-30 min at 0.2mm, 60mm/s.
// No supports needed.

// ============================================================
// PARAMETERS (must match right_pod.scad)
// ============================================================

pod_width  = 101;
pod_depth  = 70;

rail_w = 5;
base_h = 3;  // thin base — just enough to hold standoffs together

standoff_h    = 18;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

pi_hole_x_span = 58;
pi_hole_y_span = 49;

pi_x_left  = 10;
pi_x_right = pi_x_left + pi_hole_x_span;          // 68mm

pi_y_front = (pod_depth - pi_hole_y_span) / 2;   // 10.5mm — centered on Y
pi_y_rear  = pi_y_front + pi_hole_y_span;         // 59.5mm

pi_holes = [
    [pi_x_left,  pi_y_front],
    [pi_x_right, pi_y_front],
    [pi_x_left,  pi_y_rear ],
    [pi_x_right, pi_y_rear ],
];

// ============================================================
// MODULES
// ============================================================

module standoff(h, hole_d) {
    difference() {
        cylinder(h=h, d=standoff_od, $fn=20);
        cylinder(h=h + 0.1, d=hole_d, $fn=20);
    }
}

// ============================================================
// MAIN — thin cross rails + standoffs only
// ============================================================

union() {
    // Thin rail connecting left standoffs (front to rear)
    translate([pi_x_left - standoff_od/2, pi_y_front, 0])
        cube([standoff_od, pi_hole_y_span, base_h]);

    // Thin rail connecting right standoffs (front to rear)
    translate([pi_x_right - standoff_od/2, pi_y_front, 0])
        cube([standoff_od, pi_hole_y_span, base_h]);

    // Thin rail connecting front standoffs (left to right)
    translate([pi_x_left, pi_y_front - standoff_od/2, 0])
        cube([pi_hole_x_span, standoff_od, base_h]);

    // Thin rail connecting rear standoffs (left to right)
    translate([pi_x_left, pi_y_rear - standoff_od/2, 0])
        cube([pi_hole_x_span, standoff_od, base_h]);

    // Four standoffs
    for (h = pi_holes) {
        translate([h[0], h[1], base_h])
            standoff(standoff_h, standoff_hole);
    }
}