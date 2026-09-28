"""
Summarise one evening of lab runs: every lab-*.csv given on the command line
(rules blocks and brain blocks), in time order, one figure and one table.

  python tools/lab/analyze_session.py data/lab-baseline-2026-09-26-1034.csv data/lab-brain-2026-09-26-2237.csv ...

Metrics per block (only rows with a good inside reading): time in the 75-90 %
band, above 90 %, mist minutes, mist switch-ons, and for brain blocks the
delay from each "MARK FAULT ..." line to the brain's "FAULT:" verdict.
"""
import csv, datetime as dt, os, re, sys, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LO, HI = 75.0, 90.0


def load(path):
    rows, events = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            t = dt.datetime.strptime(r['pc_time'], '%Y-%m-%d %H:%M:%S')
            if r['ms']:
                if r['in_ok'] == '1':
                    rows.append(dict(t=t, phase=r['phase'], hi=float(r['rh_in']), ho=float(r['rh_out']) if r['out_ok'] == '1' else None,
                                     ti=float(r['t_in']), mist=r['mistA'] == '1' or r['mistB'] == '1'))
            elif r['event']:
                events.append((t, r['phase'], r['event']))
    # the runner's own notes (BRAIN verdicts, MARK lines) live in the .events.txt next to the CSV
    ev_path = path.replace('.csv', '.events.txt')
    if os.path.exists(ev_path):
        for line in open(ev_path):
            m = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)  \[([^\]]*)\]  (.*)', line.rstrip())
            if m and ('BRAIN' in m.group(3) or m.group(3).startswith('>> MARK') or 'mode RULES' in m.group(3) or 'restarted' in m.group(3)):
                events.append((dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S'), m.group(2), m.group(3).replace('>> ', '')))
    events.sort(key=lambda e: e[0])
    return rows, events


def block_metrics(rows, name):
    if not rows:
        return None
    n = len(rows)
    sw = sum(1 for a, b in zip(rows, rows[1:]) if b['mist'] and not a['mist']) + (1 if rows[0]['mist'] else 0)
    span = (rows[-1]['t'] - rows[0]['t']).total_seconds() / 60
    return dict(block=name, start=rows[0]['t'].strftime('%H:%M'), minutes=round(span, 1),
                in_band_pct=round(100 * sum(LO <= r['hi'] <= HI for r in rows) / n, 1),
                above_hi_pct=round(100 * sum(r['hi'] > HI for r in rows) / n, 1),
                below_lo_pct=round(100 * sum(r['hi'] < LO for r in rows) / n, 1),
                mist_min=round(sum(r['mist'] for r in rows) / 60, 1), switch_ons=sw,
                rh_min=round(min(r['hi'] for r in rows), 1), rh_max=round(max(r['hi'] for r in rows), 1))


def fault_delays(events):
    out = []
    marks = [(t, e) for t, _, e in events if e.startswith('MARK') and 'FAULT' in e]
    verdicts = [(t, e) for t, _, e in events if 'BRAIN: FAULT' in e or ('FAULT:' in e and 'MARK' not in e)]
    seen = set()
    for tm, em in marks:
        key = (' '.join(em.split()), tm.strftime('%H:%M'))   # the same MARK appears twice: sent and echoed
        if key in seen:
            continue
        seen.add(key)
        after = [(tv, ev) for tv, ev in verdicts if tv >= tm]
        for tv, ev in after[:3]:
            out.append(dict(injected=em.replace('MARK', '').strip(), at=tm.strftime('%H:%M:%S'),
                            verdict=ev.split('FAULT:')[-1].strip(), delay_s=int((tv - tm).total_seconds())))
    return out


def main():
    files = sys.argv[1:]
    blocks, all_rows, all_events = [], [], []
    for p in files:
        rows, ev = load(p)
        base = os.path.basename(p)
        name = 'rules' if 'baseline' in base else ('matched' if 'matchedrule' in base else 'brain')
        # a rules file may contain an OFF stretch before "mode RULES"; keep from that command on
        if name in ('rules', 'matched'):
            starts = [t for t, _, e in ev if 'mode RULES' in e]
            if starts:
                rows = [r for r in rows if r['t'] >= starts[-1]]
        m = block_metrics(rows, f"{name} {os.path.basename(p)[-8:-4]}")
        if m:
            m['faults'] = fault_delays(ev) if name == 'brain' else []
            blocks.append(m)
        all_rows += rows; all_events += ev
    all_rows.sort(key=lambda r: r['t'])
    print(f"{'block':14}{'start':>6}{'min':>6}{'in band%':>9}{'>90%':>6}{'<75%':>6}{'mist min':>9}{'switch':>7}{'RH min':>7}{'RH max':>7}")
    for m in blocks:
        print(f"{m['block']:14}{m['start']:>6}{m['minutes']:6.1f}{m['in_band_pct']:9.1f}{m['above_hi_pct']:6.1f}{m['below_lo_pct']:6.1f}{m['mist_min']:9.1f}{m['switch_ons']:7d}{m['rh_min']:7.1f}{m['rh_max']:7.1f}")
        for f in m['faults']:
            print(f"    fault: {f['injected']} at {f['at']} -> verdict '{f['verdict']}' after {f['delay_s']} s")
    out = files[0].rsplit('-', 1)[0] + '-session.json'
    with open(os.path.join(os.path.dirname(files[0]), f"session-{all_rows[0]['t']:%Y-%m-%d-%H%M}.json"), 'w') as f:
        json.dump(blocks, f, indent=1)

    # figure
    t0 = all_rows[0]['t']
    x = [(r['t'] - t0).total_seconds() / 60 for r in all_rows]
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True, facecolor='#fcfcfb', gridspec_kw=dict(height_ratios=[2, 1]))
    for a in ax:
        a.set_facecolor('#fcfcfb'); a.grid(axis='y', color='#e4e3df', lw=0.6)
        for sp in ('top', 'right'): a.spines[sp].set_visible(False)
    on = None
    for r, xx in zip(all_rows, x):
        if r['mist'] and on is None: on = xx
        if not r['mist'] and on is not None:
            ax[0].axvspan(on, xx, color='#dbe7f7', lw=0); on = None
    ax[0].axhspan(LO, HI, color='#2a78d6', alpha=0.06, lw=0)
    ax[0].plot(x, [r['hi'] for r in all_rows], color='#2a78d6', lw=0.8, label='inside')
    ax[0].plot([xx for r, xx in zip(all_rows, x) if r['ho'] is not None], [r['ho'] for r in all_rows if r['ho'] is not None], color='#eb6834', lw=0.8, label='outside')
    ax[0].set_ylabel('relative humidity, %'); ax[0].legend(loc='lower left', frameon=False)
    for t, ph, e in all_events:
        xx = (t - t0).total_seconds() / 60
        if t < t0:
            continue
        if 'mode RULES' in e:
            ax[0].axvline(xx, color='#52514e', lw=0.8, ls='--'); ax[0].text(xx + 0.3, 99, 'rules', fontsize=8, va='top')
        elif 'brain block start' in e and 'MARK' in e and '<<' not in e:
            ax[0].axvline(xx, color='#52514e', lw=0.8, ls='--'); ax[0].text(xx + 0.3, 99, 'brain', fontsize=8, va='top')
        elif e.startswith('MARK') and ('FAULT' in e or 'lid back' in e or 'removed' in e):
            ax[0].axvline(xx, color='#a12b2b', lw=0.8, ls=':'); ax[0].text(xx + 0.3, 62, e.replace('MARK', '').strip()[:28], fontsize=7, rotation=90, va='bottom', color='#a12b2b')
        elif 'BRAIN: FAULT' in e:
            ax[0].annotate(e.split('FAULT:')[-1].strip(), xy=(xx, 70), xytext=(xx + 0.5, 66), fontsize=8, color='#1baf7a',
                           arrowprops=dict(arrowstyle='-', color='#1baf7a', lw=0.8))
    ax[0].set_ylim(60, 100)
    ax[1].plot(x, [r['ti'] for r in all_rows], color='#2a78d6', lw=0.8)
    ax[1].set_ylabel('inside temperature, °C'); ax[1].set_xlabel(f'minutes from {t0:%H:%M}')
    faults = any('FAULT' in e for _, _, e in all_events)
    fig.suptitle(f"Lab session {t0:%Y-%m-%d}: old rule vs brain on the real box{', with injected faults' if faults else ', alternating 30 min blocks'} (blue = mist on)", x=0.01, ha='left')
    fig.tight_layout()
    png = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'figures', f'session-{t0:%Y-%m-%d-%H%M}.png')
    fig.savefig(png, dpi=140, facecolor='#fcfcfb'); print('figure:', os.path.normpath(png))


if __name__ == '__main__':
    main()
