// Builds the EEE 4103 capstone report: department cover + rubric pages, then the paper
// in IEEE conference A4 two-column format (Times New Roman, 10 pt body).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, TableBorders,
  WidthType, AlignmentType, SectionType, TabStopType, BorderStyle, ShadingType, PageBreak,
  VerticalAlign, PageNumber, Footer,
} = require("docx");

const A = path.join(__dirname, "assets");
const OUT = "C:/Users/kisho/Desktop/TERRARIUM/TERRARIUM-Report.docx";
const LOGO = path.join(__dirname, "assets/image1.png");

// ------------------------------------------------------------------ geometry
const A4W = 11906, A4H = 16838;                    // DXA
const COVER_M = 1440;                              // 1 in
const IEEE = { top: 1080, bottom: 1440, left: 907, right: 907 };   // 54 / 72 / 45.35 pt
const TEXT_W = A4W - IEEE.left - IEEE.right;       // 10092
const COL_GAP = 360;                               // 0.25 in
const COL_W = Math.floor((TEXT_W - COL_GAP) / 2);  // 4866
const COVER_W = A4W - 2 * COVER_M;                 // 9026
const PX = (dxa) => Math.round(dxa / 15);          // DXA -> px (96 dpi)

// ------------------------------------------------------------- image sizing
function imgSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89 && b[1] === 0x50) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  let i = 2;                                        // JPEG: walk to SOF0/2
  while (i < b.length) {
    if (b[i] !== 0xff) { i++; continue; }
    const m = b[i + 1];
    if (m === 0xc0 || m === 0xc2) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
    i += 2 + b.readUInt16BE(i + 2);
  }
  return { w: 1000, h: 750 };
}
function figure(file, widthDxa, caption) {
  const { w, h } = imgSize(file);
  const wp = PX(widthDxa), hp = Math.round(wp * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: file.endsWith(".jpg") ? "jpg" : "png", data: fs.readFileSync(file),
                               transformation: { width: wp, height: hp } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
      children: [new TextRun({ text: caption, size: 16 })] }),
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
    borders: o.borders, rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0 && o.header !== false, cantSplit: true,
      children: r.map((c, ci) => (c instanceof TableCell) ? c
        : cell(String(c), cols[ci], { size: o.size, bold: ri === 0 && o.header !== false,
                                       fill: ri === 0 && o.header !== false ? (o.fill || "E7E6E6") : undefined,
                                       align: o.center ? AlignmentType.CENTER : undefined })),
    })),
  });
}
const sp = (n = 0) => new Paragraph({ spacing: { after: n }, children: [] });

// ============================================================================
//  SECTION 1 - department cover page + assessment sheet
// ============================================================================
const univLines = ["American International University-Bangladesh", "Faculty of Engineering (FE)",
                   "Department of Electrical and Electronic Engineering (EEE)"];
const coverHeader = new Table({
  columnWidths: [1700, 7326], width: { size: COVER_W, type: WidthType.DXA }, borders: TableBorders.NONE,
  rows: [new TableRow({ children: [
    new TableCell({ width: { size: 1700, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new ImageRun({ type: "png", data: fs.readFileSync(LOGO), transformation: { width: 100, height: 102 } })] })] }),
    new TableCell({ width: { size: 7326, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      children: univLines.map((t, i) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
        children: [new TextRun({ text: t, bold: true, size: i === 0 ? 28 : 24 })] })) }),
  ] })],
});
const lab = (t, w) => cell([new TextRun({ text: t, bold: true, size: 22 })], w, { fill: "F2F2F2" });
const val = (t, w, span) => cell([new TextRun({ text: t, size: 22 })], w, { span });
const infoCols = [2300, 3113, 1600, 2013];
const infoTable = new Table({ columnWidths: infoCols, width: { size: COVER_W, type: WidthType.DXA }, rows: [
  new TableRow({ children: [lab("Course Name:", 2300), val("Microprocessor and Embedded Systems", 3113), lab("Course Code:", 1600), val("EEE 4103", 2013)] }),
  new TableRow({ children: [lab("Semester:", 2300), val("Summer 2025-2026", 3113), lab("Section:", 1600), val("", 2013)] }),
  new TableRow({ children: [lab("Faculty Name:", 2300), val("Debraj Das", 3113 + 1600 + 2013, 3)] }),
  new TableRow({ children: [lab("Capstone Project Title:", 2300), val("IoT-Based Automated Tropical Terrarium Using ESP32", 3113 + 1600 + 2013, 3)] }),
  new TableRow({ children: [lab("Project Group #:", 2300), val("", 3113 + 1600 + 2013, 3)] }),
] });
const stuCols = [700, 3326, 1800, 1700, 1500];
const TEAM = [["Kishor Tarafder", "23-54520-3"], ["Tahomina Era", "23-55027-3"], ["MD. Shakhawat Hossen", "23-54483-3"], ["Avishek Saha", "23-54508-3"]];
const stuRows = [["Sl #", "Student Name", "Student ID #", "Program", "Signature"]];
for (let i = 1; i <= 6; i++) { const m = TEAM[i - 1]; stuRows.push([`${i}.`, m ? m[0] : "", m ? m[1] : "", m ? "BSc in EEE" : "", ""]); }
const studentTable = grid(stuCols, stuRows, { size: 22, fill: "D9E2F3", center: true });

