# Literature Survey and Gap Analysis — IoT Terrarium Controller

*Compiled 14 Sep 2026 from OpenAlex / Semantic Scholar records (DOI-verified) plus web checks. Every entry links to its DOI. Abstracts are condensed in our own words, not copied; open the link for the original text. Papers marked ★ are the 22 I recommend you actually cite; the rest are supporting.*

---

## 0. The one-page read

**Who is closest to you.** Nine papers build automated *terrariums* (2020–2025). All of them are simple: single-threshold or fuzzy control, DHT11/DHT22 sensors, cloud dashboards (Firebase, Blynk, Node-RED), evaluations of a few hours to two weeks, and **no** safety interlocks, **no** bounded actuation, **no** offline operation, **no** run-time configuration, and **no** comparison against a baseline controller. Gap-saturation check: only 2–3 indexed papers per year on "IoT terrarium automation" — the niche is open but being entered (three papers in 2025 alone), so publish soon.

**What the wider field already knows (and you should build on).**
- Capacitive soil probes need substrate-specific calibration; air/water two-point calibration is the weakest accepted method (papers 26–30 report RMSE, R², sensor-to-sensor CV).
- Low-cost RH/temperature sensors must be validated against a reference (paper 18 does >500 observations + ANOVA; paper 30 reviews calibration practice).
- Controller comparisons are done at greenhouse scale (MPC vs relay saves 30 % energy, paper 22; sensor-based vs timer irrigation, paper 23) — **nobody has done this at terrarium scale.**

**Your defensible contributions (ranked by how much reviewers will value them):**
1. **Controller comparison on identical hardware**: timer vs single-threshold vs your hysteresis-with-bounded-bursts, measured over 48 h each (time-in-band, actuator switch count, mist run-time = water use, overshoot). Nobody in the niche has this.
2. **Fail-safe design with fault-injection evidence**: tank-empty, leak, sensor loss, Wi-Fi loss, power loss — what the system does and how fast. Absent from every terrarium paper.
3. **Local-first architecture** (on-device rules + hotspot + USB provisioning) with measured availability and command latency vs a cloud path. Every competitor is cloud-dependent.
4. **Proper sensor calibration/validation** (gravimetric soil calibration in your substrate; BME280 vs reference via saturated-salt humidity standards).
5. **Open, reproducible hardware/firmware** (you already have the repo, wiring, BOM, tools) — this is exactly what HardwareX / AgriEngineering "technical note" formats want.

**Minimum to be publishable:** items 1, 2 and 4 with real numbers. Item 3 strengthens; item 5 is nearly done.

---

## 1. Terrarium-specific systems (closest neighbours)

### 1. AquaFlora Smart Terrarium (2025) ★
**A. K. Bandara, N. H. Mohamed Halip, T. Purnshatman et al.**, "AquaFlora Smart Terrarium: A Self-Sustaining IoT-based Terrarium for Smart Ecosystem Management," *JOIV Int. J. Informatics Visualization*, vol. 9, no. 4, 2025. https://doi.org/10.62527/joiv.9.4.3403
**Summary.** ESP32 terrarium with a capacitive soil probe, DHT22 and BH1750, driving four actuators (light, humidifier, irrigation, cooling). Control and monitoring through a mobile app and Node-RED over Firebase and MQTT. A 10-hour automatic-mode run kept soil above 60 %, temperature 30.1–33.1 °C, RH 69.1–74.0 %, light 23–175 lux.
**Gaps.** 10-hour evaluation only; control law is not described beyond "automatic mode" (no hysteresis, bursts or caps); cloud-dependent (Firebase/MQTT); no interlocks for reservoir or leakage; sensors uncalibrated; no baseline comparison. RH stayed *below* the 75–90 % tropical band, which they do not discuss.
**Use.** Your primary "nearest neighbour". Your positioning table should contrast directly with it.

### 2. Fuzzy-logic plant environment automation as a basis for smart terrariums (2025) ★
**M. F. Z. Rahman, R. Satwika, S. Achmad**, IEEE Int. Conf. on Artificial Intelligence and Smart Devices (ICAISD), 2025. https://doi.org/10.1109/ICAISD68166.2025.11385768
**Summary.** ESP32 with DHT11, resistive soil sensor and LDR; a fuzzy inference system drives a fan, pump and grow lamp; Blynk provides remote monitoring and manual override. Results are qualitative: fan runs when hot, pump when dry, lamp when dark.
**Gaps.** No quantitative performance (no time-in-band, no error metrics); DHT11 (±5 % RH) and resistive soil sensor (corrodes); cloud-dependent; no safety logic; fuzzy rules are not compared with simpler control.
**Use.** Represents the "fuzzy" alternative; your comparison experiment can include a fuzzy variant or argue hysteresis achieves the same non-chatter behaviour with zero tuning.

