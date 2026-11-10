#!/usr/bin/env python3
"""Greenhollow sound set, v6.

Extends sound5 (imported unchanged) with combat, creature, pet, quest and UI
effects plus four more seamless music loops. Same rules as v5: everything is
synthesized with numpy (additive voices through time-varying formants,
Karplus-Strong strings, modal and FM bells, band-limited sawtooth bowed
strings, filtered-noise textures, synthesized-IR convolution reverb), no
samples, fixed seeds, so every run writes byte-identical files. Loudness uses
sound5's own finish_sfx / finish_music targets so the sets sit together.

    python sound6.py <root>     -> writes <root>/assets/sounds/*.wav
"""
import math
import os
import sys

import numpy as np

import sound5 as S5
from sound5 import (SR, TAU, N, tvec, mhz, RNG, smooth01, nrm, pan, fit, boxsmooth, eq, svf,
                    conv_lin, conv_circ, reverb_ir, modal, fm_bell, pluck, pad_chord, pad_tone,
                    flute, hand_drum, shaker, formant_gain, finish_sfx, write_wav, Song, body_ir,
                    finish_music, melody_notes, glass_note, handbell, bubble, drone)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def pts(n, points):
    """Piecewise-linear control curve from (seconds, value) breakpoints."""
    xs, ys = zip(*points)
    return np.interp(tvec(n), xs, ys)


def snoise(n, rate, seed):
    """Smooth random control signal (~rate Hz), zero mean, unit std."""
    x = RNG(seed).standard_normal(n)
    w = max(1, N(1.0 / rate))
    x = boxsmooth(boxsmooth(x, w), w)
    x -= x.mean()
    return x / (np.std(x) + 1e-12)


def panv(mono, p):
    """Constant-power pan with a per-sample position."""
    th = (np.asarray(p, float) + 1.0) * math.pi / 4.0
    return np.vstack([mono * np.cos(th), mono * np.sin(th)]) * math.sqrt(2.0)


def place(out, t0, x):
    if x.ndim == 1 and out.ndim == 2:
        x = pan(x, 0.0)
    i = N(t0)
    m = min(x.shape[-1], out.shape[-1] - i)
    if m > 0:
        out[..., i:i + m] += x[..., :m]
    return out


def noise(n, seed):
    return RNG(seed).standard_normal(n)


def grains_st(n, times, amps, pans, seed, glen=(0.0003, 0.0012)):
    """Sparse stereo noise grains (crackle, crunch, grit)."""
    r = RNG(seed)
    y = np.zeros((2, n))
    for t0, a, p in zip(times, amps, pans):
        g = max(4, N(r.uniform(*glen)))
        i = N(t0)
        if i < 0 or i + g > n:
            continue
        s = a * r.standard_normal(g) * np.hanning(g) * math.sqrt(2.0)
        th = (p + 1.0) * math.pi / 4.0
        y[0, i:i + g] += s * math.cos(th)
        y[1, i:i + g] += s * math.sin(th)
    return y


IR6 = {}


def ir6(name):
    if not IR6:
        IR6['dist'] = reverb_ir(2.0, 2.0, 0.040, seed=911, hf=0.35, lp=4500, hp=150, early=5, er_span=0.09)
        IR6['town'] = reverb_ir(1.5, 2.4, 0.014, seed=912, hf=0.45, lp=8500)
        IR6['meadow'] = reverb_ir(2.4, 3.6, 0.025, seed=913, hf=0.40, lp=8000)
        IR6['cave'] = reverb_ir(5.5, 7.0, 0.060, seed=914, hf=0.30, lp=5500, hp=60, early=14, er_span=0.12)
        IR6['story'] = reverb_ir(3.0, 4.2, 0.022, seed=915, hf=0.42, lp=8000)
    return IR6[name]


def rv(x, name, wet):
    """Like sound5.verb, but also knows the v6 rooms."""
    if x.ndim == 1:
        x = pan(x, 0.0)
    irs = S5.irs()
    ir = irs[name] if name in irs else ir6(name)
    return x + wet * conv_lin(x, ir)[:, :x.shape[1]]


# --------------------------------------------------------------------------
# voice: additive glottal source through time-varying formants
# --------------------------------------------------------------------------
def voice(n, f0, forms, seed, tilt=1.0, fmax=7500.0, sub=0.0, jit=0.0, jit_rate=30.0):
    """forms: list of (F, bw, amp); each may be a per-sample array.
    sub > 0 adds half-order partials (period doubling: growl/grunt roughness)."""
    f0 = np.broadcast_to(np.asarray(f0, float), (n,)).copy()
    if jit > 0:
        f0 *= 1.0 + jit * snoise(n, jit_rate, seed + 7)
    ph = np.cumsum(TAU * f0 / SR)
    kmax = int(fmax / max(30.0, float(f0.min()))) + 1
    steps = [(k, 1.0) for k in range(1, kmax + 1)]
    if sub > 0:
        steps += [(k - 0.5, sub) for k in range(1, kmax + 1)]
    y = np.zeros(n)
    for k, g in steps:
        fk = k * f0
        bl = np.clip((fmax - fk) / (0.3 * fmax), 0.0, 1.0)
        if not bl.any():
            continue
        y += g * bl * k ** -tilt * formant_gain(fk, forms) * np.sin(k * ph)
    return y


def formant_noise(n, forms, seed):
    x = noise(n, seed)
    y = np.zeros(n)
    for F, bw, a in forms:
        F = np.broadcast_to(np.asarray(F, float), (n,))
        y += a * svf(x, F, np.maximum(F / bw, 0.5), 'bp')
    return y


# --------------------------------------------------------------------------
# instruments
# --------------------------------------------------------------------------
def saw(f, seed):
    """PolyBLEP band-limited sawtooth with a per-sample frequency."""
    dt = f / SR
    p = (RNG(seed).uniform() + np.cumsum(dt)) % 1.0
    y = 2.0 * p - 1.0
    m = p < dt
    x = p[m] / dt[m]
    y[m] -= x + x - x * x - 1.0
    m = p > 1.0 - dt
    x = (p[m] - 1.0) / dt[m]
    y[m] -= x * x + x + x + 1.0
    return y


def _lines(notes, n, att_fn, rel):
    """Shared note-line logic: log-pitch track, amplitude, time-since-onset."""
    lf = np.full(n, math.log(mhz(notes[0][2])))
    amp = np.zeros(n)
    tso = np.full(n, 99.0)
    for ts, d, m, v in notes:
        i0 = N(ts)
        if i0 >= n:
            continue
        lf[i0:] = math.log(mhz(m))
        ln = min(n - i0, N(d + rel + 0.02))
        u = tvec(ln)
        e = att_fn(u, d) * (1.0 - smooth01((u - d) / rel)) * v
        sl = slice(i0, i0 + ln)
        amp[sl] = np.maximum(amp[sl], e)
        tso[sl] = u
    return lf, amp, tso


def bowed(notes, n, seed, vib_rate=5.3, vib_depth=0.0045, att=0.22, rel=0.4, port=0.06,
          body=(('hp', 55, 0.7), ('peak', 230, 1.2, 4.0), ('peak', 520, 1.4, 3.0),
                ('peak', 1400, 1.2, -2.0), ('lp', 2600, 0.6), ('lp', 4200, 0.7))):
    """Bowed string: band-limited saw, slow bow attack with swell, delayed
    vibrato, bow noise, fixed body resonances."""
    r = RNG(seed)
    t = tvec(n)

    def a_fn(u, d):
        return smooth01(u / att) ** 1.3 * (1.0 + 0.12 * np.sin(np.pi * np.clip(u / max(d, 0.3), 0, 1)))

    lf, amp, tso = _lines(notes, n, a_fn, rel)
    f = np.exp(boxsmooth(lf, N(port)))
    depth = vib_depth * smooth01((tso - 0.15) / 0.5)
    jit = boxsmooth(r.standard_normal(n), N(0.05))
    jit *= 0.0008 / (np.std(jit) + 1e-12)
    y = saw(f * (1.0 + depth * np.sin(TAU * vib_rate * t + 0.6 * np.sin(TAU * 0.23 * t)) + jit), seed + 1)
    bow = eq(r.standard_normal(n), [('bp', 2500, 0.7)], circular=True)
    y = y * amp + 0.04 * (bow / np.std(bow)) * amp ** 1.5
    return eq(y, list(body), circular=True)


