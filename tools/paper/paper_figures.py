"""
Column-width figures for the paper (IEEE two-column: 3.38 in wide), drawn at final size
so that text prints at 7 pt. Uses the paper's terms ("rule", "learning"), not the lab's.

  python tools/paper/paper_figures.py
    -> docs/figures/paper-fig1-system.png
       docs/figures/paper-fig2-fault-session.png
       docs/figures/paper-fig3-evening-session.png
"""
import csv, os, re, datetime as dt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA, FIG = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'docs', 'figures')
W = 3.38                      # column width, inches
INK, INK2, GRID = '#1b1b1b', '#555555', '#e2e2de'
IN_C, OUT_C, MIST_C, BAND_C = '#1f5fbf', '#d9772b', '#cfe0f6', '#f1f1ee'
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 7,
                     'axes.labelsize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'axes.edgecolor': INK2,
                     'axes.linewidth': 0.6, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5})
T = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')


def load(name):
    rows, events = [], []
    for r in csv.DictReader(open(os.path.join(DATA, name))):
        if r['ms']:
            if r['in_ok'] == '1':
                rows.append((T(r['pc_time']), float(r['rh_in']), float(r['rh_out']) if r['out_ok'] == '1' else None,
                             r['mistA'] == '1' or r['mistB'] == '1'))
    ev = os.path.join(DATA, name.replace('.csv', '.events.txt'))
    if os.path.exists(ev):
        for line in open(ev, encoding='utf-8', errors='replace'):
            m = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)  \[[^\]]*\]  (.*)', line.rstrip())
            if m:
                events.append((T(m.group(1)), m.group(2)))
    return rows, events


def style(ax):
    ax.grid(axis='y', color=GRID, lw=0.5)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


def shade_mist(ax, rows, t0):
    on = None
    for t, _, _, m in rows:
        x = (t - t0).total_seconds() / 60
        if m and on is None:
            on = x
        if not m and on is not None:
            ax.axvspan(on, x, color=MIST_C, lw=0, zorder=0); on = None
    if on is not None:
        ax.axvspan(on, (rows[-1][0] - t0).total_seconds() / 60, color=MIST_C, lw=0, zorder=0)


def trace(ax, rows, t0):
    x = [(t - t0).total_seconds() / 60 for t, *_ in rows]
    ax.plot(x, [r[1] for r in rows], color=IN_C, lw=0.6, zorder=3)
    xo = [(t - t0).total_seconds() / 60 for t, _, o, _ in rows if o is not None]
    ax.plot(xo, [o for _, _, o, _ in rows if o is not None], color=OUT_C, lw=0.6, zorder=3)


