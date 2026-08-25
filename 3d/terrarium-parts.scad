/* ============================================================================
 * TERRARIUM — 3D PRINTABLE PARTS
 * EEE4103 capstone · OpenSCAD (free: openscad.org)
 *
 * HOW TO USE
 *   1. Open this file in OpenSCAD
 *   2. Change PART below to whichever piece you want
 *   3. F5 to preview, F6 to render, then File > Export > Export as STL
 *   4. Slice the STL in Cura/PrusaSlicer and print
 *
 * MEASURE FIRST. Every dimension marked <<MEASURE>> is a guess based on the
 * usual size of that module. Put calipers (or a ruler) on YOUR part, change
 * the number, and it refits automatically. That is the whole point of doing
 * this in code instead of drawing it.
 *
 * PRINT SETTINGS (all parts)
 *   material  PETG preferred — PLA softens in a warm humid box and creeps
 *   layer     0.2 mm
 *   walls     3 perimeters
 *   infill    25%
 *   supports  only for "fan_duct"; everything else is designed to avoid them
 * ========================================================================== */

PART = "box";   // box | lid | sensor_shield | soil_collar | fan_duct | grommet

/* ---- global ------------------------------------------------------------- */
wall      = 2.4;    // shell thickness
clr       = 0.4;    // printing clearance for parts that mate
$fn       = 48;

/* ---- your boards, in mm  <<MEASURE>> ------------------------------------ */
esp_l     = 52;  esp_w  = 28;   // ESP32 DevKit V1, 30-pin
buck_l    = 65;  buck_w = 27;   // LM2596S module with USB socket
mos_l     = 57;  mos_w  = 50;   // F5305S 4-channel MOSFET board
board_h   = 18;                 // tallest component above the PCB

/* ---- enclosure ---------------------------------------------------------- */
box_in_l  = 150;                // inner length  — fits all three boards
box_in_w  = 95;                 // inner width
box_in_h  = 45;                 // inner height
post_d    = 7;                  // screw post diameter
post_hole = 2.5;                // for an M3 self-tapping screw
cable_w   = 12;                 // width of each cable exit slot

/* ---- sensor shield ------------------------------------------------------ */
bme_l     = 13;  bme_w  = 11;   // GY-BME280  <<MEASURE>>
bh_l      = 19;  bh_w   = 14;   // GY-302 BH1750  <<MEASURE>>

/* ---- misc --------------------------------------------------------------- */
probe_w   = 24;   probe_t = 2;  // capacitive soil probe blade  <<MEASURE>>
fan_size  = 40;                 // 40x40 fan
glass_t   = 5;                  // terrarium glass thickness  <<MEASURE>>

/* ========================================================================= */
/*  ELECTRONICS ENCLOSURE                                                    */
/*  Mounts above the water line. Cables enter from BELOW so condensation     */
/*  runs down the wire and drips off instead of tracking into the box.       */
/* ========================================================================= */
module screw_post(h) {
    difference() {
        cylinder(d = post_d, h = h);
        translate([0, 0, 1]) cylinder(d = post_hole, h = h);
    }
}

module box() {
    difference() {
        union() {
            // shell
            difference() {
                cube([box_in_l + 2*wall, box_in_w + 2*wall, box_in_h + wall]);
                translate([wall, wall, wall])
                    cube([box_in_l, box_in_w, box_in_h + 1]);
            }
            // board standoffs — 4 mm clear of the floor so nothing shorts
            for (p = [[12, 14], [12, 14 + esp_w], [12 + esp_l, 14],
                      [12 + esp_l, 14 + esp_w],
                      [80, 14], [80 + mos_l - 6, 14],
                      [80, 14 + mos_w - 6], [80 + mos_l - 6, 14 + mos_w - 6]])
                translate([wall + p[0], wall + p[1], wall]) screw_post(4);

            // full-height corner posts — the lid screws bite into THESE.
            // Screwing into the floor instead would leave nothing to grip.
            for (p = [[wall + 5, wall + 5],
                      [box_in_l + wall - 5, wall + 5],
                      [wall + 5, box_in_w + wall - 5],
                      [box_in_l + wall - 5, box_in_w + wall - 5]])
                translate([p[0], p[1], wall]) screw_post(box_in_h);
        }
        // cable slots, low on one long side, open at the bottom edge
        for (x = [25, 60, 95, 130])
            translate([x, -1, wall]) cube([cable_w, wall + 2, 9]);

        // ventilation — slots high up, away from any splash
        for (x = [30 : 14 : box_in_l - 20])
            translate([x, box_in_w + wall - 0.5, box_in_h - 14])
                cube([3, wall + 2, 10]);

        // (lid screws thread into the corner posts above — nothing is
        //  drilled through the floor, which would only let water in)
    }
}