def string_pad(midis, dur, seed, att=1.1, rel=1.6):
    """Small string section: three detuned bowed voices per note."""
    n = N(dur + rel)
    t = tvec(n)
    r = RNG(seed)
    out = np.zeros((2, n))
    for j, m in enumerate(midis):
        for dc, p in ((-7.0, -0.45), (0.0, 0.0), (6.0, 0.45)):
            f0 = mhz(m) * 2 ** (dc / 1200.0)
            vib = 1.0 + 0.0035 * np.sin(TAU * r.uniform(4.6, 5.8) * t + r.uniform(0, TAU))
            out += pan(saw(f0 * vib, int(r.integers(1 << 30))), p)
    env = smooth01(t / att) * (1.0 - smooth01((t - dur) / rel))
    out = eq(out * env, [('lp', 2300, 0.6), ('lp', 3400, 0.7), ('peak', 350, 0.9, 2.5), ('hp', 110, 0.7)],
             pad=N(0.05))
    return out / (3 * len(midis))


def horn(notes, n, seed, vib_rate=5.2, vib_depth=0.004, bright=1.0):
    """Additive brass: upper partials grow with loudness (the brass 'bloom'),
    a small pitch scoop into each note, delayed vibrato."""
    r = RNG(seed)
    t = tvec(n)

    def a_fn(u, d):
        return smooth01(u / 0.03) * (1.0 + 0.18 * np.exp(-u / 0.06))

    lf, amp, tso = _lines(notes, n, a_fn, 0.12)
    scoop = -0.025 * np.exp(-np.minimum(tso, 5.0) / 0.03)
    f = np.exp(boxsmooth(lf, N(0.02))) * 2.0 ** scoop
    depth = vib_depth * smooth01((tso - 0.25) / 0.4)
    phase = np.cumsum(TAU * f * (1.0 + depth * np.sin(TAU * vib_rate * t)) / SR)
    a = np.clip(amp, 0.0, None)
    y = np.zeros(n)
    for k in range(1, 30):
        bl = np.clip((7000.0 - k * f) / 2000.0, 0.0, 1.0)
        if not bl.any():
            break
        y += bl * k ** -0.85 * a ** (1.0 + 0.5 * (k - 1) * bright) * np.sin(k * phase)
    br = eq(r.standard_normal(n), [('bp', 1400, 0.8)], pad=N(0.02))
    y += 0.03 * nrm(br) * a
    return eq(y, [('hp', 80, 0.7), ('peak', 1000, 0.9, 3.0), ('lp', 4200, 0.6)], pad=N(0.05))


def strum(S, bus, t0, voicing, down, vel, off, seed, spread=0.009):
    notes = list(voicing) if down else list(voicing[::-1])[:4]
    for i, m in enumerate(notes):
        v = vel * (1.0 - 0.07 * i)
        y = pluck(m, v, seed + i, 'guitar', dur=off + 0.3, off=off)
        S.add(bus, t0 + i * (spread if down else 0.75 * spread), pan(y, -0.35 + 0.025 * (m - 50)))


def tamb(vel, seed, dur=0.16):
    """Frame tambourine: hiss of the skin plus a handful of jingles."""
    n = N(dur)
    t = tvec(n)
    r = RNG(seed)
    hiss = eq(r.standard_normal(n), [('hp', 5000, 0.7), ('lp', 11000)], pad=N(0.01))
    hiss *= smooth01(t / 0.002) * np.exp(-t / 0.035)
    j = np.zeros(n)
    for _ in range(8):
        d = N(r.uniform(0, 0.012))
        f = r.uniform(5200, 8200)
        j[d:] += r.uniform(0.4, 1.0) * modal(n - d, [(f, 1, .030), (f * 1.37, .6, .020), (f * 1.93, .3, .012)],
                                             int(r.integers(1 << 30)), att=0.0002)
    y = 0.6 * nrm(hiss) + 0.5 * nrm(j)
    y *= 1.0 - smooth01((t - (dur - 0.03)) / 0.03)
    return nrm(y) * vel


def bird_phrase(seed):
    """A short songbird phrase: a few warbled chirps."""
    r = RNG(seed)
    kind = int(r.integers(0, 3))
    reps = int(r.integers(2, 5))
    base = r.uniform(3000, 4300)
    out = np.zeros(N(1.5))
    tt = 0.0
    for q in range(reps):
        L = r.uniform(0.05, 0.09)
        m = N(L)
        u = tvec(m)
        if kind == 0:
            f = base * (1.0 + 0.25 * np.sin(np.pi * u / L))
        elif kind == 1:
            f = base * (1.3 - 0.45 * u / L)
        else:
            f = base * (0.85 + 0.35 * u / L)
        f *= 1.0 + 0.03 * np.sin(TAU * r.uniform(35, 60) * u)
        ph = np.cumsum(TAU * f / SR)
        y = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * np.sin(np.pi * u / L) ** 2
        place(out, tt, y * (0.75 + 0.25 * r.random()))
        tt += L + r.uniform(0.03, 0.08)
    return out[:N(tt + 0.05)]


def drip(seed):
    """Water drop into a pool: a fast-rising bubble resonance plus a tiny tick."""
    r = RNG(seed)
    n = N(0.25)
    t = tvec(n)
    f0 = r.uniform(1100, 2300)
    y = bubble(n, 0.0, f0, f0 * r.uniform(1.6, 2.2), r.uniform(0.018, 0.04), rise=r.uniform(0.008, 0.016))
    tick = eq(r.standard_normal(n), [('hp', 2500, 0.7)], pad=N(0.01)) * np.exp(-t / 0.0005)
    return y + 0.12 * nrm(tick)


def cave_bell(f, seed, dur=7.0):
    """Inharmonic, slowly beating bell (FM at an irrational ratio + modal)."""
    n = N(dur)
    y = 0.7 * fm_bell(n, f, ratio=1.414, index=0.8, itau=0.6, tau=2.4, att=0.004)
    y += 0.5 * modal(n, [(f, 1, 2.6), (f * 1.004, .7, 2.4), (f * 2.32, .35, 1.2), (f * 4.25, .15, .5),
                         (f * 0.5, .25, 3.0)], seed, att=0.004)
    return y


def periodic_texture(L, seed, layers):
    """Band-noise layers, synthesized over exactly one loop (so they wrap)."""
    r = RNG(seed)
    T = L / SR
    t = tvec(L)
    freqs = np.fft.rfftfreq(L, 1.0 / SR)
    out = np.zeros((2, L))
    for ch in range(2):
        for j, (fc, bw, cyc, g) in enumerate(layers):
            mag = np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
            X = (r.standard_normal(len(freqs)) + 1j * r.standard_normal(len(freqs))) * mag
            X[0] = 0
            x = np.fft.irfft(X, L)
            x /= np.std(x)
            ph = r.uniform(0, TAU)
            env = 0.55 + 0.45 * np.sin(TAU * cyc * t / T + ph)
            out[ch] += g * x * env ** 1.5
    return out


def sparkle(n, t_lo, t_hi, count, seed, notes=(86, 88, 90, 93, 95, 98), gain=0.07, decay=0.5):
    r = RNG(seed)
    out = np.zeros((2, n))
    for _ in range(count):
        t0 = r.uniform(t_lo, t_hi)
        i = N(t0)
        if i >= n:
            continue
        f = mhz(int(r.choice(notes)))
        g = modal(n - i, [(f, 1, 0.06), (f * 2.76, 0.2, 0.02)], int(r.integers(1 << 30)))
        out[:, i:] += pan(g * gain * math.exp(-(t0 - t_lo) / decay), r.uniform(-0.7, 0.7))
    return out


