"""
The terrarium brain: a physics-shaped model that learns on the chip, uses itself
to plan mist bursts, notices faults, and repairs itself.

Written in plain arithmetic on small fixed arrays so it ports line-for-line to
the ESP32 (6 weights, two 6x6 matrices, ~600 bytes of state).

Five ideas make it better than a plain 6-number learner:

1. Physics-shaped inputs. It learns in absolute humidity, and each weight maps
   to a real part of the box: mister strength, how leaky the box is, how much
   the fan dries it. So a change in one weight names the part that changed.
2. Two learners at two speeds. A fast learner (about 17 min memory) tracks what
   is happening now; a slow learner (about 7 h memory) is the memory of the
   healthy box. Comparing them separates "the box slowly changed" from
   "something just broke".
3. Robust learning. Errors are clipped before learning (one bad reading cannot
   wreck it), the uncertainty matrix is capped (no blow-up when nothing
   happens), and weights are kept physically sensible.
4. Knows when to stop learning. When a fault is detected the slow learner
   freezes, so it never learns a broken part as normal. It restarts once the
   fault is gone or a new normal is confirmed (e.g. running on the backup disc).
5. Self-repair. It saves a known-good copy of itself every few hours and rolls
   back if its weights ever become nonsense.
"""
import math
from collections import deque
from sim_box import ah_sat, ah_from_rh, rh_from_ah

DT = 5.0              # seconds between readings
AH_REF = 20.0         # centring constant for numerical conditioning
N = 6                 # number of weights
# weight index -> physical meaning
I_MIST1, I_MIST2, I_AH, I_FAN_AH, I_FAN, I_BIAS = range(N)


class RLS:
    """Recursive least squares with forgetting, clipping and covariance cap."""

    def __init__(self, lam, p0=100.0, p_max=1e4, beta=1e-4):
        self.lam, self.p_max, self.p0, self.beta = lam, p_max, p0, beta
        self.resets = 0
        self.theta = [0.0] * N
        self.P = [[p0 if i == j else 0.0 for j in range(N)] for i in range(N)]

    def predict(self, phi):
        return sum(t * f for t, f in zip(self.theta, phi))

    def update(self, phi, y, clip):
        e = y - self.predict(phi)
        e_used = max(-clip, min(clip, e))                      # robust: bounded step
        Pphi = [sum(self.P[i][j] * phi[j] for j in range(N)) for i in range(N)]
        denom = self.lam + sum(phi[i] * Pphi[i] for i in range(N))
        K = [p / denom for p in Pphi]
        for i in range(N):
            self.theta[i] += K[i] * e_used
        for i in range(N):
            for j in range(N):
                self.P[i][j] = (self.P[i][j] - K[i] * Pphi[j]) / self.lam
        # keep the uncertainty matrix valid (symmetric, positive, bounded):
        # a forgetting learner under closed-loop data otherwise drifts into
        # negative 'uncertainty' and explodes
        for i in range(N):
            for j in range(i + 1, N):
                m = 0.5 * (self.P[i][j] + self.P[j][i])
                self.P[i][j] = self.P[j][i] = m
            self.P[i][i] += self.beta                            # floor: never fully certain
        tr = sum(self.P[i][i] for i in range(N))
        if tr <= 0 or min(self.P[i][i] for i in range(N)) <= 0:
            self.P = [[self.p0 if i == j else 0.0 for j in range(N)] for i in range(N)]
            self.resets += 1
        elif tr > self.p_max:                                  # no wind-up when idle
            s = self.p_max / tr
            self.P = [[v * s for v in row] for row in self.P]
        # keep weights physical: mist adds water, box and fan lose it
        self.theta[I_MIST1] = max(0.0, self.theta[I_MIST1])
        self.theta[I_MIST2] = max(0.0, self.theta[I_MIST2])
        self.theta[I_AH] = min(0.0, self.theta[I_AH])
        self.theta[I_FAN_AH] = min(0.0, self.theta[I_FAN_AH])
        return e

    def copy_from(self, other):
        self.theta = list(other.theta)
        self.P = [list(r) for r in other.P]


def features(ah, rh, mf1, mf2, fan):
    g = max(0.02, 1.0 - rh / 100.0)
    a = ah - AH_REF
    return [g * mf1, g * mf2, a, fan * a, fan, 1.0]


