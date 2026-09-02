// Builds TERRARIUM-Report.docx as an IEEE conference-style paper (A4, two columns,
// Times New Roman 10 pt). Paper version: no cover sheet, no cost/timeline/survey material,
// no generated diagrams; only photographs of the prototype and the measured calibration plot.
// (The earlier course-report builder is kept as build_course_report.js.bak.)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, TableBorders,
  WidthType, AlignmentType, SectionType, TabStopType, ShadingType, VerticalAlign, PageNumber, Footer,
} = require("docx");

const A = path.join(__dirname, "assets");
const OUT = "C:/Users/kisho/Desktop/TERRARIUM/TERRARIUM-Report.docx";

const TEAM = [["Kishor Tarafder", "23-54520-3"], ["MD. Shakhawat Hossen", "23-54483-3"],
              ["Tahomina Era", "23-55027-3"], ["Avishek Saha", "23-54508-3"],
              ["Jannatun Nur Deba", "23-54545-3"], ["MD. Alfaz Uddin", "23-55557-3"]];

// ------------------------------------------------------------------ geometry
const A4W = 11906, A4H = 16838;
const IEEE = { top: 1080, bottom: 1440, left: 907, right: 907 };
const TEXT_W = A4W - IEEE.left - IEEE.right;       // 10092
const COL_GAP = 360;
const COL_W = Math.floor((TEXT_W - COL_GAP) / 2);  // 4866
const PX = (dxa) => Math.round(dxa / 15);

// ------------------------------------------------------------- image helpers
function imgSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89 && b[1] === 0x50) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  let i = 2;
  while (i < b.length) {
    if (b[i] !== 0xff) { i++; continue; }
    const m = b[i + 1];
    if (m === 0xc0 || m === 0xc2) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
    i += 2 + b.readUInt16BE(i + 2);
  }
  return { w: 1000, h: 750 };
}
function img(file, widthDxa) {
  const { w, h } = imgSize(file);
  const wp = PX(widthDxa), hp = Math.round(wp * h / w);
  return new ImageRun({ type: file.endsWith(".jpg") ? "jpg" : "png", data: fs.readFileSync(file),
                        transformation: { width: wp, height: hp } });
}
const capPara = (caption) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
  children: [new TextRun({ text: caption, size: 16 })] });
function figure(file, widthDxa, caption) {
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [img(file, widthDxa)] }),
    capPara(caption),
  ];
}
function figurePair(fileA, fileB, caption, w = 2300) {
  const cellOf = (f, tag) => new TableCell({ width: { size: w + 100, type: WidthType.DXA }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [img(f, w)] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [new TextRun({ text: tag, size: 16 })] }),
  ] });
  return [
    new Paragraph({ spacing: { before: 120, after: 0 }, keepNext: true, children: [] }),
    new Table({ columnWidths: [w + 100, w + 100], width: { size: 2 * w + 200, type: WidthType.DXA },
      borders: TableBorders.NONE, alignment: AlignmentType.CENTER,
      rows: [new TableRow({ children: [cellOf(fileA, "(a)"), cellOf(fileB, "(b)")] })] }),
    capPara(caption),
  ];
}

// -------------------------------------------------------------- text helpers
const R = (text, o = {}) => new TextRun({ text, size: 20, ...o });
const body = (runs, o = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 200 }, spacing: { after: 0, line: 240 },
  children: Array.isArray(runs) ? runs : [R(runs)], ...o });
const h1 = (num, text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 240, after: 120 }, keepNext: true,
  children: [new TextRun({ text: `${num}. ${text}`, size: 20, smallCaps: true })] });
const h2 = (letter, text) => new Paragraph({
  spacing: { before: 120, after: 60 }, keepNext: true,
  children: [new TextRun({ text: `${letter}. ${text}`, size: 20, italics: true })] });
const h5 = (text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 240, after: 120 }, keepNext: true,
  children: [new TextRun({ text, size: 20, smallCaps: true })] });
const tableCaption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
  children: [new TextRun({ text, size: 16, smallCaps: true })] });