const coTable = grid([900, 2300, 500, 700, 500, 1100, 800, 1100, 1126], [
  ["CO/CLO Number", "CO/CLO Statement", "K", "P", "A", "Assessed Program Outcome Indicator", "BNQF Indicator", "Teaching-Learning Strategy", "Assessment Strategy"],
  ["3", "Demonstrate a course project using microcontrollers, sensors, actuators, switches, display devices, etc. that can solve a complex engineering problem in the electrical and electronic engineering discipline through appropriate research.", "K8", "P1 / P3 / P7", "", "P.d.1.P3", "FS.3", "Discussion", "Project Report (Literature Review)"],
  ["4", "Explain the complex engineering activities of a course project solving a complex engineering problem of the electrical and electronic engineering discipline through an effective presentation.", "", "", "A1 / A2", "P.j.3.A4", "SS.2", "Discussion", "Project Presentation"],
], { size: 15 });
const rubricTable = grid([900, 1500, 1500, 1500, 1500, 1226, 900], [
  ["COs", "Excellent to Proficient [31-45]", "Good [21-30]", "Acceptable [11-20]", "Unacceptable [1-10]", "No Response [0]", "Secured Marks"],
  ["CO3 / P.d.1.P3",
   "The outcome of the project demonstrates a course project utilizing microcontrollers, sensors, actuators, switches, display devices, and more, which can address a complex engineering problem in the electrical and electronic engineering field through appropriate research.",
   "The outcome of the project demonstrates a course project utilizing microcontrollers, sensors, actuators, switches, display devices, etc., and also addresses a complex engineering problem in the electrical and electronic engineering discipline through research.",
   "The outcome of the project demonstrates a course project using microcontrollers, sensors, actuators, switches, display devices, etc. but cannot solve a complex engineering problem properly in the electrical and electronic engineering discipline through appropriate research.",
   "The outcome of the project does not demonstrate a course project using microcontrollers, sensors, actuators, switches, display devices, etc. It also could not solve a complex engineering problem in the electrical and electronic engineering discipline through appropriate research.",
   "No Response at all / copied from others / identical submissions with gross errors / image file printed", ""],
  ["Comments", cell("", 1500 * 4, { span: 4 }), "Total Marks (45)", ""],
], { size: 15 });

const coverChildren = [
  coverHeader, sp(200),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [new TextRun({ text: "Course Capstone Project Report", bold: true, size: 32 })] }),
  infoTable, sp(240), studentTable,
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Assessment Materials and Marks Allocation", bold: true, size: 24 })] }),
  coTable, sp(200),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Assessment Rubrics:", bold: true, size: 22 })] }),
  rubricTable,
];

// ============================================================================
//  SECTION 2 - paper title block (single column)
// ============================================================================
const authorCell = (n, name, id) => new TableCell({
  width: { size: Math.floor(TEXT_W / 4), type: WidthType.DXA },
  children: [
    [`${n} ${name}`, 22, false], ["Dept. of Electrical and Electronic Engineering", 20, true],
    ["American International University-Bangladesh", 20, true], ["Dhaka, Bangladesh", 20, true],
    [`${id}@student.aiub.edu`, 20, false],
  ].map(([t, s, it]) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 },
    children: [new TextRun({ text: t, size: s, italics: it })] })),
});
const titleChildren = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
    children: [new TextRun({ text: "IoT-Based Automated Tropical Terrarium Using ESP32", size: 48 })] }),
  new Table({ columnWidths: [2523, 2523, 2523, 2523], width: { size: 10092, type: WidthType.DXA }, borders: TableBorders.NONE,
    rows: [new TableRow({ children: TEAM.map((m, i) => authorCell(["1st", "2nd", "3rd", "4th"][i], m[0], m[1])) })] }),
  sp(200),
];

