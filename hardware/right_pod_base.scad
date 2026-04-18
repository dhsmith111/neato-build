// Neato XV Signature Pro - Right Pod BASE
// Print flat (ribbed face down), no supports needed.
// Has 5x5mm peg holes at all 6 post locations for right_pod_sides.scad.
//
// ORIENTATION: bottom face on print bed, standoffs point up.

// ============================================================
// PARAMETERS (must match right_pod_sides.scad)
// ============================================================

pod_width  = 103;  // across chassis (1mm added each side vs v1)
pod_depth  = 70;   // outward from chassis
pod_height = 66;   // up the chassis surface (not used in base)

rail_w = 5;
rib_w  = 12;

standoff_h    = 9;   // halved from 18mm
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

// Peg hole dimensions (5x5mm hole accepts 4.8x4.8mm peg with 0.2mm clearance)
peg_hole = 5;
peg_depth = 6;  // how deep the peg goes into the base

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

// Post locations — peg holes go here (matching side frame post positions)
// Outer (left) side: back, front, center posts
// Inner (right) side: back, front posts only (no center — port access)
post_locations_outer = [
    [0,              0              ],  // back-left corner
    [0,              pod_depth - rail_w],  // front-left corner
    [0,              pod_depth / 2 - rail_w / 2],  // center-left
];
post_locations_inner = [
    [pod_width - rail_w, 0              ],  // back-right corner
    [pod_width - rail_w, pod_depth - rail_w],  // front-right corner
];

// ============================================================
// MODULES
// ============================================================

module ribbed_bottom() {
    difference() {
        union() {
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

        // Peg holes — outer (left) side posts
        for (p = post_locations_outer) {
            translate([p[0] + rail_w/2 - peg_hole/2, p[1] + rail_w/2 - peg_hole/2, rail_w - peg_depth])
                cube([peg_hole, peg_hole, peg_depth + 0.1]);
        }

        // Peg holes — inner (right) side posts
        for (p = post_locations_inner) {
            translate([p[0] + rail_w/2 - peg_hole/2, p[1] + rail_w/2 - peg_hole/2, rail_w - peg_depth])
                cube([peg_hole, peg_hole, peg_depth + 0.1]);
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

    for (h = pi_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}