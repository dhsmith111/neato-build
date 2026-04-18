// Neato XV Signature Pro - Outer Left Pod PRINT FILE
// All parts in one file — base + outer wall + inner wall — for a single print job.
// Base prints flat (ribbed face down). Sides lay flat on outer face.
// No supports needed.
//
// ASSEMBLY: press side wall posts into base bosses after printing.

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

boss_size  = 4;
boss_h     = 6;

socket_size  = 4.2;
socket_depth = 6.2;

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

boss_locations = [
    [rail_w/2,             rail_w/2              ],
    [rail_w/2,             pod_depth - rail_w/2  ],
    [pod_width - rail_w/2, rail_w/2              ],
    [pod_width - rail_w/2, pod_depth - rail_w/2  ],
];

// ============================================================
// MODULES
// ============================================================

module socket() {
    translate([-socket_size/2, -socket_size/2, 0])
        cube([socket_size, socket_size, socket_depth]);
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

module standoff(h, hole_d) {
    difference() {
        cylinder(h=h, d=standoff_od, $fn=20);
        cylinder(h=h + 0.1, d=hole_d, $fn=20);
    }
}

module outer_side() {
    difference() {
        union() {
            cube([rail_w, rail_w, outer_wall_h]);
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, outer_wall_h]);
            translate([0, 0, outer_wall_h / 2 - rail_w / 2])
                cube([rail_w, pod_depth, rail_w]);
            translate([0, 0, outer_wall_h - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        translate([rail_w/2, rail_w/2, 0])             socket();
        translate([rail_w/2, pod_depth - rail_w/2, 0]) socket();
    }
}

module inner_side() {
    difference() {
        union() {
            cube([rail_w, rail_w, inner_wall_h]);
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, inner_wall_h]);
            translate([0, 0, inner_wall_h - rail_w])
                cube([rail_w, pod_depth, rail_w]);
        }
        translate([rail_w/2, rail_w/2, 0])             socket();
        translate([rail_w/2, pod_depth - rail_w/2, 0]) socket();
    }
}

// ============================================================
// MAIN — base + two sides laid out flat on bed
// ============================================================

// Base — flat, ribbed face down
union() {
    ribbed_bottom();
    for (b = boss_locations) {
        translate([b[0] - boss_size/2, b[1] - boss_size/2, rail_w])
            cube([boss_size, boss_size, boss_h]);
    }
    for (h = yahboom_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}

// Outer side — flat, offset in Y
translate([0, pod_depth + 10, 0])
rotate([0, -90, 0])
outer_side();

// Inner side — flat, offset further in Y
translate([0, pod_depth * 2 + 20, 0])
rotate([0, -90, 0])
inner_side();