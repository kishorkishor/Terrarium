#!/usr/bin/env python3
"""
TERRARIUM CONSOLE - one portable file that sets up any Windows laptop to
talk to the terrarium, flashes it, watches it, and diagnoses itself.

    TerrariumConsole.exe            open the console in your browser
    TerrariumConsole.exe --auto     also fix everything it can without asking
    TerrariumConsole.exe --no-browser

What it does, in order:
  1. starts a local web page at http://localhost:8765
  2. finds the ESP32 on USB (CP210x) and on the Wi-Fi (mDNS, last IP, subnet scan)
  3. checks driver / port / toolchain / board / firmware / sensors, explains
     every failure in plain words and offers the fix
  4. installs the CP210x driver (UAC prompt) and the arduino-cli toolchain
     (downloaded on first use) when asked
  5. flashes the terrarium firmware or the bench tools to the board
  6. streams the board's serial log live, and embeds its dashboard

Everything it installs lives in %LOCALAPPDATA%\\TerrariumConsole so it never
touches the rest of the machine.
"""
import ctypes, json, os, re, shutil, socket, subprocess, sys, threading, time
import traceback, urllib.request, webbrowser, zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    import serial
    import serial.tools.list_ports as list_ports
except ImportError:  # the exe always has it; a bare script might not
    serial = None
    list_ports = None

# ----------------------------------------------------------------------------
#  paths
# ----------------------------------------------------------------------------
PORT        = 8765
FROZEN      = getattr(sys, "frozen", False)
ASSETS      = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "assets")
STATE_DIR   = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TerrariumConsole")
WORK        = os.path.join(STATE_DIR, "firmware")
CLI_DIR     = os.path.join(STATE_DIR, "arduino-cli")
CLI_EXE     = os.path.join(CLI_DIR, "arduino-cli.exe")
CLI_CFG     = os.path.join(CLI_DIR, "arduino-cli.yaml")
CLI_DATA    = os.path.join(STATE_DIR, "arduino-data")
STATE_FILE  = os.path.join(STATE_DIR, "state.json")
LOG_FILE    = os.path.join(STATE_DIR, "console.log")

CLI_URL     = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
ESP32_INDEX = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"
FQBN        = "esp32:esp32:esp32"
LIBS        = ["Adafruit BME280 Library", "BH1750"]
SKETCHES    = {"terrarium": "terrarium", "bench-web": "bench-web", "i2c-scan": "i2c-scan"}
NO_WINDOW   = 0x08000000 if os.name == "nt" else 0

os.makedirs(STATE_DIR, exist_ok=True)

# ----------------------------------------------------------------------------
#  logging - a ring buffer the page polls, plus a file
# ----------------------------------------------------------------------------
class Ring:
    def __init__(self, n=2000):
        self.n, self.items, self.seq, self.lock = n, [], 0, threading.Lock()
    def add(self, line):
        with self.lock:
            self.seq += 1
            self.items.append((self.seq, line))
            if len(self.items) > self.n:
                self.items = self.items[-self.n:]
    def since(self, seq):
        with self.lock:
            return [(s, l) for s, l in self.items if s > seq]

TASKLOG = Ring()
SERIAL  = Ring(800)

def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    print(line, flush=True)
    TASKLOG.add(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(**kw):
    st = load_state(); st.update(kw)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)

