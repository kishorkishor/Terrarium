"""
Laser-cut clear acrylic terrarium enclosure, three bays in one long box.

  [ ELECTRONICS ] solid divider [ TERRARIUM, two fittonias ] slot divider + slide damper [ AIR UNIT ]

Run:  python make_acrylic.py
Makes: sheet SVG / DXF / PDF / AI cut files, one DXF per part (for Onshape),
       a labelled part map, and an OpenSCAD 3D model of the assembly.

All numbers are millimetres. Change the PARAMETERS block and re-run.
Construction is tab-and-slot: every cross panel has tabs that pass through
slots in the front, back and base, so the box squares itself while you glue.
"""
import os, math, shutil

# ------------------------------------------------------------ PARAMETERS ---
T       = 3.0     # main sheet thickness (clear cast acrylic)
T_PLATE = 2.0     # damper plate sheet thickness (must be thinner than T)
W       = 200.0   # inner width  (front to back)
H       = 250.0   # wall height above the base
L_ELEC  = 110.0   # electronics bay inner length
L_TERR  = 320.0   # terrarium bay inner length (two fittonias side by side)
L_AIR   = 90.0    # air-unit bay inner length
M       = 8.0     # how far base / front / back overhang past the joints
TAB     = 20.0    # tab width
SHEET   = (900.0, 600.0)

SLOT_H, SLOT_PITCH, SLOT_LEN, SLOT_COLS, SLOT_GAP = 8.0, 20.0, 50.0, 3, 10.0
GRID_V0, GRID_TOP_CLEAR = 30.0, 40.0
GUIDE_W, COVER_W = 6.0, 16.0
FAN_HOLE, FAN_SCREW, FAN_SCREW_D = 38.0, 32.0, 3.4

