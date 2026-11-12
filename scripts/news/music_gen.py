#!/usr/bin/env python3
"""Background music composed for one video, no downloaded tracks (owner, 29/10: "Claude makes the music itself,
only where a passage needs it").

The designer writes a score in src/videos/<slug>/events.json:
  "score": [
    {"from": 0.0, "to": 14.5, "style": "curious_pluck", "key": "D", "mode": "major", "bpm": 100, "energy": 0.5},
    {"from": 31.0, "to": 52.0, "style": "tension", "key": "A", "mode": "minor", "bpm": 84, "energy": 0.7}
  ]
Times are on the same (prototype) timeline as the sound events; gaps between sections stay without music.
Styles: warm_pad, curious_pluck, playful, tension, documentary, lofi, space, epic.
energy 0–1 adds layers (bass, drums, sparkles). Sections fade in/out (0.8 s) so nothing starts abruptly.

Usage: music_gen.py <events.json> <timing.json> <out.wav>   (also imported by audio.py)
"""
import json, math, sys
import numpy as np
from scipy.signal import butter, lfilter, fftconvolve

SR = 48000
NOTE = {'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8,
        'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11}
# chord roots (semitones from the key) and qualities per bar, 4-bar loops
PROG = {'minor': [(0, 'm'), (8, 'M'), (3, 'M'), (10, 'M')],      # i – VI – III – VII
        'major': [(0, 'M'), (7, 'M'), (9, 'm'), (5, 'M')]}       # I – V – vi – IV
TRIAD = {'M': (0, 4, 7), 'm': (0, 3, 7)}
STYLES = ('warm_pad', 'curious_pluck', 'playful', 'tension', 'documentary', 'lofi', 'space', 'epic')


def hz(midi): return 440.0 * 2 ** ((midi - 69) / 12)


def lp(x, f, o=2):
    b, a = butter(o, min(0.99, f / (SR / 2)), 'low'); return lfilter(b, a, x)


def hp(x, f, o=2):
    b, a = butter(o, min(0.99, f / (SR / 2)), 'high'); return lfilter(b, a, x)


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n); e[:na] = np.linspace(0, 1, na, endpoint=False)
    nd = min(nd, n - na); e[na:na + nd] = np.linspace(1, s, nd, endpoint=False)
    nr = min(nr, n); e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def t_(dur): return np.arange(int(dur * SR)) / SR


# ---------------------------------------------------------------- instruments (mono float arrays)
def pad(freqs, dur, bright=1200):
    t = t_(dur); x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):                    # three slightly detuned saws per note
            ff = f * 2 ** (det / 12)
            ph = np.random.rand()
            x += 2 * ((t * ff + ph) % 1.0) - 1
    x = lp(x / (3 * len(freqs)), bright, 2)
    return x * adsr(len(t), a=min(1.2, dur / 3), d=0.3, s=0.85, r=min(1.2, dur / 3))


def pluck(f, dur=0.6, bright=0.5):                        # Karplus-Strong string
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = np.random.uniform(-1, 1, p); buf = lp(buf, 1500 + 6000 * bright, 1)
    out = np.zeros(n); idx = 0
    for i in range(n):
        out[i] = buf[idx]; nxt = (idx + 1) % p
        buf[idx] = 0.996 * 0.5 * (buf[idx] + buf[nxt]); idx = nxt
    return out * adsr(n, a=0.002, d=0.05, s=1.0, r=0.08)


def mallet(f, dur=0.5):                                   # marimba / kalimba
    t = t_(dur)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.35 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t * 22)
    return x * adsr(len(t), a=0.002, d=0.02, s=1.0, r=0.05)


def piano(f, dur=1.6, vel=0.8):                           # additive, slightly inharmonic, two decay rates
    t = t_(dur); x = np.zeros_like(t)
    for k in range(1, 9):
        fk = f * k * math.sqrt(1 + 0.0004 * k * k)
        if fk > 12000: break
        amp = vel / k ** 1.3
        x += amp * np.sin(2 * np.pi * fk * t + np.random.rand()) * (0.6 * np.exp(-t * (1.2 + 0.5 * k)) + 0.4 * np.exp(-t * (0.35 + 0.1 * k)))
    x *= 1 - np.exp(-t * 400)
    return x * adsr(len(t), a=0.001, d=0.01, s=1.0, r=0.25)


