/* ============================================================================
 * TERRARIUM — FULL SYSTEM PARTS
 * EEE4103 capstone · OpenSCAD
 *
 * THE DESIGN, IN ONE PARAGRAPH
 *   A standard clear storage box or glass tank is the vessel — printed plastic
 *   is neither transparent nor watertight, so printing the tank itself would be
 *   worse than buying one. Everything else is printed. The floor is split by a
 *   DIVIDER into a wet zone (reservoir: two mist discs + float switch) and a
 *   dry zone (substrate + plants + soil probes). A CANOPY FRAME sits on the rim
 *   carrying a cut acrylic sheet; the electronics box bolts on TOP of it, in
 *   dry air, while sensors hang UNDER it behind a shield. Air enters low
 *   through a louvre, leaves high through the fan module, so mist is pulled
 *   across the plants rather than straight up the glass.
 *
 * WHY THE ELECTRONICS ARE OUTSIDE
 *   Everything in this project fails the same way: water reaching a board.
 *   Mounting the enclosure above the canopy means condensation has to travel
 *   uphill to reach it. Cables enter through grommets from below, so drips run
 *   down the wire and fall off.
 *
 * PRINT: PETG, 0.2 mm, 3 perimeters, 25% infill. See terrarium-parts.scad for
 * the enclosure, sensor shield, soil collar and grommet.
 * ========================================================================== */

PART = "fan_module";
// fan_module | light_rail | disc_holder | divider | canopy_corner | canopy_rail

wall  = 2.4;
clr   = 0.4;
$fn   = 48;

/* ---- your vessel  <<MEASURE the inside of your tank>> ------------------- */
tank_l   = 300;    // inner length of the opening
tank_w   = 200;    // inner width
rim_t    = 4;      // wall thickness of the tank itself
sheet_t  = 3;      // acrylic sheet you will have cut for the canopy

/* ---- equipment --------------------------------------------------------- */
fan_size  = 40;    // 40x40x10 fan
fan_screw = 32;    // its screw pattern
disc_d    = 20;    // mist disc diameter  <<MEASURE>>
strip_w   = 10;    // 5050 LED strip width
strip_t   = 3;

/* ========================================================================= */
/*  FAN MODULE — bolts over a square cutout in the canopy sheet              */
/*  Louvres point DOWN and outward so rising humid air exits but splashes    */
/*  cannot fall straight onto the fan bearing.                              */
/* ========================================================================= */
module fan_module() {
    plate = fan_size + 16;
    difference() {
        union() {
            cube([plate, plate, wall]);
            // collar the fan screws into
            translate([plate/2, plate/2, wall])
                difference() {
                    cylinder(d = fan_size + 4, h = 11);
                    translate([0, 0, -1]) cylinder(d = fan_size - 2, h = 13);
                }
            // louvre blades across the opening
            for (y = [-14 : 7 : 14])
                translate([plate/2 - (fan_size - 4)/2, plate/2 + y, wall])
                    rotate([30, 0, 0]) cube([fan_size - 4, 1.6, 5]);
        }
        // air opening
        translate([plate/2, plate/2, -1]) cylinder(d = fan_size - 4, h = wall + 2);
        // fan screws
        for (p = [[-fan_screw/2, -fan_screw/2], [fan_screw/2, -fan_screw/2],
                  [-fan_screw/2, fan_screw/2], [fan_screw/2, fan_screw/2]])
            translate([plate/2 + p[0], plate/2 + p[1], -1])
                cylinder(d = 3.4, h = 20);
        // mounting screws into the canopy sheet
        for (p = [[5, 5], [plate - 5, 5], [5, plate - 5], [plate - 5, plate - 5]])
            translate([p[0], p[1], -1]) cylinder(d = 3.4, h = wall + 2);
    }
}

