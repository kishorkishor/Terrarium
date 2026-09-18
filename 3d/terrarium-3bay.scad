/* ============================================================================
 * TERRARIUM — THREE-BAY PRINTED ENCLOSURE WITH SLIDE DAMPER
 * EEE4103 capstone · OpenSCAD
 *
 * LAYOUT (left to right, all in one line)
 *
 *   [ ELECTRONICS ] solid wall + grommets [ TERRARIUM ] slide damper [ AIR UNIT: fan ]
 *
 *   Humid air never passes through the electronics. The only openings in
 *   the electronics/terrarium wall are cable grommets. The fan at the far
 *   end pulls fresh air in through the terrarium lid vent, across the plant,
 *   through the damper, and out. Damper closed = humidity retained,
 *   damper open = purge.
 *
 * DAMPER
 *   The terrarium's right wall and the air unit's left wall both have the
 *   same grid of horizontal slots. A thin plate with the same grid slides
 *   vertically in a channel between them. At rest (plate sitting on its
 *   stop) the slots are offset by half a pitch = CLOSED. Lift the tab by
 *   slot_pitch/2 = OPEN and push an M3x20 screw through the tab hole; it
 *   rests on the lids and holds the damper open. Slot pitch is more than
 *   twice the slot height, so the closed position really blocks. A servo
 *   link can use the same tab hole later.
 *
 * PRINTING
 *   Each bay is a separate open-top box; bays bolt face to face with M3
 *   screws through the flanges. Every part fits a 220 x 220 x 250 mm bed.
 *   PETG, 0.2 mm layers, 3 perimeters, 20-25 % infill, no supports.
 *   Print bays and lids upright as modelled. Print the plate flat.
 *   Terrarium bay: seal the inside seams with aquarium silicone; FDM is
 *   not watertight on its own.
 *
 * PARTS  (set PART, F6, export STL)
 *   terrarium_bay   electronics_bay   air_bay   damper_plate
 *   terrarium_lid   electronics_lid   air_lid   assembly (view only)
 * ========================================================================== */

PART = "assembly";

/* ---- global ------------------------------------------------------------- */
wall   = 2.4;      // shell thickness
clr    = 0.4;      // clearance for mating parts
$fn    = 36;

/* ---- bay sizes (inner) -------------------------------------------------- */
W      = 150;      // inner width, same for all bays
H      = 170;      // inner height, same for all bays
L_terr = 190;      // terrarium bay inner length     <<change for your plant>>
L_elec = 80;       // electronics bay inner length
L_air  = 70;       // air-unit bay inner length (fan 10 mm + room for Peltier)

/* ---- flanges & bolts ---------------------------------------------------- */
flange_w = 10;     // how far the flange sticks out sideways
flange_t = 3;      // flange thickness (= rail height on the damper face)
bolt_d   = 3.4;    // M3 clearance

/* ---- damper ------------------------------------------------------------- */
slot_h     = 7;    // slot height
slot_pitch = 16;   // vertical pitch (> 2 x slot_h so CLOSED really closes)
slot_len   = 36;   // slot length
slot_cols  = 3;
slot_gap   = 8;    // bridge between slot columns
grid_z0    = 20;   // first slot, height above inner floor
grid_z1    = 25;   // keep this much clear below the box top
plate_t    = 2;    // slide plate thickness
plate_w    = 140;
rail_w     = 3;
tab_w      = 24;
tab_h      = 40;   // reaches above the lid so you can grab it

/* ---- fan / boards ------------------------------------------------------- */
fan_size   = 40;   fan_screw = 32;   fan_hole = 38;
grommet_d  = 9;                        // cable grommet holes
esp_hx = 48;  esp_hy = 23;             // ESP32 DevKit hole spacing  <<MEASURE>>
mos_hx = 44;  mos_hy = 51;             // 4-ch MOSFET board hole spacing <<MEASURE>>
post_d = 7;   post_hole = 2.5;         // M3 self-tapping posts
strip_w = 10; strip_t = 3;             // LED strip

/* ---- derived ------------------------------------------------------------ */
OW  = W + 2*wall;            // outer width
OH  = H + wall;              // outer height
yc  = OW/2;                  // face centre (y)
grid_y0 = wall + (W - (slot_cols*slot_len + (slot_cols-1)*slot_gap))/2;
n_rows  = floor((H - grid_z1 - grid_z0 - slot_h)/slot_pitch) + 1;
plate_z0 = flange_w;         // plate rests on the flange bottom bar (closed)
plate_h  = wall + grid_z0 + (n_rows-1)*slot_pitch + slot_h + 8 - plate_z0;  // body
plate_y0 = yc - plate_w/2;

/* ========================================================================= */
/*  helpers                                                                  */
/* ========================================================================= */
module screw_post(h) {
    difference() {
        cylinder(d = post_d, h = h);
        translate([0, 0, 1]) cylinder(d = post_hole, h = h);
    }
}