const refPara = (n, text) => new Paragraph({
  alignment: AlignmentType.LEFT, indent: { left: 360, hanging: 360 }, spacing: { after: 40 },
  children: [new TextRun({ text: `[${n}]\t${text}`, size: 16 })],
  tabStops: [{ type: TabStopType.LEFT, position: 360 }] });
const sp = (n = 0) => new Paragraph({ spacing: { after: n }, children: [] });

function cell(text, width, o = {}) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text, size: o.size || 16, bold: o.bold })];
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, columnSpan: o.span, verticalAlign: VerticalAlign.CENTER,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ alignment: o.align || AlignmentType.LEFT, spacing: { after: 0 }, children: runs })],
  });
}
function grid(cols, rows, o = {}) {
  return new Table({
    columnWidths: cols, width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0, cantSplit: true,
      children: r.map((c, ci) => cell(String(c), cols[ci], { size: o.size, bold: ri === 0,
        fill: ri === 0 ? "E7E6E6" : undefined, align: o.center ? AlignmentType.CENTER : undefined })),
    })),
  });
}

// ============================================================================
//  Title block (single column, six authors in two rows)
// ============================================================================
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
const titleChildren = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
    children: [new TextRun({ text: "IoT-Based Automated Tropical Terrarium Using ESP32", size: 48 })] }),
  new Table({ columnWidths: [3364, 3364, 3364], width: { size: 10092, type: WidthType.DXA }, borders: TableBorders.NONE,
    rows: [0, 3].map((s) => new TableRow({ children: TEAM.slice(s, s + 3).map((m, i) => authorCell(ORD[s + i], m[0], m[1])) })) }),
  sp(120),
];

// ============================================================================
//  Paper body (two columns)
// ============================================================================
const abstractText =
  "Tropical terrarium plants require a narrow band of humidity, temperature, soil moisture and illumination that is difficult to maintain manually, while commercial plant controllers are either open-loop timers or cloud-dependent monitors. This paper presents the design, implementation and experimental evaluation of a self-contained terrarium controller built around the ESP32 microcontroller. The system measures air temperature, relative humidity and pressure, illuminance, soil moisture at two points, tray leakage and reservoir level, and drives two ultrasonic mist makers, an exhaust fan, a grow light and an alarm through opto-isolated MOSFET stages. Control runs entirely on the device: a rules engine combines a burst-and-soak watering state machine with a daily watering cap, humidity hysteresis with bounded burst length and cool-down, a photoperiod-gated lighting rule, and hardware interlocks for an empty reservoir and leakage. Fourteen control parameters are adjustable at run time through a web dashboard served over Wi-Fi or a local hotspot and through a USB serial interface that also provisions network credentials. Experiments on a prototype calibrated two capacitive probes by two-point measurement (usable spans of 1380 and 1415 ADC counts), showed that the opto-isolated switching stage requires a 5 V active-low drive rather than 3.3 V logic, confirmed that flyback protection is necessary for the fan, and verified wireless control at a link strength of about -53 dBm. The controller operates without internet access and keeps the enclosure within its target band without daily attention.";
const keywords = "ESP32, Internet of Things, terrarium, closed-loop control, hysteresis, environmental monitoring";

