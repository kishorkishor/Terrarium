#!/usr/bin/env python3
"""
TerrariumTester - a tiny standalone bench tester for the terrarium board.

Double-click the exe: it finds the ESP32 on USB, opens a local page at
http://127.0.0.1:8770 with big ON/OFF buttons for every output plus live
sensor readings, so every channel can be exercised by hand.

Deliberately separate from TerrariumConsole.exe (port 8765): this one does
manual control only - no flashing, no Wi-Fi setup, no thresholds. Only one
program can hold the COM port at a time, so close the console (and the
Arduino Serial Monitor) while using the tester.

Talks the firmware's USB protocol:  CMD STATUS / OUT / MODE / PING -> "#R {json}"
"""

import json
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import serial
from serial.tools import list_ports

HTTP_PORT = 8770
BAUD = 115200
OUT_NAMES = ("water", "hum", "light", "buzz", "fan")


# --------------------------------------------------------------------------- #
#  serial link                                                                #
# --------------------------------------------------------------------------- #
class SerialLink:
    def __init__(self):
        self.ser = None
        self.port = None
        self.msg = "searching for the board on USB..."
        self.log = deque(maxlen=400)
        self.last_status = None
        self.last_status_ts = 0.0
        self._cmd_lock = threading.Lock()
        self._resp = None
        self._resp_evt = threading.Event()
        self._want = False
        self._alive = False

    # ---- connection ------------------------------------------------------- #
    @staticmethod
    def find_port():
        best = None
        for p in list_ports.comports():
            if p.vid == 0x10C4 and p.pid == 0xEA60:      # CP210x = our board
                return p.device
            if p.vid is not None and best is None:       # any real USB serial
                best = p.device
        return best

    def open(self, port):
        try:
            s = serial.Serial()
            s.port = port
            s.baudrate = BAUD
            s.timeout = 0.2
            # keep DTR/RTS low so opening the port does not auto-reset the ESP32
            s.dtr = False
            s.rts = False
            s.open()
        except serial.SerialException as e:
            if "denied" in str(e).lower() or "busy" in str(e).lower():
                self.msg = f"{port} is busy - close TerrariumConsole.exe or the Arduino Serial Monitor"
            else:
                self.msg = f"cannot open {port}: {e}"
            return False
        self.ser = s
        self.port = port
        self.msg = f"connected on {port}"
        self._alive = True
        threading.Thread(target=self._reader, daemon=True).start()
        time.sleep(0.3)
        return True

    def close(self):
        self._alive = False
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.port = None

    @property
    def connected(self):
        return self.ser is not None and self._alive

    # ---- reader thread: route "#R " replies, keep the rest as boot log ---- #
    def _reader(self):
        while self._alive and self.ser:
            try:
                raw = self.ser.readline()
            except serial.SerialException:
                self.msg = "board unplugged - searching again..."
                self.close()
                return
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            if line.startswith("#R "):
                try:
                    obj = json.loads(line[3:])
                except ValueError:
                    continue
                if isinstance(obj, dict) and "out" in obj:
                    self.last_status = obj
                    self.last_status_ts = time.time()
                if self._want:
                    self._resp = obj
                    self._resp_evt.set()
            else:
                self.log.append(f"{time.strftime('%H:%M:%S')}  {line}")

    # ---- one command, one reply ------------------------------------------- #
    def command(self, line, timeout=3.0):
        if not self.connected:
            return None
        with self._cmd_lock:
            self._resp = None
            self._resp_evt.clear()
            self._want = True
            try:
                self.ser.write((line + "\n").encode())
            except serial.SerialException:
                self._want = False
                self.close()
                return None
            ok = self._resp_evt.wait(timeout)
            self._want = False
            return self._resp if ok else None

    def fresh_status(self, max_age=1.0):
        if self.connected and time.time() - self.last_status_ts > max_age:
            self.command("CMD STATUS")
        return self.last_status


LINK = SerialLink()


def auto_connect_loop():
    while True:
        if not LINK.connected:
            port = SerialLink.find_port()
            if port:
                LINK.open(port)
            else:
                LINK.msg = "no board found - plug the ESP32 in over USB"
        time.sleep(3)


