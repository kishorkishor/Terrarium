// Builds the paper in IEEE conference style (A4, two columns, Times New Roman 10 pt) from the
// measured results in docs/RESULTS.md and the figures in docs/figures.
//   node tools/paper/build_paper.js      -> docs/paper/terrarium-brain-paper-blind.docx (double-blind, for review)
//                                           docs/paper/terrarium-brain-paper.docx       (with authors, camera-ready)
// Needs tools/report/node_modules/docx.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, TableBorders,
  WidthType, AlignmentType, SectionType, TabStopType, ShadingType, VerticalAlign, PageNumber, Footer,
} = require(path.join(__dirname, "..", "report", "node_modules", "docx"));

const ROOT = path.join(__dirname, "..", "..");
const FIG = path.join(ROOT, "docs", "figures");
const OUTDIR = path.join(ROOT, "docs", "paper");

const TEAM = [["Kishor Tarafder", "23-54520-3"], ["MD. Shakhawat Hossen", "23-54483-3"],
              ["Tahomina Era", "23-55027-3"], ["Avishek Saha", "23-54508-3"],
              ["Jannatun Nur Deba", "23-54545-3"], ["MD. Alfaz Uddin", "23-55557-3"]];

// ------------------------------------------------------------------ geometry
const A4W = 11906, A4H = 16838;
const IEEE = { top: 1080, bottom: 1440, left: 907, right: 907 };
const TEXT_W = A4W - IEEE.left - IEEE.right;
const COL_GAP = 360;
const COL_W = Math.floor((TEXT_W - COL_GAP) / 2);
const PX = (dxa) => Math.round(dxa / 15);

// ------------------------------------------------------------- image helpers
function imgSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89 && b[1] === 0x50) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  return { w: 1000, h: 750 };
}
function img(file, widthDxa) {
  const { w, h } = imgSize(file);
  const wp = PX(widthDxa), hp = Math.round(wp * h / w);
  return new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: wp, height: hp } });
}
const capPara = (caption) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 },
  children: [new TextRun({ text: caption, size: 16 })] });
function figure(file, widthDxa, caption) {
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 100, after: 40 }, keepNext: true,
      children: [img(file, widthDxa)] }),
    capPara(caption),
  ];
}

// -------------------------------------------------------------- text helpers
const R = (text, o = {}) => new TextRun({ text, size: 20, ...o });
const I = (text) => R(text, { italics: true });
const SUB = (text) => R(text, { subScript: true });
const SUP = (text) => R(text, { superScript: true });
const body = (runs, o = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 200 }, spacing: { after: 0, line: 240 },
  children: Array.isArray(runs) ? runs : [R(runs)], ...o });
const eq = (runs, num) => new Paragraph({
  spacing: { before: 60, after: 60 },
  tabStops: [{ type: TabStopType.CENTER, position: Math.round(COL_W / 2) }, { type: TabStopType.RIGHT, position: COL_W - 20 }],
  children: [R("\t"), ...runs, R(`\t(${num})`)] });
const h1 = (num, text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, keepNext: true,
  children: [new TextRun({ text: `${num}. ${text}`, size: 20, smallCaps: true })] });
const h2 = (letter, text) => new Paragraph({
  spacing: { before: 100, after: 40 }, keepNext: true,
  children: [new TextRun({ text: `${letter}. ${text}`, size: 20, italics: true })] });
const h5 = (text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, keepNext: true,
  children: [new TextRun({ text, size: 20, smallCaps: true })] });
const tableCaption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 100, after: 60 }, keepNext: true,
  children: [new TextRun({ text, size: 16, smallCaps: true })] });
const refPara = (n, text) => new Paragraph({
  alignment: AlignmentType.LEFT, indent: { left: 360, hanging: 360 }, spacing: { after: 30 },
  children: [new TextRun({ text: `[${n}]\t${text}`, size: 16 })],
  tabStops: [{ type: TabStopType.LEFT, position: 360 }] });
const sp = (n = 0) => new Paragraph({ spacing: { after: n }, children: [] });