// slot grid cut through an end wall lying at x = x0 (cuts x0-1 .. x0+wall+1)
module grid_cut(x0, zoff = 0) {
    for (i = [0 : n_rows-1])
        for (c = [0 : slot_cols-1])
            translate([x0 - 1, grid_y0 + c*(slot_len + slot_gap),
                       wall + grid_z0 + i*slot_pitch + zoff])
                cube([wall + 2, slot_len, slot_h]);
}

// bolt flange ring on an end face. x0 = face position, dir = +1 grows in +x
module flange(x0, dir) {
    xs = dir > 0 ? x0 : x0 - flange_t;
    difference() {
        translate([xs, -flange_w, 0]) cube([flange_t, OW + 2*flange_w, OH]);
        // opening: everything inside the bay walls, leaving a 10 mm bottom bar
        translate([xs - 1, wall, flange_w]) cube([flange_t + 2, W, OH]);
        flange_holes(xs);
    }
}
module flange_holes(xs) {
    for (p = [[-flange_w/2, 25], [-flange_w/2, OH/2], [-flange_w/2, OH - 15],
              [OW + flange_w/2, 25], [OW + flange_w/2, OH/2], [OW + flange_w/2, OH - 15],
              [wall + W/4, 5], [wall + 3*W/4, 5]])
        translate([xs - 1, p[0], p[1]]) rotate([0, 90, 0]) cylinder(d = bolt_d, h = flange_t + 2);
}

// open-top shell
module shell(L) {
    difference() {
        cube([L + 2*wall, OW, OH]);
        translate([wall, wall, wall]) cube([L, W, H + 1]);
    }
}

module grommet_cut(x0) {
    for (y = [yc - 38, yc, yc + 38])
        translate([x0 - 1, y, wall + 30]) rotate([0, 90, 0]) cylinder(d = grommet_d, h = wall + 2);
}

/* ========================================================================= */
/*  TERRARIUM BAY                                                            */
/*  left wall: grommets to electronics.  right wall: damper grid + rails.    */
/* ========================================================================= */
module terrarium_bay() {
    L = L_terr;  xr = L + 2*wall;
    difference() {
        union() {
            shell(L);
            flange(0, -1);
            flange(xr, +1);
            // damper rails on the outer right face, form the plate channel
            for (y = [plate_y0 - clr - rail_w, plate_y0 + plate_w + clr])
                translate([xr, y, 5]) cube([flange_t, rail_w, OH - 5]);
            // condensation lip along the floor at both ends
            translate([wall, wall, wall]) cube([3, W, 6]);
            translate([xr - wall - 3, wall, wall]) cube([3, W, 6]);
        }
        grommet_cut(0);
        grid_cut(xr - wall);
        // sensor window: BME280 sits on the left wall, above the grommets
        translate([-1, yc - 8, wall + 60]) cube([wall + 2, 16, 12]);
    }
}

/* ========================================================================= */
/*  DAMPER PLATE  (print flat, slots up)                                     */
/* ========================================================================= */
module damper_plate() {
    difference() {
        union() {
            cube([plate_w, plate_h, plate_t]);
            // finger / servo tab
            translate([plate_w/2 - tab_w/2, plate_h, 0]) cube([tab_w, tab_h, plate_t]);
        }
        // slots: half a pitch below the wall grid at rest -> closed at rest
        for (i = [0 : n_rows-1])
            for (c = [0 : slot_cols-1])
                translate([grid_y0 - plate_y0 + c*(slot_len + slot_gap),
                           wall + grid_z0 - plate_z0 - slot_pitch/2 + i*slot_pitch, -1])
                    cube([slot_len, slot_h, plate_t + 2]);
        // hold-open hole: lift the plate slot_pitch/2 and push an M3x20 screw
        // through; it rests on the two lid tops and keeps the damper OPEN.
        // The same hole takes a servo horn link later.
        translate([plate_w/2, OH + wall + 1.7 + slot_pitch/2 - plate_z0, -1])
            cylinder(d = 3.4, h = plate_t + 2);
        // engraved arrow: lift to open
        translate([plate_w/2 - 1, plate_h + 4, plate_t - 0.6]) cube([2, 8, 1]);
    }
}

/* ========================================================================= */
/*  AIR UNIT BAY                                                             */
/*  left wall: damper grid (plate lives between this and the terrarium).     */
/*  right wall: 40 mm fan, exhaust.  floor: drain hole for Peltier drip.     */
/* ========================================================================= */
module air_bay() {
    L = L_air;  xr = L + 2*wall;
    difference() {
        union() {
            shell(L);
            flange(0, -1);
            // fan screw bosses on the outside of the right wall
            for (p = [[-1, -1], [1, -1], [-1, 1], [1, 1]])
                translate([xr, yc + p[0]*fan_screw/2, wall + H/2 + p[1]*fan_screw/2])
                    rotate([0, 90, 0]) cylinder(d = 7, h = 3);
        }
        grid_cut(0);
        // fan opening + screws
        translate([xr - wall - 1, yc, wall + H/2]) rotate([0, 90, 0]) cylinder(d = fan_hole, h = wall + 5);
        for (p = [[-1, -1], [1, -1], [-1, 1], [1, 1]])
            translate([xr - wall - 1, yc + p[0]*fan_screw/2, wall + H/2 + p[1]*fan_screw/2])
                rotate([0, 90, 0]) cylinder(d = 3.2, h = wall + 5);
        // drain
        translate([wall + L/2, yc, -1]) cylinder(d = 6, h = wall + 2);
        // fan power cable notch, bottom right
        translate([xr - wall - 1, yc + 45, wall + 10]) rotate([0, 90, 0]) cylinder(d = 6, h = wall + 2);
    }
}

