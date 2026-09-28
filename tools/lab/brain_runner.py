"""
Runs the brain (tools/brain/brain.py) on the REAL box from the laptop.

The lab firmware streams readings at 1 Hz; every 5 s the brain gets the inside
sensor, decides the mist command, and the laptop sends MIST A/B over USB.
Everything is recorded like logger.py (same CSV, same live page on :8765),
plus a brain log next to it with the model's weights, error and fault state.

  python tools/lab/brain_runner.py --minutes 40 [--seed data/lab-step-2026-09-25-1910.csv]

The brain is pre-taught from a step-test CSV (least squares on the same
features it learns with), so it acts from the first minute and only fine-tunes.
MARKs go through data/lab-cmd.txt as usual (e.g. "MARK mister unplugged");
data/STOP ends the run with the mist off.
"""
import argparse, csv, datetime as dt, json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'brain'))
from logger import Board, serve, stopped, DATA, STOP_FILE
from brain import Brain, RLS, features, DT, N, I_MIST1, I_AH
from sim_box import ah_from_rh


def seed_from_csv(path, brain):
    """Fit the six weights to a recorded run, resampled to the brain's 5 s step."""
    rows = [r for r in csv.DictReader(open(path)) if r['ms'] and r['in_ok'] == '1']
    pts = []
    for r in rows[::int(DT)]:
        pts.append((int(r['ms']) / 1000.0, float(r['rh_in']), float(r['t_in']), 1.0 if r['mistA'] == '1' or r['mistB'] == '1' else 0.0))
    fit = RLS(lam=1.0, p0=100.0, beta=1e-9)
    mf1 = mf2 = 0.0
    prev = None
    n = 0
    for _ in range(3):                       # three passes: recursive least squares converges to the batch fit
        mf1 = mf2 = 0.0; prev = None
        for t, rh, temp, u in pts:
            ah = ah_from_rh(rh, temp)
            if prev is not None and t - prev[2] < 2 * DT:
                phi, ah_prev, _ = prev
                fit.update(phi, ah - ah_prev, 1.0); n += 1
            mf1 += (u - mf1) * DT / 5.0
            mf2 += (u - mf2) * DT / 30.0
            prev = (features(ah, rh, mf1, mf2, 0.0), ah, t)
    for r in (brain.slow, brain.fast, brain.snapshot):
        r.theta = list(fit.theta)
        # the seed is trusted: start with a small covariance so the first minutes of closed-loop
        # data fine-tune the weights instead of overwriting them (a large p0 made the mister weight
        # jump within 10 s and trip the wear warning at the start of a run)
        r.P = [[(0.05 if i == j else 0.0) for j in range(N)] for i in range(N)]
    return fit.theta, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='COM3')
    ap.add_argument('--minutes', type=float, default=40)
    ap.add_argument('--seed', default=os.path.join(DATA, 'lab-step-2026-09-25-1910.csv'))
    ap.add_argument('--http', type=int, default=8765)
    ap.add_argument('--lo', type=float, default=75); ap.add_argument('--hi', type=float, default=90)
    ap.add_argument('--dead-mister', nargs=2, type=float, metavar=('START_MIN', 'DUR_MIN'), default=None,
                    help='software fault: from START_MIN for DUR_MIN the mist commands are dropped (mister effectively dead)')
    a = ap.parse_args()
    if stopped():
        os.remove(STOP_FILE)
    stamp = f'{dt.datetime.now():%Y-%m-%d-%H%M}'
    path = os.path.join(DATA, f'lab-brain-{stamp}.csv')
    blog_path = os.path.join(DATA, f'lab-brain-{stamp}.brain.csv')

    brain = Brain(learn_hours=0.0, lo=a.lo, hi=a.hi)
    theta, n = seed_from_csv(a.seed, brain)
    print('seeded from', os.path.basename(a.seed), f'({n} steps):', ' '.join(f'{x:.4f}' for x in theta))

    if a.http: serve(a.http)
    b = Board(a.port, path)
    b.note(f'BRAIN runner: seed weights {[round(x, 4) for x in theta]} (mist {theta[I_MIST1]:.4f} g/m3 per step, leak {-theta[I_AH] / DT:.2e} /s)')
    b.send('HEADER'); b.send('SET man=400'); b.send('MODE MANUAL'); b.pump(2)
    b.phase = 'brain'; b.send('MARK brain block start')

    blog = open(blog_path, 'w', newline='')
    bw = csv.writer(blog)
    bw.writerow(['pc_time', 't_s', 'rh_in', 'temp_in', 'sensor_ok', 'cmd_main', 'cmd_backup', 'mode', 'burst_left_s',
                 'fault', 'z', 'sigma', 'mist_slow', 'mist_fast', 'leak_slow_per_s', 'leak_fast_per_s', 'active'])
    cmd_prev, last_ms, n_ev, t0 = None, None, 0, time.time()
    t_offset, last_t = 0.0, 0.0
    dead_prev = False
    try:
        while not stopped() and time.time() - t0 < a.minutes * 60:
            b.pump(1)
            r = b.last
            if not r:
                continue
            ms = int(r['ms'])
            if last_ms is not None and ms < last_ms:            # board rebooted (watchdog / power): re-arm manual mode
                b.note('board restarted (uptime went backwards): re-sending MODE MANUAL, brain keeps its memory')
                b.send('SET man=400'); b.send('MODE MANUAL'); last_ms = None; cmd_prev = None; t_offset += last_t
            if last_ms is not None and ms - last_ms < DT * 1000 - 100:
                continue
            last_ms = ms
            ok = r['in_ok'] == '1'
            rh = float(r['rh_in']) if ok else None
            temp = float(r['t_in']) if ok else None
            if brain.last_good is None and not ok:
                continue                                    # need one good reading before the brain can run blind
            t = t_offset + ms / 1000.0; last_t = ms / 1000.0
            main, backup = brain.step(t, rh, temp, 0, lambda k: 0)
            # software fault injection: the brain commands the mist, but nothing reaches the box
            el_min = (time.time() - t0) / 60
            dead = a.dead_mister is not None and a.dead_mister[0] <= el_min < a.dead_mister[0] + a.dead_mister[1]
            if dead and not dead_prev:
                b.send('MARK FAULT dead mister injected: mist commands dropped from now (brain does not know)')
            if dead_prev and not dead:
                b.send('MARK FAULT dead mister cleared: commands pass again')
            dead_prev = dead
            phys = (0, 0) if dead else (main, backup)
            if phys != cmd_prev:
                b.send(f'MIST A {phys[0]}'); b.send(f'MIST B {phys[1]}')
                cmd_prev = phys
            for when, text in brain.events[n_ev:]:
                b.note(f'BRAIN: {text}')
            n_ev = len(brain.events)
            L = brain.log[-1]
            bw.writerow([b.now(), f'{t:.0f}', '' if rh is None else f'{rh:.2f}', '' if temp is None else f'{temp:.2f}', int(ok),
                         main, backup, brain.mode, f'{max(0.0, brain.until - t):.0f}', brain.fault or '', f"{L['z']:.2f}",
                         f'{brain.sigma:.3f}', f"{L['mist_slow']:.4f}", f"{L['mist_fast']:.4f}", f"{L['leak_slow']:.2e}",
                         f"{L['leak_fast']:.2e}", brain.active])
            blog.flush()
    except KeyboardInterrupt:
        b.note('stopped by keyboard')
    finally:
        b.phase = 'end'
        b.send('MIST A 0'); b.send('MIST B 0'); b.send('MODE OFF'); b.send('STATUS'); b.pump(2)
        b.note('END brain block. weights now: ' + ' '.join(f'{x:.4f}' for x in brain.slow.theta))
        blog.close()
        with open(blog_path.replace('.brain.csv', '.brain.json'), 'w') as f:
            json.dump(dict(seed=theta, final_slow=brain.slow.theta, final_fast=brain.fast.theta,
                           events=[(round(t, 1), x) for t, x in brain.events]), f, indent=1)
        if stopped():
            os.remove(STOP_FILE)


if __name__ == '__main__':
    main()
