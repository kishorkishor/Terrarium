"""
1 cm lid-cycle test: does model-based burst sizing save mist on a tight enclosure?

With the lid propped only 1 cm the enclosure holds about 80 %RH by itself (measured 28 Sep, room 66 %),
above both controllers' 77 % trigger, so a plain run never mists. Each cycle therefore starts from a
dried enclosure:
  0. WAIT   nothing happens until the start button is pressed (or data/GO appears): someone must be at the box
  1. DRY    mist off; the live page asks for the lid to come off until the inside reading has been at
            or below the dry threshold for 15 s (threshold = min(76, max(73, outside + 3))); if the box has
            not dried within 30 min the test stops (a cycle never starts from an undried box)
  2. CLOSE  the page asks for the lid to go back with a 1 cm gap and the button to be pressed
            (or data/GO to be created); waits up to 20 min, else the test stops
  3. RUN    one controller for --block minutes (default 20):
              rule     = matched rule in the firmware: mist below 77 %, stop at 88 % or 300 s, rest 60 s
              learning = the learning controller on the laptop (5 s steps, seeded from the step test)
Cycles alternate rule, learning, rule, learning (--cycles, default 4). A 40 s fog check runs first so the
disc never runs dry. One CSV for the whole run (phase column = c<k>-dry / c<k>-close / c<k>-rule /
c<k>-learning), one .brain.csv per learning cycle, events in .events.txt, per-cycle metrics in
.cycles.json. The firmware's production settings (75/90 %, 300 s, 180 s) are restored at the end.

  python tools/lab/lid_cycle_test.py [--cycles 4] [--block 20] [--http 8766]
Stop early: create data/STOP (mist off, mode OFF, settings restored).
"""
import argparse, csv, datetime as dt, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'brain'))
from logger import Board, serve, stopped, DATA, STOP_FILE, LIVE, LIVE_LOCK
from brain_runner import seed_from_csv
from brain import Brain, DT

SEED = os.path.join(DATA, 'lab-step-2026-09-25-1910.csv')
GO_FILE = os.path.join(DATA, 'GO')


class Abort(Exception):
    pass


def prompt(text, await_go=False):
    with LIVE_LOCK:
        LIVE['prompt'] = text
        LIVE['await_go'] = await_go
        if await_go:
            LIVE['go'] = False


def go_pressed():
    if os.path.exists(GO_FILE):
        try:
            os.remove(GO_FILE)
        except OSError:
            pass
        return True
    with LIVE_LOCK:
        return LIVE['go']


def val(b, key, ok_key):
    r = b.last
    try:
        return float(r[key]) if r and r.get(ok_key) == '1' else None
    except (KeyError, ValueError):
        return None


def rh_in(b):
    return val(b, 'rh_in', 'in_ok')


def rh_out(b):
    return val(b, 'rh_out', 'out_ok')


