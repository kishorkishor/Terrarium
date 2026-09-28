# Camera leaf-wetness research: prior-art and feasibility audit

Audit date: 2026-09-16. Decision: do not build around the proposed broad novelty claims. A narrower measurement-reliability study merits a feasibility pilot, conditional on observable signal and independent validation. No hardware or firmware was changed during this audit.

## Scope and search limits

Checked available skills and MCP capabilities, then searched publisher pages, PMC, arXiv, author code repositories and Google Patents. The plugin-management skill was used to discover Elicit; it was available to suggest but was not installed/connected. No Elicit search was performed. The pasted report's statements about an OpenAlex/Semantic Scholar sweep and Elicit student-plan API access are its provenance claims, not verified actions in this audit.

Search families included camera/optical leaf wetness; active illumination; real-leaf gravimetry; time-series wetness detection; camera-window condensation; lens soiling; uncertainty/abstention; and public datasets. Exact phrase searches for leaf-wetness abstention and illumination invariance did not establish a matching study. This is a targeted prior-art audit, not proof of absence or an exhaustive systematic review. The 2026 CNN-LSTM paper was accessible at abstract level; unreported details cannot be treated as absent.

## Closest prior work

| Source | Verified relevance | Consequence |
|---|---|---|
| [Patel et al., 2022, Sensors](https://doi.org/10.3390/s22218558) | Camera-based wetness detection using an artificial reference surface and deep learning. | Basic camera classification is established. |
| [Kondaparthi et al., 2024, Sensors](https://doi.org/10.3390/s24154836) | High-resolution imaging, controlled night lighting, a reference plate, and lighting-dependent classification. Rain-related blurry images are treated as wet. | LEDs and lighting handling are established. The blurry-to-wet assumption motivates testing independently varied leaf and window states; it does not demonstrate that their field system failed. |
| [Wu et al., 2024, Biosystems Engineering](https://doi.org/10.1016/j.biosystemseng.2024.05.019) | Real grape leaves, two red lasers, RGB imaging and a balance specified at 0.1 mg precision, logging every second. Deposition experiments use image features and a generalized additive model. | Real leaves, active optical sensing and continuous mass acquisition already exist. A full onset/drying validation is a narrower distinction, not a proven first. This method is not a CNN. |
| [Hydra, ACM MobiCom 2024; arXiv version 2025](https://arxiv.org/html/2508.02409v1) | Combines radar and RGB on real plants; evaluates wetness duration and environmental changes. Sections 2.1 and 5.3 describe a calibrated two-pin commercial moisture meter as the reference. | Its reference can be critically assessed, but is not missing. Duration sensing on real leaves is established. |
| [Sankaramaddi et al., 2026, Journal of Biosystems Engineering](https://doi.org/10.1007/s42853-026-00302-6) | Abstract describes temporal wetness classification with a ConvLSTM vision system. | Adding image history is not sufficient novelty. Full methodological details remain unverified. |
| [Lv et al., 2022, Frontiers in Plant Science](https://doi.org/10.3389/fpls.2022.861534) | Image-based dew detection on leaves and stems using edge detection networks. | Visible droplet analysis on real foliage is established. |
| [EP4407301A1, published patent application](https://patents.google.com/patent/EP4407301A1/en) | Optical monitoring of leaf wetting over time, dry references and ambient-light subtraction using captures without emitted illumination. | Light-on/off subtraction and reference-based optical detection are already disclosed. Patent disclosure is not experimental validation; this audit is not a legal opinion. |
| [Let's Get Dirty, WACV 2021](https://openaccess.thecvf.com/content/WACV2021/papers/Uricar_Lets_Get_Dirty_GAN_Based_Data_Augmentation_for_Camera_Lens_WACV_2021_paper.pdf) | Camera lens soiling detection and synthetic augmentation. | Detecting an impaired optical view is an established computer-vision task. |
| [Yang et al., 2026, camera soiling severity](https://pmc.ncbi.nlm.nih.gov/articles/PMC13259091/) | Static and temporal soiling assessment for camera availability and downstream use. | Neither camera-health scoring nor temporal stabilization is new in general. |

Public implementation: [Hydra author repository](https://github.com/liuyime2/MobiCom24-Hydra). Existing RGB/radar data cannot validate our proposed independently controlled window contamination or switched-light protocol.

## Corrections to the pasted gap check

1. An omission in an abstract is not evidence of a research gap. Hydra explicitly specifies its reference measurement; the paywalled 2026 paper cannot be classified as having no physical reference from its abstract alone.
2. The assertion that all six direct methods use CNNs is contradicted by Wu's generalized additive model. A training-free optical rule also has relevant patent precedent.
3. Continuous gravimetry is already used in the closest optical paper. A contribution would require better validation of a particular measurement problem, not just adding a scale.
4. Active differencing may reduce stable ambient illumination. It does not automatically remove changing exposure/gain, saturation, leaf movement, angle, gloss or changing ambient light between frames. Use 'robustness to tested lighting conditions', not 'illumination-invariant', unless proved within a clearly defined model and operating range.
5. Sub-$10 cost and on-device execution are proposed engineering targets. Both require a complete bill of materials and measured runtime/memory/energy. Existing ownership does not make a component free in a published cost comparison.
6. No training set does not mean no calibration or no independent validation set. Thresholds selected using evaluation data invalidate the test.
7. A one- or two-week pilot is not evidence that a Q1 submission is ready. Journal quartiles depend on database, category and year; this audit does not certify the pasted venue rankings or acceptance prospects.
8. Model errors from different crops, references and sampling intervals cannot become universal accuracy targets. Compare methods on the same events and reference.

## Why the proposed cheap load cell is not automatically ground truth

Engineering inference: a leaf-on-scale record contains surface water, tissue-water changes, water deposited on the support, drift and airflow forces. Returning to the initial total mass does not prove that surface water has disappeared. Foliar water uptake and transpiration effects are documented in [Gerlein-Safdi et al., 2018](https://pubmed.ncbi.nlm.nih.gov/29955985/).

Before relying on any load-cell/HX711 combination, measure its assembled noise, drift, minimum detectable mass and response under the actual fan/mist conditions. Validate support shielding and dry-leaf controls. ADC bit depth is not balance accuracy. Small-film dry-off is the hardest endpoint; do not promise it without a suitable reference instrument and uncertainty analysis.

A separate clear, close-up optical view can support a pilot about visible surface water, with timestamped labels and uncertain transition intervals. It cannot certify absence of microscopic wetness. [Microscopic leaf-wetness research](https://doi.org/10.3389/fpls.2013.00422) explains why this distinction matters.

## Candidate question that remains defensible

Can a low-cost camera system reduce false wetness-duration readings caused by water on its viewing window, while retaining a useful proportion of measurements on real leaves?

This is a candidate application and validation gap within the reviewed sources. It is not a claim to have invented optical wetness sensing, lens-contamination detection, abstention or active illumination.

Independently vary leaf state and optical-path state:

| Leaf | Viewing window | Desired behavior |
|---|---|---|
| No visible water | Clear | No visible water detected |
| Visible water | Clear | Wet |
| No visible water | Wet/fogged | Correct reading if observable; otherwise cannot measure |
| Visible water | Wet/fogged | Correct reading if observable; otherwise cannot measure |

Test wetting and drying transitions, not only static large droplets. A separate unobscured view must establish the visible-water reference. A dry reference target should be protected from wetting; its clarity does not necessarily establish visibility everywhere on the leaf, so local obstruction matters.

Compare: single-light features; light-on/off subtraction; dual-angle illumination; a simple image-quality rejection rule; and the proposed combined rule. RH is a contextual baseline, not a sufficient competitor. A strong claim also needs comparison with relevant learned or temporal methods where practical.

Primary outcomes: onset and dry-off timing error; false wet/dry readings under independent window contamination; measurement availability; and error versus availability as rejection increases. Unknown periods must remain unknown, with duration bounds where appropriate. Never count rejected frames as dry or silently omit difficult intervals from duration reporting.

Keep complete leaves and wet/dry events together in train/calibration/test splits. Hold out leaves and days; neighboring frames are not independent replicates. Repeated cycles on one leaf do not substitute for biological diversity. Determine replication from pilot variability and effect size, not an arbitrary '30 per condition'.

## Go/no-go conditions before committing to a paper

- Continue only if water signals remain distinguishable across held-out leaves, realistic fine mist and useful changes in angle and lighting.
- Continue only if the added method beats simple quality rejection at comparable availability, rather than improving accuracy solely by refusing almost everything.
- Continue only if onset/dry-off reference uncertainty is smaller than the claimed improvement.
- Treat additional LEDs, protected camera placement and window/reference materials as pilot hardware. Do not buy a Peltier or generic load cell merely to preserve the original title.
- With one week, target feasibility evidence and a defensible dataset protocol. A mature publication claim requires the resulting evidence, not the feature list.

Provisional title: 'Camera-based monitoring of visible leaf wetness under viewing-window contamination'. Add low-cost/on-device/duration claims only after they are demonstrated.

Overall verdict: broad novelty rejected; narrower reliability question plausible but unconfirmed; Q1 readiness not established. Earlier enthusiasm for the broader camera idea should be revised in light of these closer sources.

## Elicit connection follow-up

Elicit was subsequently installed and its MCP tools became available. Three searches were attempted: camera/active-illumination LWD; leaf wetness with window contamination and abstention; and gravimetrically validated optical drying measurements. All returned api_access_denied: the connected account plan does not include API access. No papers were returned by Elicit. This verifies the limitation for this connected account, without establishing its plan name. The evidence and verdict above still derive from the direct-source web audit.
