// Neato XV Signature Pro - Outer Left Pod
// Mounts: Yahboom PD Power Expansion Board
// Location: outer left (exposed edge), viewed from behind robot
//
// ORIENTATION:
//   Bottom face = velcros to robot chassis (print this face on bed)
//   Posts extend upward (away from chassis)
//   Open: top, front, back
//   Protected: left and right sides with edge rails
//   Extra thick outer (left) rail for protection on exposed edge
//   Battery cable notch on inner (right) edge
//
// All measurements in mm. Print in PLA, no supports needed.

// ============================================================
// PARAMETERS
// ============================================================

// Yahboom board: 65mm long x 56mm wide (rotated 90° — long axis runs along Y/depth).
// Walls on X axis (short board dimension): pod_width = 56 + 3 + 3 + outer_rail_w + rail_w = 77mm
// Open on Y axis (long board dimension): pod_depth = 65 + 3 + 3 = 71mm
pod_width  = 77;
pod_depth  = 71;
pod_height = 66;

rail_w       = 5;
outer_rail_w = 10; // extra thick exposed outer edge

rib_w = 12; // wide enough that standoff (6mm dia) sits fully centered with 3mm to spare each side

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5 for Yahboom

cable_notch_w = 25;
cable_notch_d = 20;

// Yahboom hole pattern: 49mm x 58mm (rotated — short span on X, long span on Y)
// Standoffs placed at exactly these positions, centered in pod.
// Ribs move to match standoffs.
yahboom_hole_x_span = 49;
yahboom_hole_y_span = 58;

yahboom_x_left  = (pod_width - yahboom_hole_x_span) / 2;  // 18.5mm from left
yahboom_x_right = yahboom_x_left + yahboom_hole_x_span;   // 76.5mm from left

yahboom_y_front = (pod_depth - yahboom_hole_y_span) / 2;  // 7mm from front
yahboom_y_rear  = yahboom_y_front + yahboom_hole_y_span;  // 56mm from front
yahboom_y_mid   = (yahboom_y_front + yahboom_y_rear) / 2; // 31.5mm — center structural rib

// Ribs centered exactly on standoff Y positions
rib_positions = [yahboom_y_front, yahboom_y_mid, yahboom_y_rear];

yahboom_holes = [
    [yahboom_x_left,  yahboom_y_front],
    [yahboom_x_right, yahboom_y_front],
    [yahboom_x_left,  yahboom_y_rear ],
    [yahboom_x_right, yahboom_y_rear ],
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

    // Ribs centered on standoff Y positions, with battery cable notch on inner (right) edge
    for (y_center = rib_positions) {
        y = y_center - rib_w / 2;
        difference() {
            translate([0, y, 0])
                cube([pod_width, rib_w, rail_w]);
            // Notch cuts into the inner (right) edge for battery cable routing
            translate([pod_width - cable_notch_w, y - 0.1, -0.1])
                cube([cable_notch_w + 0.1, rib_w + 0.2, rail_w + 0.2]);
        }
    }
}

module side_rails() {
    outer_wall_h = pod_height * 0.75;  // ~50mm — protection on exposed edge
    inner_wall_h = pod_height * 0.50;  // ~33mm — wire routing access

    // Outer (left) side — extra thick, taller, no center post
    cube([outer_rail_w, rail_w, outer_wall_h]);                            // back post
    translate([0, pod_depth - rail_w, 0])
        cube([outer_rail_w, rail_w, outer_wall_h]);                        // front post
    translate([0, 0, outer_wall_h - rail_w])
        cube([outer_rail_w, pod_depth, rail_w]);                           // top horizontal

    // Inner (right) side — half height, no center post, wire routing access
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, inner_wall_h]);                              // back post
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, inner_wall_h]);                              // front post
    translate([pod_width - rail_w, 0, inner_wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);                                 // top horizontal
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

    for (h = yahboom_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}