### 3. IoT-driven plant care in terrariums (2025) ★
**D. Septiawan, Misbahuddin, G. W. Wiriasto**, *Int. J. Electrical, Energy and Power System Engineering*, vol. 8, no. 1, pp. 72–85, 2025. https://doi.org/10.31258/ijeepse.8.1.72-85
**Summary.** ESP32 with DHT11 and YL-69 resistive soil sensor, relay and mini pump; Android app via Firebase. A 14-day observation of a Rombusa plant suggested optimal soil moisture of 60–70 % (mean 65 %).
**Gaps.** Single actuator (pump); humidity and light are monitored, not controlled; resistive probe; cloud-only; no interlocks; no calibration; n = 1 plant, no control group.
**Use.** Evidence that the niche evaluates on single plants over short windows; your 48-h controlled comparison is a step up.

### 4. Sugeno fuzzy humidity and moisture control in a terrarium (2024) ★
**D. S. M. Cahyani, M. Ikhsan**, *Int. J. Recent Technology and Applied Science (IJORTAS)*, vol. 6, no. 2, 2024. https://doi.org/10.36079/lamintang.ijortas-0602.711
**Summary.** Humidity and temperature readings feed a Sugeno fuzzy controller that decides irrigation actions; tests under several ambient conditions reportedly kept humidity within limits with "low error".
**Gaps.** No numeric error, no dataset, no actuator-cycle analysis; humidity is regulated through irrigation rather than misting; no interlocks or offline mode.
**Use.** Second fuzzy-terrarium reference; together with #2 shows the field reaching for fuzzy without benchmarking it.

### 5. IoT automation of temperature, humidity and lighting in a terrarium (2024)
**Q. T. Yoastha, I. Nirmala, Suhardi**, *J. Information System Research (JOSH)*, vol. 5, no. 4, 2024 (Indonesian). https://doi.org/10.47065/josh.v5i4.5335
**Summary.** DHT22 and LDR; automatic watering on "abnormal" humidity and light adjusted to room brightness; web page and LCD display. Reports sensor accuracies of 97.45 % (RH), 98.51 % (light) and 98.61 % (ultrasonic level).
**Gaps.** "Accuracy" figures are agreement with a handheld meter, not calibration; threshold control; no hysteresis, caps or safety logic; short tests.
**Use.** Shows that even "accuracy" claims in the niche are informal — motivates your reference-based validation.

### 6. Smart TERRY — autonomous smart terrarium for bearded dragons (2024)
**W. P. Rey, A. C. Villaluz, K. W. J. D. Rey**, IEEE Int. Conf. on Information and Communication Technology (ICICT), 2024. https://doi.org/10.1109/ICICT62343.2024.00076
**Summary.** Reptile terrarium manager with sensors/actuators, mobile app, air-quality analysis, feeding management and alerts; evaluated with a 30-participant PSSUQ usability questionnaire.
**Gaps.** Animal (not plant) enclosure; evaluation is usability, not control performance; cloud app.
**Use.** Shows the reptile branch of the niche and that user-acceptance evaluation is accepted in these venues (your survey can be framed the same way).

### 7. Fuzzy-controlled terrarium for Sulcata tortoise hatchlings (2025)
**S. S. Al Ayyubi, P. Rusimamto**, *Jurnal Teknik Elektro*, vol. 14, no. 2, pp. 122–130, 2025 (Indonesian). https://doi.org/10.26740/jte.v14n2.p122-130
**Summary.** IoT terrarium where a fuzzy controller drives a **mist maker** and an incandescent lamp from DS18B20 and DHT22 readings; reports holding the basking temperature within 0.7 °C and humidity within 1 % of set-point during daytime.
**Gaps.** Animal enclosure; daytime only; no soil or light sensing; no interlocks; no offline path.
**Use.** The only neighbour that also uses an ultrasonic mist maker as the humidity actuator — cite when justifying your actuator choice.

