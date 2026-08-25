/* ============================================================================
 * BENCH WEB — live wiring dashboard in a browser
 *
 * Serves a page that refreshes every second showing every input on the board.
 * Plug a sensor in and watch it turn green. Nothing to reflash, nothing to
 * read in a terminal — just leave the page open while you build.
 *
 *   soil 1   D34      capacitive probe
 *   soil 2   D35      capacitive probe
 *   leak     D32      drip tray sensor
 *   float    D27      tank switch (INPUT_PULLUP)
 *   I2C      D21/D22  line health + address scan, tried BOTH pin orders
 *
 * Wi-Fi name and password come from wifi_secret.h (generated from config.h).
 * If Wi-Fi fails it starts its own hotspot: Terrarium / terrarium123
 *
 * Board: ESP32 Dev Module
 * ========================================================================== */
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include "wifi_secret.h"

#define PIN_SOIL_1 34
#define PIN_SOIL_2 35
#define PIN_LEAK   32
#define PIN_FLOAT  27
#define PIN_SDA    21
#define PIN_SCL    22

WebServer server(80);

int readAvg(int pin) {
  long acc = 0;
  for (int i = 0; i < 8; i++) { acc += analogRead(pin); }
  return acc / 8;
}

/* an unconnected analog pin drifts; a real sensor holds steady */
bool floating(int pin) {
  int lo = 4095, hi = 0;
  for (int i = 0; i < 16; i++) {
    int v = analogRead(pin);
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  return (lo < 400 && (hi - lo) > 80);
}

int lineHigh(int pin) {
  pinMode(pin, INPUT);
  int hi = 0;
  for (int i = 0; i < 20; i++) { if (digitalRead(pin)) hi++; delayMicroseconds(200); }
  return hi;
}

/* Only the addresses this project can actually contain. A full 126-address
   sweep takes seconds when nothing answers, because every miss waits for a
   bus timeout — far too slow for a page that refreshes every second. */
const byte KNOWN[] = { 0x23, 0x5C, 0x76, 0x77, 0x3C, 0x3D, 0x40, 0x48, 0x68 };

/* scan a bus and append every address found to buf; returns how many */
int scanBus(int sda, int scl, char* buf, size_t n) {
  Wire.end();
  Wire.begin(sda, scl);
  Wire.setClock(100000);
  Wire.setTimeOut(8);
  int found = 0;
  size_t at = 0;
  buf[0] = 0;
  for (unsigned k = 0; k < sizeof(KNOWN); k++) {
    byte a = KNOWN[k];
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      const char* who = "";
      if (a == 0x76 || a == 0x77) who = " BME280";
      else if (a == 0x23)         who = " BH1750";
      else if (a == 0x5C)         who = " BH1750 (ADDR high)";
      at += snprintf(buf + at, n - at, "%s0x%02X%s", found ? ", " : "", a, who);
      found++;
      if (at > n - 40) break;
    }
  }
  return found;
}

void handleStatus() {
  int s1 = readAvg(PIN_SOIL_1), s2 = readAvg(PIN_SOIL_2), lk = readAvg(PIN_LEAK);
  bool f1 = floating(PIN_SOIL_1), f2 = floating(PIN_SOIL_2);
  pinMode(PIN_FLOAT, INPUT_PULLUP);
  int fl = digitalRead(PIN_FLOAT);

  int sda = lineHigh(PIN_SDA), scl = lineHigh(PIN_SCL);

  char norm[160], swap[160];
  int nFound = scanBus(PIN_SDA, PIN_SCL, norm, sizeof(norm));
  int sFound = 0;
  swap[0] = 0;
  if (nFound == 0) sFound = scanBus(PIN_SCL, PIN_SDA, swap, sizeof(swap));

  char json[700];
  snprintf(json, sizeof(json),
    "{\"s1\":%d,\"s1f\":%d,\"s2\":%d,\"s2f\":%d,\"leak\":%d,\"float\":%d,"
    "\"sda\":%d,\"scl\":%d,\"n\":%d,\"norm\":\"%s\",\"sn\":%d,\"swap\":\"%s\","
    "\"ip\":\"%s\",\"up\":%lu}",
    s1, f1 ? 1 : 0, s2, f2 ? 1 : 0, lk, fl,
    sda, scl, nFound, norm, sFound, swap,
    WiFi.localIP().toString().c_str(), millis() / 1000);
  server.send(200, "application/json", json);
}