# ----------------------------------------------------------------------------
#  helpers
# ----------------------------------------------------------------------------
def run(cmd, timeout=600, stream=False):
    """Run a command hidden; optionally stream its lines into the task log."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace",
                         creationflags=NO_WINDOW)
    out = []
    for line in p.stdout:
        line = line.rstrip("\r\n")
        if not line or line.startswith("\x1b"):
            continue
        out.append(line)
        if stream:
            log("  " + line[-160:])
    p.wait(timeout=timeout)
    return p.returncode, "\n".join(out)

def powershell(script, timeout=120):
    return run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", script], timeout=timeout)

def http_get(url, timeout=3.0):
    req = urllib.request.Request(url, headers={"User-Agent": "TerrariumConsole"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()

def ensure_work_firmware():
    """Copy bundled sketches into a writable folder (config edits persist)."""
    os.makedirs(WORK, exist_ok=True)
    for name in SKETCHES.values():
        dst = os.path.join(WORK, name)
        if not os.path.isdir(dst):
            shutil.copytree(os.path.join(ASSETS, "firmware", name), dst)
    return WORK

def wifi_from_config():
    cfg = os.path.join(ensure_work_firmware(), "terrarium", "config.h")
    s = open(cfg, encoding="utf-8").read()
    ssid = re.search(r'WIFI_SSID\s+"([^"]*)"', s)
    pw   = re.search(r'WIFI_PASS\s+"([^"]*)"', s)
    return (ssid.group(1) if ssid else ""), (pw.group(1) if pw else "")

def set_wifi(ssid, pw):
    cfg = os.path.join(ensure_work_firmware(), "terrarium", "config.h")
    s = open(cfg, encoding="utf-8").read()
    s = re.sub(r'(WIFI_SSID\s+)"[^"]*"', lambda m: m.group(1) + '"%s"' % ssid, s)
    s = re.sub(r'(WIFI_PASS\s+)"[^"]*"', lambda m: m.group(1) + '"%s"' % pw, s)
    open(cfg, "w", encoding="utf-8").write(s)

def write_bench_secret():
    ssid, pw = wifi_from_config()
    bw = os.path.join(ensure_work_firmware(), "bench-web", "wifi_secret.h")
    open(bw, "w", encoding="utf-8").write(
        '#pragma once\n#define BW_SSID "%s"\n#define BW_PASS "%s"\n' % (ssid, pw))

# ----------------------------------------------------------------------------
#  USB / serial
# ----------------------------------------------------------------------------
_USB_CACHE = {"t": 0, "val": (None, "not scanned yet")}

def find_usb_port(max_age=2.0):
    """Return (port, description) of the CP210x board, or (None, reason).
    Enumerating COM ports on Windows can take a second or more, and the page
    asks every 1.5 s, so results are cached briefly."""
    if list_ports is None:
        return None, "pyserial missing"
    now = time.time()
    if now - _USB_CACHE["t"] < max_age:
        return _USB_CACHE["val"]
    val = (None, "no CP210x device on any COM port")
    for p in list_ports.comports():
        desc = p.description or ""
        if (p.vid or 0) == 0x10C4 or "CP210" in desc or "Silicon Labs" in desc:
            val = (p.device, desc); break
    _USB_CACHE.update(t=now, val=val)
    return val

def port_holder(port):
    """Name the process holding a COM port (usually the Arduino Serial Monitor)."""
    code, out = powershell(
        "Get-Process | Where-Object { $_.MainWindowTitle -match '%s' } | "
        "Select-Object -First 1 | ForEach-Object { $_.ProcessName + ' (window: ' + $_.MainWindowTitle + ')' }" % port)
    return out.strip() or "another program"

class SerialReader(threading.Thread):
    """Keeps the board's serial output flowing into SERIAL while nobody else
    needs the port. paused=True releases the port (for flashing)."""
    def __init__(self):
        super().__init__(daemon=True)
        self.paused = False
        self.port = None
        self.ok = False
        self.error = ""
    def run(self):
        while True:
            if self.paused or serial is None:
                self.ok = False; time.sleep(0.5); continue
            port, _ = find_usb_port()
            if not port:
                self.ok = False; self.port = None; time.sleep(2); continue
            self.port = port
            try:
                with serial.Serial(port, 115200, timeout=1) as s:
                    self.ok = True; self.error = ""
                    buf = b""
                    while not self.paused:
                        chunk = s.read(256)
                        if not chunk:
                            continue
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            txt = line.decode("utf-8", "replace").rstrip("\r")
                            if txt.strip():
                                SERIAL.add(txt)
            except Exception as e:
                self.ok = False
                self.error = str(e)
                time.sleep(2)

READER = SerialReader()

def reset_board():
    """Pulse the auto-reset line through the USB bridge."""
    port, _ = find_usb_port()
    if not port or serial is None:
        return False, "board not on USB"
    READER.paused = True
    time.sleep(0.6)
    try:
        with serial.Serial(port, 115200) as s:
            s.dtr = False; s.rts = True; time.sleep(0.15); s.rts = False
        return True, "reset pulse sent"
    except Exception as e:
        return False, str(e)
    finally:
        READER.paused = False

# ----------------------------------------------------------------------------
#  the board on the network
# ----------------------------------------------------------------------------
BOARD = {"ip": None, "status": None, "kind": None, "checked": 0}

def probe(ip, timeout=0.5):
    try:
        body = http_get("http://%s/api/status" % ip, timeout)
        d = json.loads(body)
        if "tankOk" in d:
            return "terrarium", d
        if "sda" in d and "scl" in d:
            return "bench-web", d
    except Exception:
        pass
    return None, None

def find_board(full_scan=True):
    cands = []
    st = load_state()
    if st.get("board_ip"):
        cands.append(st["board_ip"])
    try:
        cands.append(socket.gethostbyname("terrarium.local"))
    except Exception:
        pass
    cands.append("192.168.4.1")          # the board's own hotspot
    for ip in cands:
        kind, d = probe(ip, 2.0)
        if kind:
            return ip, kind, d
    if not full_scan:
        return None, None, None
    me = local_ip()
    if not me:
        return None, None, None
    base = me.rsplit(".", 1)[0]
    log("scanning %s.1-254 for the board ..." % base)
    ips = ["%s.%d" % (base, i) for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=64) as ex:
        results = list(ex.map(lambda ip: probe(ip, 0.6), ips))
    for ip, (kind, d) in zip(ips, results):
        if kind:
            return ip, kind, d
    return None, None, None

def refresh_board(full_scan=False):
    ip, kind, d = find_board(full_scan)
    BOARD.update(ip=ip, kind=kind, status=d, checked=time.time())
    if ip:
        save_state(board_ip=ip)
    return ip

# ----------------------------------------------------------------------------
#  toolchain
# ----------------------------------------------------------------------------
def cli(args, timeout=900, stream=False):
    return run([CLI_EXE, "--config-file", CLI_CFG] + args, timeout=timeout, stream=stream)

def existing_ide_data():
    """Arduino IDE already on this PC? Reuse its ESP32 core instead of
    downloading 300 MB again."""
    for d in (os.path.join(os.path.expanduser("~"), "Documents", "ArduinoData"),
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Arduino15")):
        if os.path.isdir(os.path.join(d, "packages", "esp32")):
            return d
    return None

def toolchain_state():
    if not os.path.isfile(CLI_EXE) or not os.path.isfile(CLI_CFG):
        return "missing", "arduino-cli not installed yet"
    code, out = cli(["core", "list"], timeout=90)
    if "esp32:esp32" not in out:
        return "partial", "arduino-cli present but the ESP32 core is missing"
    code, out = cli(["lib", "list"], timeout=90)
    missing = [l for l in LIBS if l.split()[0] not in out]
    if missing:
        return "partial", "library missing: " + ", ".join(missing)
    return "ok", "arduino-cli + ESP32 core + libraries present"

def install_toolchain():
    os.makedirs(CLI_DIR, exist_ok=True)
    if not os.path.isfile(CLI_EXE):
        z = os.path.join(CLI_DIR, "arduino-cli.zip")
        log("downloading arduino-cli (about 18 MB) ...")
        last = [-1]
        def hook(n, bs, total):
            if total > 0:
                pct = min(100, n * bs * 100 // total)
                if pct // 10 != last[0]:
                    last[0] = pct // 10; log("  %d%%" % pct)
        urllib.request.urlretrieve(CLI_URL, z, hook)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(CLI_DIR)
        os.remove(z)
        log("arduino-cli unpacked")
    data = existing_ide_data() or CLI_DATA
    if data != CLI_DATA:
        log("found an Arduino IDE install - reusing its ESP32 core at " + data)
    user = os.path.join(os.path.expanduser("~"), "Documents", "Arduino")
    run([CLI_EXE, "config", "init", "--dest-file", CLI_CFG, "--overwrite"], timeout=60)
    cli(["config", "set", "directories.data", data], timeout=30)
    cli(["config", "set", "directories.user", user], timeout=30)
    cli(["config", "add", "board_manager.additional_urls", ESP32_INDEX], timeout=30)
    state, _ = toolchain_state()
    if state != "ok":
        log("installing the ESP32 core (a few hundred MB - this is the slow part) ...")
        cli(["core", "update-index"], timeout=600, stream=True)
        cli(["core", "install", "esp32:esp32"], timeout=3600, stream=True)
        for l in LIBS:
            log("installing library: " + l)
            cli(["lib", "install", l], timeout=600, stream=True)
    state, msg = toolchain_state()
    log("toolchain: " + msg)
    return state == "ok"

def flash(sketch):
    name = SKETCHES.get(sketch)
    if not name:
        log("unknown sketch " + sketch); return False
    state, msg = toolchain_state()
    if state != "ok":
        log("toolchain not ready: " + msg + " - run Install toolchain first"); return False
    port, why = find_usb_port()
    if not port:
        log("board not found on USB: " + why); return False
    src = os.path.join(ensure_work_firmware(), name)
    if name == "bench-web":
        write_bench_secret()
    READER.paused = True
    time.sleep(0.8)
    try:
        log("compiling %s ..." % name)
        code, out = cli(["compile", "--fqbn", FQBN, src], timeout=900)
        for l in [l for l in out.splitlines() if "Sketch uses" in l or "error" in l.lower()][-6:]:
            log("  " + l[-160:])
        if code != 0:
            log("compile FAILED"); return False
        log("uploading to %s ..." % port)
        code, out = cli(["upload", "-p", port, "--fqbn", FQBN, src], timeout=600)
        for l in out.splitlines():
            if any(k in l for k in ("Hash of data verified", "Hard resetting", "rror", "busy", "denied")):
                log("  " + l[-160:])
        if code != 0:
            if "busy" in out or "denied" in out:
                log("the COM port is held by " + port_holder(port) + " - close it and retry")
            log("upload FAILED"); return False
        log("flashed %s OK" % name)
        return True
    finally:
        READER.paused = False

# ----------------------------------------------------------------------------
#  driver
# ----------------------------------------------------------------------------
def driver_state():
    port, _ = find_usb_port()
    if port:
        return "ok", "CP210x driver working - board on " + port
    code, out = run(["pnputil", "/enum-drivers"], timeout=60)
    if "silabser.inf" in out:
        return "ok", "driver installed (plug the board in to see a COM port)"
    code, out = powershell("Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_10C4' } | "
                           "Select-Object -ExpandProperty Status")
    if "Error" in out or "Unknown" in out:
        return "fail", "board is plugged in but Windows has no driver for it"
    return "warn", "no CP210x driver found on this PC"

def install_driver():
    inf = os.path.join(ASSETS, "cp210x", "silabser.inf")
    if not os.path.isfile(inf):
        log("driver files missing from this build"); return False
    log("installing CP210x driver - approve the Windows UAC prompt ...")
    code, out = powershell(
        "$p = Start-Process pnputil -ArgumentList '/add-driver','%s','/install' "
        "-Verb RunAs -Wait -PassThru; $p.ExitCode" % inf.replace("'", "''"), timeout=300)
    log("pnputil exit: " + out.strip())
    run(["pnputil", "/scan-devices"], timeout=60)
    time.sleep(2)
    state, msg = driver_state()
    log("driver: " + msg)
    return state == "ok"

# ----------------------------------------------------------------------------
#  diagnostics - every check: id, status, message, fix
# ----------------------------------------------------------------------------
def diagnose(full_scan=False):
    checks = []
    def add(cid, status, msg, fix=None, detail=""):
        checks.append({"id": cid, "status": status, "msg": msg, "fix": fix, "detail": detail})

    try:
        http_get("https://downloads.arduino.cc/", 5)
        add("internet", "ok", "internet reachable")
    except Exception:
        add("internet", "warn", "no internet - installs will fail, everything else works",
            detail="The board, the dashboard and flashing all work offline. Only first-time installs need the internet.")

    st, msg = driver_state()
    add("driver", st, msg, "install_driver" if st != "ok" else None,
        detail="The CP210x chip on the ESP32 needs a driver before Windows gives it a COM port.")

    port, why = find_usb_port()
    if port:
        add("usb", "ok", "board on " + port)
    else:
        add("usb", "fail", "board not on USB (" + why + ")",
            detail="Plug the ESP32 in with a DATA cable - many phone cables only carry power. Its red LED should light.")

    if port:
        err = READER.error.lower()
        if READER.ok:
            add("port", "ok", "serial log streaming from " + port)
        elif "denied" in err or "busy" in err:
            add("port", "fail", port + " is held by " + port_holder(port),
                detail="Only one program can own a COM port. Close the Arduino Serial Monitor window (titled '%s') and this will reconnect by itself." % port)
        else:
            add("port", "warn", "connecting to " + port + " ...")
    else:
        add("port", "warn", "waiting for USB")

    st, msg = toolchain_state()
    add("toolchain", "ok" if st == "ok" else "warn", msg,
        "install_toolchain" if st != "ok" else None,
        detail="arduino-cli + the ESP32 core compile and flash firmware. Installed once into %LOCALAPPDATA%\\TerrariumConsole. Not needed just to use the dashboard.")

    ip = refresh_board(full_scan)
    me = local_ip()
    if ip:
        add("wifi", "ok", "board answering at http://%s (%s firmware)" % (ip, BOARD["kind"]))
    else:
        ssid, _ = wifi_from_config()
        add("wifi", "fail", "board not found on this network", "find_board",
            detail="This PC is on %s. The firmware is set to join Wi-Fi '%s'. If this laptop is on a different network, either join that Wi-Fi, or set the new Wi-Fi below and reflash. With no router the board makes its own hotspot 'Terrarium' / terrarium123 at 192.168.4.1." % (me or "no network", ssid))

    d = BOARD["status"]
    if ip and BOARD["kind"] == "terrarium" and d:
        add("firmware", "ok", "terrarium firmware, %s, up %s" % (d.get("mode"), d.get("up")))
        probs = []
        if d.get("temp") is None: probs.append("BME280 not answering (temp/humidity) - check VCC->3V3, SDA->D21, SCL->D22, CSB->3V3, SDO->GND, then power-cycle the board")
        if d.get("lux") is None:  probs.append("BH1750 not answering (light) - check SDA->D21, SCL->D22, ADDR->GND, power-cycle")
        r1, r2 = d.get("raw1"), d.get("raw2")
        if r1 is not None and r1 < 300: probs.append("soil probe 1 reads ~0 - unplugged or no 3V3")
        if r2 is not None and r2 < 300: probs.append("soil probe 2 reads ~0 - unplugged or no 3V3")
        if d.get("leakWet"): probs.append("LEAK SENSOR WET")
        if d.get("tankOk") is False: probs.append("reservoir reads EMPTY - mist channels locked out")
        if probs:
            add("sensors", "warn", "; ".join(probs))
        else:
            add("sensors", "ok", "temp %s C, RH %s%%, lux %s, soil %s%%, leak %s" %
                (d.get("temp"), d.get("hum"), d.get("lux"), d.get("soil"), d.get("leak")))
    elif ip and BOARD["kind"] == "bench-web":
        add("firmware", "warn", "bench-web test firmware is on the board", "flash_terrarium",
            detail="Flash the real terrarium firmware when bench testing is done.")
        add("sensors", "warn", "bench mode - see the bench page at http://" + ip)
    else:
        add("firmware", "warn", "no board to ask")
        add("sensors", "warn", "no board to ask")
    return checks

# ----------------------------------------------------------------------------
#  task runner - one job at a time, in the background
# ----------------------------------------------------------------------------
TASK = {"running": None, "last": None, "ok": None}
CHECKS = []

def run_task(name, arg=None):
    if TASK["running"]:
        return False
    def go():
        global CHECKS
        TASK["running"] = name; TASK["ok"] = None
        ok = False
        try:
            log("==== %s %s" % (name, arg or ""))
            if name == "diagnose":
                CHECKS = diagnose(full_scan=(arg == "full"))
                bad = [c for c in CHECKS if c["status"] == "fail"]
                log("diagnose: %d checks, %d failing" % (len(CHECKS), len(bad)))
                ok = not bad
            elif name == "install_driver":
                ok = install_driver()
            elif name == "install_toolchain":
                ok = install_toolchain()
            elif name == "flash":
                ok = flash(arg or "terrarium")
            elif name == "flash_terrarium":
                ok = flash("terrarium")
            elif name == "find_board":
                ok = bool(refresh_board(True)); log("board: " + str(BOARD["ip"]))
            elif name == "reset":
                ok, msg = reset_board(); log(msg)
            elif name == "fix_all":
                ok = True
                st, _ = driver_state()
                if st != "ok": ok = install_driver() and ok
                st, _ = toolchain_state()
                if st != "ok": ok = install_toolchain() and ok
                refresh_board(True)
            else:
                log("unknown task " + name)
            if name != "diagnose":
                CHECKS = diagnose()
        except Exception:
            log("task crashed:\n" + traceback.format_exc()); ok = False
        TASK["ok"] = ok; TASK["last"] = name; TASK["running"] = None
        log("==== %s %s" % (name, "done" if ok else "FAILED"))
    threading.Thread(target=go, daemon=True).start()
    return True

# ----------------------------------------------------------------------------
#  local web server
# ----------------------------------------------------------------------------
PAGE = open(os.path.join(ASSETS, "console.html"), encoding="utf-8").read()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):      # keep the console window quiet
        pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            b = PAGE.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif u.path == "/api/state":
            ssid, _ = wifi_from_config()
            port, _ = find_usb_port()
            self.send_json({
                "checks": CHECKS, "task": TASK, "board": {"ip": BOARD["ip"], "kind": BOARD["kind"]},
                "status": BOARD["status"], "usb": port, "serial_ok": READER.ok,
                "wifi_ssid": ssid, "admin": is_admin(), "state_dir": STATE_DIR,
                "frozen": FROZEN, "local_ip": local_ip()})
        elif u.path == "/api/log":
            self.send_json({"lines": TASKLOG.since(int(q.get("since", ["0"])[0]))})
        elif u.path == "/api/serial":
            self.send_json({"lines": SERIAL.since(int(q.get("since", ["0"])[0]))})
        elif u.path == "/api/board":
            if BOARD["ip"]:
                kind, d = probe(BOARD["ip"], 3.0)
                if d: BOARD["status"] = d
                self.send_json(d or {"err": "no reply"})
            else:
                self.send_json({"err": "no board"})
        else:
            self.send_json({"err": "not found"}, 404)
    def do_POST(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = parse_qs(self.rfile.read(n).decode()) if n else {}
        if u.path == "/api/run":
            name = q.get("task", [""])[0]; arg = q.get("arg", [None])[0]
            self.send_json({"started": run_task(name, arg), "running": TASK["running"]})
        elif u.path == "/api/wifi":
            ssid = body.get("ssid", [""])[0]; pw = body.get("pass", [""])[0]
            set_wifi(ssid, pw)
            log("Wi-Fi set to '%s' - flash the terrarium firmware to apply it" % ssid)
            self.send_json({"ok": True})
        elif u.path == "/api/out":
            if not BOARD["ip"]:
                self.send_json({"err": "no board"}); return
            try:
                name = q.get("name", [""])[0]; state = q.get("state", ["0"])[0]
                r = http_get("http://%s/api/out?name=%s&state=%s" % (BOARD["ip"], name, state), 5)
                self.send_json(json.loads(r))
            except Exception as e:
                self.send_json({"err": str(e)})
        else:
            self.send_json({"err": "not found"}, 404)

class Server(ThreadingHTTPServer):
    # HTTPServer turns SO_REUSEADDR on. On Windows that lets a SECOND process
    # bind a port that is already being listened on, so a double-clicked exe
    # would silently start twice. Exclusive binding makes the clash visible.
    allow_reuse_address = False

def bind_server():
    """Take port 8765, or the next free one. If another console already owns
    8765 (the exe was double-clicked twice), just reopen its page and leave."""
    global PORT
    for port in range(PORT, PORT + 10):
        try:
            srv = Server(("127.0.0.1", port), H)
            PORT = port
            return srv
        except OSError:
            try:
                d = json.loads(http_get("http://127.0.0.1:%d/api/state" % port, 6))
                if "checks" in d and "state_dir" in d:
                    print("  a Terrarium Console is already running on port %d - opening it" % port, flush=True)
                    if "--no-browser" not in sys.argv:
                        webbrowser.open("http://localhost:%d" % port)
                    sys.exit(0)
            except Exception:
                pass            # something else owns that port; try the next
    print("  no free port between 8765 and 8774", flush=True)
    sys.exit(1)

def main():
    auto = "--auto" in sys.argv
    ensure_work_firmware()
    srv = bind_server()
    print("\n  TERRARIUM CONSOLE\n  state: %s\n  page:  http://localhost:%d\n" % (STATE_DIR, PORT), flush=True)
    READER.start()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if "--no-browser" not in sys.argv:
        webbrowser.open("http://localhost:%d" % PORT)
    run_task("fix_all" if auto else "diagnose")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