class Brain:
    def __init__(self, learn_hours=8.0, lo=75.0, hi=90.0):
        self.lo, self.hi = lo, hi
        self.learn_until = learn_hours * 3600
        self.fast = RLS(lam=0.998, p_max=1e3, beta=1e-6)
        self.slow = RLS(lam=0.9998, beta=1e-7)   # tiny floor, else it forgets fast
        self.snapshot = RLS(lam=0.9998, beta=1e-7)
        self.snap_time = 0.0
        self.mf1 = self.mf2 = 0.0          # filtered mist commands (5 s and 30 s)
        self.prev = None                   # (phi, ah) from last good step
        self.sigma = 0.15                  # typical one-step error, g/m^3
        self.sigma_base = None
        self.gp = self.gm = 0.0            # CUSUM up / down
        self.raw_hist = deque(maxlen=12)
        self.fault = None
        self.fault_since = 0.0
        self.events = []                   # (time, text)
        self.active = 'main'
        self.backup_ok_bursts = 0
        self.safe_until = 0.0
        self.last_good = None              # (ah, temp)
        self.ah_virtual = None
        self.baseline_mist = None
        # controller state
        self.mode, self.until = 'idle', 0.0
        self.cmd = 0
        # windows for part checks: [pred_part, actual_part, steps]
        self.mw = None
        self.fw = None
        self.mist_bad = self.fan_bad = 0   # consecutive failed checks
        self.agree_since = None
        self.probe_until = 0.0
        self.zq, self.zm = [], []
        self.quiet_bias = 0.0
        self.guard = None
        self.wear_warned = False
        self.prev_for_check = None
        self.err_live = self.err_snap = 0.02
        self.rhythm = deque(maxlen=20)     # (start time, burst seconds) when healthy
        self.last_start = 0.0
        self.log = []

    # ------------------------------------------------------------------ helpers
    def mist_sum(self, r):
        return r.theta[I_MIST1] + r.theta[I_MIST2]

    def event(self, t, text):
        self.events.append((t, text))

    def rollout(self, model, ah, temp, fan_plan, burst_steps, horizon=120):
        """Predicted measured-RH peak for a candidate burst length."""
        mf1, mf2, peak = self.mf1, self.mf2, 0.0
        for k in range(horizon):
            u = 1.0 if k < burst_steps else 0.0
            mf1 += (u - mf1) * DT / 5.0
            mf2 += (u - mf2) * DT / 30.0
            rh = rh_from_ah(ah, temp)
            ah += model.predict(features(ah, rh, mf1, mf2, fan_plan(k)))
            peak = max(peak, rh_from_ah(ah, temp))
        return peak

    # --------------------------------------------------------------- main step
    def step(self, t, rh_raw, temp_raw, fan_on, fan_plan):
        # 0. integrity: weights may only change through learning. Anything else
        #    (power glitch, memory corruption) -> restore the saved copy now
        if self.guard is not None and self.slow.theta != self.guard:
            self.slow.copy_from(self.snapshot)
            self.event(t, 'model rolled back to saved copy (memory changed unexpectedly)')
        # 1. is the reading trustworthy?
        lost = rh_raw is None
        if not lost:
            self.raw_hist.append(rh_raw)
        stuck = len(self.raw_hist) == 12 and len(set(self.raw_hist)) == 1
        sensor_bad = lost or stuck
        u = 1.0 if self.cmd else 0.0

        if sensor_bad:
            if self.fault not in ('sensor lost', 'sensor stuck'):
                self.set_fault(t, 'sensor lost' if lost else 'sensor stuck')
            ah_v = self.ah_virtual if self.ah_virtual is not None else self.last_good[0]
            temp = self.last_good[1]
            rh_v = rh_from_ah(ah_v, temp)
            self.ah_virtual = ah_v + self.slow.predict(
                features(ah_v, rh_v, self.mf1, self.mf2, fan_on))
            rh_used, ah = rh_v, None
        else:
            if self.fault in ('sensor lost', 'sensor stuck'):
                self.clear_fault(t)
                self.prev = None                     # restart learning chain cleanly
            temp = temp_raw
            ah = ah_from_rh(rh_raw, temp)
            rh_used = rh_raw
            self.ah_virtual = None
            self.last_good = (ah, temp)

        # 2. learn from the last step
        z = 0.0
        if ah is not None and self.prev is not None:
            phi, ah_prev = self.prev
            y = ah - ah_prev
            clip = 3 * self.sigma
            self.fast.update(phi, y, clip)
            # anchor: directions the recent data does not pin down relax back to
            # the trusted slow values (~40 min), so fast weights stay meaningful
            for i in range(N):
                self.fast.theta[i] += 0.002 * (self.slow.theta[i] - self.fast.theta[i])
            e_slow = y - self.slow.predict(phi)
            if self.fault is None:
                self.slow.update(phi, y, clip)
                self.sigma = math.sqrt(0.99 * self.sigma ** 2 + 0.01 * min(e_slow, 4 * self.sigma) ** 2)
                self.sigma = max(self.sigma, 0.05)
            z = e_slow / self.sigma
            if phi[I_MIST2] <= 0.02 and phi[I_FAN] < 0.5:
                self.quiet_bias = 0.95 * self.quiet_bias + 0.05 * e_slow   # ~2 min memory
            if t > self.learn_until:
                self.gp = max(0.0, self.gp + z - 0.5)
                self.gm = max(0.0, self.gm - z - 0.5)
            self.part_checks(t, phi, y)

        # 3. faults that only the overall error reveals
        if t > self.learn_until and self.fault is None:
            if self.gm > 20:
                # humidity is falling faster than the healthy box allows. Could be
                # the lid or the mister: freeze memory and let the next mist burst decide
                self.set_fault(t, 'suspect loss')
            elif self.gp > 20:
                self.event(t, 'unexplained humidity gain')
                self.gp = 0.0
        if self.fault == 'suspect loss':
            self.diagnose(t, z)
        if self.fault == 'lid open / leak':
            # the fast learner re-measures the leak; when it agrees with the
            # healthy-box memory again for 10 minutes, the lid is closed
            lf, ls = -self.fast.theta[I_AH], -self.slow.theta[I_AH]
            if abs(lf - ls) < 0.5 * ls and t - self.fault_since > 600:
                self.agree_since = self.agree_since or t
                if t - self.agree_since > 600:
                    self.clear_fault(t)
                    self.agree_since = None
            else:
                self.agree_since = None

        # 4. self-repair: snapshot and roll back
        if t > self.learn_until and self.baseline_mist is None:
            self.baseline_mist = self.mist_sum(self.slow)
            self.sigma_base = self.sigma
            self.snapshot.copy_from(self.slow)
            self.snap_time = t
        if self.baseline_mist is not None and self.fault is None and self.prev_for_check:
            phi_c, y_c = self.prev_for_check
            self.err_live = 0.997 * self.err_live + 0.003 * (y_c - self.slow.predict(phi_c)) ** 2
            self.err_snap = 0.997 * self.err_snap + 0.003 * (y_c - self.snapshot.predict(phi_c)) ** 2
            if self.err_live > 2.0 * self.err_snap and t - self.snap_time > 1800:
                self.slow.copy_from(self.snapshot)
                self.err_live = self.err_snap
                self.event(t, 'model rolled back to saved copy (predicting worse than it used to)')
        if (self.baseline_mist and not self.wear_warned and self.active == 'main'
                and self.mist_sum(self.slow) < 0.8 * self.baseline_mist):
            self.wear_warned = True
            self.event(t, 'maintenance: main mister below 80 % of day-1 strength (clean or replace disc)')
        if self.fault is None and t - self.snap_time > 6 * 3600 and self.err_live <= 1.2 * self.err_snap:
            self.snapshot.copy_from(self.slow)
            self.snap_time = t

        # 5. decide the mist command
        self.control(t, rh_used, ah if ah is not None else self.ah_virtual, temp, fan_plan)

        # 6. filters and memory for next step
        self.mf1 += (u - self.mf1) * DT / 5.0
        self.mf2 += (u - self.mf2) * DT / 30.0
        self.prev_for_check = None
        if ah is not None and self.prev is not None:
            self.prev_for_check = (self.prev[0], ah - self.prev[1])
        if ah is not None:
            self.prev = (features(ah, rh_used, self.mf1, self.mf2, fan_on), ah)
        self.guard = list(self.slow.theta)
        self.log.append(dict(t=t, rh=rh_used, z=z, fault=self.fault or '',
                             mist_fast=self.mist_sum(self.fast), mist_slow=self.mist_sum(self.slow),
                             leak_fast=-self.fast.theta[I_AH] / DT, leak_slow=-self.slow.theta[I_AH] / DT,
                             active=self.active))
        main = 1 if (self.cmd and self.active == 'main') else 0
        backup = 1 if (self.cmd and self.active == 'backup') else 0
        return main, backup

    # ---------------------------------------------------------- part checks
    def part_checks(self, t, phi, y):
        """Did the mister / fan do what the healthy model says they should?"""
        th = self.slow.theta
        pred_mist = th[I_MIST1] * phi[I_MIST1] + th[I_MIST2] * phi[I_MIST2]
        pred_fan = th[I_FAN_AH] * phi[I_FAN_AH] + th[I_FAN] * phi[I_FAN]
        pred_all = self.slow.predict(phi)
        mist_active = phi[I_MIST2] > 0.02
        fan_active = phi[I_FAN] > 0.5
        if mist_active and not fan_active:
            if self.mw is None:
                self.mw = [0.0, 0.0, 0]
            self.mw[0] += pred_mist
            # what the mister really added, after removing any background drain
            # (e.g. an open lid) measured while the box was quiet
            self.mw[1] += y - (pred_all - pred_mist) - self.quiet_bias
            self.mw[2] += 1
        if self.mw is not None and (not (mist_active and not fan_active) or self.mw[2] >= 24):
            # verdict when the burst's effect has passed, or every 2 min of misting
            pred, actual, n = self.mw
            self.mw = None
            judge = self.fault in (None, 'main mister dead')
            if judge and t > self.learn_until and pred > 0.6 and n >= 8:
                self.mist_bad = self.mist_bad + 1 if actual < 0.3 * pred else 0
                if self.mist_bad >= 2:
                    self.mist_bad = 0
                    if self.active == 'main':
                        self.set_fault(t, 'main mister dead')
                        self.active = 'backup'
                        self.backup_ok_bursts = 0
                        self.event(t, 'switched to backup mister')
                    else:
                        self.set_fault(t, 'both misters dead')
                        self.safe_until = t + 1e9
                elif self.mist_bad == 0 and self.fault == 'main mister dead':
                    self.backup_ok_bursts += 1
                    if self.backup_ok_bursts >= 2:      # backup verified: new normal
                        self.clear_fault(t, 'running on backup, learning resumed')
        if fan_active and self.mw is None:
            if self.fw is None:
                self.fw = [0.0, 0.0, 0]
            self.fw[0] += pred_fan
            self.fw[1] += y - (pred_all - pred_fan)       # what the fan really removed
            self.fw[2] += 1
        elif self.fw is not None:
            pred, actual, n = self.fw
            self.fw = None
            judge = self.fault in (None, 'fan stalled')
            if judge and t > self.learn_until and pred < -0.6 and n >= 8:
                self.fan_bad = self.fan_bad + 1 if actual > 0.3 * pred else 0
                if self.fan_bad >= 2:
                    if self.fault is None:
                        self.set_fault(t, 'fan stalled')
                elif self.fan_bad == 0 and self.fault == 'fan stalled':
                    self.clear_fault(t)

    def diagnose(self, t, z):
        """Active test after an unexplained humidity loss.
        Phase 1 (4 min): no mist. A leak keeps draining faster than the
        healthy model allows; a dead mister does not.
        Phase 2 (up to 3 min of mist): does misting do what it should?"""
        ph = self.prev[0] if self.prev else None
        if ph is None:
            return
        quiet = ph[I_MIST2] <= 0.02 and ph[I_FAN] < 0.5
        misting = ph[I_MIST2] > 0.02 and ph[I_FAN] < 0.5
        if t < self.probe_until:
            if quiet:
                self.zq.append(z)
            return
        if misting:
            self.zm.append(z)
        if len(self.zm) >= 24 or t - self.fault_since > 900:
            qz = sum(self.zq) / len(self.zq) if self.zq else 0.0
            mz = sum(self.zm) / len(self.zm) if self.zm else 0.0
            # a dead mister makes the misting phase much worse than the quiet
            # phase; a leak makes both equally bad
            if mz - qz < -0.6 and self.zm:
                self.set_fault(t, 'main mister dead')
                self.active = 'backup'
                self.backup_ok_bursts = 0
                self.event(t, 'switched to backup mister')
            elif qz < -0.3:
                self.set_fault(t, 'lid open / leak')
            elif False:
                self.set_fault(t, 'main mister dead')
                self.active = 'backup'
                self.backup_ok_bursts = 0
                self.event(t, 'switched to backup mister')
            else:
                self.clear_fault(t, 'false alarm, nothing wrong')

    def set_fault(self, t, name):
        self.fault, self.fault_since = name, t
        self.gp = self.gm = 0.0
        if name == 'suspect loss':
            self.probe_until = t + 240
            self.zq, self.zm = [], []
        self.event(t, 'FAULT: ' + name)

    def clear_fault(self, t, note='fault cleared'):
        self.event(t, note + (' (' + self.fault + ')' if self.fault else ''))
        self.fault = None
        self.gp = self.gm = 0.0

    # --------------------------------------------------------------- control
    def control(self, t, rh, ah, temp, fan_plan):
        if t < self.learn_until:                        # learning phase: old rules
            if self.mode == 'mist' and (rh >= self.hi or t >= self.until):
                self.mode, self.until, self.cmd = 'cool', t + 180, 0
            elif self.mode == 'cool' and t >= self.until:
                self.mode = 'idle'
            elif self.mode == 'idle' and rh < self.lo:
                self.mode, self.until, self.cmd = 'mist', t + 300, 1
            return
        if self.fault in ('sensor lost', 'sensor stuck') and len(self.rhythm) >= 4:
            # blind: replay the misting rhythm learned on healthy days
            durs = sorted(d for _, d in self.rhythm)
            gaps = sorted(b[0] - a[0] for a, b in zip(self.rhythm, list(self.rhythm)[1:]))
            dur, gap = durs[len(durs) // 2], gaps[len(gaps) // 2]
            if self.mode == 'mist' and t >= self.until:
                self.mode, self.cmd = 'idle', 0
            elif self.mode != 'mist' and t - self.last_start >= gap:
                self.mode, self.until, self.cmd = 'mist', t + dur, 1
                self.last_start = t
            return
        if self.fault == 'suspect loss' and t < self.probe_until:
            self.cmd, self.mode = 0, 'idle'              # quiet probe: watch, don't mist
            return
        if t < self.safe_until:                         # safe mode: do nothing
            self.cmd, self.mode = 0, 'idle'
            return
        if self.mode == 'mist':
            if t >= self.until:
                self.mode, self.until, self.cmd = 'cool', t + 60, 0
            return
        if self.mode == 'cool':
            if t >= self.until:
                self.mode = 'idle'
            return
        if rh < self.lo + 2:
            # healthy: plan with the slow (trusted) model. During a fault the slow
            # model is frozen, so plan with the fast one that tracks the new
            # situation - unless the sensor itself is bad (fast has no data then).
            sensor_fault = self.fault in ('sensor lost', 'sensor stuck')
            model = self.slow if (self.fault is None or sensor_fault) else self.fast
            target = 88.0 if self.fault is None else 84.0   # be careful when unsure
            lo_b, hi_b = 1, 60                          # 5 s .. 300 s, peak rises with length
            if self.rollout(model, ah, temp, fan_plan, hi_b) < target:
                best = hi_b
            else:
                while lo_b < hi_b:
                    mid = (lo_b + hi_b) // 2
                    if self.rollout(model, ah, temp, fan_plan, mid) >= target:
                        hi_b = mid
                    else:
                        lo_b = mid + 1
                best = lo_b
            self.mode, self.until, self.cmd = 'mist', t + best * DT, 1
            if self.fault is None:
                self.rhythm.append((t, best * DT))       # remember the healthy rhythm
            self.last_start = t


class Rules:
    """The current firmware: hysteresis 75/90 %, 5-min cap, 3-min cooldown."""

    def __init__(self, lo=75.0, hi=90.0):
        self.lo, self.hi = lo, hi
        self.mode, self.until, self.cmd = 'idle', 0.0, 0

    def step(self, t, rh_raw):
        if rh_raw is None:                              # firmware fail-safe
            self.mode, self.cmd = 'idle', 0
            return
        if self.mode == 'mist' and (rh_raw >= self.hi or t >= self.until):
            self.mode, self.until, self.cmd = 'cool', t + 180, 0
        elif self.mode == 'cool' and t >= self.until:
            self.mode = 'idle'
        elif self.mode == 'idle' and rh_raw < self.lo:
            self.mode, self.until, self.cmd = 'mist', t + 300, 1
