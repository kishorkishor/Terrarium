"""
Fit the box model from a step-test CSV (tools/lab/logger.py --protocol step).

Per round: baseline drift, rise rate (absolute humidity), plateau, decay time
constant toward the outside air. Prints a table, writes <csv>.fit.json and a
figure docs/figures/<name>.png.

  python tools/lab/analyze_step.py data/lab-step-2026-09-25-1910.csv
"""
import csv, json, math, os, sys, re, datetime as dt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def ah_sat(t):
    es = 6.112 * math.exp(17.62 * t / (243.12 + t))
    return 216.7 * es / (273.15 + t)


def ah(rh, t):
    return rh / 100.0 * ah_sat(t)


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            if not r['ms'] or r['in_ok'] != '1' or r['out_ok'] != '1':
                continue
            try:
                rows.append(dict(t=dt.datetime.strptime(r['pc_time'], '%Y-%m-%d %H:%M:%S'), phase=r['phase'],
                                 ti=float(r['t_in']), hi=float(r['rh_in']), to=float(r['t_out']), ho=float(r['rh_out']),
                                 mist=r['mistA'] == '1' or r['mistB'] == '1'))
            except ValueError:
                pass
    return rows


def linfit(xs, ys):
    n = len(xs); sx = sum(xs); sy = sum(ys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    d = n * sxx - sx * sx
    return (n * sxy - sx * sy) / d if d else float('nan')


def analyse(rows):
    total = [r for r in rows]
    rounds = sorted({re.match(r'([AB]\d+)-', r['phase']).group(1) for r in rows if re.match(r'[AB]\d+-', r['phase'])})
    out = []
    for rd in rounds:
        base = [r for r in rows if r['phase'] == rd + '-baseline']
        rise = [r for r in rows if r['phase'] == rd + '-rise']
        dec = [r for r in rows if r['phase'] == rd + '-decay']
        if not (base and rise and dec):
            continue
        t0 = rise[0]['t']
        sec = lambda r: (r['t'] - t0).total_seconds()
        # baseline drift (%RH per min) over the quiet phase
        drift = linfit([sec(r) for r in base], [r['hi'] for r in base]) * 60
        # rise: AH slope over the first 60 s of misting, and the g = 1 - RH/100 factor at start
        r60 = [r for r in rise if sec(r) <= 60]
        slope = linfit([sec(r) for r in r60], [ah(r['hi'], r['ti']) for r in r60])
        g0 = max(0.02, 1 - rise[0]['hi'] / 100)
        plateau = max(r['hi'] for r in rise)
        # decay: fit ln(AH_in - AH_out) against time over the first 15 min
        td0 = dec[0]['t']
        pts = []
        for r in dec:
            s = (r['t'] - td0).total_seconds()
            d = ah(r['hi'], r['ti']) - ah(r['ho'], r['to'])
            if s <= 900 and d > 0.05:
                pts.append((s, math.log(d)))
        k = -linfit([p[0] for p in pts], [p[1] for p in pts]) if len(pts) > 30 else float('nan')
        rh_drop = dec[0]['hi'] - dec[-1]['hi']
        out.append(dict(round=rd, start_rh=rise[0]['hi'], plateau_rh=plateau, rise_s=sec(rise[-1]),
                        rise_ah_per_s=slope, k_mist_dry=slope / g0, baseline_drift_rh_per_min=drift,
                        decay_tau_s=1 / k if k and k > 0 else float('nan'), decay_rh_drop_20min=rh_drop,
                        outside_rh=sum(r['ho'] for r in dec) / len(dec), temp_in=sum(r['ti'] for r in rise) / len(rise),
                        cooling_c=rise[0]['ti'] - min(r['ti'] for r in dec)))
    return out


def figure(rows, fits, png):
    t0 = rows[0]['t']
    x = [(r['t'] - t0).total_seconds() / 60 for r in rows]
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, facecolor='#fcfcfb')
    for a in ax:
        a.set_facecolor('#fcfcfb'); a.grid(axis='y', color='#e4e3df', lw=0.6)
        for sp in ('top', 'right'): a.spines[sp].set_visible(False)
    on = None
    for r, xx in zip(rows, x):
        if r['mist'] and on is None: on = xx
        if not r['mist'] and on is not None:
            for a in ax: a.axvspan(on, xx, color='#dbe7f7', lw=0)
            on = None
    ax[0].plot(x, [r['hi'] for r in rows], color='#2a78d6', lw=0.9, label='inside (0x76)')
    ax[0].plot(x, [r['ho'] for r in rows], color='#eb6834', lw=0.9, label='outside (0x77)')
    ax[0].set_ylabel('relative humidity, %'); ax[0].legend(loc='lower right', frameon=False)
    ax[1].plot(x, [r['ti'] for r in rows], color='#2a78d6', lw=0.9)
    ax[1].plot(x, [r['to'] for r in rows], color='#eb6834', lw=0.9)
    ax[1].set_ylabel('temperature, °C'); ax[1].set_xlabel('minutes from start')
    for f in fits:
        ax[0].annotate(f"{f['round']}: peak {f['plateau_rh']:.1f} %, τ {f['decay_tau_s']/60:.0f} min", xy=(0, 0), xytext=(0, 0), alpha=0)
    fig.suptitle(f"Step test {rows[0]['t']:%Y-%m-%d}: one mist maker, measured at 1 Hz (blue = mist on)", x=0.01, ha='left')
    fig.tight_layout(); fig.savefig(png, dpi=140, facecolor='#fcfcfb')


def main():
    path = sys.argv[1]
    rows = load(path)
    with open(path) as f:
        n_all = sum(1 for r in csv.DictReader(f) if r['ms'])
    fits = analyse(rows)
    print(f"{len(rows)} good rows of {n_all} ({100*len(rows)/n_all:.1f} %)")
    print(f"{'round':6}{'start%':>8}{'peak%':>8}{'rise s':>8}{'k_mist':>8}{'tau min':>9}{'drop20':>8}{'out%':>7}{'cool C':>8}")
    for f in fits:
        print(f"{f['round']:6}{f['start_rh']:8.1f}{f['plateau_rh']:8.1f}{f['rise_s']:8.0f}{f['k_mist_dry']:8.3f}{f['decay_tau_s']/60:9.1f}{f['decay_rh_drop_20min']:8.1f}{f['outside_rh']:7.1f}{f['cooling_c']:8.2f}")
    if fits:
        mean = lambda k: sum(f[k] for f in fits) / len(fits)
        sd = lambda k: (sum((f[k] - mean(k)) ** 2 for f in fits) / max(1, len(fits) - 1)) ** 0.5
        summary = {k: dict(mean=mean(k), sd=sd(k)) for k in ('plateau_rh', 'k_mist_dry', 'decay_tau_s', 'rise_s', 'decay_rh_drop_20min', 'cooling_c')}
        print('\nmean ± sd:', {k: f"{v['mean']:.3f} ± {v['sd']:.3f}" for k, v in summary.items()})
    else:
        summary = {}
    with open(path.replace('.csv', '.fit.json'), 'w') as f:
        json.dump(dict(file=os.path.basename(path), good_rows=len(rows), all_rows=n_all, rounds=fits, summary=summary), f, indent=1)
    here = os.path.dirname(os.path.abspath(__file__))
    png = os.path.join(here, '..', '..', 'docs', 'figures', os.path.basename(path).replace('.csv', '.png'))
    figure(rows, fits, png); print('figure:', os.path.normpath(png))


if __name__ == '__main__':
    main()
