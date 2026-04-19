// Neato XV Signature Pro - ALL PODS
// All three pods arranged for a single print job on 220x220mm bed.
// Print flat, no supports needed.
//
// Layout (top view):
//   Right pod:       X=0-103,  Y=0-70
//   Outer left pod:  X=0-72,   Y=80-151
//   Inner left pod:  X=108-163, Y=0-57

use <right_pod.scad>
use <inner_left_pod.scad>
use <outer_left_pod.scad>

// Right pod — bottom-left
translate([0, 0, 0])
    right_pod();

// Outer left pod — above right pod
translate([0, 80, 0])
    outer_left_pod();

// Inner left pod — right of right pod
translate([108, 0, 0])
    inner_left_pod();