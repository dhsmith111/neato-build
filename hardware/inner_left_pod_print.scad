// Neato XV Signature Pro - Inner Left Pod PRINT FILE
// All parts in one file — base + both side walls — for a single print job.
// Base prints flat (ribbed face down). Sides lay flat on outer face.
// No supports needed.
//
// ASSEMBLY: press side wall posts into base bosses after printing.

// ============================================================
// PARAMETERS
// ============================================================

pod_width  = 55;
pod_depth  = 57;
pod_height = 66;

rail_w = 5;
rib_w  = 12;
wall_h = pod_height / 2;  // ~33mm half height

standoff_h    = 9;
standoff_od   = 6;
standoff_hole = 3.2; // M3 for relay

boss_size  = 4;
boss_h     = 6;

socket_size  = 4.2;
socket_depth = 6.2;

relay_hole_x_span = 33.5;
relay_hole_y_span = 45.0;

relay_x_left  = (pod_width - relay_hole_x_span) / 2;
relay_x_right = relay_x_left + relay_hole_x_span;

relay_y_front = (pod_depth - relay_hole_y_span) / 2;
relay_y_rear  = relay_y_front + relay_hole_y_span;
relay_y_mid   = (relay_y_front + relay_y_rear) / 2;

rib_positions = [relay_y_front, relay_y_mid, relay_y_rear];

relay_holes = [
    [relay_x_left,  relay_y_front],
    [relay_x_right, relay_y_front],
    [relay_x_left,  relay_y_rear ],
    [relay_x_right, relay_y_rear ],
];

boss_locations = [
    [rail_w/2,             rail_w/2             ],
    [rail_w/2,             pod_depth - rail_w/2 ],
    [pod_width - rail_w/2, rail_w/2             ],
    [pod_width - rail_w/2, pod_depth - rail_w/2 ],
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

module side() {
    difference() {
        union() {
            cube([rail_w, rail_w, wall_h]);
            translate([0, pod_depth - rail_w, 0])
                cube([rail_w, rail_w, wall_h]);
            translate([0, pod_depth / 2 - rail_w / 2, 0])
                cube([rail_w, rail_w, wall_h]);
            translate([0, 0, wall_h - rail_w])
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
    for (h = relay_holes) {
        translate([h[0], h[1], rail_w])
            standoff(standoff_h, standoff_hole);
    }
}

// Left side — flat, offset in X
translate([pod_width + 10, 0, 0])
rotate([0, -90, 0])
side();

// Right side — flat, offset further in X
translate([pod_width + 10, pod_depth + 10, 0])
rotate([0, -90, 0])
side();