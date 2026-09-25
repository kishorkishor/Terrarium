# Self-healing climate control: gap check and resource check

Date: 2026-09-24. Sources: Consensus (6 searches), OpenAlex duplication test and two gap-saturation curves, plus a read of `firmware/terrarium`. Consensus links are listed as given by Consensus; open each paper and record its DOI before citing.

## 1. Verdict

Each building block has been published on its own: detecting faults in greenhouses, virtual sensors that stand in for a failed humidity sensor, and small AI models running on an ESP32. What has not been published is the closed loop on real hardware. That means a cheap microcontroller that detects a fault, names the failed part and then reconfigures itself to keep the plant climate in range, tested with physically injected faults, with the climate outcome measured against rule-based handling. The only greenhouse paper that reconfigures after a fault did it in simulation. So the paper is worth doing, but the contribution is the integration plus the measured recovery, not any single component.

## 2. What is already done

| Piece | Done by | What they did | What they did not do |
|---|---|---|---|
| Fault detection and identification in greenhouses | [Linker 2000, Computers and Electronics in Agriculture](https://consensus.app/papers/details/90a09ffa63c15168abb5c4904ad79df6/) | Hybrid physical and neural-network model, sensor and actuator failures, tested on experimental data | No automatic recovery, PC-based, large greenhouse |
| Same, observer based | [Linker 2002, Control Engineering Practice](https://consensus.app/papers/details/052d6bcfc2ed584d95fa0d9401848597/) | Experimental greenhouse; ventilation failure found in under 30 min, slow faults in hours | No recovery |
| Same, small farm unit | [Munser 2026, Journal of Process Control](https://consensus.app/papers/details/2d0835ee81995196b7f437fe174748cf/) | Residual observers on a small vertical-farming unit, faults distinguished during operation | No recovery, observer theory, no public data |
| Replacing failed sensors with AI predictions | [Shekarian 2024, Computers and Electronics in Agriculture](https://consensus.app/papers/details/23c26ad7d2235a898c6e22da7f549c38/) | Cloud 1D-CNNs predict greenhouse humidity (RMSE 3.47 % RH) when a sensor fails | Cloud only, sensors only, no actuator faults, no control outcome |
| Virtual humidity sensor with accommodation | [Ponce 2024, Heliyon](https://consensus.app/papers/details/494d5d4f6c7a5b73b36d7ebb31e4d4e3/) | Buildings and a museum store; 95 % fault detection and identification | Not plants, no actuators |
| Virtual sensors for farming | [Chourlias 2025, Internet of Things](https://consensus.app/papers/details/24cc6cdc088e5130a1584c16fae0784b/) | Field nodes, public dataset, LightGBM virtual sensors | Monitoring only, no control |
| Fault-tolerant (fault-hiding) greenhouse control | [Hameed 2017, Int. J. Automation and Control](https://consensus.app/papers/details/9913931b572654c4816dbc63449ba4ff/) | Virtual sensors and actuators restore control after sensor or actuator faults | **Simulation only** |
| AI anomaly detection trained on an ESP32 | [Antonini 2023, Sensors](https://consensus.app/papers/details/b41e474727295a52a4aea46c5c74d657/) | Isolation forest trained on the chip in seconds, industrial pumps | Detection only, not agriculture |
| Actuator health in commercial smart farms | [Choe 2025, Applied Sciences](https://consensus.app/papers/details/090ab2088c005b8b8f48f01178cfcb84/) | Field-validated anomaly detection and remaining-life estimation for switches and sensors | Cloud/web platform, maintenance forecasting, no live recovery |
| Labelled fault datasets | [Attarha 2023](https://consensus.app/papers/details/919858cc31365593921b18add9d99894/), [Bruijn 2016](https://consensus.app/papers/details/76f2dcd95b1557009ea952361f503009/) | Sensor-fault datasets, mostly synthetic injection | No actuator faults, no misting enclosure |

The recent surveys ([Zou 2023, Sensors](https://consensus.app/papers/details/fb069ef279e056dd8e1884afdff272d2/); [Daurenbayeva 2023, Energies](https://consensus.app/papers/details/f821bc39ef815353b901772d9008e5c5/)) list recovery and real-world validation as open problems.

## 3. What is not done

1. **Detect, identify and recover, all on the microcontroller**, in a plant enclosure, with recovery actions that act on the real climate (virtual sensor takeover, backup actuator switchover, safe mode).
2. **Physically injected actuator faults** in a small misting enclosure: dead mist disc, empty reservoir, stalled fan, lid left open. Existing agriculture datasets inject sensor faults in software.
3. **Measured climate outcome of a fault**: time in the humidity band, and water or plant exposure, with self-healing versus rule-based fail-safes versus no handling.
4. **AI versus plain rules on the same faults.** This is the comparison reviewers will ask for, and nobody reports it for this class of system.

## 4. Momentum

- On-device fault detection and fault-tolerant control for greenhouse climate: about 10 papers a year, flat to slowly rising. Not crowded.
- TinyML anomaly detection on the ESP32: 2 papers in 2023, 2 in 2025, 7 in 2026. Rising fast, so publish soon.

Both counts come from a broadened lexical query and are only indicative.

## 5. The study

**Working title:** Self-healing humidity control on a low-cost microcontroller: on-device fault detection, isolation and recovery in a misted plant enclosure, validated with physically injected faults.

**How it works**

1. **Predictor.** A small model (a linear autoregressive model first, then a small neural network if it helps) predicts the next humidity reading from recent humidity, temperature, mist state, fan state and light. It is trained on the laptop from 2 to 3 days of normal logs. The weights are exported as a C array to the ESP32, and the model uses a few kilobytes.
2. **Detection.** The residual between prediction and measurement is watched over a sliding window.
3. **Isolation.** A fault-signature table maps residual patterns and actuator states to the failed part.
4. **Recovery.**
   - Humidity sensor failed or stuck: control continues on the predicted humidity (virtual sensor).
   - Humidity mist disc dead: switch to the second mist module, but only if it shares the same air volume.
   - Tank empty, fan stalled or lid open: safe mode plus the buzzer.

**Baselines:** (a) the current firmware rules, which turn misting off when humidity is unreadable and rely on the float switch, and (b) no fault handling.

**Fault list, with current hardware**

| Fault | How to inject | Why it matters |
|---|---|---|
| BME280 disconnected | Pull the I2C lead | Easy case. Current rules stop misting and the plants dry out |
| BME280 stuck or fouled | Seal it in a small bag, or wet it | Hard case. Readings look valid but are wrong, and rules miss it |
| Mist disc dead | Unplug the disc lead, drive stays on | Actuator fault invisible to current firmware |
| Reservoir empty with a failed float | Empty the tank and tape the float up | Two faults at once, the disc would run dry |
| Exhaust fan stalled | Block the blades | Only detectable through the climate response |
| Lid open | Open the lid | Environmental fault, not a hardware one |
| One soil probe failed | Unplug one of the two probes | Uses the redundant pair |

**Metrics:** detection delay, correct isolation rate, false alarms per day on normal data, time in the humidity band during each fault, and mist-minutes wasted.

**Output:** the paper, plus the labelled dataset (normal operation and injected faults) released openly.

## 6. Resources

| Item | Status | Note |
|---|---|---|
| ESP32 | Have | Enough memory for the model |
| BME280, BH1750, 2 soil probes, float, leak sensor | Have | Soil pair gives sensor redundancy |
| Two mist modules (GPIO25 humidity, GPIO16 watering) | Have | **Check** that both discs mist into the same air volume. If not, backup switchover is dropped and recovery is virtual sensor plus safe mode only |
| Exhaust fan | Have | Circulation fan is not fitted (`ENABLE_FAN_CIRC 0`), so it is left out of the fault list |
| Rule-based fail-safes in firmware | Have | Serve as baseline (a) |
| Serial logging every 2 s, laptop tools | Have | Laptop must stay connected during runs |
| **Reference humidity sensor (SHT31 or second BME280)** | **Buy, about 500 to 700 taka** | Mandatory. It scores the virtual sensor when the main one is disabled. It is never used by the controller |
| Spare mist disc | Buy, cheap | Fresh disc before the fault campaign |
| Micro-SD module | Optional, about 200 taka | Only if the laptop cannot stay attached for days |
| Current sensor on actuators | Not needed | Would make actuator faults trivial and weaken the model-based claim |

Total new spend is under 1500 taka.

## 7. Time (two weeks, tight but feasible)

| Days | Work |
|---|---|
| 1 to 3 | Add the reference sensor. Log normal operation around the clock with the firmware's normal cycles |
| 4 | Train the predictor, set thresholds from normal data only, port to the ESP32 |
| 5 to 8 | Fault campaign: 7 faults, 5 repeats each, under self-healing, rules and no handling. About 20 minutes per run, roughly 30 hours of attended work |
| 9 to 14 | Analysis, figures, writing, dataset packaging |

## 8. Risks

- **"Incremental over Linker 2000 and Shekarian 2024."** The answer is recovery on the chip, actuator faults, the measured climate outcome and open data. Say this in the first paragraph of the introduction.
- **The model does not beat simple rules.** Report it honestly. The recovery results still stand, and a clean negative comparison is publishable.
- **Five repeats is small.** State it, report per-run results, and keep the dataset open so others can extend it.

## 9. Venues

- Computers and Electronics in Agriculture (Q1). It already published Linker 2000 and Shekarian 2024, so it is the natural home.
- Smart Agricultural Technology (Q1 in recent listings). Realistic first target if the first one rejects.
- Sensors or Internet of Things. Fallback.