### 8. Multi-sensor reptile terrarium on ATMEGA328 (2024)
**R. P. Pirdaus, B. Rahmani**, *Jutisi*, vol. 13, no. 1, 2024. https://doi.org/10.35889/jutisi.v13i1.1871
**Summary.** DHT11 and GUVA-S12SD UV sensor on an ATmega328; fan and humidifier for temperature/humidity, UVA/UVB lamps switched when external UV is low. Authors note the fan is "not optimal at extreme temperatures" and the humidifier "requires regular monitoring".
**Gaps.** Their own limitations are exactly your interlock/monitoring contribution (humidifier running unattended); no connectivity; 8-bit MCU.
**Use.** Quote their stated limitation as motivation for reservoir/leak interlocks.

### 9. Low-cost compact horticultural chamber for tropical highland flora (2020) ★
**M. Wrazidlo, A. Bzymek**, *Technologies*, vol. 8, no. 4, art. 62, 2020. https://doi.org/10.3390/technologies8040062
**Summary.** Desktop environmental chamber that partially automates conditions for tepui-highland genera (Heliamphora, Drosera, Utricularia…), designed for amateur cultivation at minimum cost; evaluation is a set of functional tests judged "satisfying".
**Gaps.** No IoT/remote interface; no quantitative control metrics; no calibration; no safety features.
**Use.** The closest "tropical specialist plant enclosure" reference in a reputable MDPI venue — good for motivating species-specific micro-climate bands.

*Web-found but not indexed (verify before citing):* "Developing a low-cost Smart Terrarium in the Context of Home Automation Applications" (STM32F407, ~15 % energy reduction, ResearchGate 2021) and "Humidity and Temperature Control System for Terrarium" (Arduino, DHT11, humidifier + fan on relays, ResearchGate 2020). Both are on ResearchGate only: https://www.researchgate.net/publication/350843466 and https://www.researchgate.net/publication/383749475 .

---

## 2. Small-scale indoor plant systems and growth chambers

### 10. P4L — IoT-based indoor plant care system (2023) ★
**G. Guerrero-Ulloa, M. A. Méndez García, V. Torres et al.**, *J. Ambient Intelligence and Smart Environments*, 2023. https://doi.org/10.3233/AIS-220483
**Summary.** Automated care of potted plants for indoor air quality, built from Arduino-compatible parts, developed with a test-driven methodology (TDDM4IoTS); validation is a survey of developers who used the methodology.
**Gaps.** Validation is about the software method, not plant-environment performance; no control-law analysis.
**Use.** Cite for the indoor-plant motivation and to contrast "methodology-validated" with your "measurement-validated" work.

### 11. Personalized smart flowerpot with 3D printing and cloud (2023)
**Y. Li, J. Luo, Z. Liu et al.**, *Sensors*, vol. 23, no. 13, art. 6116, 2023. https://doi.org/10.3390/s23136116
**Summary.** FDM-printed pot with an Arduino framework monitoring soil moisture, temperature, humidity and light; data to Bamfa Cloud over Wi-Fi; app control of watering and lighting.
**Gaps.** Monitoring-first; cloud-only; no closed-loop evaluation; no safety logic.
**Use.** Shows the "smart pot" branch; your enclosure-level closed loop is a superset.

### 12. PlantTalk — smartphone-based intelligent hydroponic plant box (2019) ★
**L.-D. Van, Y.-B. Lin, T.-H. Wu et al.**, *Sensors*, vol. 19, no. 8, art. 1763, 2019. https://doi.org/10.3390/s19081763
**Summary.** IoT plant box whose control intelligence (LED, spray, pump) is configured and even programmed in Python from a smartphone; demonstrated CO₂ reduction 53 % faster than a conventional plant system.
**Gaps.** Requires a smartphone/server infrastructure (IoTtalk); not designed for offline operation; no fail-safe discussion.
**Use.** Precedent for "user-configurable control at run time" — your NVS-stored 14 parameters are the lightweight version.

### 13. Low-cost controlled-environment growth chamber for mother plants (2025) ★
**J. Guerrero-Sánchez, C. A. Olvera-Olvera, L. O. Solís-Sánchez et al.**, *AgriEngineering*, vol. 7, no. 6, art. 177, 2025. https://doi.org/10.3390/agriengineering7060177
**Summary.** Technical note: insulated chamber with LED lighting, extractor ventilation, recirculating irrigation and Arduino UNO monitoring; a Stevia mother plant kept 30 days; full schematics and BOM provided for replication. Authors state no replication or control group.
**Gaps.** Monitoring rather than closed-loop regulation; no interlocks; single plant, no statistics.
**Use.** A model for the *format* you can target (technical note with full replication package) and for what reviewers accept as preliminary validation.