module lid() {
    difference() {
        union() {
            cube([box_in_l + 2*wall, box_in_w + 2*wall, wall]);
            // lip that drops inside the shell and keeps mist out
            translate([wall + clr, wall + clr, wall])
                difference() {
                    cube([box_in_l - 2*clr, box_in_w - 2*clr, 4]);
                    translate([wall, wall, -1])
                        cube([box_in_l - 2*wall - 2*clr,
                              box_in_w - 2*wall - 2*clr, 6]);
                }
        }
        for (p = [[wall + 5, wall + 5],
                  [box_in_l + wall - 5, wall + 5],
                  [wall + 5, box_in_w + wall - 5],
                  [box_in_l + wall - 5, box_in_w + wall - 5]])
            translate([p[0], p[1], -1]) cylinder(d = 3.4, h = 10);
    }
}

/* ========================================================================= */
/*  SENSOR SHIELD                                                            */
/*  Holds BME280 + BH1750 high in the airspace with a roof over them. The    */
/*  roof matters: mist landing directly on a BME280 pins it at 100% RH and   */
/*  the humidity control never releases. Slots let air through, not drips.   */
/* ========================================================================= */
module sensor_shield() {
    plate_l = bme_l + bh_l + 14;
    plate_w = max(bme_w, bh_w) + 8;

    difference() {
        union() {
            cube([plate_l, plate_w, wall]);                     // backplate
            translate([0, 0, wall]) cube([plate_l, wall, 16]);   // rear rib
            // sloped roof — condensation runs off the front edge
            translate([0, 0, 16 + wall])
                rotate([-12, 0, 0]) cube([plate_l, plate_w + 4, wall]);
            // module pockets
            translate([4, 4, wall])
                frame(bme_l, bme_w, 3);
            translate([bme_l + 10, 4, wall])
                frame(bh_l, bh_w, 3);
        }
        // airflow slots through the backplate
        for (x = [6 : 6 : plate_l - 6])
            translate([x, plate_w/2, -1]) cube([2, 6, wall + 2]);
        // hanging holes
        translate([4, plate_w - 3, -1]) cylinder(d = 3.4, h = wall + 2);
        translate([plate_l - 4, plate_w - 3, -1]) cylinder(d = 3.4, h = wall + 2);
    }
}

module frame(l, w, h) {          // open-bottomed pocket a PCB drops into
    difference() {
        cube([l + 2*wall, w + 2*wall, h]);
        translate([wall, wall, -1]) cube([l + clr, w + clr, h + 2]);
    }
}

/* ========================================================================= */
/*  SOIL PROBE COLLAR                                                        */
/*  Sets burial depth so every reading is taken at the same place. Move it   */
/*  and your calibration is meaningless — depth changes the reading more     */
/*  than moisture does.                                                      */
/* ========================================================================= */
module soil_collar() {
    difference() {
        cylinder(d = probe_w + 14, h = 8);
        translate([-(probe_w + clr)/2, -(probe_t + clr)/2, -1])
            cube([probe_w + clr, probe_t + clr, 10]);          // blade slot
        translate([0, 0, -1]) cylinder(d = probe_w - 4, h = 3); // save plastic
    }
    // legs that sit on the soil surface
    for (a = [0, 120, 240])
        rotate([0, 0, a]) translate([probe_w/2 + 3, 0, 0]) cylinder(d = 4, h = 3);
}

/* ========================================================================= */
/*  FAN DUCT — 40 mm fan onto a flat panel                                   */
/* ========================================================================= */
module fan_duct() {
    outer = fan_size + 12;
    difference() {
        union() {
            cube([outer, outer, wall]);
            translate([outer/2, outer/2, wall])
                cylinder(d1 = fan_size, d2 = fan_size - 6, h = 14);
        }
        translate([outer/2, outer/2, -1])
            cylinder(d1 = fan_size - 4, d2 = fan_size - 10, h = 20);
        // fan screw holes, 32 mm square pattern
        for (p = [[-16, -16], [16, -16], [-16, 16], [16, 16]])
            translate([outer/2 + p[0], outer/2 + p[1], -1])
                cylinder(d = 3.4, h = wall + 2);
    }
}

/* ========================================================================= */
/*  CABLE GROMMET — seals a drilled hole where wires cross the enclosure     */
/* ========================================================================= */
module grommet() {
    difference() {
        union() {
            cylinder(d = 16, h = 2);
            cylinder(d = 11.6, h = 2 + glass_t + 2);
            translate([0, 0, 2 + glass_t]) cylinder(d = 16, h = 2);
        }
        translate([0, 0, -1]) cylinder(d = 7, h = glass_t + 10);
        // split so it can be fitted over an existing cable
        translate([-1, 0, -1]) cube([2, 10, glass_t + 10]);
    }
}

/* ========================================================================= */
if      (PART == "box")           box();
else if (PART == "lid")           lid();
else if (PART == "sensor_shield") sensor_shield();
else if (PART == "soil_collar")   soil_collar();
else if (PART == "fan_duct")      fan_duct();
else if (PART == "grommet")       grommet();