# --------------------------------------------------------------------------
# sound effects
# --------------------------------------------------------------------------
def sfx_bow():
    dur = 0.85
    n = N(dur)
    t = tvec(n)
    r = RNG(1101)
    # string twang: pitch settles as the string is released, upper partials die first
    f = 92.0 * (1.0 + 0.22 * np.exp(-t / 0.012))
    ph = np.cumsum(TAU * f / SR)
    tw = np.zeros(n)
    for k in range(1, 70):
        if 92.0 * k > 7000:
            break
        tw += k ** -1.0 * np.sin(k * ph) * np.exp(-t / (0.20 / k ** 0.55))
    tw *= 1.0 - np.exp(-t / 0.0004)
    slap = eq(r.standard_normal(n), [('bp', 2200, 0.8)], pad=N(0.02)) * np.exp(-t / 0.004)
    knock = modal(n, [(180, 1, .03), (410, .6, .02), (760, .4, .012), (1320, .2, .008)], 1102)
    thump = np.sin(np.cumsum(TAU * (60 + 50 * np.exp(-t / 0.01)) / SR)) * np.exp(-t / 0.05)
    # arrow: down-sweeping air with fletching flutter, flying off to the right
    u = np.maximum(t - 0.02, 0.0)
    fc = 3600.0 * (650.0 / 3600.0) ** smooth01(u / 0.45)
    wh = svf(r.standard_normal(n), fc, 1.3, 'bp')
    flut = 0.7 + 0.3 * np.sin(np.cumsum(TAU * (55.0 - 25.0 * smooth01(u / 0.45)) / SR))
    we = (t >= 0.02) * smooth01(u / 0.05) * np.exp(-np.maximum(u - 0.05, 0) / 0.13)
    wh = nrm(wh) * we * flut
    out = pan(0.8 * nrm(tw) + 0.25 * nrm(slap) + 0.35 * nrm(knock) + 0.4 * nrm(thump), -0.15)
    out += 0.55 * panv(wh, -0.1 + 0.9 * smooth01(u / 0.4))
    return finish_sfx(rv(out, 'room', 0.12), dur, -16.0, 0.15)


def sfx_magic():
    dur = 1.3
    n = N(dur)
    t = tvec(n)
    r = RNG(1201)
    sw = smooth01(t / 0.78)
    env = (0.08 + 0.92 * sw ** 1.5) * smooth01(t / 0.02) * np.exp(-np.maximum(t - 0.80, 0) / 0.17)
    wh = svf(r.standard_normal(n), 260.0 * (3400.0 / 260.0) ** sw, 1.2, 'bp')
    flick = np.clip(1.0 + 0.5 * snoise(n, 22.0, 1202), 0.15, None)          # flame turbulence
    roar = svf(r.standard_normal(n), 140.0 + 1100.0 * sw, 0.75, 'lp') * flick
    tone = np.cumsum(TAU * 90.0 * 2.0 ** (1.6 * sw) / SR)
    tone = np.sin(tone) + 0.4 * np.sin(2 * tone)
    uf = t - 0.76
    flare = svf(r.standard_normal(n), 400.0 + 3000.0 * np.exp(-np.maximum(uf, 0) / 0.08), 0.7, 'lp')
    flare *= (uf >= 0) * smooth01(uf / 0.01) * np.exp(-np.maximum(uf, 0) / 0.12)
    body = 0.55 * nrm(wh) * env + 0.6 * nrm(roar) * env + 0.22 * nrm(tone) * env + 0.35 * nrm(flare)
    out = panv(body, -0.35 + 0.7 * sw)
    k = 70
    ct = 0.12 + 1.0 * r.random(k) ** 0.8
    ca = (r.pareto(2.5, k) + 0.3) * np.interp(ct, t, env + 0.4 * (t > 0.76) * np.exp(-np.maximum(uf, 0) / 0.15))
    cr = grains_st(n, ct, ca, r.uniform(-0.6, 0.6, k), 1205)
    out += 0.5 * nrm(eq(cr, [('hp', 1500, 0.7), ('lp', 7000)], pad=N(0.01)))
    sp = np.zeros(n)                                                          # the spell's spark
    sp += 0.5 * glass_note(n, mhz(88), 1203)
    place(sp, 0.04, 0.3 * glass_note(n, mhz(93), 1204))
    out += pan(0.18 * nrm(sp), 0.0)
    return finish_sfx(rv(out, 'hall', 0.22), dur, -15.0, 0.25)


def sfx_boom():
    dur = 1.0
    n = N(dur)
    t = tvec(n)
    r = RNG(1301)
    sub = np.sin(np.cumsum(TAU * (40 + 110 * np.exp(-t / 0.03)) / SR)) * np.exp(-t / 0.17) * (1 - np.exp(-t / 0.0008))
    blast = svf(r.standard_normal(n), 300 + 5000 * np.exp(-t / 0.045), 0.7, 'lp')
    blast *= smooth01(t / 0.0015) * np.exp(-t / 0.10)
    thud = eq(r.standard_normal(n), [('bp', 180, 0.9)], pad=N(0.05)) * np.exp(-t / 0.08) * smooth01(t / 0.002)
    flick = np.clip(1.0 + 0.6 * snoise(n, 18.0, 1302), 0.1, None)
    flame = svf(r.standard_normal(n), 250 + 700 * np.exp(-t / 0.25), 0.8, 'lp') * flick
    flame *= smooth01(t / 0.03) * np.exp(-t / 0.3)
    mix = np.tanh(1.5 * (1.0 * nrm(sub) + 0.8 * nrm(blast) + 0.5 * nrm(thud) + 0.45 * nrm(flame)))
    out = pan(mix, 0.0)
    k = 80
    ct = 0.02 + r.exponential(0.16, k)
    ca = (r.pareto(2.2, k) + 0.3) * np.exp(-ct / 0.25)
    cr = grains_st(n, ct, ca, r.uniform(-0.7, 0.7, k), 1303)
    out += 0.35 * nrm(eq(cr, [('hp', 1200, 0.7), ('lp', 6500)], pad=N(0.01)))
    return finish_sfx(rv(out, 'hall', 0.25), dur, -15.5, 0.25)


def sfx_wolf():
    dur = 0.9
    n = N(dur)
    t = tvec(n)
    a = pts(n, [(0, 0), (0.05, 0.35), (0.30, 0.55), (0.42, 1.0), (0.60, 0.9), (0.74, 0.35), (0.82, 0.0), (dur, 0)])
    f0 = pts(n, [(0, 86), (0.30, 98), (0.43, 132), (0.60, 120), (0.82, 96), (dur, 96)])
    F1 = pts(n, [(0, 430), (0.30, 480), (0.44, 700), (0.62, 640), (0.82, 480), (dur, 480)])
    F2 = pts(n, [(0, 1050), (0.30, 1150), (0.44, 1500), (0.62, 1400), (0.82, 1150), (dur, 1150)])
    forms = [(F1, 200.0, 1.0), (F2, 260.0, 0.55), (2550.0, 380.0, 0.35), (3600.0, 500.0, 0.15)]
    v = voice(n, f0, forms, 1501, tilt=0.7, sub=0.55, jit=0.07, jit_rate=45)
    rough = np.clip(1.0 + 0.9 * snoise(n, 80, 1502), 0.0, None)              # throat rattle
    v = nrm(v * rough)
    asp = nrm(formant_noise(n, forms[:3], 1503))
    hiss = nrm(eq(noise(n, 1504), [('bp', 4300, 1.2)], pad=N(0.02))) * smooth01((a - 0.6) / 0.4)
    y = (0.75 * v + 0.5 * asp * (0.6 + 0.4 * np.clip(rough, 0, 2) / 2)) * a + 0.08 * hiss
    y = eq(y, [('lp', 5500, 0.6)], pad=N(0.02))
    return finish_sfx(rv(pan(y, -0.1), 'room', 0.12), dur, -16.0, 0.08)