// ============================================================================
//  SECTION 3 - two-column paper body
// ============================================================================
const abstractText =
  "Tropical plants kept indoors need a narrow band of humidity, temperature, soil moisture and light that is difficult to hold by hand, and existing plant controllers are either blind timers or cloud-dependent products. This project designs, builds and tests a self-contained automated terrarium controller around the ESP32 microcontroller. The system senses air temperature, relative humidity and pressure (BME280), light level (BH1750), soil moisture at two points (capacitive probes), tray leakage and reservoir level, and actuates two ultrasonic mist makers, an exhaust fan, a grow light and an alarm buzzer through opto-isolated MOSFET switching stages. A closed-loop rules engine with hysteresis bands, a burst-and-soak watering cycle and a daily watering cap runs entirely on the board; safety interlocks stop misting when the reservoir is empty or a leak is detected. Control is available on a phone through Wi-Fi or the board's own hotspot, and through a Windows console over USB that also installs drivers, flashes firmware and provisions Wi-Fi credentials. All fourteen automation thresholds are editable at run time and persist in non-volatile storage. Bench testing calibrated both soil probes by two-point measurement (dry 2450/2485, wet 1070 ADC counts), confirmed reliable actuation once the MOSFET inputs were driven at 5 V in an active-low arrangement, and verified end-to-end Wi-Fi provisioning and control at a link strength of about -53 dBm. The complete electronics cost about BDT 6,200, and a 20-question user survey was designed to capture requirements. The result is a low-cost, internet-independent platform that keeps a tropical micro-climate stable without daily attention.";
const keywords = "ESP32, Internet of Things, terrarium, closed-loop control, environmental monitoring, home automation";

