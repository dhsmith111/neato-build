// Neato XV Signature Pro - Right Pod SIDES
// Sockets (4.8x4.8mm x 6mm deep) in bottom of each corner/center post
// accept matching bosses from right_pod_base.scad.
//
// PRINT ORIENTATION: lay frame flat on its OUTER face (the face facing
// away from robot). Posts print horizontally — stronger layer lines,
// faster print than vertical orientation.
// No supports needed.

// ============================================================
// PARAMETERS (must match right_pod_base.scad)
// ============================================================

pod_width  = 103;
pod_depth  = 70;
pod_height = 66;

rail_w = 5;

mid_beam_z = 32;  // raised to clear ports (board at 14mm, ports span 14-29mm)

// Port-aware inner rail gap positions (measured from ruler)
port_post_nic_usb3  = 22;
port_post_usb3_usb2 = 45;
thin_post = 2;

// Socket dimensions — fit over 4x4mm bosses with 0.2mm clearance
// 4.2mm socket fits inside 5mm rail with 0.4mm wall each side
socket_size  = 4.2;
socket_depth = 6.2;  // slightly deeper than boss for easy assembly

// ============================================================
// MODULES
// ============================================================

module socket() {
    translate([-socket_size/2, -socket_size/2, 0])
        cube([socket_size, socket_size, socket_depth]);
}

module outer_side() {
    difference() {
        union() {
            // Back post
            cube([rail_w, rail_w, pod_height]);
            // Front post
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, pod_height]);
            // Center post
            translate([0, pod_depth/2 - rail_w/2, 0])
                cube([rail_w, rail_w, pod_height]);
            // Mid horizontal
            translate([0, 0, mid_beam_z])
                cube([rail_w, pod_depth, rail_w]);
            // Top horizontal
            translate([0, 0, pod_height - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        // Sockets in base of posts
        translate([rail_w/2, rail_w/2, 0])           socket();  // back
        translate([rail_w/2, pod_depth - rail_w/2, 0]) socket();  // front
        translate([rail_w/2, pod_depth/2, 0])          socket();  // center
    }
}

module inner_side() {
    difference() {
        union() {
            // Back corner post (NIC side)
            translate([pod_width - rail_w, 0, 0])
                cube([rail_w, rail_w, pod_height]);
            // Front corner post (USB side)
            translate([pod_width - rail_w, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, pod_height]);
            // Thin inter-port posts (reach up to mid beam)
            translate([pod_width - thin_post, port_post_nic_usb3 - thin_post/2, 0])
                cube([thin_post, thin_post, mid_beam_z]);
            translate([pod_width - thin_post, port_post_usb3_usb2 - thin_post/2, 0])
                cube([thin_post, thin_post, mid_beam_z]);
            // Mid horizontal beam
            translate([pod_width - rail_w, 0, mid_beam_z])
                cube([rail_w, pod_depth, rail_w]);
            // Single center post above mid beam
            translate([pod_width - thin_post, (port_post_nic_usb3 + port_post_usb3_usb2)/2 - thin_post/2, mid_beam_z + rail_w])
                cube([thin_post, thin_post, pod_height - mid_beam_z - rail_w*2]);
            // Top horizontal beam
            translate([pod_width - rail_w, 0, pod_height - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        // Sockets in base of corner posts only
        translate([pod_width - rail_w/2, rail_w/2, 0])           socket();  // back
        translate([pod_width - rail_w/2, pod_depth - rail_w/2, 0]) socket();  // front
    }
}

// ============================================================
// MAIN
// Each side rotated 90° on X axis so it lies flat on the print bed.
// Posts print horizontally — stronger layer adhesion, faster print.
// ============================================================

// Outer side — rotate 90° on Y so wide face is flat on bed
translate([pod_height, 0, 0])
rotate([0, 90, 0])
outer_side();

// Inner side — offset so both print side by side without overlap
translate([pod_height + pod_width + 10, 0, 0])
rotate([0, 90, 0])
inner_side();