def rhodes(freqs, dur):                                   # soft electric piano chord with tremolo
    t = t_(dur); x = np.zeros_like(t)
    for f in freqs:
        x += (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)) * np.exp(-t * 0.9)
    x *= 0.85 + 0.15 * np.sin(2 * np.pi * 4.5 * t)
    return x / len(freqs) * adsr(len(t), a=0.005, d=0.05, s=1.0, r=0.3)


def bass(f, dur, drive=1.5):
    t = t_(dur)
    x = np.tanh(drive * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)))
    return lp(x, 900, 2) * adsr(len(t), a=0.005, d=0.08, s=0.8, r=0.06)


def kick(gain=1.0):
    t = t_(0.35); f = 45 + 110 * np.exp(-t * 30)
    return gain * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def snare(gain=0.6):
    t = t_(0.22); n = hp(np.random.uniform(-1, 1, len(t)), 1500)
    return gain * (0.7 * n * np.exp(-t * 18) + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))


def hat(gain=0.25, open_=False):
    t = t_(0.25 if open_ else 0.06); n = hp(np.random.uniform(-1, 1, len(t)), 7000)
    return gain * n * np.exp(-t * (12 if open_ else 70))


def tom(f=110, gain=0.8):
    t = t_(0.6); ff = f * (1 + 0.5 * np.exp(-t * 20))
    return gain * np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 5)


def reverb(x, secs=2.2, wet=0.25):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = np.random.uniform(-1, 1, n) * np.exp(-t * 6.9 / secs); ir = lp(ir, 5000, 1); ir[0] = 0
    y = fftconvolve(x, ir)[:len(x)]
    y *= np.sqrt(np.sum(x ** 2) + 1e-9) / (np.sqrt(np.sum(y ** 2)) + 1e-9)
    return (1 - wet) * x + wet * y


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf) or i + len(sig) <= 0: return
    j = min(len(buf), i + len(sig)); buf[max(0, i):j] += sig[max(0, -i):j - i]