### 14. Cutting Development Chamber with AI-ready data collection (2025)
**J. G. Ávila-Sánchez, M. J. López-Martínez, V. Maeda-Gutiérrez et al.**, *Inventions*, vol. 10, no. 6, art. 108, 2025. https://doi.org/10.3390/inventions10060108
**Summary.** Modular propagation chamber holding humidity, temperature and light for cuttings, logging labeled images and environmental records (6 579 images, 67 919 records in validation with Aloysia and Stevia).
**Gaps.** Research-grade cost/complexity; no offline/consumer angle; control law not benchmarked.
**Use.** Benchmark for data-logging depth; motivates adding on-device logging to your system.

### 15. Smart indoor gardening with renewable energy (2024)
**T. Alrawashdeh, I. Alkore Alshalabi, M. Al-Jaafreh et al.**, *Bulletin of Electrical Engineering and Informatics*, vol. 13, no. 3, 2024. https://doi.org/10.11591/eei.v13i3.7101
**Summary.** IoT indoor growing system with sensors, actuator-driven feeding, solar power and cloud analysis via a website.
**Gaps.** Cloud-dependent; little quantitative control evaluation.
**Use.** Supporting reference for the indoor-growing trend.

---

## 3. Greenhouse controllers and control strategies

### 16. IoT-based greenhouse monitoring and control system (2023) ★
**V. W. Oguntosin, C. Okeke, E. Adetiba, A. Abdulkareem, J. O. Olowoleni**, *Int. J. Computing and Digital Systems*, vol. 14, no. 1, 2023. https://doi.org/10.12785/ijcds/140137
**Summary.** ESP32 reads temperature, humidity, LDR and resistive soil moisture; bulb, fan and pump switch on fixed thresholds; data stored in a database and shown on a web app.
**Gaps.** Compiled thresholds, single-sided switching, no reservoir protection, cloud database.

### 17. ESP32 smart drip irrigation and climate monitoring in greenhouses (2025) ★
**J. J. Correa-Quiroz, M. A. Toribio-Barrueto, C. Castro-Vargas**, *Emerging Science Journal*, vol. 9, no. 3, pp. 1133–1157, 2025. https://doi.org/10.28991/esj-2025-09-03-01
**Summary.** DHT11, UV, capacitive soil and ultrasonic level sensors, LCD, Arduino Cloud; automatic and manual modes; field tests showed 35 % lower water use than traditional practice.
**Gaps.** Cloud-dependent remote control; no bounded actuation or interlocks beyond level sensing.
**Use.** The 35 % figure is the kind of headline metric your timer-vs-controller experiment should produce.

### 18. Low-cost greenhouse IoT with statistically validated sensors and fuzzy control (2026) ★
**E. Wayo, S. Ruang-on, K. Songsri-in et al.**, *Int. J. Smart Sensing and Intelligent Systems*, 2026. https://doi.org/10.2478/ijssis-2026-0008
**Summary.** Each low-cost sensor validated with >500 observations and one-way ANOVA against reference instruments (deviation <3 %); fuzzy controller from agronomic thresholds; temperature 33→29 °C in 7 min, soil 38→60 % in 12 min; actuator response 2.3 s; <1 kWh/day; US$47.10 build.
**Gaps.** Greenhouse cucumber, not an enclosed terrarium; fuzzy not compared with hysteresis; no fail-safe analysis.
**Use.** The **methodological template** for your sensor-validation section (n, ANOVA, deviation) and for reporting response times and energy.

### 19. Fuzzy logic and IoT in a small-scale smart greenhouse (2024)
**V. Thomopoulos, F. Tolis, T.-F. Blounas et al.**, *Smart Agricultural Technology*, vol. 8, art. 100446, 2024. https://doi.org/10.1016/j.atech.2024.100446
**Summary.** Fuzzy controller integrated with a small greenhouse and IoT ecosystem; pilot demonstrates self-regulating micro-climate feasibility.
**Gaps.** Feasibility-level results; no quantitative comparison against simpler control.