# ----------------------------------------------------------------- Fig. 1
def fig_system():
    fig, ax = plt.subplots(figsize=(W, 2.75)); ax.set_xlim(0, 10); ax.set_ylim(0, 8.1); ax.axis('off')

    def box(x, y, w, h, text, fc='white', fs=6.3, ec=INK2, ls='-'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.12', fc=fc, ec=ec, lw=0.6, ls=ls))
        if text:
            ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, linespacing=1.15, color=INK)

    def arrow(x1, y1, x2, y2, label='', lx=None, ly=None, ha='center'):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=6, lw=0.6, color=INK))
        if label:
            ax.text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2, label,
                    fontsize=5.8, color=INK2, ha=ha, va='center')

    # enclosure band (top)
    box(0.1, 5.35, 9.8, 2.6, '', fc='#eef3fa', ec='#7a8aa6', ls='--')
    ax.text(0.3, 7.7, 'Enclosure (lid propped open 1 or 4 cm)', fontsize=6.3, color='#3a4a66', va='center')
    box(0.35, 5.55, 2.95, 1.75, 'BME280 control\nsensor 0x76,\nhigh, shielded')
    box(3.55, 5.55, 2.95, 1.75, 'Ultrasonic mist\nmaker, 5 V disc\nin a water tray')
    box(6.75, 5.55, 2.95, 1.75, 'Air: leak through\nthe gap, water\nsurface, walls')
    # ESP32 row (middle)
    box(0.35, 3.05, 2.55, 1.55, 'BME280 reference\n0x77, on bench')
    box(3.55, 3.05, 6.15, 1.55, 'ESP32 laboratory firmware: 1 Hz sampling,\nvalidity filter, safety limits, watchdog', fc='#fff7e6')
    # controller band (bottom)
    box(0.1, 0.1, 9.8, 2.45, '', fc='#f0f8f2', ec='#5f8f6e', ls='--')
    ax.text(0.3, 2.3, 'Controller (laptop over USB in this study)', fontsize=6.3, color='#2f5e3d', va='center')
    box(0.35, 0.3, 2.95, 1.65, 'Model: 6 weights,\ndual-timescale RLS')
    box(3.55, 0.3, 2.95, 1.65, 'Burst planner:\nshortest burst\nto 88 % predicted')
    box(6.75, 0.3, 2.95, 1.65, 'Fault logic: checks,\nCUSUM, quiet-then-\nmist test, rollback')
    # arrows
    arrow(1.82, 5.55, 4.4, 4.6, 'I2C', lx=3.0, ly=4.98, ha='right')
    arrow(2.9, 3.82, 3.55, 3.82)
    ax.text(3.22, 4.12, 'I2C', fontsize=5.8, color=INK2, ha='center')
    arrow(5.02, 4.6, 5.02, 5.55, 'GPIO', lx=5.25, ly=5.08, ha='left')
    arrow(7.9, 3.05, 7.9, 2.55, 'RH, T (1 Hz)', lx=8.08, ly=2.8, ha='left')
    arrow(4.6, 2.55, 4.6, 3.05, 'mist on/off (5 s)', lx=4.42, ly=2.8, ha='right')
    arrow(3.3, 1.12, 3.55, 1.12); arrow(6.5, 1.12, 6.75, 1.12)
    fig.subplots_adjust(0, 0, 1, 1)
    out = os.path.join(FIG, 'paper-fig1-system.png'); fig.savefig(out, dpi=300, facecolor='white'); plt.close(fig)
    return out


# ----------------------------------------------------------------- Fig. 2
def fig_fault_session():
    parts = ['lab-baseline-2026-09-26-1034.csv', 'lab-brain-2026-09-26-2237.csv', 'lab-brain-2026-09-26-2314.csv']
    rows, events = [], []
    for p in parts:
        r, e = load(p); rows += r; events += e
    t0 = T('2026-09-26 22:22:00')
    rows = [r for r in rows if r[0] >= t0]
    rows.sort(key=lambda r: r[0])
    fig, ax = plt.subplots(figsize=(W, 2.2)); style(ax)
    ax.axhspan(75, 90, color=BAND_C, lw=0, zorder=0)
    shade_mist(ax, rows, t0); trace(ax, rows, t0)
    m = lambda s: (T('2026-09-26 ' + s) - t0).total_seconds() / 60
    # controller spans
    for x0, x1, lab in [(m('22:22:00'), m('22:37:09'), 'rule'), (m('22:37:09'), m('23:24:40'), 'learning')]:
        ax.annotate('', xy=(x0, 99), xytext=(x1, 99), arrowprops=dict(arrowstyle='<->', lw=0.5, color=INK2))
        ax.text((x0 + x1) / 2, 99.6, lab, ha='center', va='bottom', fontsize=6.3, color=INK2)
    ax.axvspan(m('23:12:50'), m('23:14:36'), color='#e7e7e7', lw=0, zorder=1)
    marks = [('1', '23:02:11'), ('2', '23:10:47'), ('3', '23:12:50'), ('4', '23:16:30')]
    for lab, s in marks:
        ax.axvline(m(s), color='#a12b2b', lw=0.6, ls=':', zorder=2)
        ax.text(m(s), 64.6 if lab == '3' else 61.2, lab, ha='center', va='bottom', fontsize=6.3, color='#a12b2b',
                bbox=dict(boxstyle='circle,pad=0.15', fc='white', ec='#a12b2b', lw=0.5))
    verdicts = [('S', '23:02:12'), ('L', '23:08:51'), ('S', '23:16:37'), ('F', '23:23:03')]
    for lab, s in verdicts:
        ax.annotate(lab, xy=(m(s), 92.5), xytext=(m(s), 95.2), ha='center', fontsize=6.3, color='#1b7a4c', fontweight='bold',
                    arrowprops=dict(arrowstyle='-|>', lw=0.5, color='#1b7a4c', mutation_scale=5))
    ax.set_ylim(60, 102); ax.set_xlim(0, (rows[-1][0] - t0).total_seconds() / 60)
    ax.set_ylabel('RH, %'); ax.set_xlabel('minutes from 22:22')
    ax.text(0.8, 65.5, 'outside', color=OUT_C, fontsize=6.3); ax.text(20, 84.2, 'inside', color=IN_C, fontsize=6.3)
    fig.tight_layout(pad=0.3)
    out = os.path.join(FIG, 'paper-fig2-fault-session.png'); fig.savefig(out, dpi=300, facecolor='white'); plt.close(fig)
    return out


