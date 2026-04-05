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
//   Corner posts (back + front) full height
//   Two thin 3mm posts in gaps between port housings (USB/USB and USB/NIC gaps)
//     split into lower (0-20mm) and upper (42-66mm) segments to clear port zone
//   Mid horizontal beam supported by all 4 posts (2 corner + 2 thin)
//   Center vertical post above mid beam supports top horizontal
//
// Port gap Y positions (measured from board USB-far edge, converted to pod Y):
//   Board far Y edge = pi_y_rear + (58 - pi_hole_y_span)/2 = ~64mm
//   USB/USB gap center: board edge - 23mm = ~41mm in pod Y
//   USB/NIC gap center: board edge - 36mm = ~28mm in pod Y
//
// All measurements in mm. Print in PLA, no supports needed.

// ============================================================
// PARAMETERS
// ============================================================

// pod_width  = dimension across chassis (left-right when mounted) = Pi long axis direction
// pod_depth  = dimension outward from chassis (front-back)
// pod_height = dimension up the chassis surface (up-down when mounted)
// Pi board: 85mm wide x 58mm deep. 3mm clearance each side.
// Inner space = pod_width - rail_w*2 = 101 - 10 = 91mm (3mm each side of 85mm board)
// Inner depth = pod_depth - rail_w*2 = 70 - 10 = 60mm (1mm each side of 58mm board — tight but ok)
pod_width  = 101;  // across chassis
pod_depth  = 70;   // outward from chassis
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

pi_x_left  = (pod_width - pi_hole_x_span) / 2;  // 21.5mm from left rail
pi_x_right = pi_x_left + pi_hole_x_span;         // 79.5mm from left rail

pi_y_front = (pod_depth - pi_hole_y_span) / 2;   // 10.5mm from front (NIC side)
pi_y_rear  = pi_y_front + pi_hole_y_span;         // 59.5mm from front (USB side)
pi_y_mid   = (pi_y_front + pi_y_rear) / 2;        // 35mm — center structural rib

// Pi board edges (for port position calculations)
// Board depth = 58mm, hole_y_span = 49mm, so board overhangs holes by (58-49)/2 = 4.5mm each side
pi_board_y_near = pi_y_front - 4.5;  // NIC/near edge of board in pod Y
pi_board_y_far  = pi_y_rear  + 4.5;  // USB/far edge of board in pod Y (~64mm)

// Thin inter-port posts on inner (right) side rail
// Measured from NIC-side board edge: NIC/USB3 gap at 19mm, USB3/USB2 gap at 37mm
// Board NIC edge in pod Y = pi_board_y_near = pi_y_front - 4.5 = ~6mm
port_post_nic_usb3 = pi_board_y_near + 19;  // ~25mm in pod Y
port_post_usb3_usb2 = pi_board_y_near + 37; // ~43mm in pod Y

// Port zone Z heights: board at 23mm, ports ~15mm tall → zone is 23-38mm
// Lower post segment: 0 to 20mm (below board)
// Upper post segment: 42mm to pod_height (above ports)
port_z_lower = 20;
port_z_upper = 42;

thin_post = 3; // width of inter-port posts

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

    // Inner (right/vent) side — port-aware structure
    // Corner posts: full height
    translate([pod_width - rail_w, 0, 0])
        cube([rail_w, rail_w, pod_height]);                          // back corner post (NIC side)
    translate([pod_width - rail_w, pod_depth - rail_w, 0])
        cube([rail_w, rail_w, pod_height]);                          // front corner post (USB side)

    // Thin inter-port posts: full height up to mid horizontal beam
    // Placed in gaps between NIC/USB3 and USB3/USB2 port housings
    translate([pod_width - thin_post, port_post_nic_usb3 - thin_post/2, 0])
        cube([thin_post, thin_post, pod_height / 2 - rail_w / 2]);   // NIC/USB3 gap post
    translate([pod_width - thin_post, port_post_usb3_usb2 - thin_post/2, 0])
        cube([thin_post, thin_post, pod_height / 2 - rail_w / 2]);   // USB3/USB2 gap post

    // Mid horizontal beam at pod mid-height — supported by corner posts
    translate([pod_width - rail_w, 0, pod_height / 2 - rail_w / 2])
        cube([rail_w, pod_depth, rail_w]);                           // mid horizontal

    // Single center post above mid beam — supports top horizontal
    translate([pod_width - thin_post, (port_post_nic_usb3 + port_post_usb3_usb2) / 2 - thin_post/2, pod_height / 2 + rail_w / 2])
        cube([thin_post, thin_post, pod_height / 2 - rail_w]);       // center upper post

    // Top horizontal beam
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