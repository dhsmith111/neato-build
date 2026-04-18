// Neato XV Signature Pro - Right Pod SIDES
// Print lying flat on side for stronger layer adhesion on posts.
// Pegs (4.8x4.8mm x 6mm) on bottom of each corner post — press into
// matching holes in right_pod_base.scad.
//
// PRINT ORIENTATION: lay frame flat on its back face (the face that
// faces away from the robot). Posts print horizontally = strong layer lines.

// ============================================================
// PARAMETERS (must match right_pod_base.scad)
// ============================================================

pod_width  = 103;
pod_depth  = 70;
pod_height = 66;

rail_w = 5;

// Mid beam height — raised to 32mm to clear ports with 9mm standoffs
// Board sits at rail_w + standoff_h = 5 + 9 = 14mm
// Ports span ~14-29mm, beam starts at 32mm — 3mm clearance above ports
mid_beam_z = 32;

// Port-aware inner rail
// Gap positions measured directly from ruler with frame in place:
//   NIC/USB3 gap center: 22mm pod Y
//   USB3/USB2 gap center: 45mm pod Y
port_post_nic_usb3  = 22;
port_post_usb3_usb2 = 45;
thin_post = 2;  // reduced from 3mm for better port clearance

// Peg dimensions (fits into 5x5mm holes in base with 0.2mm clearance)
peg_size  = 4.8;
peg_depth = 6;

// ============================================================
// MODULES
// ============================================================

module peg() {
    translate([-peg_size/2, -peg_size/2, -peg_depth])
        cube([peg_size, peg_size, peg_depth]);
}

module outer_side() {
    // Outer (left) side — full posts + horizontals
    // Back post + peg
    cube([rail_w, rail_w, pod_height]);
    translate([rail_w/2, rail_w/2, 0]) peg();

    // Front post + peg
    translate([0, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);
    translate([rail_w/2, pod_depth - rail_w/2, 0]) peg();

    // Center post + peg
    translate([0, pod_depth / 2 - rail_w / 2, 0])
        cube([rail_w, rail_w, pod_height]);
    translate([rail_w/2, pod_depth / 2, 0]) peg();

    // Mid horizontal
    translate([0, 0, mid_beam_z])
        cube([rail_w, pod_depth, rail_w]);

    // Top horizontal
    translate([0, 0, pod_height - rail_w])
        cube([rail_w, pod_depth, rail_w]);
}

module inner_side() {
    // Inner (right/vent) side — port-aware
    // Back corner post + peg (NIC side)
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, pod_height]);
    translate([pod_width - rail_w/2, rail_w/2, 0]) peg();

    // Front corner post + peg (USB side)
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);
    translate([pod_width - rail_w/2, pod_depth - rail_w/2, 0]) peg();

    // Thin inter-port posts (no pegs — too thin, sit on base surface)
    translate([pod_width - thin_post, port_post_nic_usb3 - thin_post/2, 0])
        cube([thin_post, thin_post, mid_beam_z]);               // NIC/USB3 gap post
    translate([pod_width - thin_post, port_post_usb3_usb2 - thin_post/2, 0])
        cube([thin_post, thin_post, mid_beam_z]);               // USB3/USB2 gap post

    // Mid horizontal beam — above port zone
    translate([pod_width - rail_w, 0, mid_beam_z])
        cube([rail_w, pod_depth, rail_w]);

    // Single center post above mid beam
    translate([pod_width - thin_post, (port_post_nic_usb3 + port_post_usb3_usb2) / 2 - thin_post/2, mid_beam_z + rail_w])
        cube([thin_post, thin_post, pod_height - mid_beam_z - rail_w * 2]);

    // Top horizontal beam
    translate([pod_width - rail_w, 0, pod_height - rail_w])
        cube([rail_w, pod_depth, rail_w]);
}

// ============================================================
// MAIN
// ============================================================

union() {
    outer_side();
    inner_side();
}