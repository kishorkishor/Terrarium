"""Extra report figures: firmware/software architecture and the control-loop / watering state machine."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
INK = "#1e293b"; BLUE = "#2563eb"; TEAL = "#0e7490"; GREEN = "#16a34a"; AMBER = "#d97706"
SLATE = "#64748b"; PURPLE = "#7c3aed"; RED = "#dc2626"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
SHADOW = [pe.SimplePatchShadow(offset=(1.4, -1.4), alpha=0.16, rho=0.98), pe.Normal()]


def box(ax, x, y, w, h, lines, fc, ec, fs=9.2, tc="white", lw=1.5, shadow=True):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.3", fc=fc, ec=ec, lw=lw)
    if shadow:
        p.set_path_effects(SHADOW)
    ax.add_patch(p)
    n = len(lines)
    for i, t in enumerate(lines):
        if not t:
            continue
        ax.text(x + w / 2, y + h - (i + 0.5) * (h / n), t, ha="center", va="center",
                fontsize=fs if i == 0 else fs - 1.1, fontweight="bold" if i == 0 else "normal", color=tc)


def arrow(ax, x1, y1, x2, y2, color=SLATE, style="-|>", lw=1.8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, lw=lw, color=color,
                                 mutation_scale=14, shrinkA=1, shrinkB=1))


def label(ax, x, y, t, color=SLATE, ha="center", va="bottom", fs=7.6, style="normal"):
    ax.text(x, y, t, ha=ha, va=va, fontsize=fs, color=color, style=style)


# ------------------------------------------------------------ software architecture
fig, ax = plt.subplots(figsize=(13.0, 6.4), dpi=220)
ax.set_xlim(-10, 136); ax.set_ylim(4, 66); ax.axis("off")

cont = FancyBboxPatch((2, 12), 90, 52, boxstyle="round,pad=0.6,rounding_size=2",
                      fc="#f8fafc", ec="#94a3b8", lw=1.4, ls="--")
ax.add_patch(cont)
label(ax, 4, 62.6, "ESP32 firmware (Arduino C++)", color="#334155", ha="left", fs=10.5)
ax.texts[-1].set_fontweight("bold")

# top row: data path
box(ax, 4, 44, 22, 13, ["Sensor drivers", "BME280 + BH1750 (I2C)", "soil / leak (12-bit ADC)", "float switch (GPIO)"], "#dbeafe", BLUE, tc=INK)
box(ax, 35, 44, 22, 13, ["Rules engine", "watering state machine", "RH hysteresis, light window", "fan thresholds, fail-safes"], "#12395f", "#0a2540")
box(ax, 66, 44, 22, 13, ["Output layer", "interlocks: tank, leak,", "manual time-out", "applyOutputs(), active-low"], "#dcfce7", GREEN, tc="#14532d")
arrow(ax, 26.6, 50.5, 34.4, 50.5, color=BLUE); label(ax, 30.5, 51.4, "2 s tick", BLUE)
arrow(ax, 57.6, 50.5, 65.4, 50.5, color=GREEN); label(ax, 61.5, 51.4, "flags", GREEN)

# hardware stubs at the container edges
arrow(ax, -8, 50.5, 3.4, 50.5, color=BLUE, lw=1.6); label(ax, -8, 49.3, "I2C / ADC / GPIO", BLUE, ha="left", va="top")
arrow(ax, 88.6, 50.5, 99, 50.5, color=GREEN, lw=1.6); label(ax, 89.5, 49.3, "to MOSFET boards", GREEN, ha="left", va="top")

# services row
box(ax, 4, 20, 22, 14, ["NVS storage", "14 thresholds / timings", "Wi-Fi credentials", "survive power cycles"], "#fef3c7", AMBER, tc="#78350f")
box(ax, 35, 20, 22, 14, ["Shared command layer", "setModeCmd()", "applyOutCmd()", "setCfgKV() / finishCfg()"], "#ede9fe", PURPLE, tc="#4c1d95")
box(ax, 66, 20, 22, 14, ["Interfaces", "web server: dashboard, /api/*", "USB serial: CMD ..., #R {json}", "Wi-Fi STA + hotspot fallback"], "#ede9fe", PURPLE, tc="#4c1d95")
arrow(ax, 46, 34.6, 46, 43.4, color=PURPLE, style="<|-|>"); label(ax, 47.2, 38.4, "mode, outputs, config", PURPLE, ha="left")
arrow(ax, 34.4, 27, 26.6, 27, color=AMBER, style="<|-|>"); label(ax, 30.5, 27.9, "cfg", AMBER)
arrow(ax, 65.4, 27, 57.6, 27, color=PURPLE, style="<|-|>"); label(ax, 61.5, 26.0, "same calls", PURPLE, va="top", fs=7.0)

# clients (outside the container, right)
box(ax, 104, 46, 30, 12, ["Phone / PC browser", "Wi-Fi station or", "board hotspot (AP)"], "#f5f3ff", PURPLE, tc="#4c1d95")
box(ax, 104, 27, 30, 12, ["TerrariumConsole.exe", "setup, flash, Wi-Fi provisioning,", "full control over USB or LAN"], "#f5f3ff", PURPLE, tc="#4c1d95")
box(ax, 104, 8, 30, 12, ["TerrariumTester.exe", "manual bench control", "of every channel over USB"], "#f5f3ff", PURPLE, tc="#4c1d95")
arrow(ax, 103.4, 48, 88.6, 32, color=PURPLE, style="<|-|>", lw=1.5); label(ax, 99.5, 42.2, "HTTP", PURPLE, ha="center")
arrow(ax, 103.4, 31, 88.6, 27, color=PURPLE, style="<|-|>", lw=1.5); label(ax, 95.5, 31.8, "HTTP + serial", PURPLE)
arrow(ax, 103.4, 15, 88.6, 22, color=PURPLE, style="<|-|>", lw=1.5); label(ax, 95.5, 13.2, "serial, 115200 baud", PURPLE, va="top")

fig.savefig(os.path.join(OUT, "software-arch.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ------------------------------------------------------ control loop + state machine
fig, ax = plt.subplots(figsize=(12.4, 6.4), dpi=220)
ax.set_xlim(0, 126); ax.set_ylim(0, 64); ax.axis("off")

# left: main loop flow
label(ax, 24, 62.5, "Main loop, every 2 s", color="#334155", fs=10.5)
ax.texts[-1].set_fontweight("bold")
box(ax, 8, 52, 32, 7, ["Read sensors", "BME280, BH1750, soil x2, leak, float"], "#dbeafe", BLUE, tc=INK)
arrow(ax, 24, 51.4, 24, 46.6)
d = Polygon([(24, 46), (36, 40), (24, 34), (12, 40)], closed=True, fc="#fef3c7", ec=AMBER, lw=1.5)
d.set_path_effects(SHADOW); ax.add_patch(d)
ax.text(24, 40, "manual\nmode?", ha="center", va="center", fontsize=9, color="#78350f", fontweight="bold")
arrow(ax, 24, 33.4, 24, 28.6); label(ax, 22.5, 30.6, "no", ha="right")
box(ax, 8, 20, 32, 8.5, ["Run automatic rules", "watering FSM, RH hysteresis,", "light window + lux, fan thresholds"], "#12395f", "#0a2540")
arrow(ax, 36.6, 40, 45.4, 40); label(ax, 41, 40.8, "yes")
box(ax, 46, 35.5, 24, 9, ["Outputs follow UI", "manual mist auto-off", "after 10 min"], "#f5f3ff", PURPLE, tc="#4c1d95")
arrow(ax, 24, 19.4, 24, 14.6)
arrow(ax, 58, 34.9, 58, 14.6)
box(ax, 8, 6, 62, 8.5, ["Interlocks + applyOutputs()", "tank empty: both mist channels off  |  leak: buzzer  |  write GPIO (active-low)"],
    "#dcfce7", GREEN, tc="#14532d")

# right: watering state machine
label(ax, 100, 62.5, "Watering state machine", color="#334155", fs=10.5)
ax.texts[-1].set_fontweight("bold")
box(ax, 90, 50, 24, 8, ["IDLE", "judge soil every tick"], "#e0f2fe", TEAL, tc=INK)
box(ax, 90, 32, 24, 8, ["RUN", "mist maker 1 on, 90 s burst"], "#0e7490", "#155e75")
box(ax, 90, 14, 24, 8, ["SOAK", "wait 20 min, mist off"], "#e0f2fe", TEAL, tc=INK)
arrow(ax, 102, 49.4, 102, 40.6, color=TEAL)
ax.text(103.5, 45, "soil < 35 %  AND  tank OK\nAND  daily cap not reached", fontsize=7.6, color=INK, va="center")
arrow(ax, 102, 31.4, 102, 22.6, color=TEAL)
ax.text(103.5, 27, "burst done  OR  tank empty\n(daily total += burst time)", fontsize=7.6, color=INK, va="center")
ax.add_patch(FancyArrowPatch((90, 18), (90, 54), connectionstyle="arc3,rad=0.5", arrowstyle="-|>",
                             lw=1.8, color=TEAL, mutation_scale=14))
ax.text(78.5, 36, "soak timer\nelapsed", fontsize=7.6, color=INK, ha="center", va="center")
box(ax, 78, 2, 46, 8, ["Hard cap: 30 min of watering mist per day", "reset at midnight (NTP) or every 24 h of uptime"],
    "#fef3c7", AMBER, fs=8, tc="#78350f", shadow=False)

fig.savefig(os.path.join(OUT, "control-flow.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("figures written to", OUT)