# ------------------------------------------------------------ derived -------
WO    = W + 2*T
X_E1  = 0.0
X_D1  = T + L_ELEC
X_D2  = X_D1 + T + L_TERR
X_E2  = X_D2 + T + L_AIR
L_TOT = X_E2 + T
V_TABS = [45.0, H/2, H - 45.0]            # tabs on vertical edges of cross panels
U_TABS = [W*0.25, W*0.75]                 # bottom tabs of cross panels
N_LONG = 6
X_TABS = [L_TOT*(i + 0.5)/N_LONG for i in range(N_LONG)]   # bottom tabs of front/back
N_ROWS = int((H - GRID_TOP_CLEAR - GRID_V0 - SLOT_H)//SLOT_PITCH) + 1
GRID_U0 = (W - (SLOT_COLS*SLOT_LEN + (SLOT_COLS-1)*SLOT_GAP))/2
PLATE_W = W - 2*GUIDE_W - 2.0
PLATE_U0 = (W - PLATE_W)/2
PLATE_BODY = GRID_V0 + (N_ROWS-1)*SLOT_PITCH + SLOT_H + 17
TAB_W_PLATE, TAB_TOP = 30.0, H + T + 32


# ------------------------------------------------------------ geometry ------
def outline(A, B, bottom=(), right=(), left=(), depth=T):
    """CCW rectangle (0,0)-(A,B) with tabs sticking out of bottom/right/left edges."""
    h = TAB/2
    p = [(0, 0)]
    for c in sorted(bottom):
        p += [(c-h, 0), (c-h, -depth), (c+h, -depth), (c+h, 0)]
    p.append((A, 0))
    for c in sorted(right):
        p += [(A, c-h), (A+depth, c-h), (A+depth, c+h), (A, c+h)]
    p += [(A, B), (0, B)]
    for c in sorted(left, reverse=True):
        p += [(0, c+h), (-depth, c+h), (-depth, c-h), (0, c-h)]
    return p

def rect(x, y, w, h): return ('rect', x, y, w, h)
def circ(x, y, d):    return ('circle', x, y, d)
def hslots(u0, u1, v, w=20, h=4, step=30):
    out, u = [], u0
    while u + w <= u1 + 1e-6:
        out.append(rect(u, v, w, h)); u += step
    return out

PARTS = {}   # name -> dict(pts, holes, t, note)
def part(name, pts, holes=(), t=T, note=''):
    PARTS[name] = dict(pts=pts, holes=list(holes), t=t, note=note)

# ---- base ------------------------------------------------------------------
holes = []
for xc in X_TABS:
    holes += [rect(M + xc - TAB/2, M, TAB, T), rect(M + xc - TAB/2, M + WO - T, TAB, T)]
for xp in (X_E1, X_D1, X_D2, X_E2):
    for uc in U_TABS:
        holes.append(rect(M + xp, M + T + uc - TAB/2, T, TAB))
holes.append(circ(M + X_D2 + T + L_AIR/2, M + WO/2, 6))          # air-bay drain
part('base', outline(L_TOT + 2*M, WO + 2*M), holes, note='floor of all three bays')

# ---- front / back ------------------------------------------------------------
def long_panel(extra=()):
    hs = []
    for xp in (X_E1, X_D1, X_D2, X_E2):
        for vc in V_TABS:
            hs.append(rect(M + xp, vc - TAB/2, T, TAB))
    return outline(L_TOT + 2*M, H, bottom=[M + x for x in X_TABS]), hs + list(extra)

pts, hs = long_panel()
part('front', pts, hs, note='clear viewing side, no openings')
back_vents = hslots(M + T + 15, M + T + L_ELEC - 10, 20, w=20, h=4, step=30) + \
             hslots(M + T + 15, M + T + L_ELEC - 10, H - 25, w=20, h=4, step=30)
pts, hs = long_panel(back_vents)
part('back', pts, hs, note='vents behind the electronics bay only')

# ---- cross panels ------------------------------------------------------------
def cross(): return outline(W, H, bottom=U_TABS, right=V_TABS, left=V_TABS)

part('end_electronics', cross(), [
    circ(35, 40, 8),                 # DC barrel jack (panel mount, 8 mm)
    circ(65, 40, 12),                # 5x20 fuse holder (panel mount, 12 mm)
    rect(100, 12, 16, 10),           # USB cable slot for flashing the ESP32
    circ(150, 40, 6),                # spare / toggle switch
] + hslots(15, W - 15, H - 25, w=20, h=4, step=30) + hslots(125, W - 15, 60, w=20, h=4, step=30),
    note='outer wall of electronics bay: power jack, fuse, USB slot, vents')

part('divider_solid', cross(), [
    circ(40, 60, 12), circ(80, 60, 12), circ(120, 60, 12), circ(160, 60, 12),   # low cable grommets
    circ(100, 170, 12),              # high grommet: BME280 / BH1750 / LED / circulation fan
    circ(170, H - 15, 8),            # exhaust-fan cable, runs along the top back corner
], note='electronics | terrarium. Solid: only cable grommets. Seal each with silicone.')

grid = [rect(GRID_U0 + c*(SLOT_LEN + SLOT_GAP), GRID_V0 + i*SLOT_PITCH, SLOT_LEN, SLOT_H)
        for i in range(N_ROWS) for c in range(SLOT_COLS)]
part('divider_damper', cross(), grid + [circ(170, H - 15, 8)],
     note='terrarium | air unit. Fixed half of the slide damper.')

part('end_fan', cross(), [
    circ(W/2, H/2, FAN_HOLE),
    *[circ(W/2 + sx*FAN_SCREW/2, H/2 + sy*FAN_SCREW/2, FAN_SCREW_D) for sx in (-1, 1) for sy in (-1, 1)],
    circ(160, 30, 6),
], note='outer wall of air unit: 40 mm exhaust fan')

# ---- damper plate (thin sheet) -------------------------------------------------
tw = TAB_W_PLATE
pl = [(0, 0), (PLATE_W, 0), (PLATE_W, PLATE_BODY), (PLATE_W/2 + tw/2, PLATE_BODY),
      (PLATE_W/2 + tw/2, TAB_TOP), (PLATE_W/2 - tw/2, TAB_TOP), (PLATE_W/2 - tw/2, PLATE_BODY), (0, PLATE_BODY)]
pgrid = [rect(GRID_U0 - PLATE_U0 + c*(SLOT_LEN + SLOT_GAP), GRID_V0 - SLOT_PITCH/2 + i*SLOT_PITCH, SLOT_LEN, SLOT_H)
         for i in range(N_ROWS) for c in range(SLOT_COLS)]
pin_v = H + T + 1.7 - SLOT_PITCH/2
part('damper_plate', pl, pgrid + [circ(PLATE_W/2, pin_v, 3.4), circ(PLATE_W/2, TAB_TOP - 8, 3.4)],
     t=T_PLATE, note='sliding half. Resting on the base = CLOSED. Lift 10 mm + M3 pin = OPEN.')

for i in (1, 2):
    part(f'guide_spacer_{i}', outline(GUIDE_W, H - 10), note='glue to divider_damper, air side, at each edge')
    part(f'guide_cover_{i}', outline(COVER_W, H - 10), note='glue on top of spacer, overhanging the plate')

# ---- lids ---------------------------------------------------------------------------
lx0, lx1, lx2, lx3 = 0.0, X_D1 + T/2, X_D2 + T/2, L_TOT
def vslots(u0, u1, v0, v1, w=6, step=14):
    out, u = [], u0
    while u + w <= u1 + 1e-6:
        out.append(rect(u, v0, w, v1 - v0)); u += step
    return out

part('lid_electronics', outline(lx1 - lx0, WO), vslots(20, lx1 - 20, 40, WO - 40),
     note='vented lid')
FAN_U = 95.0   # circulation-fan bracket position along the terrarium lid
part('lid_terrarium', outline(lx2 - lx1, WO),
     vslots(18, 75, 45, WO - 45) +                         # fresh-air intake, far from the damper
     [rect(FAN_U, WO/2 - 22, T, 10), rect(FAN_U, WO/2 + 12, T, 10),   # bracket slots
      circ(FAN_U + 20, WO - 25, 6),                         # LED strip cable
      circ((lx2 - lx1) - 60, WO/2, 25)],                    # refill / misting port (cover with a plug)
     note='intake slots at the electronics end, fan-bracket slots, refill port')
nw = TAB_W_PLATE + 4
al = lx3 - lx2
notch_d = T/2 + T_PLATE + 2.5
lid_air = [(0, 0), (al, 0), (al, WO), (0, WO), (0, WO/2 + nw/2), (notch_d, WO/2 + nw/2),
           (notch_d, WO/2 - nw/2), (0, WO/2 - nw/2)]
part('lid_air', lid_air, [circ(al/2 + 10, WO/2, 20)], note='notch clears the damper tab; finger hole')
for i in range(1, 13):
    part(f'lid_locator_{i:02d}', outline(10, 50), note='glue under lids, just inside the walls (4 per lid)')

# ---- circulation fan bracket (hangs from the terrarium lid) ----------------------
bw, bh = 56.0, 70.0
br = [(0, 0), (bw, 0), (bw, bh), (bw/2 + 22, bh), (bw/2 + 22, bh + T), (bw/2 + 12, bh + T), (bw/2 + 12, bh),
      (bw/2 - 12, bh), (bw/2 - 12, bh + T), (bw/2 - 22, bh + T), (bw/2 - 22, bh), (0, bh)]
part('fan_bracket', br, [circ(bw/2, 30, FAN_HOLE)] +
     [circ(bw/2 + sx*FAN_SCREW/2, 30 + sy*FAN_SCREW/2, FAN_SCREW_D) for sx in (-1, 1) for sy in (-1, 1)],
     note='40 mm circulation fan, tabs glue into the terrarium lid slots')

# ---- electronics tray: universal 10 mm hole grid --------------------------------
tl, tw_ = L_ELEC - 6, W - 10
part('electronics_tray', outline(tl, tw_),
     [circ(7 + 10*i, 10 + 10*j, 3.2) for i in range(int((tl - 14)//10) + 1) for j in range(int((tw_ - 20)//10) + 1)],
     note='drop-in board. 10 mm grid of M3 holes fits ESP32, MOSFET boards, buck, mist drivers, buzzer')


# ------------------------------------------------------------ layout ----------
G = 6.0
def bbox(pts):
    xs, ys = zip(*pts); return min(xs), min(ys), max(xs), max(ys)

LAYOUT = {'A_3mm': [], 'B_3mm': [], 'C_2mm': []}
def place(sheet, name, x, y, rot=False):
    LAYOUT[sheet].append((name, x, y, rot))

place('A_3mm', 'front', 10, 10 + T)
place('A_3mm', 'back', 10, 10 + T + H + T + G)
place('A_3mm', 'end_electronics', 10 + L_TOT + 2*M + G + T, 10 + T)
place('A_3mm', 'end_fan', 10 + L_TOT + 2*M + G + T, 10 + T + H + T + G)

place('B_3mm', 'base', 10, 10)
ly = 10 + WO + 2*M + G
place('B_3mm', 'lid_electronics', 10, ly)
place('B_3mm', 'lid_terrarium', 10 + (lx1 - lx0) + G, ly)
place('B_3mm', 'lid_air', 10 + (lx2 - lx0) + 2*G, ly)
cx = 10 + L_TOT + 2*M + G + T
place('B_3mm', 'divider_solid', cx, 10 + T)
place('B_3mm', 'divider_damper', cx, 10 + T + H + T + G)
tx = cx + W + T + G
place('B_3mm', 'electronics_tray', tx, 10)
sy = 10 + (W - 10) + G
sx = tx
for n in ('guide_spacer_1', 'guide_spacer_2', 'guide_cover_1', 'guide_cover_2'):
    place('B_3mm', n, sx, sy); sx += bbox(PARTS[n]['pts'])[2] + G
place('B_3mm', 'fan_bracket', 10 + 12*(10 + G) + 20, ly + WO + G)
for i in range(12):
    place('B_3mm', f'lid_locator_{i+1:02d}', 10 + i*(10 + G), ly + WO + G)
place('C_2mm', 'damper_plate', 10, 10)
SHEET_SIZE = {'A_3mm': SHEET, 'B_3mm': SHEET, 'C_2mm': (PLATE_W + 20, TAB_TOP + 20)}


# ------------------------------------------------------------ writers ---------
def placed_geometry(sheet):
    """yield (name, outline pts, holes) in sheet coordinates"""
    for name, x, y, rot in LAYOUT[sheet]:
        p = PARTS[name]
        pts = [(x + u, y + v) for u, v in p['pts']]
        hs = []
        for h in p['holes']:
            if h[0] == 'rect': hs.append(('rect', x + h[1], y + h[2], h[3], h[4]))
            else:              hs.append(('circle', x + h[1], y + h[2], h[3]))
        yield name, pts, hs

def check_sheet(sheet):
    sw, sh = SHEET_SIZE[sheet]
    boxes = []
    for name, pts, _ in placed_geometry(sheet):
        b = bbox(pts)
        assert b[0] >= 0 and b[1] >= 0 and b[2] <= sw and b[3] <= sh, f'{name} off sheet {sheet}: {b}'
        for n2, b2 in boxes:
            assert b[2] <= b2[0] or b2[2] <= b[0] or b[3] <= b2[1] or b2[3] <= b[1], f'{name} overlaps {n2} on {sheet}'
        boxes.append((name, b))

def write_svg(path, sheet_wh, geoms, labels=False):
    sw, sh = sheet_wh
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}mm" height="{sh}mm" viewBox="0 0 {sw} {sh}">',
         '<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.1">']
    lab = []
    for name, pts, hs in geoms:
        d = 'M ' + ' L '.join(f'{x:.3f},{sh - y:.3f}' for x, y in pts) + ' Z'
        o.append(f'<path id="{name}" d="{d}"/>')
        for h in hs:
            if h[0] == 'rect':
                o.append(f'<rect x="{h[1]:.3f}" y="{sh - h[2] - h[4]:.3f}" width="{h[3]:.3f}" height="{h[4]:.3f}"/>')
            else:
                o.append(f'<circle cx="{h[1]:.3f}" cy="{sh - h[2]:.3f}" r="{h[3]/2:.3f}"/>')
        b = bbox(pts)
        lab.append(f'<text x="{(b[0]+b[2])/2:.1f}" y="{sh - (b[1]+b[3])/2:.1f}" font-size="9" text-anchor="middle" '
                   f'font-family="Arial" fill="#0050c8">{name}</text>')
    o.append('</g>')
    if labels: o += ['<g id="LABELS_NOT_FOR_CUTTING">'] + lab + ['</g>']
    o.append('</svg>')
    open(path, 'w').write('\n'.join(o))

def write_dxf(path, geoms):
    e = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    def line(a, b): e.extend(['0', 'LINE', '8', 'CUT', '10', f'{a[0]:.4f}', '20', f'{a[1]:.4f}', '11', f'{b[0]:.4f}', '21', f'{b[1]:.4f}'])
    def poly(pts):
        for i in range(len(pts)): line(pts[i], pts[(i + 1) % len(pts)])
    for name, pts, hs in geoms:
        poly(pts)
        for h in hs:
            if h[0] == 'rect':
                x, y, w, hh = h[1:]
                poly([(x, y), (x + w, y), (x + w, y + hh), (x, y + hh)])
            else:
                e.extend(['0', 'CIRCLE', '8', 'CUT', '10', f'{h[1]:.4f}', '20', f'{h[2]:.4f}', '40', f'{h[3]/2:.4f}'])
    e += ['0', 'ENDSEC', '0', 'EOF']
    open(path, 'w').write('\n'.join(e) + '\n')

def write_pdf(path, sheet_wh, geoms, labels=False):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    sw, sh = sheet_wh
    c = canvas.Canvas(path, pagesize=(sw*mm, sh*mm))
    c.setStrokeColorRGB(1, 0, 0); c.setLineWidth(0.1*mm if labels else 0.0283*mm)   # 0.001 in hairline
    for name, pts, hs in geoms:
        p = c.beginPath(); p.moveTo(pts[0][0]*mm, pts[0][1]*mm)
        for x, y in pts[1:]: p.lineTo(x*mm, y*mm)
        p.close(); c.drawPath(p, stroke=1, fill=0)
        for h in hs:
            if h[0] == 'rect': c.rect(h[1]*mm, h[2]*mm, h[3]*mm, h[4]*mm, stroke=1, fill=0)
            else:              c.circle(h[1]*mm, h[2]*mm, h[3]/2*mm, stroke=1, fill=0)
        if labels:
            b = bbox(pts); c.setFillColorRGB(0, 0.3, 0.8); c.setFont('Helvetica', 9)
            c.drawCentredString((b[0]+b[2])/2*mm, (b[1]+b[3])/2*mm, name)
    c.showPage(); c.save()


# ------------------------------------------------------------ OpenSCAD 3D -----
def scad_module(name):
    p = PARTS[name]
    pts = ','.join(f'[{x:.3f},{y:.3f}]' for x, y in p['pts'])
    s = [f'module {name}() {{ linear_extrude({p["t"]}) difference() {{ polygon([{pts}]);']
    for h in p['holes']:
        if h[0] == 'rect': s.append(f'  translate([{h[1]:.3f},{h[2]:.3f}]) square([{h[3]:.3f},{h[4]:.3f}]);')
        else:              s.append(f'  translate([{h[1]:.3f},{h[2]:.3f}]) circle(d={h[3]:.3f}, $fn=32);')
    s.append('} }')
    return '\n'.join(s)

def write_scad(path):
    s = ['// generated by make_acrylic.py - do not edit, change the script instead',
         'EXPLODE = 0;   // 0 = assembled, 1 = lids and damper lifted', 'A = 0.45;        // see-through preview']
    s += [scad_module(n) for n in PARTS]
    def X(n, x): return f'translate([{x:.3f},{T:.3f},0]) rotate([90,0,90]) {n}();'
    s += ['module assembly() {',
          f' color("LightCyan", A) translate([{-M},{-M},{-T}]) base();',
          f' color("LightCyan", A) translate([{-M},{T},0]) rotate([90,0,0]) front();',
          f' color("LightCyan", A) translate([{-M},{WO},0]) rotate([90,0,0]) back();',
          f' color("LightSlateGray", A) {X("end_electronics", X_E1)}',
          f' color("LightSlateGray", A) {X("divider_solid", X_D1)}',
          f' color("LightSlateGray", A) {X("divider_damper", X_D2)}',
          f' color("LightSlateGray", A) {X("end_fan", X_E2)}',
          f' color("Orange", 0.8) translate([{X_D2 + T + 0.5:.3f},{T + PLATE_U0:.3f},EXPLODE*40]) rotate([90,0,90]) damper_plate();',
          f' color("Gold", 0.7) translate([{X_D2 + T:.3f},{T:.3f},5]) rotate([90,0,90]) guide_spacer_1();',
          f' color("Gold", 0.7) translate([{X_D2 + T:.3f},{T + W - GUIDE_W:.3f},5]) rotate([90,0,90]) guide_spacer_2();',
          f' color("Gold", 0.7) translate([{X_D2 + 2*T:.3f},{T:.3f},5]) rotate([90,0,90]) guide_cover_1();',
          f' color("Gold", 0.7) translate([{X_D2 + 2*T:.3f},{T + W - COVER_W:.3f},5]) rotate([90,0,90]) guide_cover_2();',
          f' color("White", A) translate([0,0,{H} + EXPLODE*60]) lid_electronics();',
          f' color("White", A) translate([{lx1:.3f},0,{H} + EXPLODE*60]) lid_terrarium();',
          f' color("White", A) translate([{lx2:.3f},0,{H} + EXPLODE*60]) lid_air();',
          f' color("Tomato", 0.8) translate([{lx1 + FAN_U:.3f},{WO/2 - 28:.3f},{H - 70} + EXPLODE*60]) rotate([90,0,90]) fan_bracket();',
          f' color("DarkSeaGreen", 0.8) translate([{T + 3:.3f},{T + 5:.3f},8]) electronics_tray();',
          '}', 'assembly();']
    open(path, 'w').write('\n'.join(s) + '\n')


# ------------------------------------------------------------ main -------------
if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    cut = os.path.join(here, 'cut-files'); per = os.path.join(here, 'onshape-dxf-per-part')
    for d in (cut, per): os.makedirs(d, exist_ok=True)
    for sheet in LAYOUT:
        check_sheet(sheet)
        g = list(placed_geometry(sheet)); wh = SHEET_SIZE[sheet]
        base = os.path.join(cut, f'sheet_{sheet}')
        write_svg(base + '.svg', wh, g); write_dxf(base + '.dxf', g); write_pdf(base + '.pdf', wh, g)
        shutil.copyfile(base + '.pdf', base + '.ai')            # Illustrator opens PDF-format .ai natively
        write_pdf(os.path.join(here, f'PART-MAP_sheet_{sheet}.pdf'), wh, g, labels=True)
        write_svg(os.path.join(here, f'PART-MAP_sheet_{sheet}.svg'), wh, g, labels=True)
    for name, p in PARTS.items():
        if name.startswith('lid_locator') and name != 'lid_locator_01': continue
        if name.endswith('_2'): continue
        write_dxf(os.path.join(per, f'{name}.dxf'), [(name, p['pts'], p['holes'])])
    write_scad(os.path.join(here, 'acrylic-assembly.scad'))
    print(f'outer box  {L_TOT + 2*M:.0f} x {WO + 2*M:.0f} x {H + 2*T:.0f} mm   '
          f'= {(L_TOT + 2*M)/304.8:.2f} x {(WO + 2*M)/304.8:.2f} x {(H + 2*T)/304.8:.2f} ft')
    print(f'terrarium bay inner {L_TERR:.0f} x {W:.0f} x {H:.0f} mm; damper rows {N_ROWS}; parts {len(PARTS)}')
    for n, p in PARTS.items():
        b = bbox(p['pts']); print(f'  {n:22s} {b[2]-b[0]:6.1f} x {b[3]-b[1]:6.1f}  t={p["t"]}')
