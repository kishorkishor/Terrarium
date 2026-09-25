"""
Simulated terrarium for testing the brain before touching hardware.

This is NOT data. Every number here is an assumption chosen to be plausible
for a ~16 L acrylic box with one ultrasonic disc; replace it with the logged
real box as soon as the logging firmware runs.

Physics (absolute humidity AH in g/m^3, 1 s steps):
    dAH/dt =  k_mist * mist_eff * (1 - RH/100)      droplets evaporate slower near saturation
            - leak   * (AH - AH_room)               box is not airtight
            - fan    * fan_on * (AH - AH_room)      ventilation fan
            + plant                                 transpiration
Mist spreads with a first-order lag; the RH sensor has its own lag, noise and 0.1 % steps.
"""
import math, random


def ah_sat(t):
    """Saturation vapour density, g/m^3 (Magnus formula)."""
    es = 6.112 * math.exp(17.62 * t / (243.12 + t))
    return 216.7 * es / (273.15 + t)


def ah_from_rh(rh, t):
    return rh / 100.0 * ah_sat(t)


def rh_from_ah(ah, t):
    return 100.0 * ah / ah_sat(t)


class Box:
    def __init__(self, seed=1):
        self.rng = random.Random(seed)
        # assumed physical constants
        # MEASURED 2026-09-25 (data/box-exp-2026-09-25-1645.csv, 11x9x3 in box, one 5 V disc):
        # first-minute rise 0.049 g/m^3/s at 72 %RH -> k_mist ~0.17 dry-air; decay tau 690 s
        self.k_mist = 0.17          # g/m^3/s at full mist, dry air (was 0.25 assumed)
        self.k_backup = 0.20        # second (watering) disc, a bit weaker
        self.leak = 1 / 690         # 1/s, 11.5-minute time constant (measured, was 1/900)
        self.fan = 1 / 120          # 1/s extra when fan runs
        self.plant = 0.0008         # g/m^3/s
        self.room_rh = 60.0
        self.tau_mist = 15.0        # s, fog spreading
        self.tau_sensor = 6.0       # s, sensor response
        self.noise = 0.25           # %RH
        # state
        self.t = 0.0
        self.temp = 27.0
        self.ah = ah_from_rh(65, self.temp)
        self.mist_eff = 0.0
        self.rh_sensor = 65.0
        self.stuck_value = None
        # fault switches (set by the scenario)
        self.mist_gain = 1.0        # slow wear of the main disc
        self.main_dead = False
        self.leak_mult = 1.0        # lid open -> large
        self.fan_dead = False
        self.sensor_stuck = False

    def room_temp(self):
        # 27 C with a +-1.5 C daily swing
        return 27.0 + 1.5 * math.sin(2 * math.pi * self.t / 86400.0)

    def step(self, mist_main, mist_backup, fan_on, dt=1.0):
        self.temp = self.room_temp()
        ah_room = ah_from_rh(self.room_rh, self.temp)
        rh = rh_from_ah(self.ah, self.temp)
        drive = (0.0 if self.main_dead else self.k_mist * self.mist_gain) * mist_main \
            + self.k_backup * mist_backup
        target = min(1.0, drive / self.k_mist)          # normalised fog input
        self.mist_eff += (target - self.mist_eff) * dt / self.tau_mist
        g = max(0.02, 1.0 - rh / 100.0)
        fan = 0.0 if self.fan_dead else self.fan * fan_on
        d = self.k_mist * self.mist_eff * g \
            - self.leak * self.leak_mult * (self.ah - ah_room) \
            - fan * (self.ah - ah_room) + self.plant
        self.ah += d * dt
        self.ah = min(self.ah, ah_sat(self.temp))        # condensation cap
        true_rh = rh_from_ah(self.ah, self.temp)
        self.rh_sensor += (true_rh - self.rh_sensor) * dt / self.tau_sensor
        self.t += dt
        return true_rh

    def read(self):
        """What the BME280 reports: (rh, temp). Stuck sensor repeats one value."""
        if self.sensor_stuck:
            if self.stuck_value is None:
                self.stuck_value = (round(self.rh_sensor, 1), round(self.temp, 2))
            return self.stuck_value
        self.stuck_value = None
        rh = round(self.rh_sensor + self.rng.gauss(0, self.noise), 1)
        return min(100.0, rh), round(self.temp + self.rng.gauss(0, 0.05), 2)
