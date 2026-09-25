"""
Runs the same simulated 76 hours twice - once with the brain, once with the
current firmware rules - and saves a figure plus a results table.

SIMULATION ONLY. It shows the brain's logic works; it is not evidence for the
paper. The paper's numbers come from the real box.
"""
import os, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sim_box import Box
from brain import Brain, Rules, I_MIST1

H = 3600
END = 76 * H
LEARN = 8
FAULTS = [  # (name, start h, end h)
    ('lid open', 52.0, 52.67),
    ('main mister dead', 58.0, 60.0),
    ('sensor stuck', 64.0, 65.0),
    ('fan stalled', 70.0, 71.5),
]
DRIFT = (30.0, 50.0, 0.70)   # main disc wears to 70 % between 30 h and 50 h
GLITCH = 45.0                # brain memory corrupted on purpose


def fan_on(t):
    return 1 if (t % 1200) < 60 else 0     # ventilation: 60 s every 20 min


def apply_faults(box, t):
    h = t / H
    a, b, g = DRIFT
    box.mist_gain = 1.0 if h < a else (g if h > b else 1.0 - (1.0 - g) * (h - a) / (b - a))
    box.leak_mult = 8.0 if FAULTS[0][1] <= h < FAULTS[0][2] else 1.0
    box.main_dead = FAULTS[1][1] <= h < FAULTS[1][2]
    box.sensor_stuck = FAULTS[2][1] <= h < FAULTS[2][2]
    box.fan_dead = FAULTS[3][1] <= h < FAULTS[3][2]


def run(use_brain, seed=7):
    box = Box(seed=seed)
    brain, rules = Brain(learn_hours=LEARN), Rules()
    main = backup = 0
    rows, glitched = [], False
    for t in range(END):
        apply_faults(box, t)
        if t % 5 == 0:
            rh, temp = box.read()
            fan = fan_on(t)
            if use_brain:
                if not glitched and t >= GLITCH * H:
                    brain.slow.theta[I_MIST1] = brain.slow.theta[I_MIST1 + 1] = 0.0   # corrupt
                    glitched = True
                main, backup = brain.step(t, rh, temp, fan, lambda k, t0=t: fan_on(t0 + 5 * k))
            else:
                rules.step(t, rh)
                main, backup = rules.cmd, 0
            rows.append((t, box.step(main, backup, fan), main or backup))
            for _ in range(4):
                box.step(main, backup, fan_on(t))
    return rows, (brain if use_brain else None)


