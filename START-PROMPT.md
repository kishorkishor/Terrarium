# Starting a hardware project with Claude Code — the prompt that avoids the hassle

Copy the block below into a **new Claude Code session, opened in the project's
folder**, edit the `<>` parts, and attach the photos listed underneath.

Everything in it exists because *not* saying it cost real hours on the terrarium
build.

---

```
PROJECT
I'm building <one line: what it is and what it must do>.
This is for <coursework / a product / myself>, deadline <date or none>.
My experience with electronics: <first build / some / experienced>.

MY MACHINE
Windows 11 <or whatever>. Already installed: <Arduino IDE / Python / nothing>.
The board is <plugged in / not here yet> on <COM port if known>.

HARDWARE I ACTUALLY HAVE
<paste the exact list — model numbers, quantities. Photos attached.>
Still to buy: <list, or "nothing yet — tell me what to get">

WHAT I WANT FROM YOU

1. Set yourself up to work the hardware directly. Install whatever CLI tools you
   need (arduino-cli / esptool / platformio / pyserial) into a folder inside this
   project or my user profile — not system-wide. Reuse anything already on the
   machine instead of re-downloading. You have my permission to run terminal
   commands and install these without asking each time.

2. From then on: YOU flash the board and YOU read it back — serial port and/or
   its network API. I do all the physical wiring. Never assume a change worked
   because it should have; read the device and tell me what it actually says.

3. Work the loop one step at a time. Give me ONE physical action, I do it and say
   "check", you read the board and tell me the result. Do not give me five wiring
   steps at once — if step 2 was wrong, steps 3-5 waste an hour.

RULES THAT MATTER (learned the hard way)

- Read pin names off my PHOTOS, from the silkscreen. Never tell me "the pin next
  to X" or count positions — labelled pins are often not adjacent.
- Before you design any wiring, ask for photos of BOTH SIDES of every module.
  The terminal labels and the chip markings are frequently on opposite faces.
- Trust the chip markings over the product listing. Sellers mislabel parts.
  Check what's actually printed on the silicon and on the PCB.
- Never diagnose from an unloaded or floating measurement. Put a real load
  (resistor, LED, the actual device) in the circuit before believing a reading.
- When something doesn't work, isolate before theorising: strip it to the
  smallest possible circuit — one module, four wires, no breadboard rails.
- If firmware crashes, decode the backtrace with the real toolchain
  (addr2line etc.). Don't guess at the cause.
- Tell me plainly when something is a GUESS vs MEASURED. If a step's result
  can't be verified, say so instead of moving on.
- If a mistake was yours, say so and move on — I'd rather know than re-test my
  wiring for an hour.

DELIVERABLES, as we go

- Firmware, in this folder, with all my tunable values in one config file.
- Small throwaway diagnostic sketches whenever they'd answer a question faster
  than guessing (bus scanners, pin-state readers, live web status pages).
- Notes as we go: what's wired where, what the measured values were, what
  decisions we made and why.
- At the end: a single-file tool (packaged .exe is ideal) that installs drivers,
  finds the board, flashes it, reads it, and self-diagnoses with plain-English
  fixes — so I can set this up on another laptop without you.

START HERE
Look at the photos, confirm what hardware you can identify, tell me anything that
looks wrong or missing, then give me the FIRST single step.
```

---

## Photos to attach with that first message

The ones that actually earned their keep on the terrarium build:

| Photo | Why |
|---|---|
| **Each module, front AND back** | Terminal labels are on one side, chip markings on the other. Half the time lost was because only one side had been seen |
| **The microcontroller, both sides** | To read the real pin silkscreen instead of assuming a standard pinout |
| **Any power supply's label** | Voltage, current, and the centre-positive symbol |
| **A wide shot of the whole breadboard** | To trace where wires actually land, not where they were meant to |
| **The workspace** | Shows what tools exist — soldering iron, meter, spare parts |

Close, in focus, and with the printed text readable. A blurry silkscreen is a
guess, and guesses are what cost time.

## Set up before you type it

1. Open Claude Code **in the project folder** — that's what gives it file access.
2. Let it run terminal commands without confirming each one (it will ask; say yes
   for the session). Every install and every flash goes through that.
3. Have Python installed if you want the packaged .exe at the end
   (`pip install pyserial pyinstaller`) — or let it install them.
4. **Close the Arduino IDE's Serial Monitor** whenever it should flash. Only one
   program can own a COM port, and this single issue cost the terrarium build
   over an hour of confusion.

## The three things that broke the flow last time

- **Unsoldered header pins.** They look connected and conduct nothing. Every time
  the breadboard was touched, a different sensor dropped off. Solder the modules
  early rather than late.
- **A Microsoft Store install of the Arduino IDE.** Windows sandboxes Store apps,
  so its compiler cannot be driven from a script — `arduino-cli` had to be
  installed instead. Prefer the normal .exe installer.
- **Believing a product listing.** The "F5305S 4-channel MOSFET" board was
  actually opto-isolated with 60N03 transistors and needed 5 V on its inputs,
  which a 3.3 V pin can't provide. Two hours went into that one, and a photo of
  the board's front would have found it in five minutes.
