"""
Live wire monitor for firmware/lab: polls DIAG about once a second and serves
a page at http://localhost:8765 showing the I2C lines and sensors as big
coloured boxes plus a timeline of every change. Log: data/wiremon.log

  python tools/lab/wiremon.py [--port COM3] [--http 8765]
Stop with Ctrl+C. The board's serial port is held while this runs.
"""
import argparse, json, re, threading, time, datetime as dt, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import serial

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.normpath(os.path.join(HERE, '..', '..', 'data', 'wiremon.log'))

state = {'ok': False, 'sda': '?', 'scl': '?', 'found': '', 'in': '?', 'out': '?', 'when': '', 'rh_in': '', 'rh_out': ''}
history = []
lock = threading.Lock()


def classify(hi):
    return 'free (nothing pulling it)' if hi > 17 else 'GROUNDED (shorted / wet / dead chip)' if hi < 3 else 'unstable'


def poll(port):
    ser = None
    last = None
    while True:
        try:
            if ser is None:
                ser = serial.Serial(); ser.port, ser.baudrate, ser.timeout = port, 115200, 0.2
                ser.dtr = False; ser.rts = False; ser.open(); time.sleep(0.5)
            ser.reset_input_buffer(); ser.write(b'DIAG\n'); time.sleep(1.2)
            txt = ser.read(16384).decode('ascii', 'replace')
            m2 = re.search(r'SDA with own pull-up high (\d+)/20, SCL with own pull-up high (\d+)/20', txt)
            m1 = re.search(r'found:(.*)', txt)
            d = [l for l in txt.splitlines() if l.startswith('D,')]
            if not m2:
                continue
            sda, scl = classify(int(m2.group(1))), classify(int(m2.group(2)))
            found = (m1.group(1).strip() if m1 else '')
            rin = rout = ''
            if d:
                p = d[-1].split(',')
                rin, rout = p[3], p[6]
            cur = dict(ok=True, sda=sda, scl=scl, found=found or 'none',
                       **{'in': 'answering' if '0x76' in found else 'silent', 'out': 'answering' if '0x77' in found else 'silent'},
                       when=dt.datetime.now().strftime('%H:%M:%S'), rh_in=rin, rh_out=rout)
            key = (sda, scl, found)
            with lock:
                state.update(cur)
                if key != last:
                    line = f"{cur['when']}  SCL {scl:38} SDA {sda:38} sensors: {cur['found']}"
                    history.insert(0, line); del history[200:]
                    with open(LOG, 'a') as f: f.write(line + '\n')
                    last = key
        except serial.SerialException as e:
            with lock:
                state.update(ok=False, when=dt.datetime.now().strftime('%H:%M:%S'))
            ser = None; time.sleep(2)


PAGE = """<!doctype html><html><head><meta charset=utf-8><title>Wire monitor</title>
<style>body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:16px}
h1{font-size:18px;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.box{border-radius:12px;padding:18px;font-size:22px;font-weight:600}.box small{display:block;font-size:13px;font-weight:400;opacity:.8;margin-top:6px}
.good{background:#1e6b3a}.bad{background:#a12b2b}.meh{background:#8a6d1f}.off{background:#444}
pre{background:#1b1b1b;padding:12px;border-radius:8px;font-size:13px;max-height:50vh;overflow:auto}
#t{opacity:.6;font-size:13px;margin:10px 0}</style></head><body>
<h1>Terrarium wire monitor (live, about 1 update per second)</h1>
<div class=grid>
<div class=box id=scl>SCL (D22)<small></small></div>
<div class=box id=sda>SDA (D21)<small></small></div>
<div class=box id=in>Inside sensor 0x76<small></small></div>
<div class=box id=out>Outside sensor 0x77<small></small></div>
</div><div id=t></div>
<b>Timeline (newest first): every change of state</b><pre id=h></pre>
<script>
function cls(v){return v.startsWith('free')?'good':v.startsWith('GROUNDED')?'bad':v==='answering'?'good':v==='silent'?'bad':'meh'}
async function tick(){try{const s=await (await fetch('/state')).json();
if(!s.ok){for(const k of['scl','sda','in','out']){const e=document.getElementById(k);e.className='box off';e.querySelector('small').textContent='board not connected'}}
else{const set=(k,v,extra)=>{const e=document.getElementById(k);e.className='box '+(k==='scl'||k==='sda'?(v.startsWith('free')?'good':v.startsWith('GROUNDED')?'bad':'meh'):cls(v));e.querySelector('small').textContent=v+(extra||'')};
set('scl',s.scl);set('sda',s.sda);set('in',s.in,s.rh_in&&s.rh_in!=='nan'?'  RH '+s.rh_in+' %':'');set('out',s.out,s.rh_out&&s.rh_out!=='nan'?'  RH '+s.rh_out+' %':'');}
document.getElementById('t').textContent='last update '+s.when+'   (for I2C to work, both lines must be "free" while idle and the sensors then answer)';
document.getElementById('h').textContent=s.history.join('\\n');}catch(e){}}
setInterval(tick,1000);tick();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == '/state':
            with lock:
                body = json.dumps(dict(state, history=history)).encode()
            ct = 'application/json'
        else:
            body = PAGE.encode(); ct = 'text/html; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type', ct); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--port', default='COM3'); ap.add_argument('--http', type=int, default=8765)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    threading.Thread(target=poll, args=(a.port,), daemon=True).start()
    print(f'wire monitor: http://localhost:{a.http}   log {LOG}')
    ThreadingHTTPServer(('127.0.0.1', a.http), H).serve_forever()


if __name__ == '__main__':
    main()