const paperChildren = [
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
    children: [new TextRun({ text: "Abstract\u2014", bold: true, italics: true, size: 18 }),
               new TextRun({ text: abstractText, bold: true, size: 18 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
    children: [new TextRun({ text: "Keywords\u2014", bold: true, italics: true, size: 18 }),
               new TextRun({ text: keywords, bold: true, italics: true, size: 18 })] }),

  // ---------------------------------------------------------------- I. INTRO
  h1("I", "Introduction"),
  h2("A", "Background of Study and Motivation"),
  body("A terrarium is a small enclosed ecosystem in which tropical plants such as ferns, mosses and orchids are grown. These species need 70 to 90 percent relative humidity, a temperature of roughly 22 to 28 degrees Celsius, evenly moist but never waterlogged soil and about twelve hours of light per day. In a Bangladeshi home these conditions are hard to maintain by hand: air-conditioned rooms and the dry season pull humidity down within hours, while over-watering by an anxious owner rots the roots. Manual care fails silently, because the owner only notices the damage after the plant has already declined."),
  body("The commercial products that address this problem fall into two groups. Timer-based misting systems act blindly, misting even when the enclosure is already saturated. Cloud-connected plant monitors, on the other hand, stop working the moment the internet connection or the vendor's service is unavailable, and they rarely close the loop on more than one variable. Neither group offers hardware safety interlocks against an empty reservoir or a leaking tray."),
  body("The motivation of this work is therefore to build a controller that senses, decides and acts locally on the enclosure itself, that closes the loop on every important variable at once, that can be tuned by a non-expert from a phone, and that remains fully functional with no internet access. Using a microcontroller platform, sensors, actuators, switching devices and a display interface to solve this multi-variable control problem is precisely the kind of complex engineering activity that the course targets."),
  h2("B", "Project Objectives"),
  body("The objectives of the project were: 1) to design a fully enclosed, sensor-driven micro-climate control system for a tropical terrarium; 2) to develop ESP32 firmware with a closed-loop rules engine having automatic and manual modes for misting, airflow and lighting; 3) to implement five sensing channels covering temperature, humidity, pressure, light, dual soil moisture, leakage and water level; 4) to incorporate safety interlocks, namely a reservoir float cut-off, a leak alarm, a daily watering cap and buzzer alerts; 5) to provide dual-mode control through a phone dashboard over Wi-Fi or hotspot and a Windows console over USB; and 6) to calibrate the soil sensors and analyze the system's behaviour against measured data."),
  h2("C", "A Brief Outline of the Report"),
  body("Section II reviews recent journal literature on IoT-based greenhouse, irrigation and plant-monitoring systems and positions this work against it. Section III describes the working principle, the process of work, the components and the test setup. Section IV presents the numerical analysis, the measured results, their comparison, the cost analysis and the limitations. Section V concludes the report and lists future endeavours. The as-built wiring diagram and the project timeline are given in the appendix."),

  // ------------------------------------------------------------ II. LIT REVIEW
  h1("II", "Literature Review"),
  body("Oguntosin et al. [1] developed an ESP32-based greenhouse monitoring and control system that reads temperature, humidity, a light-dependent resistor and a resistive soil-moisture sensor, and switches a bulb, a fan and a pump whenever a parameter crosses a fixed threshold. Data are stored in a database and shown on a web application. The work demonstrates the basic sense-decide-act loop on the same microcontroller family used here, but its thresholds are compiled into the firmware, control is single-sided (no hysteresis) and there is no protection against an empty water source."),
  body("Correa-Quiroz, Toribio-Barrueto and Castro-Vargas [2] reported an ESP32 drip-irrigation and climate-monitoring system for greenhouses using DHT11, capacitive soil-moisture and ultrasonic water-level sensors with an LCD and the Arduino Cloud. Field tests showed a 35 percent reduction in water use, and the system offers both automatic and manual modes, a feature adopted in this project. However, remote control depends on a cloud service, so the greenhouse cannot be reached when the internet is down."),
  body("Abu Sneineh and Shabaneh [3] built a smart hydroponics monitor on the ESP32 with TDS, pH, water-level and temperature sensors; pumps are actuated automatically when readings deviate from set values, or manually from the Blynk smartphone application. The paper confirms that a single ESP32 can run a multi-variable control loop with a phone interface, but again the interface is cloud-hosted and the actuation decisions have no time-based safety limits."),
  body("Mellit et al. [4] designed a remote greenhouse-monitoring prototype around a NodeMCU that measures air temperature, relative humidity, capacitive soil moisture, light intensity and carbon dioxide, publishes them to a web page, sends GSM alerts and adds a Raspberry Pi camera with a convolutional neural network for disease detection. The breadth of sensing is close to this project, while the two-processor architecture and cellular alerting raise the cost well above what a home terrarium can justify."),
  body("Garcia et al. [5] surveyed sensors and IoT nodes used in smart irrigation and highlighted that low-cost capacitive soil-moisture probes are now accurate enough for irrigation scheduling if they are calibrated in the target medium. This finding motivated the two-point calibration procedure used in Section III and the choice of capacitive rather than resistive probes, which corrode in wet soil."),
  body("Hercog, Lerher, Truntic and Tezak [6] documented the design and implementation of ESP32-based IoT devices for teaching, covering the Arduino tool-chain, sensor interfacing over I2C and Wi-Fi connectivity. Their evaluation of the ESP32 as a dual-core, Wi-Fi-capable and inexpensive platform supports its selection as the controller of this project."),
  body("Simo, Dzitac, Badea and Meianu [7] presented a low-cost IoT greenhouse monitoring device that digitizes environmental and electrical quantities for a farmer's decision making. Like most of the surveyed work it is monitoring-oriented; the actuation side is left to the user."),
  body("Table I summarizes the comparison. The gap that this project addresses is the combination of multi-variable closed-loop control with hysteresis, hardware safety interlocks, run-time adjustable thresholds and local-first operation that keeps working, and stays controllable from a phone, with no internet or cloud service at all."),
  tableCaption("TABLE I.  Comparison of Related Work with This Project"),
  grid([900, 760, 1000, 900, 700, 606], [
    ["Work", "Platform", "Sensed variables", "Actuation", "Offline control", "Safety interlocks"],
    ["[1] 2023", "ESP32", "T, RH, light, soil", "Bulb, fan, pump", "No", "No"],
    ["[2] 2025", "ESP32", "T, RH, UV, soil, level", "Drip valve", "No (cloud)", "Level sensing only"],
    ["[3] 2023", "ESP32", "T, pH, TDS, level", "Pumps", "No (Blynk)", "No"],
    ["[4] 2021", "NodeMCU + RPi", "T, RH, soil, light, CO2", "Irrigation, fan", "No", "No"],
    ["[7] 2022", "IoT node", "Environment, electrical", "None", "No", "No"],
    ["This work", "ESP32", "T, RH, P, lux, 2x soil, leak, level", "2 mist, fan, light, buzzer", "Yes (hotspot + USB)", "Float, leak, daily cap, timeouts"],
  ], { size: 15 }),
  sp(120),

  // ------------------------------------------------------- III. METHODOLOGY
  h1("III", "Methodology and Modeling"),
  h2("A", "Introduction"),
  body("The system was developed as a bench prototype in stages, each verified with measurements before the next was added: controller and tool-chain bring-up, sensor bring-up and calibration, the power and actuation stage, the firmware rules engine and web interface, the Windows console and provisioning path, and finally a stand-alone manual tester used for the experiments in Section IV. The enclosure parts were designed in OpenSCAD for PETG printing and are integrated after the bench phase."),
  h2("B", "Working Principle of the Proposed Project"),
  body("Fig. 1 shows the block diagram. Every two seconds the ESP32 reads the BME280 and BH1750 over the I2C bus, samples the two capacitive soil probes and the leak probe on 12-bit analog inputs, and reads the float switch. The readings feed a rules engine that holds the state of five outputs. In automatic mode the engine applies the following laws; in manual mode the outputs follow the user directly while the safety interlocks remain active."),
  ...figure(path.join(A, "block-diagram.png"), COL_W, "Fig. 1. Block diagram of the automated terrarium system."),
  body("Soil moisture is derived from the raw ADC value by the two-point linear calibration"),
  new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: Math.floor(COL_W / 2) }, { type: TabStopType.RIGHT, position: COL_W }],
    spacing: { before: 120, after: 120 }, children: [
      R("\t"), R("M", { italics: true }), R(" (%) = "), R("100 (ADC", { italics: true }), R("dry", { italics: true, subScript: true }),
      R(" \u2212 ADC", { italics: true }), R("raw", { italics: true, subScript: true }), R(") / (ADC", { italics: true }),
      R("dry", { italics: true, subScript: true }), R(" \u2212 ADC", { italics: true }), R("wet", { italics: true, subScript: true }), R(")"), R("\t(1)") ] }),
  body([R("where "), R("ADC", { italics: true }), R("dry", { italics: true, subScript: true }), R(" and "), R("ADC", { italics: true }), R("wet", { italics: true, subScript: true }),
        R(" are the readings measured with the probe in air and fully submerged in water. Watering follows a burst-and-soak cycle: when the average moisture falls below the dry threshold (default 35 percent) and the reservoir is not empty, mist maker 1 runs for one burst (default 90 s), the controller waits a soak period (default 20 min) for the water to spread, and then re-judges the soil. A hard cap (default 30 min of misting per day) bounds the water that can be delivered even if a probe fails wet-low.")]),
  body([R("Humidity uses a hysteresis band: mist maker 2 turns on when RH falls below "), R("RH", { italics: true }), R("low", { italics: true, subScript: true }),
        R(" (default 75 percent) and off when RH rises above "), R("RH", { italics: true }), R("high", { italics: true, subScript: true }),
        R(" (default 90 percent), with a maximum burst length of 5 min and a cool-down of 3 min between bursts. Fig. 2 shows the simulated behaviour of this law. The band prevents the rapid on-off chatter that a single threshold would produce, and the cool-down lets the sensor catch up with the mist it has just released.")]),
  ...figure(path.join(A, "hysteresis.png"), COL_W, "Fig. 2. Simulated humidity hysteresis cycle with the default 75 / 90 percent band."),
  body("The grow light follows a photoperiod window (default 07:00 to 19:00, clock from NTP when available) gated by the measured light level: it switches on below 800 lx and off above 2000 lx inside the window and is always off outside it. The exhaust fan turns on above 32 degrees Celsius and off below 29. Three interlocks override everything: an empty reservoir disables both mist channels, a wet leak probe raises the buzzer alarm, and any manual mist command is automatically cancelled after ten minutes."),
  body("The MOSFET board is driven active-low. Its opto-coupled inputs need about 5 V to switch, which the 3.3 V logic of the ESP32 cannot supply directly; therefore each channel's PWM terminal is tied to the 5 V rail and its GND terminal is pulled low by the ESP32 pin to turn the channel on. The firmware inverts every output accordingly, including the PWM duty used to dim the grow light, and writes all outputs to the off state before and after the pins are configured at boot so that no channel can pulse during a reset."),
  h2("C", "Process of Work (Experimental and Simulation Processes)"),
  body("Work started on 11 August 2026 and followed the timeline in the appendix. The tool-chain was set up around the CP210x USB driver and the Arduino ESP32 core (version 3.3.11), driven from the command line so that every build and every serial trace could be captured. Sensor bring-up began with an I2C bus scan; the BME280 was found only after its chip-select and address pins were tied before power-up, and the BH1750 read intermittently until its header was soldered. Both soil probes were calibrated by the two-point method in air and in water. The actuation stage was then added and the drive arrangement of the MOSFET board was established by measurement (Section IV). The firmware rules engine, the on-board web dashboard and the USB command protocol were written next, followed by the Windows console, which automates driver and tool-chain installation, firmware flashing and Wi-Fi provisioning over the cable, and the stand-alone tester used for manual channel tests."),
  body("The simulation process consisted of modelling the humidity hysteresis law as a discrete-time loop with a constant mist-on rise rate and a constant leak-down rate to predict the cycle period and duty (Fig. 2), and of a power-budget calculation for the 12 V supply (Section IV-A). In parallel, a 20-question user survey titled Automated Terrarium System Survey was designed on Google Forms to capture requirements: respondent background, indoor plant-care habits and failures, the usefulness of each automation feature on a 1 to 5 scale, mobile-application and alert preferences, safety trust, and an acceptable price range for Bangladesh."),
  h2("D", "Description of the Components"),
  body("Table II lists the main components with their role. The ESP32 DevKit V1 provides two cores, Wi-Fi and a CP2102 USB-serial bridge that doubles as the console link. The GY-BME280 module measures temperature, relative humidity and pressure over I2C at address 0x76; the BH1750FVI measures illuminance over I2C at address 0x23. The capacitive soil probes and the leak probe are read on the 12-bit ADC inputs, which are input-only pins chosen so that the Wi-Fi radio does not disturb them. The float switch is read with an internal pull-up. Two 4-channel opto-isolated MOSFET boards switch the loads: board A on the 5 V rail for the two ultrasonic mist makers (DC 5 V, 1 A driver modules) and the buzzer, board B on 12 V for the fans and the LED grow light. A 12 V, 5 A adapter feeds a fused LM2596S buck converter that produces the 5 V rail. Schottky diodes (1N5819) are fitted across each fan as flyback protection."),
  tableCaption("TABLE II.  Main Components and Their Function"),
  grid([1500, 1466, 1900], [
    ["Component", "Interface / rating", "Function"],
    ["ESP32 DevKit V1", "CP2102 USB, Wi-Fi", "Controller, web server, USB console"],
    ["GY-BME280", "I2C 0x76, 3.3 V", "Air temperature, RH, pressure"],
    ["BH1750FVI", "I2C 0x23, 3.3 V", "Illuminance (lux)"],
    ["Capacitive soil probe x2", "ADC GPIO34 / 35", "Soil moisture at two points"],
    ["Leak probe", "ADC GPIO32", "Drip-tray leak detection"],
    ["Float switch", "GPIO27, pull-up", "Reservoir empty interlock"],
    ["MOSFET board x2", "Opto-isolated, 60N03", "5 V and 12 V load switching"],
    ["Mist maker x2", "DC 5 V, 1 A driver", "Watering burst, humidity"],
    ["Fan WDM4010S12", "12 V, 0.08 A", "Exhaust / circulation"],
    ["LED strip 5050", "12 V, IP65", "Grow light, PWM dimmed"],
    ["Passive buzzer", "GPIO26, 2.7 kHz", "Alarm"],
    ["12 V 5 A adapter + LM2596S", "12 V in, 5 V out", "Power supply"],
  ], { size: 15 }),
  sp(120),
  h2("E", "Test / Experimental Setup"),
  body("Fig. 3 shows the bench setup: the ESP32 and sensors on a breadboard, the MOSFET board and buck converter on the 5 V side, and the mist maker, leak probe and buzzer placed in a plastic tub that served as a stand-in enclosure. A digital multimeter was used for rail voltages and switching checks, the serial monitor at 115200 baud for the firmware trace, the on-board dashboard on a phone for wireless control, and the tester application for driving each channel by hand while observing the sensors. The photograph is of the bench build; enclosure photographs are added after integration."),
  ...figure(path.join(A, "bench-photo.jpg"), Math.floor(COL_W * 0.72), "Fig. 3. Bench prototype under test with all channels live."),

  // ---------------------------------------------------------- IV. RESULTS
  h1("IV", "Results and Discussions"),
  h2("A", "Simulation / Numerical Analysis"),
  body("Calibration resolution. With the measured end points of probe 1 (2450 counts in air, 1070 in water) the usable span is 1380 counts, so one ADC count corresponds to 0.072 percent moisture; for probe 2 (2485 / 1070) the span is 1415 counts and the resolution 0.071 percent. A reading of 1800 counts on probe 1 maps by (1) to 47.1 percent. The resolution is two orders of magnitude finer than the 35 percent watering threshold, so quantization does not affect the decision."),
  body("Watering budget. With a 90 s burst and a 20 min soak the loop can start at most 2.7 bursts per hour; the 30 min daily cap therefore limits misting to 20 bursts, or about 7 percent of the day, regardless of sensor state. Humidity cycle. The simulation in Fig. 2 with a rise of 0.055 percent per second while misting and a fall of 0.028 percent per second otherwise gives a cycle of about 5 min on and 9 min off, a duty of about 35 percent, well inside the 5 min burst limit."),
  body("Power budget. The rated loads are two mist drivers at 5 V, 1 A (10 W), two fans at 12 V, 0.08 A (1.9 W), a 1 m 5050 LED strip (up to 14.4 W) and the controller with sensors (about 0.5 W), a total of about 27 W against the 60 W adapter, or 45 percent utilization with every load on at once. The LM2596S buck at 5 V, 2.5 A delivers the mist and logic current with margin. A Peltier cooler, considered for a future stage, would need its own supply because a TEC1-12706 alone draws up to 60 W."),
  h2("B", "Measured Response / Experimental Results"),
  body("Table III gives the soil-probe calibration measured on the bench, and Fig. 4 plots the resulting transfer curves. Both probes gave stable readings within a few counts when held in air or in water, and responded to wetting within seconds. The supply chain measured 12.0 V at the adapter and 5.2 V at the buck output under load. The I2C scan reported the BME280 at 0x76 and the BH1750 at 0x23; the BME280 reads room conditions of about 67 percent RH and responds to breath or mist within seconds, and the BH1750 tracks room-light changes."),
  tableCaption("TABLE III.  Measured Soil-Sensor Calibration (12-bit ADC)"),
  grid([1216, 1216, 1216, 1218], [
    ["Probe", "ADC dry (air)", "ADC wet (water)", "Usable span"],
    ["Soil 1", "2450", "1070", "1380"],
    ["Soil 2", "2485", "1070", "1415"],
  ], { size: 16, center: true }),
  ...figure(path.join(A, "soil-cal.png"), COL_W, "Fig. 4. Measured soil-moisture calibration transfer curves."),
  body("Actuation. Driving the MOSFET-board inputs from a 3.3 V pin produced only a dim input LED and no switching; the input terminal measured about 0.6 to 0.8 V across the opto-coupler. With the PWM terminal on the 5 V rail and the GND terminal pulled low by the ESP32 the channel switched cleanly, the input LED lit fully and the mist maker ran from the dashboard, the console and the tester. Switching a 12 V fan on the 5 V board without a flyback diode caused the ESP32 to brown out and reset; the same test with the load removed switched the channel LED reliably, confirming the inductive kick as the cause and the diode as the remedy."),
  body("Connectivity. The board joined the home network with a received signal strength of about -53 dBm, and the dashboard was reachable from a phone on the same network. Wi-Fi credentials entered in the console were pushed over USB, after which the board restarted, joined the new network and was rediscovered by the console automatically. With no router present the board raised its own hotspot and the dashboard was reachable at its fixed address. During development, apparent packet loss of two thirds of requests was traced not to the radio but to a firmware panic on every status request caused by a mismatched format string; after the fix the dashboard served every request. Settings changed from the console were read back correctly after a power cycle."),
  h2("C", "Comparison between Numerical and Experimental Results"),
  body("The calibration model reproduces the measured end points by construction, and the measured span (1380 and 1415 counts) confirms that the 12-bit ADC resolution predicted in Section IV-A is available in practice. The hysteresis law behaved as simulated: in automatic mode the humidity channel engaged as soon as the measured RH (67 percent) was below the 75 percent threshold and released only after the upper threshold was crossed or the 5 min burst limit expired, exactly the sequence in Fig. 2; the observed engagement was at first mistaken for a fault until the model explained it. The measured 5.2 V rail is 4 percent above the 5.0 V design value and within the tolerance of the mist drivers and the ESP32 regulator, so the power budget holds. A quantitative long-duration comparison of the RH trace against the simulation is planned for the 48-hour soak test described in Section IV-E."),
  h2("D", "Cost Analysis"),
  body("Table IV lists the cost of the electronics actually used, at the supplier prices paid, together with an estimate for the enclosure materials that are still being sourced. The electronics total about BDT 6,200 and the complete system about BDT 8,200 (roughly USD 70). This falls inside the BDT 8,001 to 12,000 bracket offered as an option in the user survey and is far below imported combinations of a humidistat, an irrigation timer and a lighting controller, none of which provide the interlocks or the phone interface of this design."),
  tableCaption("TABLE IV.  Cost of the Built System (BDT)"),
  grid([2216, 700, 950, 1000], [
    ["Item", "Qty", "Unit", "Total"],
    ["ESP32 DevKit V1 (CP2102)", "1", "650", "650"],
    ["GY-BME280 module", "1", "420", "420"],
    ["BH1750FVI module", "1", "235", "235"],
    ["Capacitive soil moisture sensor", "2", "195", "390"],
    ["Float switch", "1", "299", "299"],
    ["Leak (water level) sensor", "1", "49", "49"],
    ["USB mist maker kit with driver", "2", "380", "760"],
    ["MOSFET F5305S 4-channel board", "2", "550", "1,100"],
    ["12 V 40 mm fan", "2", "150", "300"],
    ["12 V 5 A adapter", "1", "450", "450"],
    ["LM2596S buck converter", "1", "380", "380"],
    ["Passive buzzer module", "1", "52", "52"],
    ["1N5819 Schottky diodes (10)", "1", "30", "30"],
    ["Switch, fuse holders, capacitors, resistors, barrel jack", "1", "299", "299"],
    ["Veroboard, headers, terminals, jumpers, heat shrink, breadboard", "1", "795", "795"],
    ["Electronics subtotal", "", "", "6,209"],
    ["Enclosure, acrylic, silicone, LED strip, fuses (estimate)", "1", "1,965", "1,965"],
    ["Total", "", "", "8,174"],
  ], { size: 15 }),
  sp(120),
  h2("E", "Limitations in the Project"),
  body("At the time of writing the system is a verified bench build; the printed enclosure and the 12 V board for the light and fans are being integrated, so the results above come from the 5 V stage in a tub. The planned 48-hour unattended run, which will provide the RH and soil traces for a quantitative comparison with the simulation and a comparison against a reference hygrometer, is not yet complete, and the survey responses are still being collected. The BH1750 module was unreliable until its header was soldered, and the BME280 requires its mode pins to be fixed before power-up, two assembly details that must be respected in the final build. Humidity is measured at one point, so gradients inside a larger enclosure are not seen. Finally, the ultrasonic mist makers must never run dry, which the float interlock enforces only if the switch is installed as designed."),

  // ------------------------------------------------------- V. CONCLUSION
  h1("V", "Conclusion and Future Endeavors"),
  body("A complete closed-loop terrarium controller was designed, built and verified end to end on the bench. Seven sensed quantities feed a rules engine on a single ESP32 that drives mist, fan, light and alarm outputs through isolated switching stages, with hysteresis, timed watering, a daily cap and hardware interlocks providing safe, stable operation. Both soil probes were calibrated, the actuation path was characterized and corrected to an active-low 5 V drive, and wireless and USB control paths including credential provisioning were demonstrated. All thresholds are tunable at run time, and the system operates with no internet connection. The platform costs about BDT 8,200 and is reproducible from the published firmware, tools and wiring documentation."),
  body("Future work will integrate the printed PETG enclosure and the 12 V lighting and airflow stage, complete the 48-hour soak test with a reference hygrometer, add on-board data logging with trend charts and push alerts, and evaluate a Peltier cooling stage for the hottest months. Longer-term extensions are camera-based plant-health monitoring, battery backup and the networking of several enclosures under one console."),

  // ------------------------------------------------------------ REFERENCES
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