### 20. NodeMCU greenhouse monitor with GSM alerts and CNN disease detection (2021) ★
**A. Mellit, M. Benghanem, O. Herrak, A. Messalaoui**, *Energies*, vol. 14, no. 16, art. 5045, 2021. https://doi.org/10.3390/en14165045
**Summary.** Air temperature, RH, capacitive soil moisture, light and CO₂ published to a web page; GSM anomaly alerts; Raspberry Pi camera with CNN for disease; PV-powered.
**Gaps.** Two-processor architecture and cellular alerts push cost far above a home enclosure; control rules simple.

### 21. Single-neuron PID temperature/humidity regulation in solar greenhouses (2024) ★
**S. Huang, H. Xiang, C. Leng et al.**, *Electronics*, vol. 13, no. 11, art. 2083, 2024. https://doi.org/10.3390/electronics13112083
**Summary.** HC32F460 MCU with RT-Thread running a single-neuron PID; against conventional PID the temperature RMSE fell from 1.594 to 0.734 (50.2 % precision improvement), with faster vent response.
**Gaps.** Requires modulating actuators (vents); mist makers and fans in a terrarium are on/off, so PID is not directly applicable.
**Use.** Cite when explaining why you chose hysteresis/on-off over PID for switched actuators — and as the metric style (RMSE) to report.

### 22. Model predictive control versus relay control in a greenhouse (2021) ★
**C. Bersani, M. Fossa, A. Priarone et al.**, *Energies*, vol. 14, no. 11, art. 3353, 2021. https://doi.org/10.3390/en14113353
**Summary.** MPC on a ground-source heat pump in a 15.3 × 9.9 m greenhouse tracked a temperature profile and saved about 30 % electric power over 20 h compared with reactive relay control.
**Gaps.** Requires a plant model and compute; unrealistic for a 5-litre enclosure on an ESP32.
**Use.** The key precedent that *controller-vs-controller* comparison is publishable; frame your work as the terrarium-scale analogue (hysteresis vs threshold vs timer).

### 23. Sensor-based vs time-based irrigation scheduling (2021) ★
**M. Mohammed, K. Riad, N. K. Alqahtani**, *Sensors*, vol. 21, no. 12, art. 3942, 2021. https://doi.org/10.3390/s21123942
**Summary.** Cloud-controlled subsurface irrigation for date palms; sensor-based scheduling cut water by 64.1 % and time-based by 61.2 % versus surface irrigation; water productivity 1.783 vs 1.44 kg/m³.
**Gaps.** Field scale, ThingSpeak cloud.
**Use.** Direct template for your "timer vs sensor-driven misting" experiment (report water volume and time-in-band).

### 24. ESP32 hydroponics monitor with Blynk (2023) ★
**A. Abu Sneineh, A. A. A. Shabaneh**, *MethodsX*, vol. 11, art. 102401, 2023. https://doi.org/10.1016/j.mex.2023.102401
**Summary.** TDS, pH, water-level and temperature sensors; pumps triggered automatically on deviation or manually through Blynk.
**Gaps.** Cloud-hosted control; no time limits on actuation.

### 25. IoT-equipped smart greenhouse survey and other anchors
See Section 5 for the survey papers (31–35) that the recent greenhouse literature cites in common.

---

## 4. Soil-moisture and low-cost sensor calibration

### 26. Characterization of low-cost capacitive soil-moisture sensors (2020) ★
**P. Placidi, L. Gasperini, A. Grassi et al.**, *Sensors*, vol. 20, no. 12, art. 3585, 2020. https://doi.org/10.3390/s20123585
**Summary.** Experimental characterization of a commercial coplanar capacitive probe; for a defined soil with constant solid-to-volume ratio the output voltage relates reliably to gravimetric water content.
**Gaps.** Single soil type; lab conditions.
**Use.** Justifies substrate-specific calibration.

### 27. Calibration and validation of SEN0193 for automated monitoring (2019) ★
**E. A. A. D. Nagahage, I. S. P. Nagahage, T. Fujino**, *Agriculture*, vol. 9, no. 7, art. 141, 2019. https://doi.org/10.3390/agriculture9070141
**Summary.** Soil-specific calibration of the SKU:SEN0193 probe against gravimetric measurement and a Delta-T SM-200; RMSE 0.09 (sensor), 0.07 (SM-200 factory) and 0.06 cm³ cm⁻³ (SM-200 soil-specific) across dry-to-saturated, and 0.05 / 0.08 / 0.03 in the field-capacity range.
**Use.** Method and metric (RMSE in cm³ cm⁻³) to copy for your probes.