def sfx_howl():
    dur = 1.9
    n = N(dur)
    t = tvec(n)
    f0 = pts(n, [(0, 360), (0.12, 450), (0.35, 560), (0.90, 600), (1.15, 575), (1.38, 470), (1.50, 420), (dur, 420)])
    f0 = f0 * (1.0 + 0.008 * np.sin(TAU * 5.2 * t) * smooth01((t - 0.3) / 0.4))
    a = pts(n, [(0, 0), (0.08, 0.5), (0.30, 0.95), (1.0, 1.0), (1.30, 0.7), (1.48, 0.0), (dur, 0)])
    F1 = pts(n, [(0, 500), (0.30, 800), (1.0, 850), (1.40, 550), (dur, 550)])
    F2 = pts(n, [(0, 1000), (0.30, 1300), (1.0, 1250), (1.40, 900), (dur, 900)])
    forms = [(F1, 250.0, 1.0), (F2, 300.0, 0.5), (2700.0, 400.0, 0.15)]
    v = voice(n, f0, forms, 1601, tilt=1.8, jit=0.004, jit_rate=12)
    br = formant_noise(n, forms[:2], 1602)
    y = (nrm(v) + 0.08 * nrm(br)) * a
    y = eq(y, [('lp', 2800, 0.6), ('hp', 180, 0.7)], pad=N(0.02))            # far away: dull, thin
    dry = pan(y, 0.3)
    wet = conv_lin(dry, ir6('dist'))[:, :n]
    return finish_sfx(0.45 * dry + 1.0 * wet, dur, -17.5, 0.35, fin=0.003)


def grunt(n, t0, length, fa, fb, seed, F1=380.0, F2=880.0, rough=0.9):
    t = tvec(n)
    u = t - t0
    f0 = fa + (fb - fa) * smooth01(u / length)
    forms = [(F1, 180.0, 1.0), (F2, 240.0, 0.55), (2150.0, 320.0, 0.25), (3200.0, 450.0, 0.1)]
    v = voice(n, f0, forms, seed, tilt=0.65, sub=0.8, jit=0.09, jit_rate=55)
    am = np.clip(1.0 + rough * snoise(n, 90, seed + 3), 0.0, None)
    asp = formant_noise(n, forms[:3], seed + 4)
    a = (u >= 0) * smooth01(u / 0.012) * (1.0 - smooth01((u - (length - 0.05)) / 0.05))
    return (0.8 * nrm(v * am) + 0.45 * nrm(asp)) * a


def sfx_boar():
    dur = 0.75
    n = N(dur)
    t = tvec(n)
    r = RNG(1701)
    # snort: air through the nostrils, fluttering
    nz = r.standard_normal(n)
    sn = (eq(nz, [('bp', 750, 2.0)], pad=N(0.02)) + 0.7 * eq(nz, [('bp', 1900, 2.5)], pad=N(0.02)) +
          0.3 * eq(nz, [('lp', 500, 0.7)], pad=N(0.02)))
    flut = (0.5 + 0.5 * np.sin(np.cumsum(TAU * (42 - 10 * smooth01(t / 0.15)) / SR))) ** 2
    se = smooth01(t / 0.01) * np.exp(-t / 0.06) * (1.0 - smooth01((t - 0.13) / 0.03))
    snort = nrm(sn) * se * (0.35 + 0.65 * flut)
    g1 = grunt(n, 0.20, 0.16, 110, 95, 1702)
    g2 = grunt(n, 0.42, 0.20, 100, 78, 1712, F1=360.0, F2=820.0)
    out = pan(0.6 * snort, 0.1) + pan(0.9 * g1 + 0.85 * g2, -0.05)
    out = eq(out, [('lp', 5000, 0.6)], pad=N(0.02))
    return finish_sfx(rv(out, 'room', 0.1), dur, -16.5, 0.08)


def sfx_bat():
    dur = 0.7
    n = N(dur)
    t = tvec(n)
    r = RNG(1801)
    flaps = np.zeros(n)
    tt = 0.0
    while tt < 0.62:                                    # ~14 wingbeats a second
        m = N(0.05)
        u = tvec(m)
        puff = eq(r.standard_normal(m), [('lp', 1400, 0.7), ('peak', 450, 1.5, 6.0)], pad=N(0.01))
        puff *= smooth01(u / 0.012) * np.exp(-np.maximum(u - 0.012, 0) / 0.012)
        place(flaps, tt, nrm(puff) * math.sin(math.pi * min(1.0, tt / 0.65)) ** 0.7)
        tt += (1.0 / 14.0) * (1.0 + 0.04 * r.standard_normal())
    sq = np.zeros(n)
    for t0, L, fa, fp, fe in ((0.10, 0.045, 2900, 3800, 2600), (0.21, 0.060, 3100, 4000, 2500),
                              (0.30, 0.040, 3000, 3600, 2700)):
        m = N(L)
        u = tvec(m)
        f = pts(m, [(0, fa), (0.25 * L, fp), (L, fe)])
        ph = np.cumsum(TAU * f / SR)
        s = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
        s *= smooth01(u / 0.004) * (1.0 - smooth01((u - (L - 0.015)) / 0.015)) * (1 + 0.25 * np.sin(TAU * 90 * u))
        s += 0.05 * eq(r.standard_normal(m), [('bp', 3500, 1.0)], pad=N(0.005)) * s
        place(sq, t0, s)
    p = -0.6 + 1.2 * smooth01(t / 0.65)
    out = panv(0.5 * nrm(flaps), p) + panv(0.6 * nrm(sq), p)
    out = eq(out, [('lp', 9000, 0.6)], pad=N(0.02))
    return finish_sfx(rv(out, 'room', 0.15), dur, -17.0, 0.1)


def sfx_golem():
    dur = 1.4
    n = N(dur)
    t = tvec(n)
    r = RNG(1401)
    sub = np.sin(np.cumsum(TAU * (34 + 48 * np.exp(-t / 0.05)) / SR)) * np.exp(-t / 0.22) * (1 - np.exp(-t / 0.002))
    stone = modal(n, [(62, 1, .16), (97, .85, .12), (151, .7, .09), (226, .55, .06), (331, .4, .045),
                      (487, .28, .03), (702, .18, .02), (1040, .1, .012)], 1402, att=0.0012)
    crunch = eq(r.standard_normal(n), [('lp', 1400, 0.7), ('hp', 120, 0.7)], pad=N(0.02))
    crunch *= smooth01(t / 0.002) * np.exp(-t / 0.05)
    k = 160
    gt = 0.002 + r.exponential(0.04, k)
    grit = grains_st(n, gt, (r.pareto(2.0, k) + 0.3) * np.exp(-gt / 0.06), r.uniform(-0.4, 0.4, k), 1403)
    grit = eq(grit, [('bp', 2500, 0.7)], pad=N(0.01))
    peb = np.zeros((2, n))
    for _ in range(18):                                   # pebbles settling
        t0 = 0.08 + r.exponential(0.18)
        i = N(t0)
        if i >= n - N(0.05):
            continue
        f = r.uniform(1200, 3500)
        y = modal(n - i, [(f, 1, r.uniform(.01, .03)), (f * 1.62, .5, .01)], int(r.integers(1 << 30)), att=0.0003)
        peb[:, i:] += pan(y * r.uniform(0.3, 1.0) * math.exp(-(t0 - 0.08) / 0.3), r.uniform(-0.7, 0.7))
    rumble = eq(r.standard_normal(n), [('lp', 95, 0.7), ('hp', 22, 0.7)], pad=N(0.1))
    rumble = nrm(rumble) * smooth01(t / 0.03) * np.exp(-t / 0.45) * np.clip(1.0 + 0.3 * snoise(n, 6.0, 1404), 0, None)
    mix = np.tanh(1.3 * (1.0 * nrm(sub) + 0.75 * nrm(stone) + 0.5 * nrm(crunch) + 0.6 * rumble))
    out = pan(mix, 0.0) + 0.3 * nrm(grit) + 0.18 * nrm(peb)
    return finish_sfx(rv(out, 'hall', 0.2), dur, -15.5, 0.3)