// ============================================================================
//  SECTION 4 - appendix, single column, full-width figures
// ============================================================================
const appendixChildren = [
  h5("Appendix"),
  body("Fig. 5 reproduces the as-built wiring diagram of the bench build, generated from an interactive page developed for the project in which every wire can be selected and traced. Solid wires are connected and verified; dashed wires are planned. Fig. 6 shows the project timeline."),
  ...figure(path.join(A, "wiring-crop.png"), 7200, "Fig. 5. As-built wiring diagram of the bench build (32 of 39 planned connections live)."),
  ...figure(path.join(A, "gantt.png"), 8800, "Fig. 6. Project timeline from 11 August 2026 (completed work in dark, planned in light)."),
  body("The survey instrument (Automated Terrarium System Survey, Google Forms, 20 questions) covers respondent background, plant-care habits and failures, usefulness ratings of automatic irrigation, climate control and lighting, mobile-application and alert preferences, safety concerns and trust in safety features, sustainability beliefs and an acceptable price range. Response charts are appended once collection closes."),
];

// ================================================================== document
const pageFooter = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 16 })] })] });

const doc = new Document({
  creator: "EEE 4103 project group",
  title: "IoT-Based Automated Tropical Terrarium Using ESP32",
  styles: { default: { document: { run: { font: "Times New Roman", size: 20 } } } },
  sections: [
    { properties: { page: { size: { width: A4W, height: A4H }, margin: { top: COVER_M, bottom: COVER_M, left: COVER_M, right: COVER_M } } },
      children: coverChildren },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: A4W, height: A4H }, margin: IEEE } },
      footers: { default: pageFooter }, children: titleChildren },
    { properties: { type: SectionType.CONTINUOUS, page: { size: { width: A4W, height: A4H }, margin: IEEE },
                    column: { count: 2, space: COL_GAP, equalWidth: true } },
      footers: { default: pageFooter }, children: paperChildren },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: A4W, height: A4H }, margin: IEEE } },
      footers: { default: pageFooter }, children: appendixChildren },
  ],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
