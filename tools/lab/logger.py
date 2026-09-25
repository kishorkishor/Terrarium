"""
Laptop logger for firmware/lab. Records every data line to CSV and can run the
paper's test protocols unattended.

  python tools/lab/logger.py                      just log (whatever mode the board is in)
  python tools/lab/logger.py --protocol baseline  current rules (75-90 %, 5 min cap), log until stopped
  python tools/lab/logger.py --protocol step      step tests: mist A x3, mist B x3 (about 3 h)
  python tools/lab/logger.py --protocol decay     mist off, just watch the box dry out

While it runs:
  - add a line to data/lab-cmd.txt to send a command, e.g.  MARK lid open
  - create the file data/STOP to end cleanly (mist off, mode restored)
Output: data/lab-<protocol>-<date>-<time>.csv plus a .events.txt next to it.
"""
import argparse, csv, os, sys, time, datetime as dt, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import serial

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', '..', 'data'))
CMD_FILE = os.path.join(DATA, 'lab-cmd.txt')
STOP_FILE = os.path.join(DATA, 'STOP')
FIELDS = ['ms', 't_in', 'rh_in', 'p_in', 't_out', 'rh_out', 'p_out',
          'mistA', 'mistB', 'mode', 'in_ok', 'out_ok', 'tank_ok']