def sfx_meow():
    dur = 0.8
    n = N(dur)
    t = tvec(n)
    f0 = pts(n, [(0, 540), (0.06, 600), (0.20, 760), (0.34, 740), (0.52, 560), (0.64, 470), (dur, 460)])
    f0 = f0 * (1.0 + 0.006 * np.sin(TAU * 6.0 * t))
    F1 = pts(n, [(0, 320), (0.06, 380), (0.18, 900), (0.34, 850), (0.50, 650), (0.64, 430), (dur, 430)])
    F2 = pts(n, [(0, 1900), (0.08, 1900), (0.20, 1650), (0.36, 1500), (0.52, 1100), (0.64, 850), (dur, 850)])
    F3 = pts(n, [(0, 2900), (0.20, 2800), (0.60, 2500), (dur, 2500)])
    mouth = smooth01((t - 0.04) / 0.12)                     # "m" opens into "eow"
    forms = [(F1, 160.0, 1.0), (F2, 220.0, 0.6 * (0.3 + 0.7 * mouth)), (F3, 320.0, 0.3 * (0.2 + 0.8 * mouth)),
             (250.0, 100.0, 0.8 * (1.0 - mouth))]
    v = voice(n, f0, forms, 1901, tilt=1.25, jit=0.008, jit_rate=20)
    asp = formant_noise(n, forms[:3], 1902)
    a = pts(n, [(0, 0), (0.04, 0.35), (0.14, 0.85), (0.30, 1.0), (0.50, 0.8), (0.62, 0.45), (0.70, 0.0), (dur, 0)])
    y = (0.85 * nrm(v) + 0.12 * nrm(asp)) * a
    return finish_sfx(rv(pan(y, 0.05), 'room', 0.12), dur, -17.5, 0.1)


def bark1(n, seed, fp=470.0, length=0.15):
    t = tvec(n)
    T = n / SR
    f0 = pts(n, [(0, 330), (0.018, fp), (0.06, fp * 0.92), (length, fp * 0.7), (T, fp * 0.7)])
    F1 = pts(n, [(0, 500), (0.03, 900), (0.09, 800), (length, 550), (T, 550)])
    F2 = pts(n, [(0, 1300), (0.03, 1700), (length, 1350), (T, 1350)])
    forms = [(F1, 220.0, 1.0), (F2, 300.0, 0.7), (2700.0, 400.0, 0.45), (3800.0, 600.0, 0.2)]
    v = voice(n, f0, forms, seed, tilt=0.75, sub=0.25, jit=0.03, jit_rate=60)
    asp = formant_noise(n, forms[:3], seed + 1)
    a = smooth01(t / 0.008) * (1.0 - smooth01((t - (length - 0.04)) / 0.04)) * (1.0 - 0.35 * smooth01(t / length))
    return (0.8 * nrm(v) + 0.45 * nrm(asp)) * a


def sfx_bark():
    dur = 0.75
    n = N(dur)
    out = np.zeros((2, n))
    place(out, 0.02, pan(bark1(N(0.2), 2001, 470.0, 0.14), -0.05))
    place(out, 0.26, pan(0.9 * bark1(N(0.22), 2011, 500.0, 0.16), 0.0))
    return finish_sfx(rv(out, 'room', 0.15), dur, -16.0, 0.12)


def sfx_eat():
    dur = 0.75
    n = N(dur)
    r = RNG(2101)
    out = np.zeros((2, n))
    for j, (t0, g) in enumerate(((0.0, 1.0), (0.24, 0.85), (0.47, 0.65))):
        m = N(0.2)
        u = tvec(m)
        chomp = eq(r.standard_normal(m), [('lp', 380, 0.8)], pad=N(0.02)) * smooth01(u / 0.003) * np.exp(-u / 0.025)
        thud = np.sin(TAU * 120 * u) * np.exp(-u / 0.02) * (1 - np.exp(-u / 0.002))
        k = 260
        gt = r.exponential(0.03, k) + 0.004
        ga = np.minimum(r.pareto(1.8, k) + 0.2, 2.5) * np.exp(-gt / 0.05)
        cr = grains_st(m, gt, ga, r.uniform(-0.25, 0.25, k), 2102 + j, glen=(0.0003, 0.0015))
        crunch = 0.6 * nrm(eq(cr, [('bp', 1800, 0.8)], pad=N(0.01))) + 0.5 * nrm(eq(cr, [('bp', 4200, 0.9)], pad=N(0.01)))
        crunch = np.tanh(2.5 * crunch) / math.tanh(2.5)        # dense, not spiky
        seg = pan(0.45 * nrm(chomp) + 0.2 * nrm(thud), 0.0) + 0.8 * crunch
        place(out, t0, g * seg)
    for t0 in (0.17, 0.40):                               # small wet mouth sounds
        place(out, t0, pan(0.05 * bubble(N(0.05), 0.0, 700, 1100, 0.01, rise=0.01), 0.0))
    return finish_sfx(rv(out, 'room', 0.08), dur, -17.5, 0.08)


def sfx_quest():
    dur = 0.9
    n = N(dur)
    out = np.zeros((2, n))
    for j, (t0, m, a, p) in enumerate(((0.0, 79, 0.7, -0.2), (0.085, 83, 0.75, 0.0), (0.17, 86, 0.95, 0.2))):
        i = N(t0)
        y = 0.8 * handbell(n - i, mhz(m), 2201 + j) + 0.35 * glass_note(n - i, mhz(m), 2211 + j)
        out[:, i:] += pan(a * y, p)
    out += pan(0.45 * pluck(67, 0.6, 2221, 'harp', dur=dur), -0.1)
    place(out, 0.17, pan(0.35 * pluck(74, 0.5, 2222, 'harp', dur=dur - 0.17), 0.1))
    out += sparkle(n, 0.2, 0.6, 8, 2231)
    out = eq(out, [('highshelf', 6000, 0.7, -3.0)], pad=N(0.05))
    return finish_sfx(rv(out, 'hall', 0.25), dur, -15.5, 0.25)


def sfx_complete():
    dur = 1.7
    n = N(dur)
    lead = horn([(0.0, 0.09, 67, 0.75), (0.10, 0.09, 72, 0.8), (0.20, 0.10, 76, 0.85), (0.32, 0.82, 79, 0.95)], n, 2301)
    h2 = horn([(0.32, 0.82, 76, 0.7)], n, 2302, vib_depth=0.003)
    h3 = horn([(0.32, 0.82, 72, 0.7)], n, 2303)
    h4 = horn([(0.32, 0.85, 60, 0.75)], n, 2304)
    out = 0.9 * pan(lead, 0.05) + 0.55 * pan(h2, -0.25) + 0.5 * pan(h3, 0.3) + 0.55 * pan(h4, -0.1)
    for j, m in enumerate((48, 55, 60, 64, 67, 72, 76, 79)):          # harp sweep up the chord
        t0 = 0.32 + 0.022 * j
        place(out, t0, pan(0.35 * pluck(m, 0.55 + 0.02 * j, 2311 + j, 'harp', dur=dur - t0), -0.45 + 0.12 * j))
    place(out, 0.32, pan(0.5 * hand_drum(0.9, 2321, 70, 1.0, 0.15), 0.0))
    i = N(0.34)
    out[:, i:] += pan(0.2 * handbell(n - i, mhz(84), 2331), 0.2)
    i = N(0.50)
    out[:, i:] += pan(0.12 * glass_note(n - i, mhz(91), 2332), -0.2)
    out += sparkle(n, 0.4, 1.0, 10, 2341, gain=0.05)
    out = eq(out, [('highshelf', 6000, 0.7, -3.0)], pad=N(0.05))
    return finish_sfx(rv(out, 'hall', 0.3), dur, -15.0, 0.35)


def coin_ring(m, f, seed, tau):
    parts = [(1.0, 1.0, 1.0), (1.508, 0.7, 0.8), (2.03, 0.5, 0.6), (2.62, 0.35, 0.45), (3.23, 0.2, 0.35)]
    r = RNG(seed)
    return modal(m, [(f * q, a * r.uniform(0.6, 1.0), tau * d) for q, a, d in parts], seed, att=0.0002)


def sfx_coin():
    dur = 0.7
    n = N(dur)
    t = tvec(n)
    r = RNG(2401)
    out = np.zeros((2, n))
    hits = ((0.0, 0.9), (0.045, 0.6), (0.075, 0.75), (0.13, 0.5), (0.19, 0.55), (0.27, 0.35), (0.36, 0.25))
    for j, (t0, a) in enumerate(hits):
        m = N(0.5)
        u = tvec(m)
        y = np.zeros(m)
        for c in range(2):                                   # two coins touching
            f = float(r.choice([2350.0, 2900.0, 3450.0, 4100.0])) * r.uniform(0.97, 1.03)
            y += (1.0 if c == 0 else 0.5) * coin_ring(m, f, 2402 + 10 * j + c, r.uniform(0.04, 0.16))
        click = eq(r.standard_normal(m), [('hp', 3000, 0.7)], pad=N(0.01)) * np.exp(-u / 0.0006)
        place(out, t0, pan(a * (nrm(y) + 0.25 * nrm(click)), r.uniform(-0.4, 0.4)))
    knock = modal(n, [(210, 1, .025), (380, .6, .018), (620, .35, .012)], 2490, att=0.0008)
    pouch = eq(r.standard_normal(n), [('lp', 320, 0.7)], pad=N(0.02)) * np.exp(-t / 0.03) * smooth01(t / 0.002)
    out += pan(0.25 * nrm(knock) + 0.25 * nrm(pouch), 0.0)
    out = eq(out, [('highshelf', 7000, 0.7, -4.0)], pad=N(0.05))
    return finish_sfx(rv(out, 'room', 0.15), dur, -16.5, 0.12)