const paperChildren = [
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
    children: [new TextRun({ text: "Abstract\u2014", bold: true, italics: true, size: 18 }),
               new TextRun({ text: abstractText, bold: true, size: 18 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
    children: [new TextRun({ text: "Keywords\u2014", bold: true, italics: true, size: 18 }),
               new TextRun({ text: keywords, bold: true, italics: true, size: 18 })] }),

  // ================================================================ I
  h1("I", "Introduction"),
  body("A terrarium is a small, largely enclosed ecosystem in which tropical plants such as ferns, mosses, nerve plants (Fittonia) and orchids are cultivated. Inside the enclosure the plants sustain their own water cycle: moisture evaporates from the substrate, condenses on the walls and returns, so the system can remain stable for weeks when the balance is correct. These species require 70 to 90 percent relative humidity, a temperature of about 22 to 28 degrees Celsius, evenly moist but never waterlogged soil, and roughly twelve hours of light per day. In a tropical urban home such conditions are hard to hold by hand: summer temperatures in Dhaka reach 33 to 36 degrees Celsius, air conditioning and the dry season lower indoor humidity within hours, and the illuminance near a window varies from a few hundred lux to several thousand. Manual care fails silently, because the owner notices the damage only after the plant has declined."),
  body("Existing products fall into two groups. Timer-based misting systems act without feedback: they mist on schedule even when the enclosure is saturated and continue when the reservoir is empty, which destroys the ultrasonic transducer. Cloud-connected plant monitors close the loop on at most one variable, depend on an internet connection and a vendor service, and offer no hardware protection against an empty reservoir or a leaking tray. Published research systems, reviewed in Section II, are mostly monitoring oriented, use a single threshold per variable and rely on cloud platforms for remote control."),
  body("This paper presents a low-cost controller that senses, decides and acts locally on the enclosure, closes the loop on every relevant variable at once, fails safe, and remains fully operable without internet access. The main contributions are: (1) a control design that combines a burst-and-soak watering state machine with a daily cap, humidity hysteresis with bounded bursts and cool-down, photoperiod-gated lighting and hardware interlocks; (2) a run-time configurable, local-first architecture in which a phone dashboard and a USB serial interface share one command layer; (3) an experimentally established switching-stage design, namely a 5 V active-low drive of opto-isolated MOSFET channels with flyback protection; and (4) a calibrated prototype operating with a live plant."),
  body("The remainder of the paper is organized as follows. Section II reviews related work. Section III describes the system design and Section IV its implementation. Section V reports the experimental results and discussion, and Section VI concludes the paper."),

  // ================================================================ II
  h1("II", "Related Work"),
  body("Oguntosin et al. [1] developed an ESP32-based greenhouse monitoring and control system that reads temperature, humidity, a light-dependent resistor and a resistive soil-moisture sensor and switches a bulb, a fan and a pump whenever a parameter crosses a fixed threshold; readings are stored in a database and shown on a web application. The work demonstrates the basic sense-decide-act loop on the same microcontroller family, but thresholds are compiled into the firmware, control is single-sided without hysteresis, and there is no protection against an empty water source."),
  body("Correa-Quiroz et al. [2] reported an ESP32 drip-irrigation and climate-monitoring system for greenhouses with DHT11, capacitive soil-moisture and ultrasonic water-level sensors, an LCD and the Arduino Cloud. Field tests showed a 35 percent reduction in water use, and the system offers automatic and manual modes. Remote control, however, depends on a cloud service. Abu Sneineh and Shabaneh [3] built a hydroponics monitor on the ESP32 with TDS, pH, water-level and temperature sensors in which pumps are actuated automatically or from the Blynk application; again the interface is cloud-hosted and the actuation carries no time-based limits."),
  body("Mellit et al. [4] designed a remote greenhouse-monitoring prototype around a NodeMCU that measures air temperature, relative humidity, capacitive soil moisture, light intensity and carbon dioxide, publishes them to a web page, sends GSM alerts and adds a Raspberry Pi camera with a convolutional neural network for disease detection. The breadth of sensing is close to the present work, while the two-processor architecture raises the cost well above what a home terrarium justifies. Simo et al. [7] presented a low-cost IoT greenhouse monitoring device for a farmer's decision making; like most surveyed work it is monitoring oriented and leaves actuation to the user."),
  body("Garcia et al. [5] surveyed sensors and IoT nodes for smart irrigation and concluded that low-cost capacitive soil-moisture probes are adequate for irrigation scheduling if calibrated in the target medium, and that they outlast resistive probes whose electrodes corrode in wet soil; this motivated the calibration procedure of Section III-B. The BME280 provides humidity, temperature and pressure in one I2C device with a specified humidity accuracy of about 3 percent RH [9], sufficient for a 15 percent hysteresis band, and the BH1750 reports illuminance directly in lux [10]. Hercog et al. [6] documented the design of ESP32-based IoT devices and evaluated the ESP32 as a dual-core, Wi-Fi-capable and inexpensive platform [8], which supports its selection here."),
  body("Table I summarizes the comparison. The gap addressed by this work is the combination of multi-variable closed-loop control with hysteresis, hardware safety interlocks, run-time adjustable parameters, a manual mode with automatic time-outs, and local-first operation that stays controllable from a phone without any internet or cloud service."),
  tableCaption("TABLE I.  Comparison with Related Systems"),
  grid([900, 760, 1000, 900, 700, 606], [
    ["Work", "Platform", "Sensed variables", "Actuation", "Offline control", "Safety interlocks"],
    ["[1]", "ESP32", "T, RH, light, soil", "Bulb, fan, pump", "No", "No"],
    ["[2]", "ESP32", "T, RH, UV, soil, level", "Drip valve", "No (cloud)", "Level sensing only"],
    ["[3]", "ESP32", "T, pH, TDS, level", "Pumps", "No (Blynk)", "No"],
    ["[4]", "NodeMCU + RPi", "T, RH, soil, light, CO2", "Irrigation, fan", "No", "No"],
    ["[7]", "IoT node", "Environment, electrical", "None", "No", "No"],
    ["This work", "ESP32", "T, RH, P, lux, 2x soil, leak, level", "2 mist, fan, light, buzzer", "Yes (hotspot + USB)", "Float, leak, daily cap, time-outs"],
  ], { size: 15 }),
  sp(120),

  // ================================================================ III
  h1("III", "System Design"),
  h2("A", "Architecture"),
  body("The system consists of a sensing stage, a controller and an actuation stage arranged around a single ESP32 module. The sensing stage comprises a BME280 (temperature, relative humidity, pressure) and a BH1750 (illuminance) on the I2C bus, two capacitive soil-moisture probes and a leak probe on the 12-bit analog inputs, and a float switch on a digital input. The actuation stage consists of two 4-channel opto-isolated MOSFET boards: one on a 5 V rail for the two ultrasonic mist makers and the alarm, the other on 12 V for the fan and the LED grow light. A 12 V adapter feeds a fused buck converter that provides the 5 V rail, and the ESP32's on-board regulator supplies 3.3 V to the sensors. Table II lists the components. Every two seconds the controller samples all inputs, evaluates the control rules of Section III-C, applies the safety interlocks and writes the outputs; clients on Wi-Fi or USB observe and command the system through a shared command layer described in Section IV."),
  tableCaption("TABLE II.  System Components"),
  grid([1500, 1466, 1900], [
    ["Component", "Interface / rating", "Function"],
    ["ESP32 DevKit V1", "CP2102 USB, Wi-Fi", "Controller, web server, USB interface"],
    ["GY-BME280", "I2C 0x76, 3.3 V", "Air temperature, RH, pressure"],
    ["BH1750FVI", "I2C 0x23, 3.3 V", "Illuminance (lux)"],
    ["Capacitive soil probe x2", "ADC, 3.3 V", "Soil moisture at two points"],
    ["Leak probe", "ADC, 3.3 V", "Drip-tray leak detection"],
    ["Float switch", "GPIO, pull-up", "Reservoir empty interlock"],
    ["MOSFET board x2", "Opto-isolated, 60N03", "5 V and 12 V load switching"],
    ["Mist maker x2", "DC 5 V, 1 A driver", "Watering, humidity"],
    ["Fan", "12 V, 0.08 A", "Exhaust ventilation"],
    ["LED strip 5050", "12 V, IP65", "Grow light, PWM dimmed"],
    ["Passive buzzer", "2.7 kHz tone", "Alarm"],
    ["12 V adapter, LM2596S buck", "12 V in, 5 V out", "Power supply"],
  ], { size: 15 }),
  sp(120),
  h2("B", "Sensing and Calibration"),
  body("Soil moisture is derived from the raw ADC reading of each capacitive probe by the two-point linear calibration"),
  new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: Math.floor(COL_W / 2) }, { type: TabStopType.RIGHT, position: COL_W }],
    spacing: { before: 120, after: 120 }, children: [
      R("\t"), R("M", { italics: true }), R(" (%) = "), R("100 (ADC", { italics: true }), R("dry", { italics: true, subScript: true }),
      R(" \u2212 ADC", { italics: true }), R("raw", { italics: true, subScript: true }), R(") / (ADC", { italics: true }),
      R("dry", { italics: true, subScript: true }), R(" \u2212 ADC", { italics: true }), R("wet", { italics: true, subScript: true }), R(")"), R("\t(1)") ] }),
  body([R("where "), R("ADC", { italics: true }), R("dry", { italics: true, subScript: true }), R(" and "), R("ADC", { italics: true }), R("wet", { italics: true, subScript: true }),
        R(" are the readings obtained with the probe in air and fully submerged in water, and the result is clamped to the range 0 to 100 percent. The two probes are averaged for the watering decision so that a single dry pocket does not trigger a burst. The probes and the leak probe are connected to input-only pins of the first ADC unit, because the second unit is unavailable while the Wi-Fi radio is active. The leak probe is treated as wet above a fixed count, and the float switch is read through an internal pull-up with a configurable empty state. Three consecutive failed humidity readings are treated as a sensor fault that switches the humidity mist off rather than on, since a dropped I2C transaction is not evidence of dry air.")]),
  h2("C", "Control Strategy"),
  body([R("Watering follows a burst-and-soak state machine with the states IDLE, RUN and SOAK. When the average moisture falls below the dry threshold and the reservoir is not empty, the first mist maker runs for one burst of duration "), R("t", { italics: true }), R("run", { italics: true, subScript: true }),
        R("; the controller then waits a soak period "), R("t", { italics: true }), R("soak", { italics: true, subScript: true }),
        R(" for the water to spread through the substrate before the soil is judged again. A hard cap bounds the total misting time per day even if a probe fails in the dry direction; the daily total is reset at midnight when a network clock is available and every 24 h of uptime otherwise.")]),
  body([R("Humidity control uses a hysteresis band: the second mist maker turns on when RH falls below "), R("RH", { italics: true }), R("low", { italics: true, subScript: true }),
        R(" and off when RH exceeds "), R("RH", { italics: true }), R("high", { italics: true, subScript: true }),
        R(", subject to a maximum burst length and a cool-down between bursts. The band avoids the on-off chatter of a single threshold, and the cool-down allows the sensor to register the mist just released before a new decision is made. The grow light follows a photoperiod window gated by illuminance: it is switched on below "), R("E", { italics: true }), R("on", { italics: true, subScript: true }),
        R(" and off above "), R("E", { italics: true }), R("off", { italics: true, subScript: true }),
        R(" inside the window and is always off outside it; without a valid clock the illuminance gate acts alone. The exhaust fan turns on above 32 degrees Celsius and off below 29. Three interlocks override all rules: an empty reservoir disables both mist channels, a wet leak probe raises the alarm, and any manual mist command is cancelled after a fixed time. Table III lists the parameters and their default values; all are adjustable at run time.")]),
  tableCaption("TABLE III.  Control Parameters and Default Values"),
  grid([1900, 1000, 1966], [
    ["Parameter", "Default", "Role"],
    ["Soil dry threshold", "35 %", "watering below this average moisture"],
    ["RH low / high", "75 / 90 %", "humidity mist on / off"],
    ["Illuminance on / off", "800 / 2000 lx", "grow light on / off"],
    ["Photoperiod", "07 to 19 h", "lighting window"],
    ["Light duty", "220 / 255", "PWM brightness"],
    ["Burst / soak", "90 s / 20 min", "watering cycle"],
    ["Daily cap", "30 min", "maximum watering per day"],
    ["Humidity burst / cool-down", "300 s / 180 s", "bounded misting"],
    ["Manual time-out", "10 min", "manual mist auto-off"],
  ], { size: 15 }),
  sp(120),
  h2("D", "Power and Switching Stage"),
  body("The power architecture has three rails. The 12 V rail from the adapter, protected by a 3 A fuse, feeds the buck converter and the 12 V loads. The 5 V rail from the buck converter feeds the ESP32, the mist driver modules and the inputs of the opto-couplers on both switching boards. The 3.3 V rail feeds the sensors only. Bulk capacitors at the buck output and at each mist driver absorb the inrush of a transducer so that the logic supply does not dip."),
  body("The opto-coupled inputs of the MOSFET boards require about 5 V to switch, which the 3.3 V logic of the ESP32 cannot supply directly. Each channel is therefore driven active-low: the input's positive terminal is tied to the 5 V rail and its return is pulled low by an ESP32 pin, so the microcontroller only sinks the small opto-LED current. The firmware inverts every output accordingly, including the PWM duty of the grow light, and writes all outputs to the off state before and after the pins are configured at boot, so that no channel can pulse during a reset. Because the fan is an inductive load, a 1N5819 Schottky diode is placed across it with the cathode to the positive lead; the ultrasonic transducers are piezoelectric loads and need no diode."),

  // ================================================================ IV
  h1("IV", "Implementation"),
  h2("A", "Firmware"),
  body("The firmware is written in C++ for the Arduino ESP32 core. A single non-blocking loop samples the sensors every 2 s, evaluates the rules in automatic mode or the manual guards in manual mode, and calls one output function that applies the interlocks and writes the pins. The fourteen control parameters are stored in non-volatile memory, are loaded at boot with compiled defaults as fallback, and can be changed by any client at run time. A shared command layer implements mode changes, output commands and parameter writes exactly once; both the HTTP handlers of the embedded web server and the USB serial parser call it, so wired and wireless control cannot diverge. Status strings are assembled in fixed buffers, and time comparisons use signed differences so that the 49-day millisecond counter wrap cannot freeze a cool-down."),
  h2("B", "Interfaces and Provisioning"),
  body("The embedded web server exposes a dashboard page and a small JSON API for status, outputs, mode, parameters and network credentials. The USB serial interface accepts the same commands as line-oriented text at 115200 baud and marks every reply with a prefix so that a host can separate replies from the boot log. Network credentials saved through either interface take precedence over compiled placeholders. If no network is configured or the connection fails, the board raises its own access point immediately and keeps retrying the saved network in the background every 90 s, while the clock is re-synchronized from NTP every 5 min until it succeeds. A host application was written to install the USB driver and the tool-chain, flash the firmware, provision credentials over the cable and exercise each output channel manually; it was used for the experiments in Section V."),
  h2("C", "Prototype"),
  body("Fig. 1(a) shows the bench setup used for the electrical measurements, with the ESP32 and sensors on a breadboard, the 5 V switching board and buck converter, and the mist maker, leak probe and buzzer in a plastic tub. Fig. 1(b) shows the prototype operating with a live Fittonia plant in a transparent enclosure: a soil probe is inserted in the substrate, the air sensor and the fan are mounted inside, and the controller is housed alongside. A digital multimeter was used for the rail voltages and switching checks, and a serial terminal for the firmware trace."),
  ...figurePair(path.join(A, "bench-photo.jpg"), path.join(A, "prototype-photo.jpg"),
    "Fig. 1. (a) Bench setup for the electrical measurements; (b) prototype operating with a live Fittonia plant."),

  // ================================================================ V
  h1("V", "Results and Discussion"),
  h2("A", "Sensor Calibration"),
  body("Table IV gives the two-point calibration of the soil probes and Fig. 2 the resulting transfer curves. Both probes read within a few counts of their end points when held in air or in water and responded to wetting within seconds. The usable spans of 1380 and 1415 counts correspond to a resolution of 0.072 and 0.071 percent moisture per count, two orders of magnitude finer than the 35 percent watering threshold, so quantization does not influence the decision. A disconnected probe floats near 2490 counts, which the firmware interprets as dry. The I2C scan reported the BME280 at address 0x76 and the BH1750 at 0x23; the BME280 read room conditions of about 67 percent RH and responded to breath or mist within seconds, and the BH1750 tracked changes in room light."),
  tableCaption("TABLE IV.  Two-Point Soil Probe Calibration (12-bit ADC)"),
  grid([1216, 1216, 1216, 1218], [
    ["Probe", "Dry (air)", "Wet (water)", "Span"],
    ["Probe 1", "2450", "1070", "1380"],
    ["Probe 2", "2485", "1070", "1415"],
  ], { size: 16, center: true }),
  ...figure(path.join(A, "soil-cal.png"), COL_W, "Fig. 2. Measured soil-moisture calibration transfer curves."),
  h2("B", "Electrical Characterization"),
  body("Table V compares design values with measurements. The adapter delivered 12.0 V and the buck converter 5.2 V under load, 4 percent above the 5.0 V design value and within the tolerance of the mist drivers and the ESP32 regulator. Driving a switching-board input from a 3.3 V pin produced only a faint input indication and no switching, with about 0.6 to 0.8 V measured across the opto-coupler; the expectation that 3.3 V logic would drive the inputs was therefore rejected and the active-low 5 V arrangement of Section III-D adopted, after which the channel switched cleanly and the mist maker ran on command. Switching the fan without a flyback diode caused the ESP32 to brown out and reset, whereas the same channel switched reliably with the load removed, which identifies the inductive transient as the cause and confirms the diode as the remedy."),
  tableCaption("TABLE V.  Design Values Versus Measurements"),
  grid([2466, 1200, 1200], [
    ["Quantity", "Design", "Measured"],
    ["Adapter output", "12.0 V", "12.0 V"],
    ["5 V rail (buck output)", "5.0 V", "5.2 V"],
    ["ESP32 3.3 V rail", "3.3 V", "3.2 V"],
    ["Opto input, 3.3 V drive", "switching", "0.6 to 0.8 V, no switching"],
    ["Opto input, 5 V active-low", "5 V / 0 V", "5.2 V / 0 V, switching"],
    ["Fan without flyback diode", "no effect", "controller reset"],
    ["Wi-Fi link strength", "> -70 dBm", "-53 dBm"],
  ], { size: 15, center: true }),
  sp(120),
  h2("C", "Control Behaviour and Connectivity"),
  body("With the humidity band at its defaults, the humidity channel engaged as soon as the measured RH of 67 percent lay below the 75 percent lower threshold and released only when the upper threshold was crossed or the burst limit expired, as the control law prescribes. The watering state machine executed its burst and soak phases on command, and the alarm produced a clean 2.7 kHz tone from the manual control. On the network side the board joined the local access point with a received signal strength of about -53 dBm, and the dashboard was reachable from a phone. Credentials pushed over USB caused the board to restart, join the new network and be rediscovered automatically; with no router present the board raised its own access point and the dashboard remained reachable. A parameter changed from the host was read back correctly after a power cycle. During development an apparent loss of two thirds of dashboard requests was traced not to the radio but to a firmware fault on every status request caused by a mismatched format string; after the correction every request was served."),
  h2("D", "Discussion"),
  body("The results confirm the two design decisions that were not obvious a priori: opto-isolated switching boards intended for 5 V logic must be driven active-low from a 3.3 V microcontroller, and inductive loads need flyback protection even at fan currents of 80 mA, because the transient couples into the shared supply and resets the controller. The hysteresis and burst-limited control produced the expected non-chattering behaviour, and the local-first architecture met the requirement of full operability without internet access. The evaluation has limits. The measurements were made on the 5 V stage of a prototype with a temporary enclosure; a long-duration unattended run against a reference hygrometer, which would allow a quantitative comparison of the humidity trace with the control model, remains to be performed. Humidity is sensed at one point, so gradients inside a larger enclosure are not observed, and the air sensor must be shielded from direct mist. Finally, the transducers must never run dry, which the float interlock guarantees only when the switch is installed in the reservoir."),

  // ================================================================ VI
  h1("VI", "Conclusion and Future Work"),
  body("A self-contained closed-loop terrarium controller was designed, implemented and evaluated on a single ESP32. Seven sensed quantities drive mist, ventilation, lighting and alarm outputs through isolated switching stages under a rules engine that combines a watering state machine, humidity hysteresis, bounded burst times, a daily cap and hardware interlocks. The soil probes were calibrated, the switching stage was characterized and corrected to an active-low 5 V drive with flyback protection, and control was demonstrated over Wi-Fi, a local access point and USB, with all parameters adjustable at run time and no dependence on internet services. Future work will integrate a purpose-built enclosure with the 12 V lighting and ventilation stage, perform a long-duration run against a reference hygrometer, add on-device data logging, and evaluate thermoelectric cooling for the hottest months."),

  // ================================================================ REFS
  h5("References"),
  refPara(1, "V. W. Oguntosin, C. Okeke, E. Adetiba, A. Abdulkareem, and J. O. Olowoleni, \u201cIoT-based greenhouse monitoring and control system,\u201d Int. J. Comput. Digit. Syst., vol. 14, no. 1, 2023, doi: 10.12785/ijcds/140137."),
  refPara(2, "J. J. Correa-Quiroz, M. A. Toribio-Barrueto, and C. Castro-Vargas, \u201cIoT system with ESP32 for smart drip irrigation and climate monitoring in greenhouses,\u201d Emerg. Sci. J., vol. 9, no. 3, pp. 1133\u20131157, Jun. 2025, doi: 10.28991/esj-2025-09-03-01."),
  refPara(3, "A. Abu Sneineh and A. A. A. Shabaneh, \u201cDesign of a smart hydroponics monitoring system using an ESP32 microcontroller and the Internet of Things,\u201d MethodsX, vol. 11, Art. no. 102401, 2023, doi: 10.1016/j.mex.2023.102401."),
  refPara(4, "A. Mellit, M. Benghanem, O. Herrak, and A. Messalaoui, \u201cDesign of a novel remote monitoring system for smart greenhouses using the Internet of Things and deep convolutional neural networks,\u201d Energies, vol. 14, no. 16, Art. no. 5045, Aug. 2021, doi: 10.3390/en14165045."),
  refPara(5, "L. Garc\u00eda, L. Parra, J. M. Jim\u00e9nez, J. Lloret, and P. Lorenz, \u201cIoT-based smart irrigation systems: An overview on the recent trends on sensors and IoT systems for irrigation in precision agriculture,\u201d Sensors, vol. 20, no. 4, Art. no. 1042, Feb. 2020, doi: 10.3390/s20041042."),
  refPara(6, "D. Hercog, T. Lerher, M. Trunti\u010d, and O. Te\u017eak, \u201cDesign and implementation of ESP32-based IoT devices,\u201d Sensors, vol. 23, no. 15, Art. no. 6739, Jul. 2023, doi: 10.3390/s23156739."),
  refPara(7, "A. Sim\u00f3, S. Dzi\u0163ac, G. E. Badea, and D. Meianu, \u201cSmart agriculture: IoT-based greenhouse monitoring system,\u201d Int. J. Comput. Commun. Control, vol. 17, no. 6, Art. no. 5039, Dec. 2022, doi: 10.15837/ijccc.2022.6.5039."),
  refPara(8, "Espressif Systems, \u201cESP32 series datasheet,\u201d v4.x, Shanghai, China. [Online]. Available: https://www.espressif.com/en/support/documents/technical-documents"),
  refPara(9, "Bosch Sensortec, \u201cBME280: Combined humidity and pressure sensor,\u201d Datasheet BST-BME280-DS002, Reutlingen, Germany."),
  refPara(10, "ROHM Semiconductor, \u201cBH1750FVI: Digital 16-bit serial output type ambient light sensor IC,\u201d Datasheet, Kyoto, Japan."),
];

// ================================================================== document
const pageFooter = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 16 })] })] });
const pageProps = { size: { width: A4W, height: A4H }, margin: IEEE };

const doc = new Document({
  creator: "Kishor Tarafder et al.",
  title: "IoT-Based Automated Tropical Terrarium Using ESP32",
  styles: { default: { document: { run: { font: "Times New Roman", size: 20 } } } },
  sections: [
    { properties: { page: pageProps }, footers: { default: pageFooter }, children: titleChildren },
    { properties: { type: SectionType.CONTINUOUS, page: pageProps, column: { count: 2, space: COL_GAP, equalWidth: true } },
      footers: { default: pageFooter }, children: paperChildren },
  ],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