### 28. Calibration of low-cost capacitive probes for irrigation management (2025) ★
**A. A. Abdelmoneim, C. M. Al Kalaany, R. Khadra et al.**, *Sensors*, vol. 25, no. 2, art. 343, 2025. https://doi.org/10.3390/s25020343
**Summary.** Twelve SEN0193 units, three replicas each at five gravimetric moisture levels (5–40 %) in loamy silt; generalized calibration R² 0.85–0.87, RMSE 4.5–4.9 %; sensor-to-sensor CV 10–16 % above 30 % moisture and 6.5–10.3 % below.
**Use.** Gives the sensor-to-sensor variability argument for calibrating *each* probe (you have two).

### 29. Calibration of an Arduino-based capacitive probe across soil textures (2022) ★
**I. M. Kulmány, Á. Bede-Fazekas, A. Beslin et al.**, *J. Hydrology and Hydromechanics*, 2022. https://doi.org/10.2478/johh-2022-0014
**Summary.** Repeatability/reproducibility study on clay loam, sandy loam and silt loam against thermogravimetry; probe response differs by texture; polynomial texture-specific calibration reaches R² ≥ 0.89.
**Use.** Supports a polynomial (not linear) fit if your terrarium substrate shows curvature.

### 30. Low-cost soil and ambient monitoring with a novel fitting procedure (2021)
**P. Placidi, R. Morbidelli, D. Fortunati et al.**, *Sensors*, vol. 21, no. 15, art. 5110, 2021. https://doi.org/10.3390/s21155110
**Summary.** LoRaWAN network of off-the-shelf sensors compared against a Sentek reference in two soils; good temperature agreement, non-constant sensitivity of the low-cost VWC probe, and a new non-linear parameter-fitting procedure.
**Use.** Shows reference comparison over a continued experiment — the standard you should meet.

### 31. Systematic review of low-cost air-temperature sensors and calibration (2025) ★
**J. A. Abdinoor, Z. Hashim, B. Horváth et al.**, *Atmosphere*, vol. 16, no. 7, art. 842, 2025. https://doi.org/10.3390/atmos16070842
**Summary.** PRISMA review (2015–2024) of 22 commercial low-cost sensors; DHT22 the most used; calibration models fall into linear, polynomial and machine-learning; reporting is heterogeneous and many studies skip calibration.
**Use.** Cite to justify validating the BME280 and to pick a reporting format (MAE/RMSE against a reference).

---

## 5. Surveys and platform references (related-work anchors)

### 32. IoT-based smart irrigation systems: sensors and IoT trends (2020) ★
**L. García, L. Parra, J. M. Jiménez, J. Lloret, P. Lorenz**, *Sensors*, vol. 20, no. 4, art. 1042, 2020. https://doi.org/10.3390/s20041042 — survey of sensed parameters, nodes and wireless technologies; establishes that calibrated low-cost capacitive probes are acceptable for scheduling.

### 33. IoT in greenhouse agriculture: enabling technologies, applications, protocols (2022) ★
**M. S. Farooq, S. Riaz, M. Abu Helou et al.**, *IEEE Access*, vol. 10, 2022. https://doi.org/10.1109/ACCESS.2022.3166634 — hierarchy of IoT-greenhouse components, cloud/edge, protocols, mobile apps, open issues. A "common ancestor" cited by most recent greenhouse papers.

### 34. Multi-sensor monitoring, intelligent control and data processing for smart greenhouses (2025) ★
**E. Bicamumakuba, M. N. Reza, H. Jin et al.**, *Sensors*, vol. 25, no. 19, art. 6134, 2025. https://doi.org/10.3390/s25196134 — review of 114 studies: sensors, control (IoT automation, fuzzy, MPC, RL) and filtering (Kalman, AI); finds calibration and interoperability as the main sensing challenges and computational cost as the control challenge.

### 35. Greenhouse control strategies and modelling techniques review (2025)
**K. Li, J. Shi, C. Hu et al.**, *Agriculture*, vol. 15, no. 20, art. 2135, 2025. https://doi.org/10.3390/agriculture15202135 — PID/fuzzy/MPC vs adaptive, neural and RL control; useful to state where simple hysteresis sits and why it fits tiny enclosures.