def sfx_heal():
    dur = 1.4
    n = N(dur)
    t = tvec(n)
    r = RNG(2501)
    swell = smooth01(t / 0.6)
    env = swell * np.exp(-np.maximum(t - 0.7, 0) / 0.3)
    pad = np.zeros(n)
    for j, m in enumerate((65, 69, 72, 76, 79)):
        pad += pad_tone(mhz(m), n, 2502 + j, bright=0.35, det=(-5.0, 4.0), nh=5)
    out = pan(0.45 * nrm(pad) * env, 0.0)
    air = svf(r.standard_normal(n), 900.0 * (5200.0 / 900.0) ** smooth01(t / 0.9), 1.5, 'bp')
    out += pan(0.15 * nrm(air) * env, -0.2)
    for j, (t0, m) in enumerate(((0.0, 72), (0.09, 77), (0.18, 79), (0.27, 84), (0.37, 89), (0.48, 91))):
        i = N(t0)
        f = mhz(m)
        y = modal(n - i, [(f, 1, .5), (2 * f, .2, .2), (3.01 * f, .05, .1)], 2511 + j, att=0.006)
        out[:, i:] += pan(0.28 * (0.7 + 0.06 * j) * y, -0.4 + 0.16 * j)
    shim = np.zeros(n)
    for m in (96, 100, 103):
        shim += np.sin(TAU * mhz(m) * t + r.uniform(0, TAU)) * (1 + 0.5 * np.sin(TAU * r.uniform(5.5, 8.0) * t))
    out += pan(0.05 * nrm(shim) * env * smooth01((t - 0.2) / 0.5), 0.3)
    out += sparkle(n, 0.3, 1.0, 16, 2521, notes=(89, 91, 93, 96, 98, 101), gain=0.05)
    out = eq(out, [('highshelf', 6000, 0.7, -3.0)], pad=N(0.05))
    return finish_sfx(rv(out, 'hall', 0.35), dur, -16.0, 0.35, fin=0.004)


def sfx_type():
    dur = 0.05
    n = N(dur)
    t = tvec(n)
    y = modal(n, [(1650, 1, .005), (3100, .35, .003), (820, .4, .007)], 2601, att=0.0004)
    c = eq(noise(n, 2602), [('bp', 3000, 0.8)], pad=N(0.01)) * np.exp(-t / 0.0008)
    y = eq(y + 0.25 * nrm(c), [('lp', 6000, 0.6)], pad=N(0.01))
    return finish_sfx(pan(y, 0.0), dur, -20.5, 0.02, fin=0.0008)


def sfx_page():
    dur = 0.6
    n = N(dur)
    t = tvec(n)
    r = RNG(2701)
    motion = pts(n, [(0, 0), (0.05, 0.25), (0.12, 0.15), (0.20, 0.8), (0.30, 1.0), (0.38, 0.5), (0.42, 0.2),
                     (0.50, 0.05), (dur, 0)])
    swish = svf(r.standard_normal(n), 900.0 + 3200.0 * motion, 0.8, 'bp') * motion
    swish *= 1.0 + 0.25 * np.sin(TAU * 28.0 * t) * motion          # the sheet wobbling
    k1, k2, k3 = 60, 35, 70
    ct = np.concatenate([r.uniform(0.0, 0.08, k1), r.uniform(0.1, 0.36, k2), 0.36 + r.exponential(0.03, k3)])
    ca = np.concatenate([r.pareto(2.5, k1) + 0.2, 0.5 * (r.pareto(2.5, k2) + 0.2), 0.8 * (r.pareto(2.5, k3) + 0.2)])
    cr = grains_st(n, ct, ca, r.uniform(-0.3, 0.3, len(ct)), 2702, glen=(0.0002, 0.0008))
    cr = eq(cr, [('hp', 2500, 0.7), ('peak', 5000, 1.0, 3.0)], pad=N(0.01))
    u = t - 0.38
    flap = eq(r.standard_normal(n), [('lp', 700, 0.7)], pad=N(0.02)) * (u >= 0) * smooth01(u / 0.004) * np.exp(-np.maximum(u, 0) / 0.025)
    p = -0.35 + 0.7 * smooth01(t / 0.45)
    out = panv(0.7 * nrm(swish) + 0.35 * nrm(flap), p) + 0.35 * nrm(cr)
    return finish_sfx(rv(out, 'room', 0.08), dur, -19.0, 0.08)


# --------------------------------------------------------------------------
# music
# --------------------------------------------------------------------------
def mixdown(S, lv, sends, ir, wet, target, pre=None, stems=False):
    x = S.mix(lv, sends, ir, wet=wet, pre=pre)
    if stems:
        st = {}
        for name in lv:
            if name in S.bus:
                y = S.looped(name)
                if pre and name in pre:
                    y = pre[name](y)
                st[name] = lv[name] * y
        return st, x
    return finish_music(x, target)


def spans_of(prog, beats_per_bar):
    spans = []
    for b, nm in enumerate(prog):
        if spans and spans[-1][0] == nm:
            spans[-1][2] += beats_per_bar
        else:
            spans.append([nm, b * beats_per_bar, beats_per_bar])
    return spans


# ------------------------------- town -------------------------------------
TOWN_CH = {   # bass root, strum voicing, pad voicing
    'G':  (43, [50, 55, 59, 62, 67], [55, 59, 62]),
    'D':  (38, [50, 54, 57, 62, 66], [54, 57, 62]),
    'Em': (40, [52, 55, 59, 64, 67], [52, 55, 59]),
    'C':  (36, [48, 52, 55, 60, 64], [52, 55, 60]),
    'Am': (45, [52, 57, 60, 64, 69], [52, 57, 60]),
}
TOWN_PROG = ['G', 'D', 'Em', 'C', 'G', 'Am', 'C', 'D', 'Em', 'C', 'G', 'D', 'C', 'D', 'G', 'D']
TOWN_MEL = [
    [(71, .5), (74, .5), (79, 1), (78, .5), (76, .5), (74, 1)],
    [(74, 1.5), (72, .5), (71, .5), (69, .5), (66, 1)],
    [(67, .5), (71, .5), (76, 1), (74, .5), (76, .5), (78, 1)],
    [(79, 1.5), (76, .5), (72, 2)],
    [(71, .5), (74, .5), (79, 1), (81, .5), (79, .5), (78, .5), (76, .5)],
    [(76, 1), (72, .5), (76, .5), (81, 1), (79, .5), (76, .5)],
    [(79, .5), (76, .5), (72, .5), (76, .5), (74, 1), (72, 1)],
    [(74, 2), (None, 1), (74, .5), (76, .5)],
    [(79, 1), (78, .5), (76, .5), (71, 1), (76, 1)],
    [(72, .5), (74, .5), (76, 1), (79, 1), (76, 1)],
    [(74, 1.5), (71, .5), (67, 1), (71, 1)],
    [(69, .5), (71, .5), (74, 1), (78, 1.5), (None, .5)],
    [(79, 1), (81, .5), (79, .5), (76, 1), (72, 1)],
    [(74, .5), (76, .5), (78, 1), (81, 1), (78, 1)],
    [(79, 2), (74, 1), (71, 1)],
    [(74, 1), (None, 1), (66, .5), (67, .5), (69, 1)],
]


