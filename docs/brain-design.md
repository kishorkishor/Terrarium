# The terrarium brain: design

Date: 2026-09-25. Code: `tools/brain/` (`brain.py` is the brain, `sim_box.py` a simulated box, `run_demo.py` the comparison). Figure: `docs/figures/brain-sim-demo.png`.

**Everything in section 4 comes from a simulated box.** It shows the logic works and catches its own bugs before hardware. It is not evidence for the paper. The paper's numbers must come from the real enclosure.

## 1. What it is, in one paragraph

The brain is a small model that learns, on the ESP32 itself, how humidity in your box responds to the mister, the fan and the temperature. It uses that model to plan each mist burst so humidity lands in range without overshooting. It compares what should happen with what does happen to catch broken parts, runs a short test to work out which part broke, and then recovers. It also guards its own memory: it keeps a known-good copy of itself and restores it if the live copy is corrupted or starts predicting worse.

## 2. How it is built

### The model
The model predicts the change in absolute humidity (grams of water per cubic metre) over the next 5 seconds from six inputs:

| Input | Physical meaning |
|---|---|
| Mist command, smoothed over 5 s, times (1 − RH/100) | Mister output; droplets evaporate less easily near saturation |
| Mist command, smoothed over 30 s, same factor | Slower spreading of the fog |
| Absolute humidity | Natural drying through gaps in the box |
| Fan on × absolute humidity | Extra drying while the fan runs |
| Fan on | Fan offset |
| Constant | Plant transpiration and room level |

Working in absolute humidity instead of %RH removes most of the effect of temperature. The same humidity reading means different amounts of water at 25 °C and 30 °C.

### Seven mechanisms

1. **On-chip learning.** Recursive least squares updates the six weights after every reading. Weights are kept physically sensible: the mister can only add water, and the box and fan can only remove it.
2. **Two learners at two speeds.** A fast learner with about 40 minutes of memory tracks what is happening now. A slow learner with about 7 hours of memory is the memory of the healthy box. The fast one is gently anchored to the slow one, so anything recent data doesn't pin down stays sensible.
3. **Numerical safety.** The learner's uncertainty matrix is kept symmetric, given a tiny floor and capped, and it is reset if it ever becomes invalid. Errors are clipped before learning, so one bad reading cannot wreck the model.
4. **Planned misting.** When humidity drops below 77 %, the brain simulates candidate bursts 10 minutes ahead and picks the shortest one whose predicted peak reaches 88 %. The old rules mist until 90 % and overshoot.
5. **Fault detection in three layers.**
   - **Sensor checks:** a missing reading, or the same value 12 times in a row, means the sensor is lost or stuck.
   - **Part checks:** after every 2 minutes of misting, it asks whether the mister added the water the healthy model expects. After every fan run, it asks whether the fan removed it. The check first subtracts any background drain measured while the box was quiet, so a leak cannot make the mister look broken. Two failures in a row are needed to declare a fault.
   - **Overall watchdog:** a cumulative-sum test (CUSUM) on the prediction error spots humidity falling faster than the healthy box allows.
6. **Suspect, then test, then name the fault.** An unexplained loss does not jump to a conclusion. The brain stops misting for 4 minutes and watches, then mists and watches again. A leak drains in both phases. A dead mister only fails while misting. During any fault, the slow learner freezes, so it never learns a broken part as normal.
7. **Recovery and self-repair.**
   - **Dead mister:** switch to the second mister. After two good bursts, accept that as the new normal and resume learning.
   - **Lost or stuck sensor:** replay the misting rhythm learned on healthy days, meaning the typical burst length and gap.
   - **Leak or stalled fan:** raise an alarm and keep controlling with the fast learner, which adapts to the new situation.
   - **Slow wear:** adapt to it rather than calling it a fault, but warn when the mister is below 80 % of its first-day strength.
   - **Memory:** keep a known-good copy, saved every 6 hours only if it predicts at least as well as the old copy. Restore it at once if the weights change without learning, or if the live model predicts twice as badly as the copy for 30 minutes.