### 36. Design and implementation of ESP32-based IoT devices (2023) ★
**D. Hercog, T. Lerher, M. Truntič, O. Težak**, *Sensors*, vol. 23, no. 15, art. 6739, 2023. https://doi.org/10.3390/s23156739 — platform justification for the ESP32.

---

## 6. Positioning matrix (terrarium neighbours vs. this work)

| # | Work | MCU | Sensors | Control law | Interlocks | Offline control | Run-time config | Evaluation | Calibration |
|---|---|---|---|---|---|---|---|---|---|
| 1 | AquaFlora 2025 | ESP32 | cap. soil, DHT22, BH1750 | threshold ("auto mode") | none | no (Firebase/MQTT) | no | 10 h | no |
| 2 | Rahman 2025 | ESP32 | DHT11, soil, LDR | fuzzy | none | no (Blynk) | no | qualitative | no |
| 3 | Septiawan 2025 | ESP32 | DHT11, YL-69 | threshold | none | no (Firebase) | no | 14 d, 1 plant | no |
| 4 | Cahyani 2024 | n/s | RH, T | Sugeno fuzzy | none | n/s | no | "low error" | no |
| 5 | Yoastha 2024 | n/s | DHT22, LDR | threshold | none | web + LCD | no | short | meter comparison |
| 7 | Al Ayyubi 2025 | n/s | DS18B20, DHT22 | fuzzy (mist maker) | none | n/s | no | daytime | no |
| 8 | Pirdaus 2024 | ATmega328 | DHT11, UV | threshold | none | none | no | short | no |
| 9 | Wrazidlo 2020 | n/s | T, RH | partial automation | none | none | no | functional | no |
| — | **This work** | ESP32 | BME280, BH1750, 2× cap. soil, leak, float | hysteresis + bounded bursts + daily cap + photoperiod | float, leak, time-outs, fail-safe on sensor loss | yes (hotspot + USB) | 14 params in NVS | *to be done: 48 h × 3 controllers* | *to be done: gravimetric + reference RH* |

The two italic cells are what stands between you and a paper.

---

## 7. What to add or change to make it publishable

### 7.1 Experiments (in priority order)

**E1 — Controller comparison on the same enclosure (the core result).**
Run three controllers for 48 h each on the same terrarium, same plant, same season: (a) fixed timer misting (the commercial baseline, e.g. 30 s every 2 h), (b) single-threshold on/off at 80 % RH, (c) your hysteresis 75/90 % with 5-min burst cap and 3-min cool-down. Log every 30 s. Report: % time inside 70–90 % RH, RH mean and standard deviation, number of actuator switch events per day, total mist run-time (∝ water and disc wear), largest overshoot, and the same for soil moisture. Precedent: papers 22 and 23. Expected story: hysteresis matches the threshold controller on time-in-band with far fewer switch events and less water than the timer.

**E2 — Fault-injection / fail-safe tests.**
Six scripted faults: reservoir empty (float), leak probe wet, BME280 unplugged mid-run, soil probe disconnected (reads ~2490), Wi-Fi router off, power cut and restore. For each, record what the outputs did and the reaction time from the serial log. Present as a table; no terrarium paper has one. Ties your firmware details (three-bad-reads rule, boot-safe outputs, NVS restore) to evidence.

**E3 — Sensor calibration and validation.**
Soil: gravimetric calibration in *your* substrate — five moisture levels × three samples per probe, oven-dry to get true water content, fit linear and polynomial, report R² and RMSE (papers 27–29). Air: check the BME280 against saturated-salt humidity standards, a cheap and accepted method (NaCl ≈ 75.3 % RH, MgCl₂ ≈ 32.8 % RH at 25 °C, sealed jar overnight) and against the HTC-2 or any reference hygrometer; report MAE. This converts your "±3 % datasheet" claim into measured data (paper 18 style).

**E4 — Local-first vs cloud path.**
Measure command-to-actuation latency over the hotspot, over the home LAN, and (for comparison) via a Blynk/Firebase round trip you set up once; measure availability during a deliberate 1-hour internet outage (your system: 100 %; cloud path: 0 %). Small table, strong argument.

**E5 (optional, adds weight) — Plant response.**
Three to four weeks of your Fittonia under the controller vs a second Fittonia under manual care: weekly photos, leaf count, wilting events. Paper 3 did 14 days on one plant; two plants with a control already beats it.

