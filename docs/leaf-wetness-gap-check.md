# Gap check: camera-based leaf wetness duration (LWD) sensing

Date: 2026-09-16. Sources: OpenAlex + Semantic Scholar sweep, web search, and reading of the open-access papers. Elicit's student plan has no API access, so it was not used. Every DOI resolved at the time of writing.

## 1. Verdict in three lines

- The plain idea "a camera with LEDs decides if a leaf is wet and how long it stays wet" is **already published**, mainly by one University of Florida group (four papers, 2021 to 2026) and by two other groups (Hohenheim 2024, Hydra/MobiCom 2024).
- What is **not** published: real leaves plus continuous gravimetric ground truth for both wet onset and dry-off, an illumination-invariant feature that needs no training data, a sub-10-dollar on-device node, and an abstention (cannot-measure) output. Each of these is a stated weakness or an omission in the existing papers.
- So the project is viable only if it is framed around those four items, never as "first camera leaf wetness sensor". With that framing a two-week lab study is realistic for Biosystems Engineering or Smart Agricultural Technology, and a stretch for Computers and Electronics in Agriculture.

## 2. The prior work you must cite and position against

### Camera-based leaf wetness (direct neighbours)

1. **Patel, Lee, Peres 2021, Smart Agricultural Technology, "Strawberry plant wetness detection using computer vision and deep learning."** <https://doi.org/10.1016/j.atech.2021.100013> Colour and thermal images of strawberry plants, CNN, labels by visual inspection of images. Result: colour images alone are enough for high accuracy. Gap they leave: no quantitative ground truth, no duration end-point analysis, PC processing.
2. **Patel, Lee, Peres 2022, Sensors, "Imaging and deep learning based approach to leaf wetness detection in strawberry."** <https://doi.org/10.3390/s22218558> Wyze camera every 15 min, **painted white acrylic reference plate, not leaves**, LED for night, CNN trained in Google Colab. 96 % vs manual labels, 79 to 92 % vs the advisory system. Limitations they state: labelling errors at onset and offset (about plus or minus 1.5 h per day), plate needs a wiper, processing in the cloud.
3. **Kondaparthi, Lee, Peres 2024, Sensors, "Utilizing high-resolution imaging and AI for accurate leaf wetness detection for the Strawberry Advisory System."** <https://doi.org/10.3390/s24154836> Raspberry Pi Camera 3, on a Raspberry Pi 3, still a **reference plate**. Two-stage CNN: first classify time-of-day/lighting (day, night, blue, cloudy, blurry), then a wetness CNN per class. 95.8 % vs manual labels. Limitations they state: lighting drives the errors, dust and insects give 3.1 % false wet, tiny dew droplets give 7.5 % false dry, plate paint degrades in about five months.
4. **Sankaramaddi, Lee, Peres 2026, J. Biosystems Engineering, "Time-series detection of leaf wetness using a CNN-LSTM-based vision system in strawberry farming."** <https://doi.org/10.1007/s42853-026-00302-6> Adds an LSTM over image sequences to catch droplet evolution. Paywalled; abstract confirms high-resolution camera and a wet/dry classifier. Gap: still deep learning, still needs labelled sequences, no physical reference.
5. **Wu, Wang, Spohrer et al. 2024, Biosystems Engineering, "Non-contact leaf wetness measurement with laser-induced light reflection and RGB imaging."** <https://doi.org/10.1016/j.biosystemseng.2024.05.019> Closest in spirit to yours. Red laser plus RGB camera on **real grape leaves**, semi-automatic droplet deposition platform, generalised additive model predicting a continuous wetness value from segmented area, red-channel intensity and droplet count. Gap: measures deposition, not drying; single species; laser plus lab platform; no on-device version; no abstention.
6. **Hydra, ACM MobiCom 2024 / arXiv 2508.02409, "Accurate multi-modal leaf wetness sensing with mm-wave and camera fusion."** <https://arxiv.org/abs/2508.02409> 76 to 81 GHz FMCW radar fused with RGB by CNN and transformer, real leaves, up to 96 % in the lab and about 90 % in the field. Their own motivation: earlier methods "fail to measure real natural leaves directly" and are not robust to lighting. Gap: radar board costs hundreds of dollars, ground truth method not stated in the abstract, camera-only branch degrades badly in poor light (reported drop from roughly 90 % to roughly 69 % in evening light in the web summary; confirm in the PDF before citing the numbers).

### Contact sensors and models (baselines and context)

