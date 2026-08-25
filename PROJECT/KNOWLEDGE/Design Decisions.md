---
tags: [terrarium, decisions]
updated: 2026-08-06
---

# Design Decisions

Why the build is the way it is. Each entry: choice → reason.

## Architecture
- **ESP32 DevKit V1 (WROOM-32, CP2102)** over ESP8266 (only ONE analog pin — we need 3),
  over S3/C3/C6 (far fewer beginner tutorials), over WROVER (uses GPIO16/17 internally,
  breaks the pin map). Most-tutorialised board on the internet → "randomnerdtutorials ESP32 + part".
- **Mist-as-watering**: 2× cheap 5V ultrasonic kits — one waters (timed burst 90s + 20min soak),
  one humidifies. Replaced pump + 24V fogger (those remain the upgrade path).
- **Phone control = board-hosted web app**, not Blynk/cloud: no accounts, works on hotspot,
  IS the offline-operation demo. Add-to-Home-Screen makes it feel native.
- **Two F5305S boards, split by voltage**: A @5V (mist), B @12V (light+fans). One board can't
  mix voltages — common DC input. Alternative: D4184 per channel.

## Components
- **BME280 over DHT22/DHT11**: DHT22 is ±5% RH and saturates permanently above ~90% RH —
  terrarium air lives there. BME280 does 0–100% on I2C for the same money.
- **Capacitive soil only, never resistive**: resistive forks (SNM047-style, ৳99) electrolyse and
  corrode in weeks of wet soil. Cheap price = wrong type. Check: solid paddle, no exposed prongs.
- **Fixed-5V buck (LM2596S 2222)** over adjustable XL4015: adjustable ships at random voltage —
  the #1 way to kill an ESP32. (If adjustable anyway: set 5.00V unloaded FIRST.)
- **12V 5A adapter** over the tempting ৳120/130 one — that's 12V 1–2A; our rail peaks ~2A →
  brown-outs mid-pump-cycle.
- **52mm PP float** ৳299 over industrial 2M cable float ৳1,065 — same reed contact.
- **৳49 leak sensor** (or gold-coated ৳80) over WaveShare ৳440 — wet/dry alarm needs no precision.
- **MOSFET modules over relays** (silent, PWM-dimmable light) and over **bare MOSFETs**
  (ZerOneTech's IRFZ44N/IRF520 are NOT logic-level — half-on at 3.3V gate → overheat).
- **F5305S verified** from its own listing: trigger 3–20V (3.3V OK), out 5–36V 5A/ch,
  level-follow PWM/digital despite the scary "pulse trigger" name.
- **Mist kits verified**: 2W @5V ≈0.4A each; built-in 4h auto-off is harmless because the MOSFET
  power-cycles them every burst. MUST be the auto-start type — reject touch-button modules.

## Electrical safety choices
- All analog on **ADC1** (Wi-Fi kills ADC2 silently) — see [[Pin Map]]
- 10k pulldowns on every MOSFET IN (boot-glitch = pump fires during reset)
- 1N5819 flyback on fans (motors kick back; mist discs & LED strip don't need them)
- Fuse 3A on 12V+ **before every branch** · one common ground · caps at ESP32 + both boards
- Sensor supply 3.3V, never 5V (soil at 5V outputs ~3V → at the ADC ceiling; leak at 5V = pin killer)

## Shop lessons (for the report's "process" section)
- Same product varies wildly by listing: ESP32 ৳493 vs ৳650 at the same shop
- Suspiciously cheap usually means wrong variant (soil ৳99 = resistive)
- Quotes drift architectures — the ৳1050 "ultra mist maker" + ৳240 pump quote was silently
  rebuilding the OLD design; know which machine you're buying

[[Parts & Cart]] · [[Safety & Care]]