**E6 — Spatial humidity gradient.** Add the second BME280 you own at the far corner; report the top-to-bottom RH difference. Turns a limitation into a result.

### 7.2 Design changes worth making before the runs
- **On-device data logging** (CSV to flash or to the console app every 30 s). Without it E1–E6 cannot be reported. Paper 14 logged ~68 000 records; you need a few thousand.
- **Reservoir weighing or a level scale** so water use is measured, not inferred from run-time (paper 23 reports m³ per palm; you report mL per day).
- Keep the **second RH sensor** for E6.
- Freeze the firmware version used for all runs and tag it in the repo (reviewers ask).

### 7.3 Framing and title
Candidate title: *"A Fail-Safe, Local-First Closed-Loop Controller for Tropical Plant Terrariums: Hysteresis Control with Safety Interlocks on a Low-Cost ESP32 Platform."*
Novelty statement (three sentences reviewers can check): existing terrarium automation (1–9) uses single thresholds or fuzzy rules, cloud dashboards and short uncalibrated evaluations; we contribute a bounded hysteresis control scheme with hardware interlocks and offline operation, and we are the first to compare timer, threshold and hysteresis control on identical terrarium hardware with calibrated sensors and fault-injection tests.

### 7.4 Where to submit (realistic for this scope)
- **HardwareX** (Elsevier, open hardware; wants BOM, build instructions, validation — you already have the repo, wiring page, tools). Best fit if E1–E3 are done.
- **AgriEngineering** or **Smart Agricultural Technology** (technical note / short article; papers 13 and 19 are there).
- **Sensors** (MDPI) if the calibration and controller comparison are strong; harder.
- Conferences: IEEE ICCIT / ICEEICT / ECCE (Bangladesh), AIUB's ICAEEE, IEEE R10 TENCON — good for a first version while the journal version matures.

### 7.5 Risks reviewers will raise (prepare answers)
1. "Only one enclosure and one plant" → run each controller twice (different weeks) and report both; state limits honestly.
2. "Hysteresis is not new" → agree; the novelty is the *combination* (bounded bursts, daily cap, interlocks, offline) and the *measured comparison* in this niche.
3. "DHT11 papers are weak baselines" → that is the point; cite 18 and 31 for why validated sensors matter.
4. "Cloud is convenient" → present E4 numbers and the outage test.

---

## 8. Paper-ready related-work paragraphs (numbering matches this file)

**Terrarium automation.** Automated terrariums have appeared only recently. AquaFlora [1] drives light, humidity, irrigation and cooling from an ESP32 with capacitive soil, DHT22 and BH1750 sensors through Node-RED and Firebase, and reports a 10-hour run; Rahman et al. [2] and Cahyani and Ikhsan [4] replace thresholds with fuzzy inference but report no quantitative control metrics; Septiawan et al. [3] automate irrigation only and observe a single plant for 14 days; Yoastha et al. [5] add lighting control with a web and LCD interface; Al Ayyubi and Rusimamto [7] and Pirdaus and Rahmani [8] address reptile enclosures, the latter noting that the humidifier "requires regular monitoring". Wrazidlo and Bzymek [9] built a low-cost chamber for tropical highland flora with partial automation. Across these works the control law is a single threshold or an untuned fuzzy set, remote access depends on a cloud service, sensors are uncalibrated, no hardware interlocks protect against an empty reservoir or leakage, and no work compares its controller against a baseline.

**Small-scale plant systems.** Indoor plant-care systems [10, 11, 15], smartphone-programmable plant boxes [12] and low-cost growth or propagation chambers [13, 14] show the demand for compact automated enclosures and, in [13, 14], the value of full replication packages and data logging; they remain monitoring-first or research-grade.

**Greenhouse control.** Greenhouse studies provide the methodological template this work follows: threshold and fuzzy systems on ESP32 [16–19, 24], validated sensors with reported deviation and response times [18], PID variants for modulating actuators [21], and controller-versus-controller comparisons — MPC against relay control [22] and sensor-based against time-based irrigation [23] — which have not been performed at terrarium scale.

**Sensing.** Capacitive soil probes need substrate-specific calibration with reported RMSE and sensor-to-sensor variability [26–30], and low-cost humidity sensors should be validated against a reference [18, 31]; surveys [32–35] and the ESP32 platform evaluation [36] complete the background.
