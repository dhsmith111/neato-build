// Neato XV Signature Pro - Right Pod
// Mounts: Pi 5 + AI HAT+ 2 (pre-stacked)
// Location: right side of rear chassis (viewed from behind robot)
//
// ORIENTATION (as mounted on robot):
//   Bottom face = velcros to robot chassis (print this face on bed)
//   Pi long axis (85mm) runs horizontally across chassis
//   Pi USB/ethernet ports face inward (toward center vent) = right side of pod
//   Left and right sides protected by rails
//   Top, front, back open
//
// INNER (right) side rail:
//   No vertical posts — full port zone left open for USB/ethernet access
//   Horizontal beam at bottom and top only
//
// All measurements in mm. Print in PLA, no supports needed.

// ============================================================
// PARAMETERS
// ============================================================

// pod_width  = dimension across chassis (left-right when mounted) = Pi long axis direction
// pod_depth  = dimension outward from chassis (front-back)
// pod_height = dimension up the chassis surface (up-down when mounted)
pod_width  = 95;   // across chassis — Pi board is 85mm, 5mm clearance each side
pod_depth  = 63;   // outward from chassis
pod_height = 66;   // up the chassis surface

rail_w = 5;
rib_w  = 12; // wide enough that standoff (6mm dia) sits fully centered with 3mm to spare each side

standoff_h    = 18;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

// Pi 5 hole pattern: 58mm x 49mm
// X = across chassis (width), Y = outward from chassis (depth)
// Standoffs placed at exactly these positions. Ribs move to match.
pi_hole_x_span = 58;
pi_hole_y_span = 49;

pi_x_left  = (pod_width - pi_hole_x_span) / 2;  // 18.5mm from left rail
pi_x_right = pi_x_left + pi_hole_x_span;         // 76.5mm from left rail

pi_y_front = (pod_depth - pi_hole_y_span) / 2;   // 7mm from front
pi_y_rear  = pi_y_front + pi_hole_y_span;         // 56mm from front
pi_y_mid   = (pi_y_front + pi_y_rear) / 2;        // 31.5mm — center structural rib

// Ribs centered exactly on standoff Y positions
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
    cube([rail_w, pod_depth, rail_w]);                     // left edge
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, pod_depth, rail_w]);                 // right edge (inner/vent side)
    cube([pod_width, rail_w, rail_w]);                     // back edge
    translate([0, pod_depth - rail_w, 0])
        cube([pod_width, rail_w, rail_w]);                 // front edge

    // Ribs centered on standoff Y positions
    for (y_center = rib_positions) {
        translate([0, y_center - rib_w / 2, 0])
            cube([pod_width, rib_w, rail_w]);
    }
}

module side_rails() {
    // Outer (left) side — full posts + horizontals
    cube([rail_w, rail_w, pod_height]);                              // back post
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);                          // front post
    translate([0, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, pod_height]);                          // center post
    translate([0, 0, pod_height / 2 - rail_w / 2])
        cube([rail_w, pod_depth, rail_w]);                           // mid horizontal
    translate([0, 0, pod_height - rail_w])
        cube([rail_w, pod_depth, rail_w]);                           // top horizontal

    // Inner (right/vent) side — horizontal beams only, no vertical posts
    // Port zone left fully open for USB/ethernet access
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

    for (h = pi_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}