7. **Gillespie, McDonnell, O'Hare 2021, Expert Systems with Applications.** <https://doi.org/10.1016/j.eswa.2021.115255> RH-threshold rule (best at 92 %) vs machine learning over 30 stations; ML gains only about 5 %. Use: the RH proxy is your weak baseline and this shows its ceiling.
8. **Wang, Sánchez-Molina, Li et al. 2019, Water.** <https://doi.org/10.3390/w11010158> Four LWD models in greenhouses; best mean absolute error 1.3 to 1.9 h. Use: the error scale that a direct sensor must beat.
9. **Wade, Check, Chilvers 2025, Smart Agricultural Technology.** <https://doi.org/10.1016/j.atech.2025.100919> IoT leaf wetness sensors at different canopy heights in corn and soybean; 85 % RH threshold correlates with sensor wetness; off-site stations under-report wetness events by 10 to 17 %. Use: shows placement and proxy errors in the field.
10. **Spafford, Hausbeck, Werling 2025, Smart Agricultural Technology.** <https://doi.org/10.1016/j.atech.2025.100941> Low-cost IoT forecaster with a METER PHYTOS 31 leaf wetness sensor; states plainly that leaf wetness sensors "are not standardized". Use: the standardisation gap sentence.
11. **"A novel low-cost smart leaf wetness sensor", Computers and Electronics in Agriculture 2018.** <https://doi.org/10.1016/j.compag.2017.11.001> PCB artificial leaf with charge-transfer capacitive sensing on a microcontroller. Use: the low-cost contact baseline; a 1-dollar rain-sensor plate is the same principle in resistive form.
12. **Yogi et al. 2026, Applied Materials Today, MXene flexible leaf wetness sensor.** <https://doi.org/10.1016/j.apmt.2026.103281> Materials route; shows the field is active in 2026.
13. **Abdullah 2016, AUT thesis, "Leaf wetness duration modelling using ANFIS."** <https://openalex.org/W2556076988> Comparative test of commercial sensors: dielectric beats resistive, painting changes response, no accepted standard.
14. **Solís and Rojas-Herrera 2021, Biomimetics.** <https://doi.org/10.3390/biomimetics6020029> ML prediction of LWD from weather, best about 60 min per day error. Use: another number for the error scale.
15. **Wikipedia / historical note:** mechanical dew balances that record weight change from dew are an old, known principle. Weighing is therefore a legitimate reference method, not a novelty claim in itself.

## 3. What is genuinely open (and which paper proves it)

| Open item | Evidence it is open |
|---|---|
| Real leaves with a continuous physical reference for both onset and dry-off | UF uses a painted plate and eyeballed labels (2, 3). Hohenheim uses real leaves but measures deposition, not drying (5). Hydra does not state its ground truth (6). |
| Illumination-invariant detection without a lighting classifier | UF needed a five-class time-of-day model and still lists lighting as the main error source (3). Hydra's camera branch degrades in evening light (6). |
| No training set, runs on the camera board itself | All six camera papers use CNNs on a PC, cloud or Raspberry Pi; none run on the camera microcontroller. |
| Abstention when the view is occluded by fog, drops or dirt | Not reported by any of 1 to 6. UF reports dust and insects as false positives (3) with no mechanism to flag them. |
| Cross-species behaviour (glossy, hairy, waxy leaves) | UF: plate only. Hohenheim: grape only. Hydra: field mix but not analysed per leaf type. |

## 4. How the study must be framed to survive review

- **Title direction:** "Illumination-invariant, gravimetrically validated leaf wetness duration sensing on real leaves with a sub-10-dollar camera node."
- **Claim exactly this:** first optical LWD method validated against continuous water mass on the leaf, lighting-independent by active dual-angle flash differencing, on-device, with an explicit cannot-measure state. Do not claim first camera method, first real-leaf method, or first low-cost method.
- **Baselines inside the same box:** RH-above-90 % rule (papers 7, 9), a resistive plate (paper 11 principle), and a plain single-flash colour threshold to show the dual-angle differencing matters.
- **Reference:** load cell under the leaf clip, sampled every 30 s; wet onset = mass rise, dry-off = mass back to baseline within noise. Report onset delay and dry-off error in minutes against this reference, the way papers 8 and 14 report hours.
- **Stress tests reviewers will ask for:** fogged window, drops on window, dim ambient light, leaf angle, five leaf types, fan off/low/high drying, at least 30 wet-dry cycles per condition.
- **Limitations to write yourself before a reviewer does:** mist wetness in a box is not field dew; one slow-cooling dew run if the Peltier is available; ESP32-CAM sensor quality; no disease outcome.

## 5. Venues

- Biosystems Engineering (Q1, published paper 5): best fit for a measurement-method paper with a physical reference.
- Smart Agricultural Technology (Q1 in recent listings, published papers 1, 9, 10): realistic first target.
- Computers and Electronics in Agriculture (Q1): possible, will demand field data or a very strong measurement contribution.
- Sensors (published papers 2 and 3): fallback.

## 6. Decision

Proceed, with the reframed contribution in section 4. Parts to buy: ESP32-CAM, 1 kg load cell + HX711, optional FC-37 rain plate. Two normal white LEDs at left and right 45 degrees from the existing strip.