def song_town(stems=False):
    r = RNG(5001)
    beat = 60.0 / 128.0
    bar = 4 * beat
    L = N(16 * bar)                      # 30 s
    S = Song(L, N(8))
    sd = 6000
    pattern = [(0.0, True, 0.80, 0.85), (1.0, True, 0.52, 0.40), (1.5, False, 0.42, 0.35),
               (2.5, False, 0.48, 0.40), (3.0, True, 0.58, 0.40), (3.5, False, 0.42, 0.35)]
    for b, nm in enumerate(TOWN_PROG):
        root, gv, _ = TOWN_CH[nm]
        for bt, down, v, offb in pattern:
            sd += 10
            t0 = (b * 4 + bt) * beat + r.normal(0, 0.004)
            strum(S, 'gtr', max(0.0, t0), gv, down, float(np.clip(v + r.normal(0, 0.04), 0.2, 1.0)), offb * beat, sd)
        sd += 1
        S.add('bass', b * bar, pan(pluck(root, 0.85, sd, 'bass', dur=beat + 0.4, off=0.85 * beat), 0.0))
        sd += 1
        S.add('bass', b * bar + 2 * beat, pan(pluck(root + 7, 0.7, sd, 'bass', dur=beat + 0.4, off=0.85 * beat), 0.0))
        if b % 2 == 1:
            sd += 1
            S.add('bass', b * bar + 3.5 * beat, pan(pluck(root + 12, 0.45, sd, 'bass', dur=0.5 * beat + 0.4,
                                                          off=0.45 * beat), 0.0))
        # hand drums: low on 1 and 3, slaps on 2 and 4, ghosts on the off-beats
        for bt, v, f0, d, sl, p in ((0, 0.80, 105, 0.5, 0.25, -0.1), (2, 0.60, 105, 0.5, 0.25, -0.1),
                                    (3.5, 0.30, 120, 0.4, 0.3, -0.1), (1, 0.50, 190, 0.3, 0.7, 0.15),
                                    (3, 0.50, 190, 0.3, 0.7, 0.15), (1.5, 0.20, 175, 0.25, 0.7, 0.15)):
            if bt == 1.5 and b % 2 == 0:
                continue
            sd += 1
            S.add('drum', (b * 4 + bt) * beat + r.normal(0, 0.003), pan(hand_drum(v, sd, f0, d, sl), p))
        for bt in (1, 3):
            sd += 1
            S.add('tamb', (b * 4 + bt) * beat + r.normal(0, 0.003), pan(tamb(0.6, sd), 0.4))
        for e, v in enumerate([0.55, 0.3, 0.45, 0.3, 0.55, 0.3, 0.45, 0.35]):
            sd += 1
            S.add('shk', (b * 4 + 0.5 * e) * beat + r.normal(0, 0.004), pan(shaker(v, sd), -0.45))
    for k, (nm, st, d) in enumerate(spans_of(TOWN_PROG, 4)):
        S.add('pad', st * beat, pad_chord(TOWN_CH[nm][2], d * beat + 0.2, 600 + k, att=0.5, rel=0.9, bright=0.45))
    notes = melody_notes(TOWN_MEL, beat, 4, r, base_vel=0.74, legato=0.86)
    S.add('flute', 0.0, pan(flute(notes, S.n, 111, vib_rate=5.4, vib_depth=0.0035), 0.12))
    dbl = melody_notes(TOWN_MEL[8:], beat, 4, r, base_vel=0.45, start_bar=8, legato=1.0)
    for t0, d, m, v in dbl:
        sd += 1
        S.add('harp', t0, pan(pluck(m, v, sd, 'harp'), -0.2))
    bir = body_ir()
    pre = {'gtr': lambda x: conv_circ(x, bir)}
    lv = {'gtr': 0.28, 'bass': 0.45, 'pad': 0.10, 'flute': 0.30, 'harp': 0.42, 'drum': 0.55,
          'tamb': 0.30, 'shk': 0.35}
    sends = {'gtr': 0.3, 'bass': 0.05, 'pad': 0.5, 'flute': 0.45, 'harp': 0.4, 'drum': 0.2, 'tamb': 0.25,
             'shk': 0.25}
    return mixdown(S, lv, sends, ir6('town'), 0.55, -22.5, pre=pre, stems=stems)


# ------------------------------- meadow -----------------------------------
MEADOW_CH = {
    'D': [50, 57, 62, 66, 69, 74], 'G': [43, 50, 55, 59, 62, 67], 'A': [45, 52, 57, 61, 64, 69],
    'Bm': [47, 54, 59, 62, 66, 71], 'Em': [40, 47, 52, 55, 59, 64], 'Asus': [45, 52, 57, 62, 64, 69],
}
MEADOW_BASS = {'D': 38, 'G': 43, 'A': 45, 'Bm': 47, 'Em': 40, 'Asus': 45}
MEADOW_PROG = ['D', 'G', 'D', 'A', 'Bm', 'G', 'Em', 'A', 'G', 'D', 'G', 'A', 'Bm', 'G', 'Asus', 'A']
MEADOW_MEL = [
    [(None, 2), (69, 1)], [(74, 2), (71, 1)], [(69, 1.5), (66, .5), (69, 1)], [(76, 3)],
    [(74, 2), (78, 1)], [(79, 1.5), (78, .5), (76, 1)], [(74, 1), (71, 1), (67, 1)], [(69, 3)],
    [(71, 1.5), (74, .5), (79, 1)], [(78, 2), (74, 1)], [(76, 1.5), (74, .5), (71, 1)], [(73, 2), (69, 1)],
    [(71, 1.5), (74, .5), (78, 1)], [(79, 2), (76, 1)], [(74, 1.5), (76, .5), (74, 1)], [(73, 2), (None, 1)],
]


def song_meadow(stems=False):
    r = RNG(5101)
    beat = 60.0 / 96.0
    bar = 3 * beat
    L = N(16 * bar)                      # 30 s
    S = Song(L, N(10))
    sd = 7000
    pat = [0, 1, 2, 3, 4, 2]
    velp = [0.72, 0.45, 0.52, 0.48, 0.50, 0.42]
    for b, nm in enumerate(MEADOW_PROG):
        vc = MEADOW_CH[nm]
        for e in range(6):
            m = vc[pat[e]]
            t0 = (b * 3 + 0.5 * e) * beat + r.normal(0, 0.006)
            v = float(np.clip(velp[e] + r.normal(0, 0.04), 0.2, 1.0))
            sd += 1
            S.add('harp', max(0.0, t0), pan(pluck(m, v, sd, 'harp'), -0.45 + 0.025 * (m - 43)))
        sd += 1
        S.add('bass', b * bar, pan(pluck(MEADOW_BASS[nm], 0.55, sd, 'bass', dur=bar + 0.5, off=bar - 0.1), 0.0))
        if 4 <= b <= 15:
            sd += 1
            S.add('drum', b * bar + r.normal(0, 0.004), pan(hand_drum(0.50, sd, 95, 0.6, 0.15), -0.1))
            sd += 1
            S.add('drum', (b * 3 + 2) * beat + r.normal(0, 0.004), pan(hand_drum(0.22, sd, 140, 0.35, 0.5), -0.05))
    for k, (nm, st, d) in enumerate(spans_of(MEADOW_PROG, 3)):
        vc = MEADOW_CH[nm]
        S.add('pad', st * beat, pad_chord([vc[1], vc[2], vc[3]], d * beat + 0.4, 700 + k, att=1.0, rel=1.5, bright=0.45))
    notes = melody_notes(MEADOW_MEL, beat, 3, r, base_vel=0.70)
    S.add('flute', 0.0, pan(flute(notes, S.n, 122, vib_rate=5.0, vib_depth=0.004, breath=1.1), 0.15))
    tt = 2.2
    while tt < L / SR - 0.5:                         # birds across the field
        S.add('bird', tt, pan(bird_phrase(int(r.integers(1 << 30))) * r.uniform(0.5, 1.0), float(r.uniform(-0.85, 0.85))))
        tt += 3.5 + r.uniform(-1.0, 2.0)
    S.bus['air'] = np.concatenate([S5.wind(L, 7101), np.zeros((2, S.n - L))], axis=1)
    lv = {'harp': 0.50, 'bass': 0.30, 'pad': 0.20, 'flute': 0.26, 'drum': 0.30, 'bird': 0.05, 'air': 0.02}
    sends = {'harp': 0.45, 'bass': 0.1, 'pad': 0.6, 'flute': 0.55, 'drum': 0.3, 'bird': 1.2, 'air': 0.3}
    return mixdown(S, lv, sends, ir6('meadow'), 0.6, -23.0, stems=stems)


