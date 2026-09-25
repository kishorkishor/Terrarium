# TinyML on the ESP32 for the terrarium: what exists and what we can build

Date: 2026-09-24. Sources: 7 Consensus searches (the connector's free monthly quota of 30 is now used up until 1 October), 1 OpenAlex search and 2 OpenAlex gap-saturation curves. Consensus Deep Search was not available: it needs a signed-in browser session, and the built-in browser is signed out. Links are as given by Consensus or OpenAlex; record each DOI before citing.

## 1. Verdict

Running a small model on an ESP32 is well established. Greenhouse temperature forecasting on microcontrollers is published, and so are models that copy expert rules to switch actuators. What is missing is a model that **learns the enclosure's own humidity dynamics on the chip while it runs**, and then uses that one model both to **mist predictively** and to **notice when the enclosure behaves wrongly**. The on-device learning papers use images, audio and gestures, not climate control. The model-predictive control papers for greenhouses run in simulation, on PCs or on PLCs, not on a 5-dollar chip driving an ultrasonic mister. That combination is our gap.

## 2. What is already done

### Small models on microcontrollers for greenhouse climate
| Paper | What it did | What it did not do |
|---|---|---|
| [Codeluppi 2021, Sensors](https://consensus.app/papers/details/5fbe72529a8950e380592a74b54224ba/) | Neural nets forecast greenhouse air temperature on an edge device; RMSE 0.29 to 0.40 °C | Forecast only, no control, humidity not modelled |
| [Alati 2022, IEEE CCNC](https://consensus.app/papers/details/f9687549b0da54f1ab2b886c253c5d99/) | MLP temperature forecast runs on an Arduino Nano 33 BLE Sense | Forecast only |
| [Morales-García 2023, J. Supercomputing](https://consensus.app/papers/details/b8d696e3d58a59b887f5ac5590a60361/) | Energy and accuracy trade-off of microcontrollers predicting indoor greenhouse temperature in situ | Forecast only |
| [Abdelmadjid 2024](https://consensus.app/papers/details/64ad7e2e85295cceaa74f3530687d47f/) | XGBoost and LightGBM ensemble forecasts temperature and humidity (R² above 0.99) | Offline, no control, no on-chip run reported |
| [Bua 2025, Future Internet](https://doi.org/10.3390/fi17050214) | Low-complexity fuzzy-neural microclimate prediction for edge devices, 4 greenhouses | Prediction only |

### Small models that switch actuators
| Paper | What it did | What it did not do |
|---|---|---|
| [Ihoume 2022, Artificial Intelligence in Agriculture](https://consensus.app/papers/details/c95c3a25b17556048c7f09fbc94ca22f/) | 151-parameter MLP maps sensor readings to 5 actuator actions in a strawberry greenhouse, 96 % accuracy against labels | Learns labels, not dynamics. Accuracy against labels, not climate outcome |
| [Sukowati 2026, JNTETI](https://doi.org/10.22146/jnteti.v15i3.25532) | K-NN on an ESP32 replaces thresholds for mushroom climate control including a mist maker; 15 KB, 12 ms | 81 expert-defined classes, so it reproduces rules. No learning of the box, no comparison of climate outcome |
| [Taueatsoala 2026, arXiv](https://consensus.app/papers/details/6d48b01ca0b55ae5af1841c2ca980fe4/); [Surbakti 2025](https://consensus.app/papers/details/ef3cd467c38853e0ac4b92d0a5c9acea/) | TinyML irrigation decisions on an ESP32 | Irrigation, offline-trained, static models |

### Learning on the chip itself (on-device training)
| Paper | What it did | What it did not do |
|---|---|---|
| [TinyOL, Ren 2021, IJCNN](https://consensus.app/papers/details/f8192e6960b552e8bec8870ba02a616e/) | Incremental training on a microcontroller from streaming data | Generic benchmarks |
| [Disabato 2021, IEEE TNNLS](https://consensus.app/papers/details/00d2f470b79a50479c311df33ccee649/) | TinyML that adapts to concept drift. It names sensor or actuator faults as one cause of drift | Image and audio benchmarks |
| [TyBox, Pavan 2023, ACM TECS](https://consensus.app/papers/details/bc8f2bcc60eb5298a1b850085c9bfe05/) | Generates code for incremental on-device learning | Classification tasks, not control |

The OpenAlex curve for on-device training on agricultural sensors found 14 strict matches (4, 1, 6, 3 papers from 2023 to 2026), none of them about climate. The tool warns the strict count undercounts, so read this as "rare", not "zero".

### Predictive control and learned control for greenhouses
| Paper | Where it runs |
|---|---|
| [Morcego 2023, Computers and Electronics in Agriculture](https://consensus.app/papers/details/0ce743c3715358a0b2a7e6439aeed913/): reinforcement learning versus MPC | Simulation |
| [Ajagekar 2022](https://consensus.app/papers/details/3018f7fd737a53fbbd27aabe566cd191/), [Mallick 2024](https://consensus.app/papers/details/db6c7819526258c689708fe8da2459c8/): deep RL and RL-tuned MPC | Simulation |
| [Ito 2021](https://consensus.app/papers/details/487053cdc2d35a2db95a9d8e795e73bd/): MPC for a small greenhouse with cheap humidifiers | Simulation |
| [Li 2026, Agriculture](https://consensus.app/papers/details/c35addd05e0953f199f05c4bee662c14/): predictive fuzzy PID | Industrial PLC, real greenhouse |
| [El Ghoumari 2005, Computers and Electronics in Agriculture](https://consensus.app/papers/details/d1517a9462aa522abf26b1eafccac2e3/): real-time MPC of air temperature | PC, research greenhouse |
| [Sun 2023](https://consensus.app/papers/details/1b9bc12e5d6253a6b1c4d84833a41887/): grey-box humidity model, identified automatically, runs on an STM32 | A room humidifier; plans when to start, no plants, no faults |

### A warning worth citing
[Bicski 2023, IEEE Internet of Things Magazine](https://consensus.app/papers/details/5493bd3f76b25efbba536adeedc4271b/) found a simple autoregressive model beat an autoencoder by up to 7.2 % for anomaly detection on industrial time series, and ran faster. Any claim that "AI" helps must be tested against simple models and plain rules.

## 3. What is not done

1. **A humidity model of a misted enclosure that the ESP32 learns by itself, and keeps updating while it runs.** Existing on-chip greenhouse models are trained once on a PC and then frozen.
2. **Using that learned model to control the mister predictively** on the chip: choosing the burst length that reaches the target without overshoot. Predictive humidity control exists only in simulation, on PCs or on PLCs.
3. **Using the same model to separate normal slow change from faults.** The plant grows and the weather changes, and the model should follow that. A dead mister or a stuck sensor is sudden, and it should raise a fault. Disabato 2021 names this problem but tests it only on image and audio data.
4. **Measured climate outcome against the current hysteresis controller on the same hardware.** Every TinyML control paper above reports model accuracy, not time in band, overshoot, switch count or water used.

## 4. What we build: one tiny self-learning model with three jobs

**The model.** The next humidity reading is predicted from the last few readings, whether the mist and fan are on, and the temperature. Start with a linear model of about 6 numbers, updated on the chip after every reading by recursive least squares. That update needs a few dozen multiplications and under 1 KB of memory. As a comparison, also run a small neural network (about 100 to 200 parameters) trained on the laptop and deployed with TensorFlow Lite Micro or EloquentTinyML. If the neural net does not beat the linear model, report that honestly (see Bicski 2023).

**Job 1, predictive misting.** Before each burst, the chip asks the model how long to mist to land in the target band. This replaces the fixed "mist until 90 %, then 3-minute cooldown" rule.

**Job 2, fault detection.** A large, sudden gap between prediction and reading means a fault. The self-healing plan in [self-healing-gap-check.md](self-healing-gap-check.md) takes over from here.

**Job 3, adapting to slow change.** Slow drift in the model's numbers is accepted as normal. Examples are the plant growing, the room warming and the water level dropping. Logging those numbers shows the box changing over days, which is a result in itself.

**Baselines:** the current firmware (hysteresis 75 to 90 % with a 5-minute cap and 3-minute cooldown), and the same predictive controller with the model frozen after day 1.

**Metrics:** time in the humidity band, overshoot above the upper limit, mist switch-ons per day, mist minutes (water), model prediction error over time, fault detection delay and false alarms.

## 5. Resources

| Item | Status |
|---|---|
| ESP32 | Have. Recursive least squares is trivial for it; a small neural net fits easily |
| BME280, mist module, exhaust fan, logging over USB | Have |
| arduino-cli and Python on the laptop | Have (`tools/arduino-cli.exe`) |
| Reference humidity sensor (SHT31 or second BME280) | **Buy, about 500 to 700 taka**. Needed to score predictions honestly, and shared with the self-healing study |
| TensorFlow Lite Micro or EloquentTinyML library | Free, Arduino library |

## 6. Time (about two weeks, shares data with the self-healing study)

| Days | Work |
|---|---|
| 1 to 3 | Log normal operation with the current controller. This is also baseline data |
| 4 | Fit the linear and neural models on the laptop, compare them, port the chosen one and the on-chip update |
| 5 to 8 | Run the predictive controller for 3 days, then repeat the fault injections from the self-healing plan with the learned model as detector |
| 9 to 14 | Analysis and writing |

## 7. Risks

- **"Self-tuning control is 50 years old."** True. The contribution is not the algorithm. It is a learned, updating model driving an ultrasonic mister on a microcontroller, one model doing control and diagnosis, and a measured climate outcome against the controller everyone in this niche uses. Cite the classic adaptive-control lineage openly.
- **Predictive misting gives only a small gain over hysteresis.** Report the size of the gain, whatever it is. Fewer switch-ons and less water at the same time in band is still useful.
- **One box.** Run the predictive and baseline controllers on alternating days and report day-by-day results.

## 8. How this fits with the self-healing paper

Both studies use the same logs, the same reference sensor and the same fault campaign. Two options:

- **One stronger paper:** "A self-learning, self-healing mist controller on a low-cost microcontroller." Target: Computers and Electronics in Agriculture, which published Linker 2000, Shekarian 2024, El Ghoumari 2005 and Morcego 2023.
- **Two papers:** the self-healing study in Computers and Electronics in Agriculture, and the on-device learning study in Smart Agricultural Technology or the IEEE Internet of Things Journal.

## 9. Deep Search questions for Consensus

All three were run on 2026-09-24. Results, links and the confirmed gap are in [publication-plan.md](publication-plan.md), sections 1 and 3.

1. What methods have been used to train or update machine learning models directly on microcontrollers for environmental control, and how were they evaluated?
2. Has model predictive or learning-based humidity control been implemented on low-cost microcontrollers with ultrasonic humidifiers, and what performance did it achieve compared with on/off control?
3. How do studies distinguish sensor or actuator faults from normal concept drift in embedded or IoT control systems?