LIVE = {'phase': 'starting', 'row': {}, 'points': [], 'events': [], 'file': ''}
LIVE_LOCK = threading.Lock()

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Lab live</title>
<style>body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:14px}
h1{font-size:17px;margin:0 0 10px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:12px}
.box{border-radius:10px;padding:12px;background:#222}.box b{display:block;font-size:26px;margin-top:4px}.box small{opacity:.7}
.on{background:#1e6b3a}.bad{background:#a12b2b}canvas{width:100%;height:260px;background:#1b1b1b;border-radius:8px}
pre{background:#1b1b1b;padding:10px;border-radius:8px;font-size:12px;max-height:30vh;overflow:auto}#t{opacity:.6;font-size:12px;margin:8px 0}</style></head><body>
<h1>Terrarium lab: live experiment</h1>
<div class=grid>
<div class=box id=ph><small>phase</small><b>-</b></div>
<div class=box id=ri><small>inside RH %</small><b>-</b></div>
<div class=box id=ro><small>outside RH %</small><b>-</b></div>
<div class=box id=ti><small>inside temp C</small><b>-</b></div>
<div class=box id=to><small>outside temp C</small><b>-</b></div>
<div class=box id=ma><small>mist A</small><b>-</b></div>
<div class=box id=mb><small>mist B</small><b>-</b></div>
<div class=box id=sn><small>sensors</small><b>-</b></div>
</div>
<canvas id=c width=1200 height=260></canvas><div id=t></div>
<b>Events (newest first)</b><pre id=e></pre>
<script>
function draw(pts){const c=document.getElementById('c'),g=c.getContext('2d'),W=c.width,H=c.height;g.clearRect(0,0,W,H);if(pts.length<2)return;
const t0=pts[0][0],t1=pts[pts.length-1][0],sx=t=>(t-t0)/Math.max(1,(t1-t0))*(W-50)+40,sy=v=>H-20-(v-50)/50*(H-40);
g.fillStyle='rgba(60,120,220,.25)';for(const p of pts){if(p[3])g.fillRect(sx(p[0]),20,2,H-40)}
g.strokeStyle='#333';for(let v=50;v<=100;v+=10){g.beginPath();g.moveTo(40,sy(v));g.lineTo(W-10,sy(v));g.stroke();g.fillStyle='#888';g.font='11px sans-serif';g.fillText(v,8,sy(v)+4)}
const line=(i,col)=>{g.strokeStyle=col;g.lineWidth=1.5;g.beginPath();let f=true;for(const p of pts){if(p[i]==null)continue;const x=sx(p[0]),y=sy(p[i]);f?g.moveTo(x,y):g.lineTo(x,y);f=false}g.stroke()};
line(1,'#4caf50');line(2,'#ff9800');g.fillStyle='#4caf50';g.fillText('inside',W-120,14);g.fillStyle='#ff9800';g.fillText('outside',W-60,14)}
async function tick(){try{const s=await (await fetch('/state')).json();const r=s.row||{};
const set=(id,v,cls)=>{const e=document.getElementById(id);e.querySelector('b').textContent=v;if(cls!==undefined)e.className='box '+cls};
set('ph',s.phase);set('ri',r.rh_in||'-');set('ro',r.rh_out||'-');set('ti',r.t_in||'-');set('to',r.t_out||'-');
set('ma',r.mistA==='1'?'ON':'off',r.mistA==='1'?'on':'');set('mb',r.mistB==='1'?'ON':'off',r.mistB==='1'?'on':'');
const ok=(r.in_ok==='1')+(r.out_ok==='1');set('sn',ok+' of 2 ok',ok===2?'':'bad');
document.getElementById('t').textContent='last hour, blue = mist on, y-axis 50 to 100 %RH. file: '+s.file;
document.getElementById('e').textContent=s.events.join('\n');draw(s.points)}catch(e){}}
setInterval(tick,1000);tick();</script></body></html>"""


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == '/state':
            with LIVE_LOCK:
                body = json.dumps(LIVE).encode()
            ct = 'application/json'
        else:
            body = PAGE.encode(); ct = 'text/html; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type', ct); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


def serve(port):
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', port), _H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f'live page: http://localhost:{port}')
    except OSError as e:
        print('live page not started:', e)


class Board:
    def __init__(self, port, csv_path):
        self.port = port
        self.ser = None
        self.last = {}                 # latest data row
        self.f = open(csv_path, 'w', newline='')
        self.w = csv.writer(self.f)
        self.w.writerow(['pc_time', 'phase'] + FIELDS + ['event'])
        with LIVE_LOCK: LIVE['file'] = os.path.basename(csv_path)
        self.ev = open(csv_path.replace('.csv', '.events.txt'), 'a')
        self.phase = 'idle'
        self.buf = b''
        self.last_data = time.time()
        self.connect()

    def connect(self):
        while True:
            try:
                s = serial.Serial()
                s.port, s.baudrate, s.timeout = self.port, 115200, 0.2
                s.dtr = False; s.rts = False          # do not reset the board
                s.open()
                self.ser = s
                self.note('logger connected to ' + self.port)
                return
            except serial.SerialException as e:
                print('waiting for', self.port, '-', e)
                time.sleep(5)

    def now(self):
        return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def note(self, text):
        line = f'{self.now()}  [{self.phase}]  {text}'
        print(line)
        self.ev.write(line + '\n'); self.ev.flush()
        with LIVE_LOCK:
            LIVE['events'].insert(0, line); del LIVE['events'][150:]; LIVE['phase'] = self.phase

    def send(self, cmd):
        self.note('>> ' + cmd)
        try:
            self.ser.write((cmd + '\n').encode())
        except serial.SerialException:
            self.ser = None; self.connect(); self.ser.write((cmd + '\n').encode())

    def reset_board(self):
        """Pulse the ESP32 reset line (RTS). The firmware restores its mode from flash."""
        try:
            self.ser.rts = True; time.sleep(0.1); self.ser.rts = False
        except serial.SerialException:
            pass
        self.last_data = time.time()

    def pump(self, seconds=0.0):
        """Read and record everything for `seconds` (at least one pass)."""
        end = time.time() + seconds
        while True:
            if time.time() - getattr(self, 'last_data', time.time()) > 20:
                self.note('no data for 20 s: board frozen? resetting it'); self.reset_board()
            try:
                self.buf += self.ser.read(4096)
            except serial.SerialException:
                self.note('serial lost, reconnecting'); self.connect()
            while b'\n' in self.buf:
                raw, self.buf = self.buf.split(b'\n', 1)
                self.line(raw.decode('ascii', 'replace').strip())
            self.commands()
            if time.time() >= end:
                return
            time.sleep(0.05)

    def line(self, s):
        if s.startswith('D,'):
            parts = s.split(',')[1:]
            if len(parts) != len(FIELDS):
                return
            self.last = dict(zip(FIELDS, parts)); self.last_data = time.time()
            self.w.writerow([self.now(), self.phase] + parts + ['']); self.f.flush()
            f = lambda k: (float(self.last[k]) if self.last[k] != 'nan' else None)
            with LIVE_LOCK:
                LIVE['row'] = self.last; LIVE['phase'] = self.phase
                LIVE['points'].append([time.time(), f('rh_in'), f('rh_out'), self.last['mistA'] == '1' or self.last['mistB'] == '1'])
                del LIVE['points'][:-3600]
        elif s.startswith('E,') or s.startswith('S,'):
            text = s.split(',', 2)[-1] if s.startswith('E,') else s
            self.w.writerow([self.now(), self.phase] + [''] * len(FIELDS) + [text]); self.f.flush()
            self.note('<< ' + text)
        elif s:
            print('   ' + s)

    def commands(self):
        if os.path.exists(CMD_FILE):
            try:
                with open(CMD_FILE) as f:
                    cmds = [c.strip() for c in f if c.strip()]
                os.remove(CMD_FILE)
            except OSError:
                return
            for c in cmds:
                self.send(c)

    def rh(self):
        try:
            return float(self.last.get('rh_in', 'nan'))
        except ValueError:
            return float('nan')

    def in_ok(self):
        return self.last.get('in_ok') == '1'


def stopped():
    return os.path.exists(STOP_FILE)


def wait(b, seconds):
    end = time.time() + seconds
    while time.time() < end and not stopped():
        b.pump(1)


def rise(b, mist, cap_s=300, min_s=90, flat=0.3, window=60):
    """Mist on until RH stops rising (less than `flat` % over `window` s) or cap."""
    b.send(f'MIST {mist} 1')
    t0, hist, lost = time.time(), [], 0
    while not stopped():
        b.pump(1)
        el = time.time() - t0
        if not b.in_ok():
            lost += 1
            if lost >= 20:
                b.note('inside sensor lost for 20 s during rise - mist off'); break
            continue
        lost = 0
        hist.append((el, b.rh()))
        old = [h for t, h in hist if el - t >= window]
        if el >= min_s and old and b.rh() - old[-1] < flat:
            b.note(f'plateau at {b.rh():.2f} % after {el:.0f} s'); break
        if el >= cap_s:
            b.note(f'cap reached at {b.rh():.2f} %'); break
    b.send(f'MIST {mist} 0')


def protocol_step(b, mists='AB', repeats=3, base_s=300, decay_s=1200):
    b.send('SET man=600'); b.send('MODE MANUAL'); b.pump(2)
    for mist in mists:
        for k in range(1, repeats + 1):
            if stopped(): return
            b.phase = f'{mist}{k}-baseline'; b.send(f'MARK {b.phase}'); wait(b, base_s)
            if stopped(): return
            b.phase = f'{mist}{k}-rise'; b.send(f'MARK {b.phase}'); rise(b, mist)
            if stopped(): return
            b.phase = f'{mist}{k}-decay'; b.send(f'MARK {b.phase}'); wait(b, decay_s)


def protocol_baseline(b):
    b.send('SET lo=75 hi=90 max=300 cool=180 use=A'); b.send('MODE RULES')
    b.phase = 'baseline-rules'
    while not stopped():
        b.pump(5)


def protocol_decay(b):
    b.send('MODE OFF'); b.phase = 'decay'
    while not stopped():
        b.pump(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='COM3')
    ap.add_argument('--protocol', default='log', choices=['log', 'baseline', 'step', 'decay'])
    ap.add_argument('--mists', default='AB', help='which mist makers the step test uses: A, B or AB')
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--http', type=int, default=8765, help='live page port (0 = off)')
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    if stopped():
        os.remove(STOP_FILE)
    path = os.path.join(DATA, f'lab-{a.protocol}-{dt.datetime.now():%Y-%m-%d-%H%M}.csv')
    if a.http: serve(a.http)
    b = Board(a.port, path)
    b.send('HEADER'); b.send('STATUS'); b.pump(3)
    b.note(f'START protocol {a.protocol} -> {path}')
    try:
        if a.protocol == 'step':
            protocol_step(b, mists=a.mists.upper(), repeats=a.repeats)
        elif a.protocol == 'baseline':
            protocol_baseline(b)
        elif a.protocol == 'decay':
            protocol_decay(b)
        else:
            b.phase = 'log'
            while not stopped():
                b.pump(5)
    except KeyboardInterrupt:
        b.note('stopped by keyboard')
    finally:
        b.phase = 'end'
        b.send('MIST A 0'); b.send('MIST B 0')
        if a.protocol == 'step':
            b.send('MODE OFF')
        b.send('STATUS'); b.pump(2)
        b.note('END')
        if stopped():
            os.remove(STOP_FILE)


if __name__ == '__main__':
    main()
