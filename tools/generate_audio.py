#!/usr/bin/env python3
"""Generate placeholder sound effects for Absolute Ballers.

Pure-python procedural SFX (no deps) written to assets/placeholder/audio/.
Final sound design replaces these WAVs 1:1 — filenames are the contract
(scripts/core/audio_manager.gd loads by basename).

Usage: python3 tools/generate_audio.py
"""

import math
import os
import random
import struct
import wave

SR = 22050
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "placeholder", "audio")

rnd = random.Random(42)


def write_wav(name, samples):
    with wave.open(os.path.join(OUT, name + ".wav"), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000))
            for s in samples))


def t_axis(dur):
    return [i / SR for i in range(int(dur * SR))]


def env_decay(t, dur, curve=6.0):
    return math.exp(-curve * t / dur)


def lowpass(samples, alpha):
    out, y = [], 0.0
    for s in samples:
        y += alpha * (s - y)
        out.append(y)
    return out


def sine_hit(freqs, dur, curve=7.0, gain=1.0):
    """Decaying sum of sines — thuds and metallic clanks."""
    out = []
    for t in t_axis(dur):
        s = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        out.append(s * env_decay(t, dur, curve) * gain)
    return out


def noise_burst(dur, curve=6.0, attack=0.0, gain=1.0, lp=1.0):
    out = []
    for t in t_axis(dur):
        a = min(1.0, t / attack) if attack > 0 else 1.0
        out.append(rnd.uniform(-1, 1) * a * env_decay(t, dur, curve) * gain)
    return lowpass(out, lp) if lp < 1.0 else out


def mix(*tracks):
    n = max(len(tr) for tr in tracks)
    return [sum(tr[i] for tr in tracks if i < len(tr)) for i in range(n)]


def bounce():
    # pitch-dropping sine thump
    out = []
    dur = 0.14
    for t in t_axis(dur):
        f = 170.0 - 80.0 * (t / dur)
        out.append(math.sin(2 * math.pi * f * t) * env_decay(t, dur, 5.0))
    return mix(out, noise_burst(0.03, curve=9.0, gain=0.25, lp=0.4))


def swish():
    return noise_burst(0.28, curve=5.0, attack=0.02, gain=0.8, lp=0.35)


def rim_clank():
    return mix(
        sine_hit([830.0, 1247.0, 1968.0], 0.32, curve=9.0, gain=0.7),
        noise_burst(0.05, curve=10.0, gain=0.3))


def slam():
    return mix(
        sine_hit([70.0, 110.0], 0.35, curve=5.0, gain=0.9),
        sine_hit([620.0, 990.0], 0.25, curve=10.0, gain=0.4),
        noise_burst(0.1, curve=7.0, gain=0.5, lp=0.5))


def block():
    return mix(
        sine_hit([120.0, 190.0], 0.18, curve=8.0, gain=0.9),
        noise_burst(0.08, curve=8.0, gain=0.45, lp=0.6))


def steal():
    # quick rising swipe
    out = []
    dur = 0.12
    for t in t_axis(dur):
        out.append(rnd.uniform(-1, 1) * (t / dur) * env_decay(t, dur, 2.0))
    return lowpass(out, 0.5)


def whoosh():
    out = []
    dur = 0.3
    for t in t_axis(dur):
        a = math.sin(math.pi * t / dur)  # rise then fall
        out.append(rnd.uniform(-1, 1) * a * 0.6)
    return lowpass(out, 0.18)


def pass_zip():
    return noise_burst(0.07, curve=7.0, gain=0.5, lp=0.45)


def buzzer():
    out = []
    dur = 0.9
    for t in t_axis(dur):
        s = (1.0 if math.sin(2 * math.pi * 233.0 * t) > 0 else -1.0) * 0.35
        s += (1.0 if math.sin(2 * math.pi * 240.0 * t) > 0 else -1.0) * 0.35
        edge = min(1.0, t / 0.01) * min(1.0, (dur - t) / 0.05)
        out.append(s * edge)
    return lowpass(out, 0.6)


def fire_ignite():
    out = []
    dur = 0.55
    for t in t_axis(dur):
        f = 280.0 + 700.0 * (t / dur)
        s = math.sin(2 * math.pi * f * t) * 0.45
        s += rnd.uniform(-1, 1) * 0.4
        out.append(s * math.sin(math.pi * min(1.0, t / dur)))
    return lowpass(out, 0.4)


def knockdown():
    return mix(
        sine_hit([75.0], 0.3, curve=5.0, gain=1.0),
        noise_burst(0.12, curve=6.0, gain=0.4, lp=0.3))


def click():
    return sine_hit([880.0], 0.06, curve=10.0, gain=0.5)


def cheer():
    # crowd roar approximation: shaped noise with slow wobble
    out = []
    dur = 1.4
    for t in t_axis(dur):
        a = min(1.0, t / 0.15) * math.exp(-2.2 * max(0.0, t - 0.3) / dur)
        wob = 0.75 + 0.25 * math.sin(2 * math.pi * 7.0 * t + math.sin(t * 3.0))
        out.append(rnd.uniform(-1, 1) * a * wob * 0.9)
    return lowpass(out, 0.25)


def crowd_loop():
    # seamless low murmur bed (AudioManager sets loop points)
    dur = 2.5
    n = int(dur * SR)
    raw = [rnd.uniform(-1, 1) for _ in range(n)]
    # crossfade tail into head for a click-free loop
    fade = int(0.25 * SR)
    for i in range(fade):
        k = i / fade
        raw[i] = raw[i] * k + raw[n - fade + i] * (1.0 - k)
    out = lowpass(raw, 0.12)
    return [s * 0.5 for s in out[:n - fade]]


SOUNDS = {
    "bounce": bounce, "swish": swish, "rim_clank": rim_clank, "slam": slam,
    "block": block, "steal": steal, "whoosh": whoosh, "pass": pass_zip,
    "buzzer": buzzer, "fire_ignite": fire_ignite, "knockdown": knockdown,
    "click": click, "cheer": cheer, "crowd_loop": crowd_loop,
}
SOUNDS["dribble"] = lambda: [s * 0.5 for s in bounce()]


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in SOUNDS.items():
        write_wav(name, fn())
    print("wrote %d sounds to %s" % (len(SOUNDS), OUT))


if __name__ == "__main__":
    main()