def pump_for(b, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if stopped():
            raise Abort('STOP file')
        b.pump(1)


# ------------------------------------------------------------------ phases
def water_check(b):
    b.phase = 'water-check'
    b.send('SET man=60'); b.send('MODE MANUAL'); pump_for(b, 5)
    before = rh_in(b)
    if before is None:
        raise Abort('inside sensor not reading')
    peak = before
    b.send('MIST A 1')
    for _ in range(60):                      # 40 s mist + 20 s lag
        pump_for(b, 1)
        v = rh_in(b)
        if v is not None:
            peak = max(peak, v)
        if _ == 39:
            b.send('MIST A 0')
    b.send('MIST A 0'); b.send('MODE OFF')
    b.note(f'water check: inside {before:.1f} -> peak {peak:.1f} % (+{peak - before:.1f}) around a 40 s burst')
    return peak - before


def dry(b, k, n):
    b.phase = f'c{k}-dry'
    b.send('MODE OFF')
    out = rh_out(b) or 70.0
    thr = min(76.0, max(73.0, out + 3.0))
    b.send(f'MARK cycle {k} dry-down: lid off until inside <= {thr:.1f} %')
    t0, below = time.time(), None
    start = rh_in(b)
    while time.time() - t0 < 1800:                    # never start a cycle from an undried box
        pump_for(b, 1)
        v = rh_in(b)
        el = int(time.time() - t0)
        stuck = el > 300 and start is not None and v is not None and v > start - 3
        prompt((f'Cycle {k} of {n}: the box is still at {v:.1f} %. Is the lid fully OFF? ' if stuck else
                f'Cycle {k} of {n}: take the lid fully OFF. ') +
               f'Inside {v if v is not None else float("nan"):.1f} %, waiting for {thr:.1f} % ({el} s).')
        if v is not None and v <= thr:
            below = below or time.time()
            if time.time() - below >= 15:
                return thr
        else:
            below = None
    raise Abort(f'cycle {k}: the box did not dry to {thr:.1f} % within 30 min (lid still on?)')


def close(b, k, n):
    b.phase = f'c{k}-close'
    if os.path.exists(GO_FILE):
        os.remove(GO_FILE)
    prompt(f'Cycle {k} of {n}: put the lid BACK with a 1 cm gap, then press the button.', await_go=True)
    b.note(f'cycle {k}: waiting for lid at 1 cm (button)')
    t0 = time.time()
    while time.time() - t0 < 1200:
        pump_for(b, 1)
        if go_pressed():
            prompt('')
            b.send(f'MARK cycle {k} lid set to 1 cm (confirmed)')
            return
    prompt('')
    raise Abort(f'cycle {k}: no confirmation that the lid is at 1 cm within 20 min')


def run_rule(b, k, n, minutes):
    b.phase = f'c{k}-rule'
    prompt(f'Cycle {k} of {n}: rule controller running ({minutes:g} min). Leave the box alone.')
    b.send('SET lo=77 hi=88 max=300 cool=60 use=A'); b.send('MODE RULES')
    b.send(f'MARK cycle {k} matched rule start (below 77 %, stop at 88 % or 300 s, rest 60 s)')
    try:
        pump_for(b, minutes * 60)
    finally:
        b.send('MODE OFF'); b.pump(1)


def run_learning(b, k, n, minutes, stamp):
    b.phase = f'c{k}-learning'
    prompt(f'Cycle {k} of {n}: learning controller running ({minutes:g} min). Leave the box alone.')
    brain = Brain(learn_hours=0.0)
    theta, _ = seed_from_csv(SEED, brain)
    b.send('SET man=400'); b.send('MODE MANUAL')
    b.send(f'MARK cycle {k} learning controller start (seeded from the step test)')
    blog_path = os.path.join(DATA, f'lab-lidcycle-{stamp}-c{k}.brain.csv')
    blog = open(blog_path, 'w', newline='')
    bw = csv.writer(blog)
    bw.writerow(['pc_time', 't_s', 'rh_in', 'temp_in', 'sensor_ok', 'cmd_main', 'cmd_backup', 'mode', 'burst_left_s',
                 'fault', 'z', 'sigma', 'mist_slow', 'mist_fast', 'leak_slow_per_s', 'leak_fast_per_s', 'active'])
    cmd_prev, last_ms, n_ev, t0 = None, None, 0, time.time()
    t_offset, last_t = 0.0, 0.0
    try:
        while time.time() - t0 < minutes * 60:
            pump_for(b, 1)
            r = b.last
            if not r:
                continue
            ms = int(r['ms'])
            if last_ms is not None and ms < last_ms:            # board restarted: re-arm manual mode
                b.note('board restarted (uptime went backwards): re-sending MODE MANUAL, model kept')
                b.send('SET man=400'); b.send('MODE MANUAL'); last_ms = None; cmd_prev = None; t_offset += last_t
            if last_ms is not None and ms - last_ms < DT * 1000 - 100:
                continue
            last_ms = ms
            ok = r['in_ok'] == '1'
            rh = float(r['rh_in']) if ok else None
            temp = float(r['t_in']) if ok else None
            if brain.last_good is None and not ok:
                continue
            t = t_offset + ms / 1000.0; last_t = ms / 1000.0
            main, backup = brain.step(t, rh, temp, 0, lambda _k: 0)
            if (main, backup) != cmd_prev:
                b.send(f'MIST A {main}'); b.send(f'MIST B {backup}')
                cmd_prev = (main, backup)
            for _when, text in brain.events[n_ev:]:
                b.note(f'BRAIN: {text}')
            n_ev = len(brain.events)
            L = brain.log[-1]
            bw.writerow([b.now(), f'{t:.0f}', '' if rh is None else f'{rh:.2f}', '' if temp is None else f'{temp:.2f}', int(ok),
                         main, backup, brain.mode, f'{max(0.0, brain.until - t):.0f}', brain.fault or '', f"{L['z']:.2f}",
                         f'{brain.sigma:.3f}', f"{L['mist_slow']:.4f}", f"{L['mist_fast']:.4f}", f"{L['leak_slow']:.2e}",
                         f"{L['leak_fast']:.2e}", brain.active])
            blog.flush()
    finally:
        b.send('MIST A 0'); b.send('MIST B 0'); b.send('MODE OFF'); b.pump(1)
        blog.close()
        with open(blog_path.replace('.brain.csv', '.brain.json'), 'w') as f:
            json.dump(dict(seed=theta, final_slow=brain.slow.theta, final_fast=brain.fast.theta,
                           events=[(round(t_, 1), x) for t_, x in brain.events]), f, indent=1)


# ----------------------------------------------------------------- metrics
def cycle_metrics(csv_path, stamp, cycles):
    rows = [r for r in csv.DictReader(open(csv_path)) if r['ms']]
    out = []
    for k in range(1, cycles + 1):
        for ctrl in ('rule', 'learning'):
            seg = [r for r in rows if r['phase'] == f'c{k}-{ctrl}' and r['in_ok'] == '1']
            if len(seg) < 60:
                continue
            v = [float(r['rh_in']) for r in seg]
            on = [r['mistA'] == '1' for r in seg]
            bursts, lens, cur = 0, [], 0
            for i, m in enumerate(on):
                if m:
                    cur += 1
                    if i == 0 or not on[i - 1]:
                        bursts += 1
                elif cur:
                    lens.append(cur); cur = 0
            if cur:
                lens.append(cur)
            first = lambda thr: next((i for i, x in enumerate(v) if x >= thr), None)
            out.append(dict(cycle=k, controller=ctrl, start=seg[0]['pc_time'][11:19], samples=len(seg),
                            start_rh=v[0], mist_s=sum(on), bursts=bursts, burst_s=lens, peak_rh=max(v),
                            mean_rh=round(sum(v) / len(v), 2), end_rh=v[-1], s_to_75=first(75.0), s_to_85=first(85.0),
                            in_band_pct=round(100 * sum(75 <= x <= 90 for x in v) / len(v), 1),
                            above_90_pct=round(100 * sum(x > 90 for x in v) / len(v), 1)))
    with open(csv_path.replace('.csv', '.cycles.json'), 'w') as f:
        json.dump(out, f, indent=1)
    print(f"{'cyc':4}{'ctrl':10}{'start':>9}{'RH0':>6}{'mist s':>8}{'bursts':>7}{'peak':>7}{'mean':>7}{'end':>7}{'s>=75':>7}{'s>=85':>7}{'band%':>7}")
    for m in out:
        print(f"{m['cycle']:<4}{m['controller']:10}{m['start']:>9}{m['start_rh']:6.1f}{m['mist_s']:8d}{m['bursts']:7d}"
              f"{m['peak_rh']:7.1f}{m['mean_rh']:7.1f}{m['end_rh']:7.1f}{str(m['s_to_75']):>7}{str(m['s_to_85']):>7}{m['in_band_pct']:7.1f}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='COM3')
    ap.add_argument('--cycles', type=int, default=4)
    ap.add_argument('--block', type=float, default=20, help='minutes each controller runs per cycle')
    ap.add_argument('--http', type=int, default=8766)
    a = ap.parse_args()
    for f in (STOP_FILE, GO_FILE):
        if os.path.exists(f):
            os.remove(f)
    stamp = f'{dt.datetime.now():%Y-%m-%d-%H%M}'
    path = os.path.join(DATA, f'lab-lidcycle-{stamp}.csv')
    serve(a.http)
    b = Board(a.port, path)
    b.send('HEADER'); b.send('STATUS'); b.pump(3)
    b.note(f'START lid-cycle test: {a.cycles} cycles x {a.block:g} min, lid 1 cm, matched rule vs learning -> {path}')
    order = ['rule' if k % 2 else 'learning' for k in range(1, a.cycles + 1)]
    try:
        # nothing mists and no cycle starts until someone is at the box
        prompt('Press the button when you are AT THE BOX and ready to move the lid (about 1 h 45 min in total).', await_go=True)
        b.phase = 'waiting-for-operator'
        b.note('waiting for the operator (button or data/GO)')
        t0 = time.time()
        while not go_pressed():
            pump_for(b, 1)
            if time.time() - t0 > 4 * 3600:
                raise Abort('nobody pressed the start button within 4 h')
        prompt('')
        b.send('MARK operator present, test starting')
        rise = water_check(b)
        if rise < 1.5:
            b.send('MARK water check failed: no fog')
            prompt('No fog in the water check. Add water to the mist tray, then press the button.', await_go=True)
            t0 = time.time()
            while not go_pressed():
                pump_for(b, 1)
                if time.time() - t0 > 1200:
                    raise Abort('no water after 20 min')
            prompt('')
            if water_check(b) < 1.5:
                raise Abort('still no fog after refilling')
        for k, ctrl in enumerate(order, start=1):
            dry(b, k, a.cycles)
            close(b, k, a.cycles)
            if ctrl == 'rule':
                run_rule(b, k, a.cycles, a.block)
            else:
                run_learning(b, k, a.cycles, a.block, stamp)
            b.note(f'cycle {k} ({ctrl}) done')
        prompt('Test finished. The lid can stay at 1 cm. Thank you!')
    except Abort as e:
        b.note(f'ABORT: {e}')
        prompt(f'Test stopped: {e}')
    except KeyboardInterrupt:
        b.note('stopped by keyboard')
    finally:
        b.phase = 'end'
        b.send('MIST A 0'); b.send('MIST B 0'); b.send('MODE OFF')
        b.send('SET lo=75 hi=90 max=300 cool=180 man=600'); b.send('STATUS'); b.pump(3)
        b.note('END lid-cycle test (production settings restored)')
        try:
            b.f.flush()
            cycle_metrics(path, stamp, a.cycles)
        except Exception as e:                    # metrics are a convenience; never mask the run
            print('metrics failed:', e)
        for f in (STOP_FILE, GO_FILE):
            if os.path.exists(f):
                os.remove(f)
        time.sleep(30)                            # keep the final prompt visible briefly


if __name__ == '__main__':
    main()