function cell(text, width, o = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 30, bottom: 30, left: 70, right: 70 },
    children: [new Paragraph({ alignment: o.align || AlignmentType.LEFT, spacing: { after: 0 },
      children: [new TextRun({ text, size: o.size || 16, bold: o.bold, italics: o.italics })] })],
  });
}
// rows whose first cell starts with "§" are group headings (italic, shaded)
function grid(cols, rows, o = {}) {
  return new Table({
    columnWidths: cols, width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: rows.map((r, ri) => {
      const group = String(r[0]).startsWith("§");
      return new TableRow({
        tableHeader: ri === 0, cantSplit: true,
        children: r.map((c, ci) => cell(group && ci === 0 ? String(c).slice(1) : String(c), cols[ci], {
          size: o.size, bold: ri === 0 || (o.boldLast && ri >= rows.length - o.boldLast), italics: group,
          fill: ri === 0 ? "E7E6E6" : (group ? "F4F4F2" : undefined),
          align: o.center && ci > 0 ? AlignmentType.CENTER : undefined })),
      });
    }),
  });
}

// ============================================================================
//  Title block
// ============================================================================
const TITLE = "Online-Learning Humidity Control with Model-Based Fault Detection for a Low-Cost Terrarium: A Hardware Evaluation Against Hysteresis Control";
const ORD = ["1st", "2nd", "3rd", "4th", "5th", "6th"];
const authorCell = (n, name, id) => new TableCell({
  width: { size: 3364, type: WidthType.DXA },
  children: [
    [`${n} ${name}`, 22, false], ["Dept. of Computer Science and Engineering", 20, true],
    ["American International University-Bangladesh", 20, true], ["Dhaka, Bangladesh", 20, true],
    [`${id}@student.aiub.edu`, 20, false], ["", 12, false],
  ].map(([t, s, it]) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 },
    children: [new TextRun({ text: t, size: s, italics: it })] })),
});
function titleChildren(blind) {
  const title = new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 200 },
    children: [new TextRun({ text: TITLE, size: 44 })] });
  if (blind) {
    return [title,
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [new TextRun({ text: "Anonymous Authors", size: 22 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: "Submitted for double-blind review", size: 20, italics: true })] })];
  }
  return [title,
    new Table({ columnWidths: [3364, 3364, 3364], width: { size: 10092, type: WidthType.DXA }, borders: TableBorders.NONE,
      rows: [0, 3].map((s) => new TableRow({ children: TEAM.slice(s, s + 3).map((m, i) => authorCell(ORD[s + i], m[0], m[1])) })) }),
    sp(100)];
}

// ============================================================================
//  Body
// ============================================================================
const abstractText =
  "Low-cost terrarium controllers regulate humidity with a fixed hysteresis rule that neither adapts to the enclosure nor notices a failed part. We present a controller built on one small physics-shaped model, six weights updated online by dual-timescale recursive least squares in absolute humidity, which sizes each mist burst and detects faults from prediction residuals followed by an active quiet-then-mist test. Its state is about 2 kB, sized for the ESP32 already in the enclosure. We evaluated it on a real acrylic enclosure with an ultrasonic mist maker and two BME280 sensors, logging at 1 Hz, in 5.5 h of closed-loop runs that alternated with the enclosure's production rule (mist below 75 % RH, 300 s cap, 180 s rest). On a dry enclosure the learning controller held the 75–90 % band 74 % and 99 % of the time against the rule's 66 % and 91 % in paired blocks, with about 40 % more mist time; a burst-level analysis attributes this difference to its 77 % trigger and 60 s rest rather than to learning, because the target was out of reach and 15 of the 18 bursts it planned ran to the same 300 s cap. Learning did change its decisions: within one burst cycle the leak estimate rose 2.3 to 4.1 times and planned bursts grew from 80–125 s to the cap. When the lid was removed the controller flagged an anomaly within 1 s and named a leak after 400 s, and it withdrew a false alarm caused by a drying sensor after testing for 6.5 min. A software-injected dead mister went undetected for 12 min; we analyse why.";
const keywords = "adaptive control, recursive least squares, fault detection, humidity control, ultrasonic misting, ESP32";