# -------------------------------- cave ------------------------------------
CAVE_CH = {'Am': [45, 52, 57, 60], 'F': [41, 48, 53, 57], 'Dm': [38, 45, 50, 53], 'E': [40, 47, 52, 56]}


def song_cave(stems=False):
    r = RNG(5201)
    L = N(30.0)
    S = Song(L, N(10))
    for k, (nm, st) in enumerate((('Am', 0.0), ('F', 7.5), ('Dm', 15.0), ('E', 22.5))):
        S.add('pad', st, pad_chord(CAVE_CH[nm], 7.5 + 0.5, 800 + k, att=3.0, rel=3.5, bright=0.32, nh=5))
    for t0, m in ((1.5, 76), (8.2, 70), (14.0, 69), (20.5, 72), (25.8, 64)):
        S.add('bell', t0, pan(cave_bell(mhz(m), int(r.integers(1 << 30))) * r.uniform(0.7, 1.0), float(r.uniform(-0.6, 0.6))))
        if r.random() < 0.6:
            S.add('bell', t0 + r.uniform(1.8, 2.6),
                  pan(0.3 * cave_bell(mhz(m + 12), int(r.integers(1 << 30)), 5.0), float(r.uniform(-0.8, 0.8))))
    tt = 0.6
    while tt < 29.6:                                  # drips: irregular, some in pairs
        sd = int(r.integers(1 << 30))
        S.add('drip', tt, pan(drip(sd) * r.uniform(0.4, 1.0), float(r.uniform(-0.8, 0.8))))
        if r.random() < 0.3:
            S.add('drip', tt + r.uniform(0.15, 0.4), pan(0.5 * drip(sd + 1), float(r.uniform(-0.8, 0.8))))
        tt += r.uniform(0.7, 3.0)
    for t0 in (0.0, 15.0):
        S.add('boom', t0, pan(hand_drum(0.55, 5210 + int(t0), 46, 1.6, 0.0), 0.0))
    S.bus['drone'] = np.concatenate([drone(L, 5202), np.zeros((2, S.n - L))], axis=1)
    air = periodic_texture(L, 5203, [(70, 40, 2, 1.0), (150, 70, 3, 0.55), (420, 60, 2, 0.12), (900, 35, 3, 0.06)])
    S.bus['air'] = np.concatenate([air, np.zeros((2, S.n - L))], axis=1)
    pre = {'pad': lambda x: eq(x, [('lp', 1400, 0.6)], circular=True)}
    lv = {'pad': 0.30, 'drone': 0.05, 'air': 0.06, 'drip': 0.10, 'bell': 0.06, 'boom': 0.40}
    sends = {'pad': 0.6, 'drone': 0.3, 'air': 0.3, 'drip': 2.0, 'bell': 2.0, 'boom': 1.0}
    return mixdown(S, lv, sends, ir6('cave'), 0.75, -23.0, pre=pre, stems=stems)


# -------------------------------- story -----------------------------------
STORY_CH = {
    'Em': [40, 47, 52, 55, 59, 64], 'C': [36, 43, 48, 52, 55, 60], 'G': [43, 50, 55, 59, 62, 67],
    'D': [38, 45, 50, 54, 57, 62], 'Am': [45, 52, 57, 60, 64, 69], 'B': [47, 54, 59, 63, 66, 71],
    'Bsus': [47, 54, 59, 64, 66, 71],
}
STORY_PROG = ['Em', 'C', 'G', 'D', 'Em', 'Am', 'C', 'B', 'Am', 'C', 'Bsus', 'B']
STORY_CELLO = [40, 48, 43, 50, 52, 45, 48, 47, 45, 48, 47, 47]
STORY_MEL = [
    [(None, 1), (67, 1), (71, 1)], [(76, 2), (74, .5), (72, .5)], [(71, 2), (67, 1)], [(69, 1.5), (71, .5), (69, 1)],
    [(67, 1), (71, 1), (76, 1)], [(76, 1.5), (72, .5), (69, 1)], [(67, 1.5), (69, .5), (72, 1)], [(71, 3)],
    [(72, 1.5), (71, .5), (69, 1)], [(67, 1), (64, 1), (67, 1)], [(66, 1.5), (64, .5), (66, 1)], [(63, 2), (None, 1)],
]


def song_story(stems=False):
    r = RNG(5301)
    beat = 60.0 / 72.0
    bar = 3 * beat
    L = N(12 * bar)                      # 30 s
    S = Song(L, N(10))
    sd = 8000
    pat = [0, 2, 3, 4, 3, 2]
    velp = [0.62, 0.38, 0.42, 0.40, 0.36, 0.32]
    for b, nm in enumerate(STORY_PROG):
        vc = STORY_CH[nm]
        for e in range(6):
            m = vc[pat[e]]
            t0 = (b * 3 + 0.5 * e) * beat + r.normal(0, 0.008)
            v = float(np.clip(velp[e] + r.normal(0, 0.04), 0.2, 1.0))
            sd += 1
            S.add('harp', max(0.0, t0), pan(pluck(m, v, sd, 'harp'), -0.45 + 0.025 * (m - 40)))
        S.add('str', b * bar, string_pad(vc[1:5], bar + 0.3, 900 + b, att=1.1, rel=1.6))
    for k, (nm, st, d) in enumerate(spans_of(STORY_PROG, 3)):
        vc = STORY_CH[nm]
        S.add('pad', st * beat, pad_chord([vc[2], vc[3], vc[4]], d * beat + 0.3, 950 + k, att=1.0, rel=1.5, bright=0.4))
    cello = [(b * bar + 0.03, bar * 0.97, STORY_CELLO[b], 0.75) for b in range(4, 12)]
    S.add('cello', 0.0, pan(bowed(cello, S.n, 8101), -0.25))
    notes = melody_notes(STORY_MEL, beat, 3, r, base_vel=0.72)
    S.add('flute', 0.0, pan(flute(notes, S.n, 133, vib_rate=4.8, vib_depth=0.004, breath=1.2), 0.18))
    S.add('chime', 0.0, pan(glass_note(N(3.0), mhz(88), 8201), 0.3))
    S.add('chime', 6 * bar, pan(0.7 * glass_note(N(3.0), mhz(83), 8202), -0.3))
    lv = {'harp': 0.30, 'str': 0.55, 'pad': 0.10, 'cello': 0.20, 'flute': 0.24, 'chime': 0.06}
    sends = {'harp': 0.5, 'str': 0.6, 'pad': 0.6, 'cello': 0.45, 'flute': 0.55, 'chime': 1.5}
    return mixdown(S, lv, sends, ir6('story'), 0.6, -23.0, stems=stems)


# --------------------------------------------------------------------------
NEW_SFX = {
    'bow': sfx_bow, 'magic': sfx_magic, 'boom': sfx_boom, 'wolf': sfx_wolf, 'howl': sfx_howl,
    'boar': sfx_boar, 'bat': sfx_bat, 'golem': sfx_golem, 'meow': sfx_meow, 'bark': sfx_bark, 'eat': sfx_eat,
    'quest': sfx_quest, 'complete': sfx_complete, 'coin': sfx_coin, 'heal': sfx_heal, 'type': sfx_type,
    'page': sfx_page,
}
NEW_MUSIC = {'town': song_town, 'meadow': song_meadow, 'cave': song_cave, 'story': song_story}
SFX = dict(S5.SFX, **NEW_SFX)
MUSIC = dict(S5.MUSIC, **NEW_MUSIC)


def build(root):
    out = os.path.join(root, 'assets', 'sounds')
    os.makedirs(out, exist_ok=True)
    jobs = list(S5.SFX.items()) + list(NEW_SFX.items()) + list(S5.MUSIC.items()) + list(NEW_MUSIC.items())
    for name, fn in jobs:
        x = fn()
        write_wav(os.path.join(out, name + '.wav'), x)
        print('wrote', name, '%.2fs' % (x.shape[1] / SR))


if __name__ == '__main__':
    build(sys.argv[1])