# ---------------------------------------------------------------- one section
def section(sec, length):
    key = NOTE.get(str(sec.get('key', 'A')).upper().replace('♭', 'B'), 9)
    mode = 'major' if str(sec.get('mode', 'minor')).lower().startswith('maj') else 'minor'
    style = sec.get('style', 'warm_pad'); style = style if style in STYLES else 'warm_pad'
    bpm = float(sec.get('bpm', 90)); bpm = min(150, max(55, bpm)); beat = 60 / bpm; bar = 4 * beat
    energy = float(sec.get('energy', 0.5)); energy = min(1, max(0, energy))
    root = 48 + key if key <= 6 else 36 + key                                   # chord root octave around C3–B3
    out = np.zeros(int((length + 3) * SR)); prog = PROG[mode]
    nbars = int(math.ceil(length / bar)) + 1
    rng = np.random.RandomState(abs(hash((style, key, mode, round(bpm)))) % 2 ** 31)
    for b in range(nbars):
        t0 = b * bar; deg, q = prog[b % 4]; tri = [root + deg + s for s in TRIAD[q]]
        voicing = [tri[0], tri[1] + 12 if style in ('space', 'warm_pad') else tri[1], tri[2]]
        fr = [hz(m) for m in voicing]
        if style in ('warm_pad', 'space', 'epic', 'tension', 'documentary'):
            add(out, 0.55 * pad(fr, bar + 0.6, bright=700 if style == 'tension' else 1400 if style != 'space' else 2200), t0)
        if style == 'warm_pad' and energy > 0.4:
            for k in range(4): add(out, 0.18 * mallet(hz(voicing[k % 3] + 12)), t0 + k * beat)
        if style == 'curious_pluck':
            add(out, 0.25 * pad(fr, bar + 0.4, bright=900), t0)
            pat = [0, 1, 2, 1, 0, 2, 1, 2]
            for k in range(8): add(out, 0.35 * pluck(hz(voicing[pat[k]] + 12), 0.7, 0.4 + 0.3 * energy), t0 + k * beat / 2)
        if style == 'playful':
            for k in range(8):
                if k in (3, 7) and rng.rand() < 0.5: continue
                add(out, 0.4 * mallet(hz(voicing[(k * 2) % 3] + 12 + (12 if k == 6 else 0))), t0 + k * beat / 2)
            for k in (0, 2): add(out, 0.35 * bass(hz(tri[0] - 12), beat * 0.9), t0 + k * beat)
            if energy > 0.3:
                for k in (1, 3): add(out, 0.25 * snare(0.5), t0 + k * beat)
        if style == 'tension':
            for k in range(8): add(out, 0.3 * bass(hz(tri[0] - 12), beat / 2 * 0.8, drive=2.5), t0 + k * beat / 2)
            if energy > 0.5:
                add(out, 0.6 * kick(), t0); add(out, 0.45 * kick(), t0 + beat * 0.35)      # heartbeat on the bar
            if energy > 0.7 and b % 2 == 1: add(out, 0.12 * pluck(hz(tri[2] + 24), 1.2, 0.2), t0 + 2 * beat)
        if style == 'documentary':
            arp = [0, 1, 2, 1]
            for k in range(4): add(out, 0.32 * piano(hz(voicing[arp[k]] + 12), 2.2, 0.6 + 0.3 * energy), t0 + k * beat)
            add(out, 0.25 * piano(hz(tri[0] - 12), 3.0, 0.7), t0)
        if style == 'lofi':
            add(out, 0.5 * rhodes([hz(m) for m in voicing + [tri[0] + 10 if q == 'm' else tri[0] + 11]], bar), t0)
            sw = beat / 2 * 0.16
            for k in range(8):
                add(out, hat(0.18), t0 + k * beat / 2 + (sw if k % 2 else 0))
            for k in (0, 2.5): add(out, 0.8 * kick(), t0 + k * beat)
            for k in (1, 3): add(out, 0.45 * snare(0.6), t0 + k * beat)
            add(out, 0.35 * bass(hz(tri[0] - 12), bar * 0.45), t0)
        if style == 'space':
            for k in range(3):
                if rng.rand() < 0.6: add(out, 0.12 * mallet(hz(voicing[rng.randint(3)] + 24), 1.2), t0 + rng.rand() * bar)
        if style == 'epic':
            if energy > 0.4:
                for k in range(4): add(out, 0.5 * tom(hz(tri[0] - 24) * 2, 0.8 if k == 0 else 0.5), t0 + k * beat)
            add(out, 0.3 * bass(hz(tri[0] - 12), bar * 0.95), t0)
        if style in ('curious_pluck', 'warm_pad', 'documentary', 'space') and energy > 0.6:
            add(out, 0.25 * bass(hz(tri[0] - 12), bar * 0.9, drive=1.0), t0)
    out = out[:int(length * SR)]
    if style == 'lofi':                                                          # warm, slightly dull, vinyl dust
        out = lp(out, 3500, 1) + 0.004 * lp(np.random.uniform(-1, 1, len(out)), 3000, 1)
    out = reverb(out, 2.6 if style in ('space', 'warm_pad', 'epic') else 1.6, 0.35 if style in ('space', 'warm_pad') else 0.2)
    f = min(int(0.8 * SR), len(out) // 3)
    if f > 0: out[:f] *= np.linspace(0, 1, f); out[-f:] *= np.linspace(1, 0, f)
    return out


def render(score, warp, total):
    """score sections on the prototype timeline -> stereo-ready mono float array of `total` seconds."""
    buf = np.zeros(int((total + 1) * SR))
    for sec in sorted(score, key=lambda s: s.get('from', 0)):
        a, b = warp(float(sec.get('from', 0))), warp(float(sec.get('to', total)))
        a, b = max(0.0, a), min(total, b)
        if b - a < 2.0: continue
        add(buf, section(sec, b - a), a)
    buf = buf[:int(total * SR)]
    pk = float(np.abs(buf).max()) or 1.0
    return buf / pk * 0.8


def write_wav(path, x):
    import wave
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    sys.path.insert(0, __import__('os').path.dirname(__file__))
    import sfx as synth
    ev = json.load(open(sys.argv[1], encoding='utf-8')); tm = json.load(open(sys.argv[2], encoding='utf-8'))
    x = render(ev.get('score') or [], synth.warp_fn(tm), float(tm['duration']))
    write_wav(sys.argv[3], x); print(f'music: {len(ev.get("score") or [])} đoạn, {len(x) / SR:.1f}s → {sys.argv[3]}')