def metrics(rows, windows):
    def pick(sel):
        return [r for r in rows if sel(r[0] / H)]
    healthy = pick(lambda h: h >= LEARN and not any(s <= h < e + 0.5 for _, s, e in windows))
    days = len(healthy) * 5 / 86400
    starts = sum(1 for a, b in zip(healthy, healthy[1:]) if b[2] and not a[2])
    out = dict(
        in_band_pct=100 * sum(75 <= r[1] <= 90 for r in healthy) / len(healthy),
        above_90_pct=100 * sum(r[1] > 90 for r in healthy) / len(healthy),
        mist_starts_per_day=starts / days,
        mist_minutes_per_day=sum(r[2] for r in healthy) * 5 / 60 / days,
    )
    for name, s, e in windows:
        w = pick(lambda h: s <= h < e)
        out['in_band_during_' + name.replace(' ', '_')] = 100 * sum(75 <= r[1] <= 90 for r in w) / len(w)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rb, brain = run(True)
    rr, _ = run(False)
    mb, mr = metrics(rb, FAULTS), metrics(rr, FAULTS)
    delays = {}
    for name, s, e in FAULTS:
        hit = [(t, txt) for t, txt in brain.events if t >= s * H and t < (e + 0.5) * H and 'FAULT' in txt]
        delays[name] = (round((hit[0][0] - s * H) / 60, 1), hit[0][1]) if hit else (None, 'missed')
    result = dict(brain=mb, rules=mr, detection_minutes=delays,
                  events=[(round(t / H, 2), x) for t, x in brain.events])
    print(json.dumps(result, indent=1))
    with open(os.path.join(here, 'demo_results.json'), 'w') as f:
        json.dump(result, f, indent=1)

    # ------------------------------------------------------------------ figure
    ink, ink2, grid, surf = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
    blue, orange, aqua = '#2a78d6', '#eb6834', '#1baf7a'
    plt.rcParams.update({'font.size': 9, 'text.color': ink, 'axes.labelcolor': ink2,
                         'xtick.color': ink2, 'ytick.color': ink2, 'axes.edgecolor': grid})
    fig, ax = plt.subplots(4, 1, figsize=(11, 10.5), sharex=True, facecolor=surf,
                           gridspec_kw=dict(height_ratios=[1.2, 1.2, 1, 1.1]))
    hb = [r[0] / H for r in rb]
    base = brain.baseline_mist
    lg = brain.log
    lh = [r['t'] / H for r in lg]
    for a in ax:
        a.set_facecolor(surf)
        a.grid(axis='y', color=grid, lw=0.6)
        for sp in ('top', 'right'):
            a.spines[sp].set_visible(False)
        a.axvspan(0, LEARN, color='#efeee9', lw=0)
        for name, s, e in FAULTS:
            a.axvspan(s, e, color='#dcdad3', lw=0)
        a.axvspan(DRIFT[0], DRIFT[1], ymin=0, ymax=0.04, color='#c9c7bf', lw=0)
    for a, rows, col, title in ((ax[0], rb, blue, 'With the brain'), (ax[1], rr, orange, 'Current rules (75/90 % on/off)')):
        a.axhspan(75, 90, color=blue if col == blue else orange, alpha=0.07, lw=0)
        a.plot([r[0] / H for r in rows], [r[1] for r in rows], color=col, lw=0.7)
        a.set_ylim(55, 100)
        a.set_ylabel('true humidity, %RH')
        a.set_title(title, loc='left', fontsize=10, color=ink)
    for i, (name, s, e) in enumerate(FAULTS):
        ax[0].text((s + e) / 2, 98.5 - 4.5 * (i % 2), name, ha='center', va='top', fontsize=7.5, color=ink2)
    ax[0].text((DRIFT[0] + DRIFT[1]) / 2, 57, 'main disc slowly wears to 70 %', ha='center', fontsize=7.5, color=ink2)
    ax[0].text(LEARN / 2, 98.5, 'learning\n(old rules)', ha='center', va='top', fontsize=7.5, color=ink2)
    ax[0].text(GLITCH + 0.4, 61, 'memory glitch', ha='left', fontsize=7.5, color=ink2)
    ax[0].axvline(GLITCH, color=ink2, lw=0.8, ls=':')
    ax[2].plot(lh, [100 * r['mist_slow'] / base if base and r['t'] >= LEARN * H else None for r in lg], color=blue, lw=1.4, label='slow learner (healthy-box memory)')
    ax[2].plot(lh, [100 * r['mist_fast'] / base if base and r['t'] >= LEARN * H else None for r in lg], color=aqua, lw=0.8, label='fast learner (right now)')
    truth = []
    for r in lg:
        h = r['t'] / H
        a0, b0, g0 = DRIFT
        gain = 1.0 if h < a0 else (g0 if h > b0 else 1 - (1 - g0) * (h - a0) / (b0 - a0))
        if FAULTS[1][1] <= h < FAULTS[1][2] and r['active'] == 'main':
            gain = 0.0
        if r['active'] == 'backup':
            gain = 0.8
        truth.append(100 * gain)
    ax[2].plot(lh, truth, color=ink2, lw=1, ls='--', label='true strength of the disc in use')
    ax[2].set_ylim(-5, 160)
    ax[2].set_ylabel('mister strength, % of day-1')
    ax[2].set_title('What the brain believes about the mister', loc='left', fontsize=10)
    ax[2].legend(loc='upper left', frameon=False, fontsize=8, ncol=3)
    # what the brain decided, one row per state, vs the true fault windows
    states = ['suspect loss', 'lid open / leak', 'main mister dead', 'sensor stuck', 'fan stalled']
    for row, st_name in enumerate(states):
        on = None
        for r in lg + [dict(t=END, fault='')]:
            if r['fault'] == st_name and on is None:
                on = r['t'] / H
            elif r['fault'] != st_name and on is not None:
                ax[3].plot([on, r['t'] / H], [row, row], color=blue, lw=6, solid_capstyle='butt')
                on = None
    for when, txt in brain.events:
        if 'rolled back' in txt or 'maintenance' in txt:
            y = -1 if 'rolled' in txt else -2
            ax[3].plot([when / H], [y], marker='o', ms=6, color=blue)
    ax[3].set_yticks(range(-2, len(states)))
    ax[3].set_yticklabels(['wear warning', 'memory restored'] + states)
    ax[3].set_ylim(-2.7, len(states) - 0.3)
    ax[3].grid(axis='y', visible=False)
    ax[3].set_title('What the brain decided (bars) against the real faults (grey)', loc='left', fontsize=10)
    ax[3].set_xlabel('simulated hours')
    ax[3].set_xlim(0, END / H)
    fig.suptitle('Terrarium brain on a SIMULATED box (logic test, not experimental data)', x=0.01, ha='left', fontsize=11, color=ink)
    fig.tight_layout()
    out = os.path.join(here, '..', '..', 'docs', 'figures')
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, 'brain-sim-demo.png'), dpi=140, facecolor=surf)
    print('figure saved')


if __name__ == '__main__':
    main()