/* ========================================================================= */
/*  ELECTRONICS BAY                                                          */
/*  right wall: grommets to terrarium.  left wall + lid: convection vents.   */
/*  floor: posts for ESP32 and the MOSFET board.                             */
/* ========================================================================= */
module electronics_bay() {
    L = L_elec;  xr = L + 2*wall;
    difference() {
        union() {
            shell(L);
            flange(xr, +1);
            // ESP32 posts (board long side along y)
            for (p = [[0, 0], [esp_hx, 0], [0, esp_hy], [esp_hx, esp_hy]])
                translate([wall + 14 + p[1], wall + 12 + p[0], wall]) screw_post(5);
            // MOSFET board posts
            for (p = [[0, 0], [mos_hx, 0], [0, mos_hy], [mos_hx, mos_hy]])
                translate([wall + 16 + p[0], wall + 82 + p[1], wall]) screw_post(5);
        }
        grommet_cut(xr - wall);
        // vents on the outer (left) wall: low intake, high exhaust
        for (y = [wall + 15 : 22 : W - 15])
            for (z = [wall + 10, OH - 22])
                translate([-1, y, z]) cube([wall + 2, 14, 5]);
        // power cable entry, left wall
        translate([-1, yc, wall + 20]) rotate([0, 90, 0]) cylinder(d = 8, h = wall + 2);
    }
}

/* ========================================================================= */
/*  LIDS  — plate with an inner lip that drops inside the bay                */
/* ========================================================================= */
module lid_base(L) {
    union() {
        cube([L + 2*wall, OW, wall]);
        translate([wall + clr, wall + clr, -6])
            difference() {
                cube([L - 2*clr, W - 2*clr, 6]);
                translate([wall, wall, -1]) cube([L - 2*clr - 2*wall, W - 2*clr - 2*wall, 8]);
            }
    }
}

module vent_slots(x0, x1, y0, y1) {
    for (x = [x0 : 12 : x1 - 6])
        translate([x, y0, -8]) cube([6, y1 - y0, 12]);
}

module terrarium_lid() {
    L = L_terr;
    difference() {
        union() {
            lid_base(L);
            // LED strip rails under the lid, running along x
            for (s = [-1, 1])
                translate([wall + 70, yc + s*(strip_w/2 + 1) - (s > 0 ? 0 : 3), -strip_t - 2])
                    difference() {
                        cube([L - 85, 3, strip_t + 2]);
                        translate([-1, s > 0 ? -1 : 1.6, 0.4]) cube([L - 83, 2.4, strip_t + 0.4]);
                    }
        }
        // fresh-air intake near the electronics end (far from the damper)
        vent_slots(wall + 12, wall + 60, wall + 20, wall + W - 20);
        // LED cable hole
        translate([wall + 8, yc, -10]) cylinder(d = 6, h = 20);
    }
}

module electronics_lid() {
    difference() {
        lid_base(L_elec);
        vent_slots(wall + 10, L_elec - 4, wall + 20, wall + W - 20);
    }
}

module air_lid() { lid_base(L_air); }

/* ========================================================================= */
/*  ASSEMBLY VIEW                                                            */
/* ========================================================================= */
module assembly(lift = 25) {
    x_elec = 0;
    x_terr = L_elec + 2*wall + 2*flange_t;
    x_air  = x_terr + L_terr + 2*wall + 2*flange_t;
    color("SlateGray")   translate([x_elec, 0, 0]) electronics_bay();
    color("SeaGreen")    translate([x_terr, 0, 0]) terrarium_bay();
    color("SteelBlue")   translate([x_air, 0, 0])  air_bay();
    // plate in its channel, resting on the stop (closed)
    color("Orange")
        translate([x_terr + L_terr + 2*wall + 0.5, plate_y0, plate_z0])
            rotate([90, 0, 90]) damper_plate();
    // lids lifted 25 mm so you can see inside
    color("LightGray", 0.7) {
        translate([x_elec, 0, OH + lift]) electronics_lid();
        translate([x_terr, 0, OH + lift]) terrarium_lid();
        translate([x_air, 0, OH + lift])  air_lid();
    }
}

/* ========================================================================= */
if      (PART == "terrarium_bay")    terrarium_bay();
else if (PART == "electronics_bay")  electronics_bay();
else if (PART == "air_bay")          air_bay();
else if (PART == "damper_plate")     damper_plate();
else if (PART == "terrarium_lid")    terrarium_lid();
else if (PART == "electronics_lid")  electronics_lid();
else if (PART == "air_lid")          air_lid();
else if (PART == "assembled_closed") assembly(0);
else                                 assembly();