/* ========================================================================= */
/*  LIGHT RAIL — clips the 12 V LED strip to the underside of the canopy     */
/*  Print several and space them along the strip.                           */
/* ========================================================================= */
module light_rail() {
    len = 40;
    difference() {
        union() {
            cube([len, strip_w + 2*wall, wall]);
            // side walls that grip the strip
            cube([len, wall, strip_t + wall + 1]);
            translate([0, strip_w + wall, 0])
                cube([len, wall, strip_t + wall + 1]);
            // return lips so the strip cannot drop out
            translate([0, wall - 0.2, strip_t + wall])
                cube([len, 1.4, 1]);
            translate([0, strip_w + wall - 1.2, strip_t + wall])
                cube([len, 1.4, 1]);
        }
        // screw slots into the sheet above
        translate([6, (strip_w + 2*wall)/2, -1]) cylinder(d = 3.4, h = wall + 2);
        translate([len - 6, (strip_w + 2*wall)/2, -1]) cylinder(d = 3.4, h = wall + 2);
    }
}

/* ========================================================================= */
/*  DISC HOLDER — keeps a mist disc at a fixed depth in the reservoir        */
/*  The disc must sit just at the surface: too deep and it drowns and stops  */
/*  atomising, too shallow and it runs dry and burns out in minutes.        */
/* ========================================================================= */
module disc_holder() {
    body_d = disc_d + 12;
    difference() {
        union() {
            cylinder(d = body_d, h = 14);
            // float ring so the holder rides the water surface
            translate([0, 0, 6]) cylinder(d = body_d + 10, h = 5);
        }
        // disc pocket, open at the bottom so water reaches the wick
        translate([0, 0, 3]) cylinder(d = disc_d + clr, h = 20);
        translate([0, 0, -1]) cylinder(d = disc_d - 5, h = 6);
        // cable notch
        translate([-2, 0, 3]) cube([4, body_d, 20]);
        // holes through the float ring — trapped air makes it sit crooked
        for (a = [0 : 60 : 300])
            rotate([0, 0, a]) translate([body_d/2 + 3, 0, 5])
                cylinder(d = 3, h = 8);
    }
}

/* ========================================================================= */
/*  DIVIDER — separates the wet reservoir from the planted substrate         */
/*  Slots let water pass slowly at the bottom while holding soil back.       */
/* ========================================================================= */
module divider() {
    d_w = tank_w;                 // spans the tank's width
    d_h = 90;                     // taller than your substrate depth
    difference() {
        union() {
            cube([wall + 1, d_w, d_h]);
            // feet so it stands up on its own while you backfill
            for (y = [15, d_w/2, d_w - 15])
                translate([-8, y - 5, 0]) cube([18, 10, wall]);
        }
        // water slots, bottom third only, chamfered so soil bridges over them
        for (y = [12 : 16 : d_w - 12])
            for (z = [8 : 12 : 40])
                translate([-1, y, z]) cube([wall + 3, 6, 3]);
    }
}

/* ========================================================================= */
/*  CANOPY FRAME — rails + corners hold a cut acrylic sheet on the tank rim  */
/*  Printed in short segments so any bed size works. Cut the sheet to        */
/*  tank_l x tank_w minus 1 mm and drop it in.                              */
/* ========================================================================= */
module canopy_rail(len = 120) {
    difference() {
        cube([len, rim_t + 2*wall + 6, 14]);
        // groove the acrylic sheet slides into
        translate([-1, wall, 8]) cube([len + 2, sheet_t + clr, 8]);
        // channel that sits over the tank wall
        translate([-1, wall + sheet_t + clr + 1, -1])
            cube([len + 2, rim_t + clr, 9]);
    }
}

module canopy_corner() {
    arm = 45;
    union() {
        canopy_rail(arm);
        rotate([0, 0, 90]) mirror([0, 1, 0]) canopy_rail(arm);
    }
}

/* ========================================================================= */
if      (PART == "fan_module")    fan_module();
else if (PART == "light_rail")    light_rail();
else if (PART == "disc_holder")   disc_holder();
else if (PART == "divider")       divider();
else if (PART == "canopy_rail")   canopy_rail();
else if (PART == "canopy_corner") canopy_corner();