static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Terrarium bench</title><style>
*{box-sizing:border-box}body{margin:0;background:#12151a;color:#e8ecf1;
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:14px;
max-width:560px;margin:0 auto}
h1{font-size:17px;font-weight:600;margin:0 0 2px}
.sub{color:#8b95a3;font-size:12px;margin-bottom:14px}
.card{background:#1b1f27;border:1px solid #2a303b;border-radius:10px;
padding:12px 14px;margin-bottom:9px;display:flex;align-items:center;gap:12px}
.dot{width:11px;height:11px;border-radius:50%;flex:0 0 auto;background:#4b5563}
.ok{background:#22c55e}.bad{background:#ef4444}.warn{background:#f59e0b}
.name{font-weight:600;flex:1}.pin{color:#6b7280;font-size:11px;font-weight:400}
.val{font-variant-numeric:tabular-nums;font-size:19px;font-weight:600}
.note{color:#8b95a3;font-size:12px;margin-top:3px}
.wide{display:block}
code{background:#252b35;padding:1px 6px;border-radius:4px;font-size:12px}
</style></head><body>
<h1>Terrarium bench monitor</h1>
<div class="sub" id="sub">connecting...</div>
<div class="card"><span class="dot" id="d1"></span><span class="name">Soil 1
<span class="pin">D34</span></span><span class="val" id="v1">--</span></div>
<div class="card"><span class="dot" id="d2"></span><span class="name">Soil 2
<span class="pin">D35</span></span><span class="val" id="v2">--</span></div>
<div class="card"><span class="dot" id="d3"></span><span class="name">Leak
<span class="pin">D32</span></span><span class="val" id="v3">--</span></div>
<div class="card"><span class="dot" id="d4"></span><span class="name">Float switch
<span class="pin">D27</span></span><span class="val" id="v4">--</span></div>
<div class="card wide"><div style="display:flex;align-items:center;gap:12px">
<span class="dot" id="d5"></span><span class="name">I2C bus
<span class="pin">D21 / D22</span></span><span class="val" id="v5">--</span></div>
<div class="note" id="n5"></div></div>
<script>
function g(i){return document.getElementById(i)}
function dot(el,c){el.className='dot '+c}
async function tick(){
 try{
  const d=await (await fetch('/api/status',{cache:'no-store'})).json();
  g('sub').textContent=d.ip+' · up '+d.up+'s · refreshing every second';
  g('v1').textContent=d.s1; dot(g('d1'),d.s1f?'bad':'ok');
  g('v2').textContent=d.s2; dot(g('d2'),d.s2f?'bad':'ok');
  g('v3').textContent=d.leak; dot(g('d3'),'');
  g('v4').textContent=d.float?'tank OK':'EMPTY'; dot(g('d4'),d.float?'ok':'warn');
  const lines=(d.sda>17&&d.scl>17);
  g('v5').textContent=d.n?(d.n+' found'):(lines?'powered, silent':'nothing');
  dot(g('d5'),d.n?'ok':(lines?'warn':'bad'));
  let msg='';
  if(d.n) msg='answering at '+d.norm;
  else if(d.sn) msg='<b>SDA and SCL are swapped</b> — found '+d.swap+' the other way round';
  else if(lines) msg='module is powered (SDA '+d.sda+'/20, SCL '+d.scl+'/20) but never replies — jumper <code>CSB</code> to <code>3V3</code> and <code>SDO</code> to <code>GND</code>';
  else msg='no powered module on the bus (SDA '+d.sda+'/20, SCL '+d.scl+'/20) — check VCC on 3V3 and GND';
  g('n5').innerHTML=msg;
 }catch(e){ g('sub').textContent='lost connection to the board'; }
}
tick(); setInterval(tick,1000);
</script></body></html>)HTML";

void setup() {
  Serial.begin(115200);
  delay(400);
  analogSetAttenuation(ADC_11db);
  pinMode(PIN_FLOAT, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.begin(BW_SSID, BW_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) { delay(400); Serial.print('.'); }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nbench page: http://%s\n", WiFi.localIP().toString().c_str());
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("Terrarium", "terrarium123");
    Serial.printf("\nhotspot Terrarium / terrarium123 -> http://%s\n",
                  WiFi.softAPIP().toString().c_str());
  }
  if (MDNS.begin("terrarium")) Serial.println(F("also http://terrarium.local"));

  server.on("/", []() { server.send_P(200, "text/html", PAGE); });
  server.on("/api/status", handleStatus);
  server.begin();
  Serial.println(F("bench web running."));
}

void loop() {
  server.handleClient();
}