### Cost on the ESP32
The state is three copies of six weights plus a 6 × 6 matrix, and a few short buffers. That is about 2 KB of memory. Each 5-second step takes a few hundred multiplications, and planning a burst takes about 5,000, a tiny fraction of the ESP32's capacity. Use double precision on the chip. The ESP32 has no hardware for it, but at one step every 5 seconds the software version is still fast enough, and it avoids the rounding trouble section 5 describes.

## 3. How it is trained

- **Days 1 to 3:** the box runs on the current rules while everything is logged. In the simulation this is the first 8 hours.
- **On the laptop:** check the model predicts well, compare it with a small neural network, and set thresholds from normal data only.
- **On the chip:** the slow learner starts from the laptop fit and keeps learning. The frozen copy used for the comparison in the paper never updates.

There is no public dataset for this. The logs from your box are the dataset, and releasing them is one of the paper's contributions.

## 4. Simulation results (logic test only)

The box was simulated for 76 hours: 8 hours of learning, then slow mister wear from 30 to 50 hours, a memory glitch at 45 hours, and four faults. The assumed physical constants are in `sim_box.py`.

| Measure | Brain | Current rules |
|---|---|---|
| Healthy hours: humidity in 75 to 90 % | 99.2 % | 93.1 % |
| Healthy hours: time above 90 % | 0.0 % | 5.9 % |
| Mist minutes per day (water) | 282 | 353 |
| Mist switch-ons per day | 144 | 114 |
| In range during open lid (40 min) | 42 % | 35 % |
| In range during dead main mister (2 h) | 92 % | 3 % |
| In range during stuck sensor (1 h) | 76 % | 3 % |
| In range during stalled fan (1.5 h) | 100 % | 96 % |

| Event | What the brain did |
|---|---|
| Memory glitch | Detected and restored in the same step |
| Mister wearing to 70 % | Tracked it closely (figure, third panel) and warned at 80 %, with no false fault |
| Lid opened | Suspected after 3 min, named "lid open / leak" after 9 min, cleared 2 min after closing |
| Main mister died | Suspected after 2 min, named and switched to backup after 8 min |
| Sensor stuck | Detected in under 1 min, recovered when readings resumed |
| Fan stalled | Detected after 21 min (it only checks during fan runs, one per 20 min), cleared after repair |

The decisions were identical on seven different random-noise seeds: no false alarms, every fault named correctly.

**One trade-off to report honestly:** the brain switches the mister on about 26 % more often, because it aims for a narrower range with shorter bursts. If disc wear from switching matters, widen the target (for example start at 76 % and aim for 89 %).

## 5. What building it taught us (these belong in the paper's methods)

Each of these was a real bug found in simulation. Each is a reason the design looks the way it does.

1. **Closed-loop data makes weights hard to identify.** The controller makes misting and humidity move together, so a fast-forgetting learner could explain the data with absurd weights that cancel out (leak estimates in the millions). The fix is the anchor to the slow learner.
2. **The uncertainty matrix went negative.** Standard recursive least squares with forgetting drifted numerically under closed-loop data until the maths exploded. The fix is to keep it symmetric, add a floor, and reset it.
3. **A safety floor that is too big makes a slow learner fast.** It absorbed an open lid within minutes, so no alarm fired. The floor must scale with the learner's memory.
4. **Plain error alarms cannot tell a leak from a dead mister.** Both look like humidity falling too fast. That is why the brain runs the quiet-then-mist test, which is also the adapt-versus-freeze question the third Deep Search listed as open.
5. **Individual weights are not reliable fault labels in closed loop.** The mister weight tracked the real disc well. The leak weight did not, so leaks are diagnosed by the active test, not by reading the weight.
6. **A one-step model is good for 10 minutes, not for an hour.** Burst planning works. Running blind for an hour does not, so a lost sensor falls back to the learned rhythm instead.

## 6. Next steps

1. Port `brain.py` to C in the firmware. It was written with fixed-size arrays and plain arithmetic for this.
2. Add the logging and fault-marker commands from `publication-plan.md`, and a ventilation schedule: exhaust fan for 60 s every 20 min. The current firmware only runs the fan above 32 °C. The brain needs regular fan runs to learn the fan and to check it, and the plants benefit from fresh air.
3. Run days 1 to 3 on the real box, fit the model, and compare real behaviour with this simulation. Where they differ, the real box wins, and the simulator's constants get updated.
