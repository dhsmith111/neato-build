// Neato XV Signature Pro - Right Pod
// Mounts: Pi 5 + AI HAT+ 2 (pre-stacked)
// Location: right side of rear chassis (viewed from behind robot)
// One-piece print — flat on bed, no supports needed.
//
// ORIENTATION (as mounted on robot):
//   Bottom face = velcros to robot chassis
//   Pi long axis runs across chassis (X)
//   USB/ethernet ports face inward (toward center vent) = high X side
//   Non-USB edge faces outer (left) wall = low X side
//
// Outer (left) wall: 75% height, mid + top horizontal beams
// Inner (right/USB) wall: 50% height, stops at mid beam — port access

// ============================================================
// PARAMETERS
// ============================================================

pod_width  = 103;
pod_depth  = 70;
pod_height = 66;

rail_w = 5;
rib_w  = 12;

outer_wall_h = pod_height * 0.75;  // ~50mm
inner_wall_h = pod_height * 0.50;  // ~33mm — stops at mid beam

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 2.7; // M2.5

pi_hole_x_span = 58;
pi_hole_y_span = 49;

pi_x_left  = 11;
pi_x_right = pi_x_left + pi_hole_x_span;  // 69mm

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

// Port-aware inner rail gap positions (measured from ruler)
port_post_nic_usb3  = 28;
port_post_usb3_usb2 = 45;
thin_post = 2;

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

module outer_wall() {
    // Back post
    cube([rail_w, rail_w, outer_wall_h]);
    // Front post
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, outer_wall_h]);
    // Center post
    translate([0, pod_depth/2 - rail_w/2, 0])
        cube([rail_w, rail_w, outer_wall_h]);
    // Mid horizontal
    translate([0, 0, outer_wall_h/2 - rail_w/2])
        cube([rail_w, pod_depth, rail_w]);
    // Top horizontal
    translate([0, 0, outer_wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);
    // Gussets at base of each post (inside corner, on top of base)
    translate([rail_w, rail_w, rail_w])
        rotate([90, 0, 90]) gusset();  // back post, toward front
    translate([rail_w, pod_depth - rail_w, rail_w])
        rotate([90, 0, 90]) rotate([0, 0, -90]) gusset();  // front post, toward back
    translate([rail_w, pod_depth/2 + rail_w/2, rail_w])
        rotate([90, 0, 90]) rotate([0, 0, -90]) gusset();  // center post, one side
    translate([rail_w, pod_depth/2 - rail_w/2, rail_w])
        rotate([90, 0, 90]) gusset();  // center post, other side
}

module inner_wall() {
    // Back corner post (NIC side)
    cube([rail_w, rail_w, inner_wall_h]);
    // Front corner post (USB side)
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, inner_wall_h]);
    // Thin inter-port posts up to mid beam
    translate([pod_width - thin_post, port_post_nic_usb3 - thin_post/2, 0])
        cube([thin_post, thin_post, inner_wall_h - rail_w]);
    translate([pod_width - thin_post, port_post_usb3_usb2 - thin_post/2, 0])
        cube([thin_post, thin_post, inner_wall_h - rail_w]);
    // Back corner post
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, inner_wall_h]);
    // Mid/top horizontal beam (single beam at top of inner wall)
    translate([pod_width - rail_w, 0, inner_wall_h - rail_w])
        cube([rail_w, pod_depth, rail_w]);
}

// Triangular gusset — 8mm along base, 8mm up post, 3mm thick
// Placed at inside corner of post where it meets the base
module gusset() {
    linear_extrude(height=3)
        polygon([[0,0], [8,0], [0,8]]);
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

    for (h = pi_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}