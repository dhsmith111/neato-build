// Neato XV Signature Pro - Outer Left Pod
// Mounts: Yahboom PD Power Expansion Board
// Location: outer left (exposed edge), viewed from behind robot
// One-piece print — flat on bed, no supports needed.
//
// ORIENTATION (as mounted on robot):
//   Bottom face = velcros to robot chassis
//   Walls on short board axis (56mm), open on long axis (65mm)
//   Outer (left/exposed) wall: 75% height, mid + top beams
//   Inner (right/vent) wall: 50% height, top beam only

// ============================================================
// PARAMETERS
// ============================================================

pod_width  = 72;
pod_depth  = 71;
pod_height = 66;

rail_w = 5;
rib_w  = 12;

outer_wall_h = pod_height * 0.75;  // ~50mm — protection on exposed edge
inner_wall_h = pod_height * 0.50;  // ~33mm — wire routing access

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

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

// ============================================================
// MODULES
// ============================================================

module gusset() {
    rotate([90, 0, 0])
        translate([0, 0, -5])
            linear_extrude(height=5)
                polygon([[0,0], [8,0], [0,8]]);
}

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

module outer_wall() {
    cube([rail_w, rail_w, outer_wall_h]);
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, outer_wall_h]);
    translate([0, 0, outer_wall_h / 2 - rail_w / 2])
        cube([rail_w, pod_depth, rail_w]);
    translate([0, 0, outer_wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);
    // Gussets — back, front, no center post on this wall
    translate([rail_w, 0, rail_w])
        gusset();
    translate([rail_w, pod_depth, rail_w])
        mirror([0, 1, 0]) gusset();
}

module inner_wall() {
    translate([pod_width - rail_w, 0, 0]) {
        cube([rail_w, rail_w, inner_wall_h]);
        translate([0, pod_depth - rail_w, 0])
            cube([rail_w, rail_w, inner_wall_h]);
        translate([0, 0, inner_wall_h - rail_w])
            cube([rail_w, pod_depth, rail_w]);
        // Gussets — back and front, extending toward outer wall (-X)
        translate([rail_w, 0, rail_w])
            mirror([1, 0, 0]) gusset();
        translate([rail_w, pod_depth, rail_w])
            mirror([1, 0, 0]) mirror([0, 1, 0]) gusset();
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
    outer_wall();
    inner_wall();

    for (h = yahboom_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}