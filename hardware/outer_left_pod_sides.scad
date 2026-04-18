// Neato XV Signature Pro - Outer Left Pod SIDES
// Two side walls — outer (left/exposed) taller, inner (right/vent) shorter.
// No center support posts — open for wire routing and port access.
// Sockets in base of each corner post accept bosses from outer_left_pod_base.scad.
//
// PRINT ORIENTATION: lay each wall flat on its outer face.
// Posts print horizontally — stronger layer lines, faster print.
// No supports needed.

// ============================================================
// PARAMETERS (must match outer_left_pod_base.scad)
// ============================================================

pod_width  = 72;
pod_depth  = 71;

rail_w       = 5;

outer_wall_h = 66 * 0.75;  // ~50mm — protection on exposed edge
inner_wall_h = 66 * 0.50;  // ~33mm — wire routing access

// Socket dimensions — fit over 4x4mm bosses with 0.2mm clearance
socket_size  = 4.2;
socket_depth = 6.2;

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
            cube([rail_w, rail_w, outer_wall_h]);
            // Front post
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, outer_wall_h]);
            // Mid horizontal beam
            translate([0, 0, outer_wall_h / 2 - rail_w / 2])
                cube([rail_w, pod_depth, rail_w]);
            // Top horizontal beam
            translate([0, 0, outer_wall_h - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        // Sockets in base of posts
        translate([rail_w/2, rail_w/2, 0])           socket();  // back
        translate([rail_w/2, pod_depth - rail_w/2, 0]) socket();  // front
    }
}

module inner_side() {
    difference() {
        union() {
            // Back post
            cube([rail_w, rail_w, inner_wall_h]);
            // Front post
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, inner_wall_h]);
            // Top horizontal
            translate([0, 0, inner_wall_h - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        // Sockets in base of posts
        translate([rail_w/2, rail_w/2, 0])           socket();  // back
        translate([rail_w/2, pod_depth - rail_w/2, 0]) socket();  // front
    }
}

// ============================================================
// MAIN
// Each side rotated so it lies flat on the print bed.
// ============================================================

// Outer side — rotate flat
rotate([0, -90, 0])
outer_side();

// Inner side — rotate flat, offset in Y
translate([0, pod_depth + 10, 0])
rotate([0, -90, 0])
inner_side();