# ----------------------------------------------------------------- Fig. 3
def fig_evening_session():
    blocks = [('lab-brain-2026-09-27-2003.csv', 'L'), ('lab-baseline-2026-09-27-2033.csv', 'R'),
              ('lab-brain-2026-09-27-2103.csv', 'L'), ('lab-baseline-2026-09-27-2133.csv', 'R'),
              ('lab-brain-2026-09-27-2203.csv', 'L')]
    rows, starts = [], []
    for name, lab in blocks:
        r, e = load(name)
        if lab == 'R':
            mr = [t for t, s in e if 'mode RULES' in s]
            if mr:
                r = [x for x in r if x[0] >= mr[-1]]
        starts.append((r[0][0], lab)); rows += r
    rows.sort(key=lambda r: r[0]); t0 = rows[0][0]
    fig, ax = plt.subplots(figsize=(W, 2.1)); style(ax)
    ax.axhspan(75, 90, color=BAND_C, lw=0, zorder=0)
    shade_mist(ax, rows, t0)
    dm0 = (T('2026-09-27 22:09:48') - t0).total_seconds() / 60
    dm1 = (T('2026-09-27 22:21:48') - t0).total_seconds() / 60
    plt.rcParams['hatch.linewidth'] = 0.35
    ax.axvspan(dm0, dm1, facecolor='none', edgecolor='#c77d7d', hatch='//////', lw=0, zorder=1)
    trace(ax, rows, t0)
    ends = [s for s, _ in starts[1:]] + [rows[-1][0]]
    for (s, lab), e in zip(starts, ends):
        x0, x1 = (s - t0).total_seconds() / 60, (e - t0).total_seconds() / 60
        if x0 > 0:
            ax.axvline(x0, color=INK2, lw=0.5, ls='--', zorder=2)
        ax.text((x0 + x1) / 2, 93.3, 'learning' if lab == 'L' else 'rule', ha='center', fontsize=6.3, color=INK2)
    ax.text((dm0 + dm1) / 2, 62.2, 'dead mister', ha='center', fontsize=6, color='#a12b2b',
            bbox=dict(boxstyle='square,pad=0.15', fc='white', ec='none'))
    ax.set_ylim(60, 97); ax.set_xlim(0, (rows[-1][0] - t0).total_seconds() / 60)
    ax.set_ylabel('RH, %'); ax.set_xlabel('minutes from 20:03')
    ax.text(1, 66.3, 'outside', color=OUT_C, fontsize=6.3); ax.text(1, 84.2, 'inside', color=IN_C, fontsize=6.3)
    fig.tight_layout(pad=0.3)
    out = os.path.join(FIG, 'paper-fig3-evening-session.png'); fig.savefig(out, dpi=300, facecolor='white'); plt.close(fig)
    return out


if __name__ == '__main__':
    for f in (fig_system(), fig_fault_session(), fig_evening_session()):
        print('wrote', os.path.relpath(f, ROOT))