# --------------------------------------------------------------------------- #
#  the page                                                                   #
# --------------------------------------------------------------------------- #
PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Terrarium Tester</title>
<style>
:root{--bg:#0d1512;--card:#15201b;--line:#24352d;--txt:#d9e8e0;--dim:#7d9488;
      --on:#22c55e;--off:#334741;--warn:#f59e0b;--bad:#ef4444;--acc:#34d399}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:15px/1.45 system-ui,Segoe UI,sans-serif;padding:18px}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:20px;letter-spacing:.06em;margin-bottom:2px}
h1 span{color:var(--acc)}
.sub{color:var(--dim);font-size:13px;margin-bottom:14px}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:13px;font-weight:600}
.b-ok{background:#052e16;color:#4ade80;border:1px solid #14532d}
.b-no{background:#3f1d1d;color:#fca5a5;border:1px solid #7f1d1d}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px}
.out{border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;gap:12px;align-items:center;justify-content:space-between}
.out .nm{font-weight:700}
.out .nt{color:var(--dim);font-size:12px;margin-top:2px}
.out .wn{color:var(--warn);font-size:12px;margin-top:2px}
button{cursor:pointer;border:0;border-radius:9px;font-weight:700;font-size:14px;padding:10px 18px;color:#06130c}
button:disabled{opacity:.45;cursor:wait}
.tgl{min-width:86px;background:var(--off);color:var(--txt)}
.tgl.on{background:var(--on);color:#052e16}
.mode{background:var(--off);color:var(--txt)}
.mode.on{background:var(--acc);color:#06130c}
.alloff{background:var(--bad);color:#fff;margin-left:auto}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:#0f1a15;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13px}
.chip b{color:var(--acc);font-size:15px}
.chip.bad b{color:var(--bad)}
pre{background:#0a100d;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:12px;
    max-height:220px;overflow:auto;color:#9fb8ab;white-space:pre-wrap}
#toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:#7f1d1d;color:#fff;
       padding:10px 18px;border-radius:10px;font-weight:600;display:none;z-index:9}
.hint{color:var(--dim);font-size:12px;margin-top:8px}
</style></head><body><div class="wrap">
<h1>TERRARIUM <span>TESTER</span></h1>
<div class="sub">manual bench control over USB - every switch, by hand</div>

<div class="card"><div class="row" style="margin:0">
  <span id="conn" class="badge b-no">connecting...</span>
  <span style="color:var(--dim);font-size:13px">mode:</span>
  <button class="mode" id="m-auto"  onclick="setMode('auto')">AUTO</button>
  <button class="mode" id="m-manual" onclick="setMode('manual')">MANUAL</button>
  <button class="alloff" onclick="allOff()">ALL OFF</button>
</div>
<div class="hint">Pressing any output switches the board to MANUAL by itself. AUTO gives control back to the rules.
Close TerrariumConsole.exe and the Arduino Serial Monitor first - only one program can hold the COM port.</div></div>

<div class="card"><div class="grid" id="outs"></div></div>

<div class="card"><div class="chips" id="chips">waiting for the board...</div></div>

<div class="card"><div style="color:var(--dim);font-size:13px;margin-bottom:6px">board log</div>
<pre id="log">-</pre></div>
</div>
<div id="toast"></div>
<script>
const OUTS = [
 {k:'water', nm:'Mist 1 - watering', nt:'D16 (silk RX2) -> GND2, load on OUT2', wn:'never run a mist disc dry'},
 {k:'hum',   nm:'Mist 2 - humidity', nt:'D25 -> GND1, load on OUT1 (wire when 2nd kit arrives)'},
 {k:'fan',   nm:'Fan',               nt:'D17 (silk TX2) -> GND3, load on OUT3', wn:'flyback diode across the fan first, stripe to +'},
 {k:'light', nm:'Grow light',        nt:'D19, moves to 12 V Board B later'},
 {k:'buzz',  nm:'Buzzer',            nt:'D26 direct, 2.7 kHz tone - loud!'}
];
let busy=false, st=null;
const $=id=>document.getElementById(id);

function toast(t){const e=$('toast');e.textContent=t;e.style.display='block';
  clearTimeout(e._t);e._t=setTimeout(()=>e.style.display='none',3200);}

function build(){
  $('outs').innerHTML = OUTS.map(o=>`
   <div class="out"><div>
     <div class="nm">${o.nm}</div>
     <div class="nt">${o.nt}</div>
     ${o.wn?`<div class="wn">&#9888; ${o.wn}</div>`:''}
   </div>
   <button class="tgl" id="b-${o.k}" onclick="toggle('${o.k}')">--</button></div>`).join('');
}

async function api(u){
  try{const r=await fetch(u);return await r.json();}catch(e){return null;}
}

async function refresh(){
  const s=await api('/api/state'); if(!s)return;
  const c=$('conn');
  c.textContent = s.connected ? ('USB - '+s.port) : s.msg;
  c.className = 'badge ' + (s.connected?'b-ok':'b-no');
  $('log').textContent = (s.log&&s.log.length)? s.log.join('\\n') : '-';
  const lg=$('log'); lg.scrollTop=lg.scrollHeight;
  st = s.status;
  if(!st){ if(!s.connected) $('chips').innerHTML='waiting for the board...'; return; }
  $('m-auto').className   = 'mode'+(st.mode==='auto'  ?' on':'');
  $('m-manual').className = 'mode'+(st.mode==='manual'?' on':'');
  for(const o of OUTS){
    const b=$('b-'+o.k), on=st.out && st.out[o.k];
    b.textContent = on?'ON':'OFF';
    b.className = 'tgl'+(on?' on':'');
  }
  const v=(x,u='')=> (x===null||x===undefined)?'--':x+u;
  $('chips').innerHTML = [
    ['temp', v(st.temp,' &deg;C')], ['RH', v(st.hum,' %')], ['lux', v(st.lux)],
    ['soil 1', v(st.soil1,' %')+' <span style="color:#597467">raw '+v(st.raw1)+'</span>'],
    ['soil 2', v(st.soil2,' %')+' <span style="color:#597467">raw '+v(st.raw2)+'</span>'],
    ['leak', (st.leakWet?'WET':'dry')+' <span style="color:#597467">'+v(st.leak)+'</span>', st.leakWet],
    ['tank', st.tankOk?'ok':'EMPTY', !st.tankOk],
    ['watered today', v(st.waterToday,' s')],
    ['net', st.ap? 'hotspot' : (st.ssid||'--')], ['ip', v(st.ip)], ['up', v(st.up)]
  ].map(([k,val,bad])=>`<div class="chip${bad?' bad':''}">${k}: <b>${val}</b></div>`).join('');
}

async function toggle(k){
  if(busy||!st)return; busy=true;
  const cur = st.out && st.out[k] ? 1:0;
  const r = await api('/api/out?name='+k+'&v='+(1-cur));
  if(r && r.err) toast(r.err);
  busy=false; refresh();
}
async function setMode(m){ if(busy)return; busy=true; await api('/api/mode?m='+m); busy=false; refresh(); }
async function allOff(){ if(busy)return; busy=true; const r=await api('/api/alloff'); if(r&&r.err)toast(r.err); busy=false; refresh(); }

build(); refresh(); setInterval(refresh, 1000);
</script></body></html>"""


# --------------------------------------------------------------------------- #
#  http server                                                                #
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}

        if u.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif u.path == "/api/state":
            LINK.fresh_status()
            self._json({
                "connected": LINK.connected,
                "port": LINK.port,
                "msg": LINK.msg,
                "status": LINK.last_status if LINK.connected else None,
                "log": list(LINK.log)[-40:],
            })

        elif u.path == "/api/out":
            name, v = q.get("name"), q.get("v")
            if name not in OUT_NAMES or v not in ("0", "1"):
                return self._json({"err": "bad request"}, 400)
            r = LINK.command(f"CMD OUT {name} {v}")
            self._json(r if r is not None else {"err": "no reply from the board"})

        elif u.path == "/api/mode":
            m = q.get("m")
            if m not in ("auto", "manual"):
                return self._json({"err": "bad mode"}, 400)
            r = LINK.command(f"CMD MODE {m}")
            self._json(r if r is not None else {"err": "no reply from the board"})

        elif u.path == "/api/alloff":
            last = None
            for n in OUT_NAMES:
                last = LINK.command(f"CMD OUT {n} 0") or last
            self._json(last if last is not None else {"err": "no reply from the board"})

        else:
            self._json({"err": "not found"}, 404)


class Server(ThreadingHTTPServer):
    # Windows quietly lets two processes share a port with SO_REUSEADDR on -
    # keep it off so a second launch fails fast and we just open the browser.
    allow_reuse_address = False


def main():
    try:
        srv = Server(("127.0.0.1", HTTP_PORT), Handler)
    except OSError:
        webbrowser.open(f"http://127.0.0.1:{HTTP_PORT}")   # already running
        return
    threading.Thread(target=auto_connect_loop, daemon=True).start()
    webbrowser.open(f"http://127.0.0.1:{HTTP_PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        LINK.close()


if __name__ == "__main__":
    main()