// built fresh for each document so images are registered in each file
const paperChildren = () => [
  body([R("Abstract", { bold: true, italics: true }), R("—" + abstractText, { bold: true })], { indent: { firstLine: 0 } }),
  sp(60),
  body([R("Keywords—", { bold: true, italics: true }), R(keywords, { italics: true })], { indent: { firstLine: 0 } }),

  // ================================================================ I
  h1("I", "Introduction"),
  body("Tropical terrarium plants such as Fittonia need relative humidity (RH) held in a narrow band, typically 75 to 90 %. Low-cost controllers achieve this with an on/off rule: mist when RH falls below a lower threshold and stop at an upper threshold or after a fixed burst. The rule is simple and robust, but its settings are fixed by the installer, so it cannot follow the enclosure it is attached to, and it cannot tell whether its actions work: a dead mister, an empty tray, an open lid and a stuck sensor all end with the controller misting into an enclosure that does not respond."),
  body("This paper examines whether one small learned model can address both weaknesses on the hardware such enclosures already have. The model predicts the next change in absolute humidity from the mist command and the current state with six weights, each tied to a physical part of the enclosure, and is updated online by recursive least squares (RLS) at two timescales: a fast learner that tracks the present and a slow learner that remembers the healthy enclosure. The same model sizes each mist burst and, by comparing prediction with measurement, raises a suspicion that an active quiet-then-mist test resolves into a named fault or a false alarm. Its state is about 2 kB, and each 5 s step costs a few hundred multiplications."),
  body("Adaptive predictive greenhouse climate control and model-based fault diagnosis are not new [1]–[3]. The contributions here are: (i) a six-weight, dual-timescale model and a suspect-then-test diagnosis sized for a microcontroller and applied to ultrasonic misting; (ii) a hardware evaluation in alternating blocks against the rule the enclosure actually ran, with a burst-level analysis that separates the effect of learning from that of the controllers' settings; (iii) hardware evidence of online adaptation, leak detection and a self-withdrawn false alarm; and (iv) a documented failure to detect a dead mister, with its cause, together with practical lessons for low-cost misted enclosures."),

  // ================================================================ II
  h1("II", "Related Work"),
  body("Boughamsa and Ramdani [1] regulated greenhouse temperature and humidity through heating and ventilation with a model predictive controller whose Takagi–Sugeno fuzzy model had its consequent parameters adapted by RLS, evaluated in simulation. Linker et al. [2] developed robust model-based failure detection and identification for greenhouses, and Singhal et al. [3] combined residual-based fault detection, isolation and recovery with model predictive temperature control, updating the controller's model once an actuator fault was isolated, in simulated scenarios. Combining an adaptive model, prediction and diagnosis is therefore established for full-size greenhouses, with heating and ventilation actuators and, in [1] and [3], evaluation in simulation. Small models on microcontrollers for greenhouse climate are also established: temperature forecasting on edge devices [4], a 151-parameter network mapping sensor readings to actuator actions [5], and a k-nearest-neighbour replacement for thresholds on an ESP32 that includes a mist maker [6]; these are trained offline, frozen and scored on accuracy rather than on climate outcome. On-device training exists in TinyOL [7], in concept-drift-aware TinyML [8], which names sensor and actuator faults as a source of drift but tests on image and audio data, and in TyBox [9], all on classification tasks. Reinforcement learning and model predictive control have been compared for greenhouse climate in simulation [10], and simple heuristics remain competitive with machine-learning anomaly detection in industrial IoT [11], which motivates a linear model and a comparison against the plain rule. Against this background, the present work contributes a microcontroller-sized dual-timescale model for a misted enclosure, measured on hardware against the rule such enclosures run, with the benefit of learning separated from that of the controller's settings."),

  // ================================================================ III
  h1("III", "System"),
  h2("A", "Hardware and Firmware"),
  body("The enclosure is an acrylic box of about 28 × 23 × 8 cm with one 5 V ultrasonic mist maker (DIY-4-1) in a water tray, switched through an opto-isolated MOSFET channel from an ESP32 DevKit V1 [13] (Fig. 1). Two BME280 sensors [12] share one I2C bus: the control sensor (0x76) is mounted high inside the box under a small droplet shield, and a reference sensor (0x77) sits on the bench about 30 cm away. The lid was propped open on one edge, by 1 cm or 4 cm, to give the enclosure a drying path; closed, it loses under 2 % RH in 20 min in a 75 % RH room. No plants were present. A laboratory firmware samples both sensors at 1 Hz in forced mode, streams RH to 0.01 %, temperature and pressure over USB, rejects implausible readings (a marginal bus returned values such as 100.00 % RH that pass naive range checks), re-probes a lost sensor every 5 s and has a 15 s task watchdog. Its rule mode reproduces the enclosure's production controller: mist below 75 % RH, stop at 90 % or after 300 s, then rest 180 s."),
  ...figure(path.join(FIG, "paper-fig1-system.png"), COL_W, "Fig. 1. System. In this study the controller ran on a laptop connected to the ESP32 over USB."),
  h2("B", "Model and Learning"),
  body([R("Humidity is modelled as absolute humidity "), I("x"), R(" (vapour density, g m"), SUP("−3"), R(") computed from RH and temperature with the Magnus formula, which removes most of the temperature dependence of RH. With a 5 s step "), I("k"), R(",")], { indent: { firstLine: 0 } }),
  eq([R("Δ"), I("x"), R("("), I("k"), R(") = θ"), SUP("T"), R("φ("), I("k"), R(")")], 1),
  eq([R("φ("), I("k"), R(") = [ "), I("g m"), SUB("1"), R(", "), I("g m"), SUB("2"), R(", "), I("a"), R(", "), I("f a"), R(", "), I("f"), R(", 1 ]"), SUP("T")], 2),
  body([R("where "), I("m"), SUB("1"), R(" and "), I("m"), SUB("2"), R(" are the mist command "), I("u"), R(" filtered with time constants of 5 s and 30 s, "), I("g"), R(" = max(0.02, 1 − RH/100) models slower evaporation near saturation, "), I("a"), R(" = "), I("x"), R(" − 20 g m"), SUP("−3"), R(", and "), I("f"), R(" is the fan state (no fan was fitted here). The weights stand for mister strength (θ"), SUB("1"), R(", θ"), SUB("2"), R("), leakage (θ"), SUB("3"), R("), fan (θ"), SUB("4"), R(", θ"), SUB("5"), R(") and background gain (θ"), SUB("6"), R("). After each step both learners apply RLS with forgetting factor λ,")], { indent: { firstLine: 0 } }),
  eq([I("K"), R(" = "), I("P"), R("φ / (λ + φ"), SUP("T"), I("P"), R("φ),    θ ← θ + "), I("K e")], 3),
  eq([I("P"), R(" ← ("), I("P"), R(" − "), I("K"), R("φ"), SUP("T"), I("P"), R(") / λ")], 4),
  body([R("with "), I("e"), R(" the prediction error clipped to three running standard deviations; λ = 0.998 (about 40 min of memory) for the fast learner and 0.9998 (about 7 h) for the slow one. "), I("P"), R(" is kept symmetric, floored and capped; the weights are constrained so that the mister can only add water and the enclosure can only remove it; and the fast weights are pulled 0.2 % per step toward the slow ones, because closed-loop data do not identify every direction and an unanchored fast learner explained the data with large cancelling weights.")], { indent: { firstLine: 0 } }),
  h2("C", "Burst Planning"),
  body("When the control reading falls below 77 % RH, the controller simulates bursts of 5 to 300 s ten minutes ahead with the slow model and picks, by bisection, the shortest whose predicted peak reaches 88 %; after the burst it rests 60 s. During a declared fault it plans with the fast model toward 84 %. The 77 % trigger and the 60 s rest are fixed settings; only the burst length depends on the model."),
  h2("D", "Fault Detection"),
  body("Faults are detected in three layers (Table I). A missing or frozen reading marks the sensor lost or stuck. A part check after every 2 min of misting compares the humidity gained with the slow model's expectation, after subtracting the background drain measured while the enclosure was quiet. A cumulative-sum (CUSUM) test on the normalised prediction error z detects humidity falling faster than the healthy model allows and raises a suspect-loss state; since a leak and a dead mister both look like too fast a fall, suspicion triggers an active test of 4 min without misting followed by misting. A leak drains in both phases, a dead mister fails only while misting, and an enclosure that behaves normally in both is a false alarm. During a fault the slow learner is frozen so that a broken part is not learned as normal, and a snapshot of the slow weights is restored if they change without learning or predict twice as badly for 30 min. Table I also states which paths were exercised on hardware."),
  tableCaption("TABLE I.  Fault Logic and the Evidence for Each Path"),
  grid([1330, 830, 1520, 1186], [
    ["Detector", "Verdict", "Response", "Evidence"],
    ["No reading, or 12 identical readings", "sensor lost / stuck", "replay the learned misting rhythm", "simulation"],
    ["Gain after 2 min of misting < 0.3 of expected, twice", "main mister dead", "switch to the second channel", "hardware: missed (V-E); simulation: yes"],
    ["Removal after a fan run < 0.3 of expected, twice", "fan stalled", "alarm; control with fast model", "simulation (no fan)"],
    ["CUSUM on z below −20", "suspect loss", "freeze slow learner; quiet watch, then mist test", "hardware: 1 s after lid removal"],
    ["Mist test: loss in both phases", "lid open / leak", "alarm; control with fast model", "hardware: 400 s"],
    ["Mist test: loss only while misting", "main mister dead", "as above", "simulation"],
    ["Mist test: normal in both phases", "false alarm", "clear, resume learning", "hardware: 6.5 min"],
    ["Weights changed without learning, or 2× worse for 30 min", "corrupted model", "restore snapshot", "simulation"],
  ], { size: 14 }),
  sp(40),
  h2("E", "Execution Platform in This Study"),
  body("In this study the model, planner and fault logic ran in Python on a laptop. Every 5 s the program read the latest control sample from the firmware's 1 Hz stream, executed one controller step and sent the mist command back, which the firmware executed under its own limits. The code uses fixed-size arrays for a direct port to C, which was not done for this study. At the start of every run the weights were seeded by a least-squares fit of the same features to the closed-box step test of Section IV-A, so each learning block began with a model of the closed enclosure and had to learn the opened one."),

  // ================================================================ IV
  h1("IV", "Experiments"),
  body("All runs used the enclosure of Section III-A and logged both sensors at 1 Hz; only samples flagged valid were analysed, and in every run reported here all samples were valid."),
  h2("A", "Step Test"),
  body("With the lid closed, a script ran three rounds of 5 min quiet, mist until the control reading stopped rising (under 0.3 % over 60 s, after at least 90 s) and 20 min off, 80 min in total. Mister strength was taken from the absolute-humidity slope over the first 60 s of each burst divided by g."),
  h2("B", "Injected Faults"),
  body("With the lid propped 1 cm, the rule ran for 15 min and the learning controller for 47 min, during which the lid was removed for 8.6 min and, later, a wet tissue was held on the control sensor for 3.7 min. Delays were measured from marker lines written into the log."),
  h2("C", "Alternating Sessions"),
  body("With the lid propped 4 cm, the controllers alternated in 30 min blocks in two sessions: at night, with the room at 71 to 73 % RH, in the order rule, learning, rule, learning; and the next evening, with the room at 69 %, in the order learning, rule, learning, rule, learning. In the last evening block the controller's mist commands were dropped before reaching the firmware from minute 6 to minute 18, so the mister was effectively dead while the controller believed it was misting. Blocks were sequential, so each started from the state the previous one left and carry-over between blocks is possible; Table IV lists the starting RH. The metrics are the fraction of samples inside the 75 to 90 % band and below it, mist minutes as a proxy for water (volume was not weighed), and the number of bursts."),

  // ================================================================ V
  h1("V", "Results"),
  h2("A", "Enclosure Characterisation"),
  body("Table II gives the step test. The mister raised the control reading to a ceiling of 89.5 ± 0.4 % RH in 104 ± 7 s and could not exceed it; its dry-air strength was 0.098 ± 0.012 g m⁻³ s⁻¹. The closed enclosure lost 1.7 ± 0.4 % RH in 20 min. The air warmed 0.2 to 0.4 °C while the disc ran and cooled about 0.5 °C below the start as the fog evaporated. Two consequences for the production rule follow: its 300 s cap is about three times longer than needed to reach the ceiling, and its 90 % stop is never reached, so every rule burst in this study ran to the cap."),
  tableCaption("TABLE II.  Step Test, Lid Closed, One Mist Maker"),
  grid([700, 780, 780, 800, 1006, 800], [
    ["Round", "Start %RH", "Peak %RH", "Mist s", "Strength g/m³/s", "Drop 20 min"],
    ["1", "83.0", "89.0", "110", "0.086", "1.8 %"],
    ["2", "86.9", "89.5", "97", "0.110", "2.0 %"],
    ["3", "87.1", "89.9", "104", "0.099", "1.2 %"],
    ["mean ± sd", "", "89.5 ± 0.4", "104 ± 7", "0.098 ± 0.012", "1.7 ± 0.4 %"],
  ], { size: 15, center: true, boldLast: 1 }),

  h2("B", "Injected Faults"),
  body("Table III summarises the responses and Fig. 2 the traces. The rule's single burst ran to the 300 s cap (70.8 to 88.2 %), and in the next 25 min the learning controller had no reason to mist; over that time its slow leak weight rose from 0.036 to 0.131 per step, a re-fit of the opened enclosure without any misting data. When the lid was removed the CUSUM raised suspect-loss 1 s after the marker; after the quiet watch the controller ran three test bursts of 10 to 40 s toward the lowered 84 % target, sized by the fast model, and declared lid open / leak 400 s after the marker. The wet tissue did not latch the sensor, but the resulting bus fault crashed the first firmware's bus-recovery routine; the chip restarted and both sensors were back 6 s after the tissue was applied, but the laptop program did not yet handle a restart, so 106 s passed without control until it was relaunched (the routine was removed and restart handling added afterwards). When the tissue was removed the reading fell from 90 to 74 % in 40 s as the sensor dried; the controller raised suspect-loss, ran its test and withdrew the alarm as a false alarm 6.5 min later. Over the session the rule held the band 96.5 % of its 15 min with 5.0 mist-minutes, and the learning controller 95.4 % of its 37 min with 1.1 mist-minutes while carrying the lid fault."),
  tableCaption("TABLE III.  Injected Faults and the Controller's Response"),
  grid([1400, 3466], [
    ["Event", "Response"],
    ["Lid fully off", "suspect loss after 1 s; 4 min quiet watch; test bursts of 10–40 s; “lid open / leak” after 400 s; band held meanwhile"],
    ["Lid back, 1 cm gap", "fault kept until the enclosure matched the healthy model for 10 min"],
    ["Wet tissue on sensor", "sensor did not latch; bus fault crashed the recovery routine; chip back after 6 s; 106 s without control"],
    ["Tissue removed", "reading fell 90 to 74 % in 40 s; suspect loss; tested; withdrawn as a false alarm after 6.5 min"],
  ], { size: 15 }),
  ...figure(path.join(FIG, "paper-fig2-fault-session.png"), COL_W, "Fig. 2. Fault session, lid 1 cm (blue shading: mist on; grey band: 75–90 %). Events: 1 lid off, 2 lid back, 3 wet tissue on, 4 tissue removed. Verdicts: S suspect loss, L lid open / leak, F false alarm withdrawn. The grey span after event 3 is the 106 s without control."),

  h2("C", "Alternating Sessions"),
  body("Table IV gives both sessions. At night the enclosure stayed within the band with little help: the rule misted four times for 14.6 min and held the band 99.4 % of its hour, and the learning controller never misted and held it 100 %. In the evening the enclosure's passive level was about 74 %, just below the band, and with the 4 cm gap one mister could lift it only to about 82 %, so both controllers misted most of the time. In the pair with similar starting points (21:03 and 21:33, starting at 76.8 and 76.2 %) the learning controller held the band 99.4 % of the time against 90.9 %, and in the pair that began from the dry enclosure 74.3 % against 65.6 %, using about 40 % more mist time (24 against 16 to 18 min per block). Fig. 3 shows the evening traces."),
  tableCaption("TABLE IV.  Alternating 30 min Blocks, Lid 4 cm"),
  grid([1560, 640, 700, 700, 660, 606], [
    ["Block (start time)", "Start %RH", "In 75–90 %", "Below 75 %", "Mist min", "Bursts"],
    ["§Night, room 71–73 % RH", "", "", "", "", ""],
    ["Rule (00:55)", "72.6", "98.9 %", "1.1 %", "10.2", "3"],
    ["Learning (01:25)", "79.3", "100 %", "0.0 %", "0.0", "0"],
    ["Rule (01:55)", "79.7", "99.9 %", "0.1 %", "4.4", "1"],
    ["Learning (02:25)", "87.6", "100 %", "0.0 %", "0.0", "0"],
    ["§Evening, room 69 % RH", "", "", "", "", ""],
    ["Learning (20:03)", "69.3", "74.3 %", "25.7 %", "24.1", "6"],
    ["Rule (20:33)", "77.8", "65.6 %", "34.4 %", "18.2", "4"],
    ["Learning (21:03)", "76.8", "99.4 %", "0.6 %", "24.0", "6"],
    ["Rule (21:33)", "76.2", "90.9 %", "9.1 %", "16.3", "4"],
    ["Learning, dead mister (22:03)", "76.8", "78.9 %", "21.1 %", "13.9", "5"],
  ], { size: 14, center: true }),
  ...figure(path.join(FIG, "paper-fig3-evening-session.png"), COL_W, "Fig. 3. Evening session on the dry enclosure, lid 4 cm (blue shading: mist reaching the enclosure). Both controllers mist most of the time; the hatched window is the injected dead mister."),

  h2("D", "What Drove the Differences"),
  body("The burst logs explain both sessions, and neither result can be credited to learning. At night the learning controller did not decide to save water: its 77 % trigger was never crossed at its 5 s sampling, whereas the rule's 75 % trigger was reached after its own bursts decayed, and both learning blocks began just after a rule burst (79.3 and 87.6 % at block start), so carry-over favoured them. The night session therefore gives no evidence of water saving. In the evening the 88 % target was out of reach, so 15 of the learning controller's 18 bursts ran to the 300 s cap, where every rule burst also stopped; the controllers differed only in trigger (77 against 75 %) and rest (60 against 180 s). A hysteresis rule with a 77 % trigger and a 60 s rest would issue the same commands except for the first burst of each block, so both the better time in band and the extra water are effects of those settings. Learning did change the controller's decisions: each block began with the closed-box seed, which predicted that 80 to 125 s would reach 88 %; within 2.5 to 3 min, one burst cycle, the fast leak estimate rose 2.3 to 4.1 times and every later plan went to the cap. Model-based sizing mattered only where the target was reachable, which on hardware happened during the lid fault (bursts of 10 to 40 s). A comparison against a rule with matched trigger and rest, in a regime where the target is reachable, is the experiment that would isolate the value of the model."),

  h2("E", "Dead Mister: A Negative Result"),
  body("In the last evening block the controller commanded 450 s of misting in the 12 min window, none of which reached the enclosure; RH fell from 80.8 to 72.3 % and the band held for 61 % of the window. No fault was declared. Offline replay shows that the part check's ratio of measured to expected gain ranged from 0.46 to 1.5 during the fault and from 0.5 to 1.5 in healthy blocks: on a leaky enclosure near its passive level the leak correction is large and uncertain, and a dead mister changes humidity by only a few percent, inside the model's error. A raw burst-onset check was tried offline and raised false alarms in healthy blocks, because the seed over-predicted the first-minute rise at the shielded sensor about fourfold, so it was not adopted. The lid fault was detected because it changes the leak by an order of magnitude. Dependable actuator diagnosis needs a direct signal, such as the mist maker's supply current, or an onset signature measured at commissioning."),

  // ================================================================ VI
  h1("VI", "Discussion and Limitations"),
  body("On this hardware the measurements support four claims: the model re-fits a changed enclosure within minutes and changes its plans accordingly; the residual-plus-test logic detects and names a leak and withdraws a false alarm; the learning controller controls at least as well as the production rule; and several failure modes of low-cost parts are real (a wet BME280 can fault the bus, and a sensor reporting a fixed 179.4 °C and 100 % RH is at its power-on defaults because register writes fail on a marginal bus, which solid wiring fixed and a power cycle did not). They do not support a control or water advantage from learning, which Section V-D attributes to the settings; dead-mister detection; the backup-mister, stuck-sensor, stalled-fan and rollback paths, which were exercised only in a 76 h simulation used as a logic check rather than as evidence; execution on the ESP32, since the controller ran on a laptop; or long-term behaviour, since the evidence is 5.5 h of closed-loop runs on one enclosure without plants, with mist minutes standing in for water volume. The ESP32 also restarted once with an interrupt-watchdog timeout late in the night session; the cause is unexplained, and the laptop program resumed control within about 20 s."),

  // ================================================================ VII
  h1("VII", "Conclusion"),
  body("A six-weight model updated online at two timescales can run a low-cost misted enclosure, re-learn the enclosure within one burst cycle, detect and name a leak and withdraw its own false alarm by testing, with a state small enough for the enclosure's microcontroller. On real hardware its control matched or exceeded the production hysteresis rule, but the burst logs show that this came from its trigger and rest settings rather than from learning, and it did not detect a dead mister. The next steps are a comparison against a rule with matched settings where the target is reachable, a direct actuator signal for the mister, the port to the ESP32 and longer runs with plants."),

  // ================================================================ ACK
  h5("Acknowledgment"),
  body("The authors used an AI assistant (Anthropic Claude) to help write the firmware, logging, analysis and controller code and to draft parts of this text from the recorded data. All experiments and measurements are the authors' own, and the authors take full responsibility for the content.", { indent: { firstLine: 0 } }),

  // ================================================================ REFS (all checked against Crossref)
  h5("References"),
  refPara(1, "M. Boughamsa and M. Ramdani, “Adaptive fuzzy control strategy for greenhouse micro-climate,” Int. J. Autom. Control, vol. 12, no. 1, 2018, doi: 10.1504/IJAAC.2018.088604."),
  refPara(2, "R. Linker, P.-O. Gutman, and I. Seginer, “Robust model-based failure detection and identification in greenhouses,” Comput. Electron. Agric., vol. 26, no. 3, pp. 255–270, 2000, doi: 10.1016/S0168-1699(00)00079-X."),
  refPara(3, "R. Singhal, R. Kumar, and S. Neeli, “Residual-based fault detection isolation and recovery of a greenhouse,” Int. J. Autom. Control, vol. 16, no. 3/4, 2022, doi: 10.1504/IJAAC.2022.122599."),
  refPara(4, "G. Codeluppi, L. Davoli, and G. Ferrari, “Forecasting air temperature on edge devices with embedded AI,” Sensors, vol. 21, no. 12, Art. no. 3973, 2021, doi: 10.3390/s21123973."),
  refPara(5, "I. Ihoume, R. Tadili, N. Arbaoui, M. Benchrifa, A. Idrissi, and M. Daoudi, “Developing a multi-label tinyML machine learning model for an active and optimized greenhouse microclimate control from multivariate sensed data,” Artif. Intell. Agric., vol. 6, pp. 129–137, 2022, doi: 10.1016/j.aiia.2022.08.003."),
  refPara(6, "A. I. Sukowati, N. Marliza, and D. Saptono, “Edge AI–based threshold-free control for mushroom farming using K-NN on ESP32,” J. Nas. Tek. Elektro Teknol. Inf., vol. 15, no. 3, pp. 239–248, 2026, doi: 10.22146/jnteti.v15i3.25532."),
  refPara(7, "H. Ren, D. Anicic, and T. A. Runkler, “TinyOL: TinyML with online-learning on microcontrollers,” in Proc. Int. Joint Conf. Neural Netw. (IJCNN), 2021, pp. 1–8, doi: 10.1109/IJCNN52387.2021.9533927."),
  refPara(8, "S. Disabato and M. Roveri, “Tiny machine learning for concept drift,” IEEE Trans. Neural Netw. Learn. Syst., vol. 35, no. 6, pp. 8470–8481, 2024, doi: 10.1109/TNNLS.2022.3229897."),
  refPara(9, "M. Pavan, E. Ostrovan, A. Caltabiano, and M. Roveri, “TyBox: An automatic design and code generation toolbox for TinyML incremental on-device learning,” ACM Trans. Embed. Comput. Syst., vol. 23, no. 3, pp. 1–27, 2024, doi: 10.1145/3604566."),
  refPara(10, "B. Morcego, W. Yin, S. Boersma, E. van Henten, V. Puig, and C. Sun, “Reinforcement learning versus model predictive control on greenhouse climate control,” Comput. Electron. Agric., vol. 215, Art. no. 108372, 2023, doi: 10.1016/j.compag.2023.108372."),
  refPara(11, "B. Bicski, K. Farkas, and A. Pekar, “Simple heuristics as a viable alternative to machine learning-based anomaly detection in industrial IoT,” IEEE Internet Things Mag., vol. 6, no. 3, pp. 104–109, 2023, doi: 10.1109/IOTM.001.2200232."),
  refPara(12, "Bosch Sensortec, “BME280: Combined humidity and pressure sensor,” Datasheet BST-BME280-DS002, Reutlingen, Germany."),
  refPara(13, "Espressif Systems, “ESP32 series datasheet,” Shanghai, China. [Online]. Available: https://www.espressif.com/en/support/documents/technical-documents"),
];

// ================================================================== document
const pageFooter = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 16 })] })] });
const pageProps = { size: { width: A4W, height: A4H }, margin: IEEE };

function build(blind) {
  return new Document({
    creator: blind ? "Anonymous" : "Kishor Tarafder et al.",
    title: TITLE,
    styles: { default: { document: { run: { font: "Times New Roman", size: 20 } } } },
    sections: [
      { properties: { page: pageProps }, footers: { default: pageFooter }, children: titleChildren(blind) },
      { properties: { type: SectionType.CONTINUOUS, page: pageProps, column: { count: 2, space: COL_GAP, equalWidth: true } },
        footers: { default: pageFooter }, children: paperChildren() },
    ],
  });
}

fs.mkdirSync(OUTDIR, { recursive: true });
(async () => {
  for (const [blind, name] of [[true, "terrarium-brain-paper-blind.docx"], [false, "terrarium-brain-paper.docx"]]) {
    const buf = await Packer.toBuffer(build(blind));
    fs.writeFileSync(path.join(OUTDIR, name), buf);
    console.log("wrote", name, buf.length, "bytes");
  }
})();
