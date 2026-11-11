#!/usr/bin/env python3
"""Greenhollow sound set, v5.

Every sound and every note of music here is synthesized from scratch with
numpy: Karplus-Strong strings with body resonance, modal (decaying partial)
bars and bells, FM bells, additive flute with breath noise and vibrato,
formant-filtered breath, filtered-noise textures, and a convolution reverb
whose impulse response is itself synthesized (band-wise decaying noise).
No samples, no downloads. All randomness uses fixed seeds, so every run
writes byte-identical files.

    python sound5.py <root>     -> writes <root>/assets/sounds/*.wav
"""
import math
import os
import sys
import wave

import numpy as np

SR = 48000
TAU = 2.0 * math.pi
CEIL = 10 ** (-1.2 / 20.0)          # sample peak ceiling, safely under -1 dBFS


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def N(sec):
    return int(round(sec * SR))


def tvec(n):
    return np.arange(n) / SR


def mhz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def RNG(seed):
    return np.random.default_rng(seed)


def smooth01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def nrm(x, p=1.0):
    m = float(np.max(np.abs(x)))
    return x * (p / m) if m > 0 else x


def pan(mono, p):
    """Constant-power pan, p in [-1, 1]."""
    th = (p + 1.0) * math.pi / 4.0
    return np.vstack([mono * math.cos(th), mono * math.sin(th)]) * math.sqrt(2.0)


def fast_len(n):
    m = max(1, int(n))
    while True:
        k = m
        for p in (2, 3, 5):
            while k % p == 0:
                k //= p
        if k == 1:
            return m
        m += 1


def fit(x, n):
    if x.shape[-1] >= n:
        return x[..., :n].copy()
    pad = [(0, 0)] * (x.ndim - 1) + [(0, n - x.shape[-1])]
    return np.pad(x, pad)


def boxsmooth(x, w):
    w = max(1, int(w))
    if w == 1:
        return x.copy()
    h = w // 2
    xp = np.concatenate([np.full(h, x[0]), x, np.full(w - h, x[-1])])
    cs = np.concatenate([[0.0], np.cumsum(xp)])
    return (cs[w:w + len(x)] - cs[:len(x)]) / w


# --------------------------------------------------------------------------
# filters (RBJ biquads, applied exactly in the frequency domain; and a
# per-sample TPT state-variable filter for time-varying sweeps)
# --------------------------------------------------------------------------
def biquad(kind, f0, q=0.7071, gain_db=0.0):
    A = 10 ** (gain_db / 40.0)
    w0 = TAU * min(f0, 0.45 * SR) / SR
    cw, sw = math.cos(w0), math.sin(w0)
    al = sw / (2.0 * q)
    if kind == 'lp':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'hp':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'bp':
        b = [al, 0.0, -al]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'peak':
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind in ('lowshelf', 'highshelf'):
        sa = 2 * math.sqrt(A) * al
        if kind == 'lowshelf':
            b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw),
                 A * ((A + 1) - (A - 1) * cw - sa)]
            a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw),
                 (A + 1) + (A - 1) * cw - sa]
        else:
            b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw),
                 A * ((A + 1) + (A - 1) * cw - sa)]
            a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw),
                 (A + 1) - (A - 1) * cw - sa]
    else:
        raise ValueError(kind)
    return [v / a[0] for v in b], [1.0, a[1] / a[0], a[2] / a[0]]


def chain_H(spec, freqs):
    z1 = np.exp(-1j * TAU * freqs / SR)
    z2 = z1 * z1
    H = np.ones(len(freqs), dtype=complex)
    for s in spec:
        kind, f0 = s[0], s[1]
        q = s[2] if len(s) > 2 else 0.7071
        g = s[3] if len(s) > 3 else 0.0
        b, a = biquad(kind, f0, q, g)
        H *= (b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)
    return H


def eq(x, spec, pad=None, circular=False):
    """Biquad chain. circular=True filters a periodic (looping) signal exactly."""
    x = np.asarray(x, float)
    n = x.shape[-1]
    m = n if circular else fast_len(n + (N(0.2) if pad is None else pad))
    X = np.fft.rfft(x, m, axis=-1)
    H = chain_H(spec, np.fft.rfftfreq(m, 1.0 / SR))
    return np.fft.irfft(X * H, m, axis=-1)[..., :n]


def svf(x, fc, q, mode='bp'):
    """Zavalishin TPT state-variable filter with per-sample cutoff/Q."""
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, float), (n,))
    q = np.broadcast_to(np.asarray(q, float), (n,))
    g = np.tan(np.pi * np.clip(fc, 20.0, 0.45 * SR) / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    X, A1, A2, A3, K = x.tolist(), a1.tolist(), a2.tolist(), a3.tolist(), k.tolist()
    out = [0.0] * n
    ic1 = ic2 = 0.0
    sel = {'lp': 0, 'bp': 1, 'hp': 2}[mode]
    for i in range(n):
        v3 = X[i] - ic2
        v1 = A1[i] * ic1 + A2[i] * v3
        v2 = ic2 + A2[i] * ic1 + A3[i] * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if sel == 1:
            out[i] = v1 * K[i]
        elif sel == 0:
            out[i] = v2
        else:
            out[i] = X[i] - K[i] * v1 - v2
    return np.array(out)


def onepole_lp(x, fc):
    a = math.exp(-TAU * fc / SR)
    s = 0.0
    out = []
    for v in x.tolist():
        s = (1.0 - a) * v + a * s
        out.append(s)
    return np.array(out)


def conv1(a, b):
    L = fast_len(len(a) + len(b) - 1)
    return np.fft.irfft(np.fft.rfft(a, L) * np.fft.rfft(b, L), L)[:len(a) + len(b) - 1]


def conv_lin(x, ir):
    if x.ndim == 1:
        x = np.vstack([x, x])
    if ir.ndim == 1:
        ir = np.vstack([ir, ir])
    n, m = x.shape[1], ir.shape[1]
    L = fast_len(n + m - 1)
    y = np.fft.irfft(np.fft.rfft(x, L, axis=1) * np.fft.rfft(ir, L, axis=1), L, axis=1)
    return y[:, :n + m - 1]


def conv_circ(x, ir):
    """Circular convolution over the loop length: reverb tails wrap into the head."""
    L = x.shape[1]
    if ir.ndim == 1:
        ir = np.vstack([ir, ir])
    return np.fft.irfft(np.fft.rfft(x, axis=1) * np.fft.rfft(ir, L, axis=1), L, axis=1)


# --------------------------------------------------------------------------
# reverb: synthesized impulse response (decaying noise, per-band RT60,
# early reflections, decorrelated L/R)
# --------------------------------------------------------------------------
def reverb_ir(rt60, length, predelay, seed, hf=0.45, lf=1.15, ramp=0.010,
              early=8, er_span=0.045, lp=9000.0, hp=120.0):
    r = RNG(seed)
    n = N(length)
    t = tvec(n)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    lc = np.log(np.maximum(freqs, 20.0))
    centers = np.log([125.0, 350.0, 900.0, 2200.0, 5000.0, 11000.0])
    W = []
    for i, c in enumerate(centers):
        w = np.zeros_like(freqs)
        if i == 0:
            w[lc <= c] = 1.0
        else:
            lo = centers[i - 1]
            m = (lc > lo) & (lc <= c)
            w[m] = (lc[m] - lo) / (c - lo)
        if i == len(centers) - 1:
            w[lc > c] = 1.0
        else:
            hi = centers[i + 1]
            m = (lc > c) & (lc <= hi)
            w[m] = (hi - lc[m]) / (hi - c)
        W.append(w)
    rts = rt60 * np.geomspace(lf, hf, len(centers))
    ir = np.zeros((2, n))
    for ch in range(2):
        X = np.fft.rfft(r.standard_normal(n))
        acc = np.zeros(n)
        for w, rt in zip(W, rts):
            acc += np.fft.irfft(X * w, n) * np.exp(-6.9078 * t / rt)
        acc *= 1.0 - np.exp(-t / ramp)
        for _ in range(early):
            d = N(r.uniform(0.003, er_span))
            acc[d] += (1 if r.random() < 0.5 else -1) * r.uniform(0.8, 2.5) * (1.0 - d / (N(er_span) + 1.0))
        ir[ch] = acc
    ir = eq(ir, [('lp', lp, 0.6), ('hp', hp, 0.6)], pad=N(0.02))
    ir = np.concatenate([np.zeros((2, N(predelay))), ir], axis=1)
    ir *= 1.0 - smooth01((tvec(ir.shape[1]) - (ir.shape[1] / SR - 0.05)) / 0.05)
    ir /= np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))
    return ir


# --------------------------------------------------------------------------
# sound sources
# --------------------------------------------------------------------------
def modal(n, partials, seed=0, att=0.0006):
    """Sum of exponentially decaying sinusoids: (freq, amp, tau)."""
    t = tvec(n)
    r = RNG(seed)
    y = np.zeros(n)
    for f, a, tau in partials:
        if f <= 0 or f > 0.42 * SR:
            continue
        y += a * np.sin(TAU * f * t + r.uniform(0, TAU)) * np.exp(-t / tau)
    return y * (1.0 - np.exp(-t / att))


def fm_bell(n, f, ratio=3.5, index=1.2, itau=0.12, tau=0.8, att=0.0015):
    t = tvec(n)
    I = index * np.exp(-t / itau)
    y = np.sin(TAU * f * t + I * np.sin(TAU * f * ratio * t)) * np.exp(-t / tau)
    return y * (1.0 - np.exp(-t / att))


def ks(f, dur, seed, t60=2.0, bright=0.5, pos=0.2, s=0.5, tri=0.5):
    """Karplus-Strong plucked string, computed one period at a time.
    The integer delay is tuned exactly by resampling the result."""
    r = RNG(seed)
    Nd = max(2, int(math.floor(SR / f - s)))
    fa = SR / (Nd + s)
    ratio = f / fa
    nout = N(dur)
    total = int(nout * ratio) + Nd + 4
    i = np.arange(Nd)
    apex = max(1, min(Nd - 2, int(pos * Nd)))
    shape = np.interp(i, [0, apex, Nd - 1], [0.0, 1.0, 0.0])
    exc = tri * shape + (1.0 - tri) * r.uniform(-1, 1, Nd)
    fc = 250.0 + 9000.0 * bright ** 2
    exc = onepole_lp(np.concatenate([exc, exc]), fc)[Nd:]
    exc -= exc.mean()
    exc /= np.max(np.abs(exc)) + 1e-12
    g = 10 ** (-3.0 / (t60 * fa))
    buf = np.zeros(total + 1)
    y = buf[1:]
    y[:Nd] = exc
    a = Nd
    while a < total:
        b = min(a + Nd, total)
        m = b - a
        y[a:b] = g * ((1.0 - s) * y[a - Nd:a - Nd + m] + s * buf[a - Nd:a - Nd + m])
        a = b
    out = np.interp(np.arange(nout) * ratio, np.arange(total), y)
    return out * (1.0 - np.exp(-tvec(nout) / 0.0007))


PLUCK = {
    #           t60 base, bright, pos,  s,    tri
    'guitar': (1.7, 0.42, 0.20, 0.50, 0.40),
    'harp':   (2.6, 0.55, 0.32, 0.45, 0.70),
    'bass':   (2.4, 0.22, 0.24, 0.50, 0.55),
    'forest': (3.2, 0.25, 0.16, 0.50, 0.50),
}


def pluck(m, vel, seed, kind='guitar', dur=None, off=None):
    t60b, br, pos, s, tri = PLUCK[kind]
    f = mhz(m)
    t60 = float(np.clip(t60b * (220.0 / f) ** 0.35, 0.6, 5.0))
    d = dur if dur is not None else min(6.0, 1.15 * t60)
    y = ks(f, d, seed, t60=t60, bright=min(0.95, br * (0.65 + 0.55 * vel)), pos=pos, s=s, tri=tri)
    y = nrm(y) * vel
    t = tvec(len(y))
    if off is not None:                 # finger damping (note-off)
        y *= 1.0 - smooth01((t - off) / 0.12)
    y *= 1.0 - smooth01((t - (d - 0.06)) / 0.06)
    return y


def pad_tone(f, n, seed, bright=0.55, det=(-6.0, 5.0), nh=6):
    t = tvec(n)
    r = RNG(seed)
    y = np.zeros(n)
    for dc in det:
        ff = f * 2 ** (dc / 1200.0)
        for k in range(1, nh + 1):
            fk = ff * k
            if fk > 6500:
                break
            y += (bright ** (k - 1)) / k ** 1.4 * np.sin(TAU * fk * t + r.uniform(0, TAU))
    return y / len(det)


def pad_chord(midis, dur, seed, att=0.9, rel=1.4, bright=0.55, nh=6):
    n = N(dur + rel)
    t = tvec(n)
    Lc, Rc = np.zeros(n), np.zeros(n)
    for j, m in enumerate(midis):
        f = mhz(m)
        Lc += pad_tone(f, n, seed * 31 + j, bright, (-7.0, 2.0), nh)
        Rc += pad_tone(f, n, seed * 31 + j + 500, bright, (-2.5, 6.5), nh)
    env = smooth01(t / att) * (1.0 - smooth01((t - dur) / rel))
    return np.vstack([Lc * env, Rc * env]) / len(midis)


def flute(notes, n, seed, vib_rate=5.0, vib_depth=0.0045, breath=1.0, chiff=1.0,
          harm=(1.0, 0.40, 0.15, 0.07, 0.03, 0.012)):
    """Additive flute: harmonic tone + breath noise + onset chiff + delayed vibrato.
    notes: list of (start_s, dur_s, midi, vel), sorted."""
    r = RNG(seed)
    t = tvec(n)
    lf = np.full(n, math.log(mhz(notes[0][2])))
    amp = np.zeros(n)
    tso = np.full(n, 99.0)
    ch = np.zeros(n)
    for ts, d, m, v in notes:
        i0 = N(ts)
        if i0 >= n:
            continue
        lf[i0:] = math.log(mhz(m))
        att = 0.085 - 0.035 * v
        rel = 0.11
        ln = min(n - i0, N(d + rel + 0.02))
        u = tvec(ln)
        e = smooth01(u / att)
        e *= 1.0 - 0.10 * np.clip(u / max(d, 0.2), 0, 1)
        if d > 0.9:
            e *= 1.0 + 0.07 * smooth01((u - 0.25) / (0.6 * d))
        e *= (1.0 - smooth01((u - d) / rel)) * v
        sl = slice(i0, i0 + ln)
        amp[sl] = np.maximum(amp[sl], e)
        tso[sl] = u
        cl = min(ln, N(0.05))
        ch[i0:i0 + cl] += v * np.exp(-u[:cl] / 0.012) * smooth01(u[:cl] / 0.003)
    f = np.exp(boxsmooth(lf, N(0.035)))
    depth = vib_depth * smooth01((tso - 0.2) / 0.5)
    ph_v = TAU * vib_rate * t + 0.8 * np.sin(TAU * 0.17 * t)
    jit = boxsmooth(boxsmooth(r.standard_normal(n), N(0.06)), N(0.06))
    jit *= 0.0010 / (np.std(jit) + 1e-12)
    phase = np.cumsum(TAU * f * (1.0 + depth * np.sin(ph_v) + jit) / SR)
    a = np.clip(amp * (1.0 + 10.0 * depth * np.sin(ph_v - 0.6)), 0.0, None)
    reg = np.minimum(1.0, 700.0 / f)
    y = np.zeros(n)
    for k, h in enumerate(harm, start=1):
        y += h * reg ** (0.6 * (k - 1)) * a ** (1.0 + 0.5 * (k - 1)) * np.sin(k * phase)
    bb = eq(r.standard_normal(n), [('bp', 2400, 0.55), ('lp', 6500)], circular=True)
    nb = eq(r.standard_normal(n), [('lp', 220, 0.6)], circular=True)
    cn = eq(r.standard_normal(n), [('bp', 3200, 0.9)], circular=True)
    bb /= np.std(bb); nb /= np.std(nb); cn /= np.std(cn)
    y += breath * (0.035 * bb * a ** 1.3 + 0.09 * nb * np.sin(phase) * a + 0.10 * chiff * cn * ch)
    return y


def hand_drum(vel, seed, f0=118.0, dur=0.6, slap=0.35):
    n = N(dur)
    t = tvec(n)
    r = RNG(seed)
    ph = np.cumsum(TAU * f0 * (1.0 + 0.10 * np.exp(-t / 0.018)) / SR)
    y = np.zeros(n)
    for rt, a, tau in [(1, 1, .20), (1.594, .55, .10), (2.136, .35, .07), (2.296, .30, .06),
                       (2.653, .18, .045), (2.918, .12, .035), (3.156, .08, .03)]:
        y += a * np.sin(rt * ph + r.uniform(0, TAU)) * np.exp(-t / tau)
    y *= 1.0 - np.exp(-t / 0.0008)
    s = eq(r.standard_normal(n), [('bp', 1400, 0.7), ('lp', 4000)], pad=N(0.02))
    s *= np.exp(-t / 0.007) * smooth01(t / 0.0008)
    y = nrm(y) + slap * vel * nrm(s)
    y *= 1.0 - smooth01((t - (dur - 0.05)) / 0.05)
    return y * vel


def shaker(vel, seed, dur=0.09):
    n = N(dur)
    t = tvec(n)
    x = eq(RNG(seed).standard_normal(n), [('bp', 5000, 0.8), ('lp', 8000), ('hp', 2500)], pad=N(0.01))
    e = smooth01(t / 0.012) * np.exp(-np.maximum(t - 0.012, 0) / 0.025)
    e *= 1.0 - smooth01((t - (dur - 0.02)) / 0.02)
    return nrm(x * e) * vel


# --------------------------------------------------------------------------
# loudness, limiting, finishing, wav
# --------------------------------------------------------------------------
KW = [('hp', 60, 0.5), ('highshelf', 1600, 0.7071, 4.0)]     # rough K-weighting


def st_loud(x, win=0.1):
    k = eq(x, KW, pad=N(0.02))
    p = np.mean(k ** 2, axis=0)
    w = N(win)
    if len(p) <= w:
        return 10 * math.log10(p.mean() + 1e-20)
    cs = np.concatenate([[0.0], np.cumsum(p)])
    return 10 * math.log10(((cs[w:] - cs[:-w]) / w).max() + 1e-20)


def limit(x, ceil, rel=0.06):
    a = np.max(np.abs(x), axis=0)
    w = max(2, N(0.0015))
    gt = np.minimum(1.0, ceil / np.maximum(a, 1e-12))
    padv = np.concatenate([np.ones(w), gt, np.ones(w)])
    gmin = np.lib.stride_tricks.sliding_window_view(padv, 2 * w + 1).min(axis=1)
    gs = boxsmooth(gmin, w)
    gs = np.minimum(gs, gt)
    rc = 1.0 - math.exp(-1.0 / (rel * SR))
    out = []
    g = 1.0
    for v in gs.tolist():
        g = min(v, g + (1.0 - g) * rc)
        out.append(g)
    return x * np.array(out)


def fades(x, fin, fout):
    n = x.shape[-1]
    t = tvec(n)
    e = smooth01(t / fin) * (1.0 - smooth01((t - (n / SR - fout)) / fout))
    e[0] = 0.0
    e[-1] = 0.0
    return x * e


def dc_free(x, fin, fout):
    """Remove DC with a fade-shaped offset, so the ends stay exactly at zero."""
    e = fades(np.ones(x.shape[-1]), fin, fout)
    return x - np.outer(x.sum(axis=1) / e.sum(), e)


def finish_sfx(x, dur, target, fout, fin=0.0015):
    n = N(dur)
    x = fit(np.asarray(x, float), n)
    x = eq(x, [('hp', 35, 0.7), ('highshelf', 9000, 0.7071, -3.0)], pad=N(0.05))
    x = dc_free(fades(x, fin, fout), fin, fout)
    x *= 10 ** ((target - st_loud(x)) / 20.0)
    if np.max(np.abs(x)) > CEIL:
        x = limit(x, CEIL * 0.995)
    return dc_free(fades(x, fin, fout), fin, fout)


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1.0, 1.0).T * 32767.0).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------
# sound effects
# --------------------------------------------------------------------------
IRS = {}


def irs():
    if not IRS:
        IRS['room'] = reverb_ir(0.30, 0.35, 0.003, seed=901, hf=0.5)
        IRS['hall'] = reverb_ir(0.85, 1.0, 0.010, seed=902, hf=0.45)
        IRS['theme'] = reverb_ir(2.1, 3.2, 0.018, seed=903, hf=0.40, lp=8000)
        IRS['forest'] = reverb_ir(4.2, 5.5, 0.035, seed=904, hf=0.32, lp=6500, hp=70)
        IRS['title'] = reverb_ir(2.8, 4.0, 0.022, seed=905, hf=0.42, lp=8500)
    return IRS


def verb(x, name, wet):
    if x.ndim == 1:
        x = pan(x, 0.0)
    return x + wet * conv_lin(x, irs()[name])[:, :x.shape[1]]


def bubble(n, t0, f0, f1, tau, rise=0.03):
    t = tvec(n) - t0
    m = t >= 0
    u = np.where(m, t, 0.0)
    f = f0 * (f1 / f0) ** smooth01(u / rise)
    ph = np.cumsum(TAU * f / SR)
    return np.where(m, np.sin(ph - ph[N(t0)] if N(t0) < n else ph) * np.exp(-u / tau) * (1 - np.exp(-u / 0.0004)), 0.0)


def sfx_hit():
    n = N(0.25)
    t = tvec(n)
    r = RNG(11)
    ti = 0.065
    fc = 380.0 * (2800.0 / 380.0) ** smooth01(t / ti)
    w = svf(r.standard_normal(n), fc, 1.6, 'bp')
    we = smooth01(t / 0.055) ** 2 * np.exp(-np.maximum(t - ti, 0) / 0.02)
    wh = nrm(w * we)
    p = np.clip(t / ti, 0, 1) - 0.5
    th = (p + 1) * np.pi / 4
    out = 0.45 * np.vstack([wh * np.cos(th), wh * np.sin(th)]) * math.sqrt(2)
    i0 = N(ti)
    m = n - i0
    u = tvec(m)
    thump = np.sin(np.cumsum(TAU * (52 + 80 * np.exp(-u / 0.02)) / SR)) * np.exp(-u / 0.075)
    meat = eq(r.standard_normal(m), [('lp', 700, 0.7), ('hp', 90)], pad=N(0.05)) * np.exp(-u / 0.03)
    knock = modal(m, [(170, 1, .06), (285, .7, .04), (430, .45, .03), (690, .25, .02), (1100, .12, .012)], 12)
    smack = eq(r.standard_normal(m), [('bp', 1800, 0.8)], pad=N(0.02)) * np.exp(-u / 0.006)
    imp = nrm(thump) + 0.55 * nrm(meat) + 0.5 * nrm(knock) + 0.16 * nrm(smack)
    imp = np.tanh(1.6 * imp * (1 - np.exp(-u / 0.0008)))
    out[:, i0:] += pan(imp, 0.05)
    return finish_sfx(verb(out, 'room', 0.12), 0.25, -16.0, 0.05)


def sfx_kill():
    n = N(0.45)
    t = tvec(n)
    r = RNG(21)
    thump = np.sin(np.cumsum(TAU * (46 + 60 * np.exp(-t / 0.03)) / SR)) * np.exp(-t / 0.09)
    sq = svf(r.standard_normal(n), 320 + 2200 * np.exp(-t / 0.05), 5.0, 'bp')
    sq *= smooth01(t / 0.006) * np.exp(-t / 0.07)
    u2 = np.maximum(t - 0.055, 0)
    sq2 = svf(r.standard_normal(n), 250 + 900 * np.exp(-u2 / 0.06), 7.0, 'bp')
    sq2 *= smooth01((t - 0.05) / 0.01) * np.exp(-u2 / 0.06)
    pop = bubble(n, 0.008, 380, 1100, 0.025)
    out = pan(0.8 * nrm(thump) + 0.75 * nrm(sq) + 0.45 * nrm(sq2) + 0.5 * nrm(pop), 0.0)
    for j in range(10):
        t0 = r.uniform(0.07, 0.32)
        f0 = r.uniform(600, 1500)
        b = bubble(n, t0, f0, f0 * r.uniform(1.3, 1.8), r.uniform(0.008, 0.02), rise=0.02)
        out += pan(b * r.uniform(0.10, 0.28) * math.exp(-(t0 - 0.07) / 0.15), r.uniform(-0.6, 0.6))
    out = np.tanh(1.3 * out)
    return finish_sfx(verb(out, 'room', 0.15), 0.45, -16.0, 0.08)


def formant_gain(f, formants):
    g = np.zeros_like(f)
    for F, bw, a in formants:
        g += a / (1.0 + ((f - F) / (bw / 2.0)) ** 2)
    return g


def sfx_hurt():
    n = N(0.30)
    t = tvec(n)
    r = RNG(31)
    thud = np.sin(np.cumsum(TAU * (60 + 70 * np.exp(-t / 0.02)) / SR)) * np.exp(-t / 0.08)
    body = eq(r.standard_normal(n), [('lp', 400, 0.7)], pad=N(0.05)) * np.exp(-t / 0.04)
    cloth = eq(r.standard_normal(n), [('bp', 1200, 0.7)], pad=N(0.02)) * np.exp(-t / 0.03)
    hit = (nrm(thud) + 0.5 * nrm(body) + 0.2 * nrm(cloth)) * (1 - np.exp(-t / 0.0008))
    # breathy grunt: glottal harmonics + aspiration through "uh" formants
    t0 = 0.025
    u = np.maximum(t - t0, 0)
    f0 = (150.0 - 35.0 * smooth01(u / 0.18)) * (1 + 0.006 * np.sin(TAU * 23 * u))
    ph = np.cumsum(TAU * f0 / SR)
    fm = [(620, 180, 1.0), (1150, 220, 0.45), (2450, 300, 0.22), (3400, 400, 0.08)]
    voice = np.zeros(n)
    for k in range(1, 40):
        fk = k * f0
        voice += (1.0 / k) * formant_gain(fk, fm) * np.sin(k * ph)
    freqs = np.fft.rfftfreq(fast_len(n + N(0.05)), 1.0 / SR)
    asp = np.fft.irfft(np.fft.rfft(r.standard_normal(n), len(freqs) * 2 - 2) *
                       (formant_gain(freqs, fm) + 0.01), len(freqs) * 2 - 2)[:n]
    ge = smooth01((t - t0) / 0.014) * np.exp(-u / 0.07) * (1 - smooth01((t - 0.24) / 0.05))
    ae = smooth01((t - t0) / 0.01) * np.exp(-u / 0.09) * (1 - smooth01((t - 0.26) / 0.04))
    grunt = 0.55 * nrm(voice) * ge + 0.6 * nrm(asp) * ae
    grunt = eq(grunt, [('lp', 3800, 0.6)], pad=N(0.02))
    out = pan(0.9 * hit, 0.0) + pan(0.75 * grunt, 0.08)
    return finish_sfx(verb(out, 'room', 0.10), 0.30, -16.0, 0.04)


def glass_note(n, f, seed):
    return (0.75 * fm_bell(n, f, ratio=1.0, index=0.9, itau=0.05, tau=0.30) +
            0.35 * modal(n, [(f * 2.756, 0.5, 0.09), (f * 5.404, 0.2, 0.04), (f * 0.5, 0.12, 0.2)], seed))


def sfx_pickup():
    n = N(0.4)
    a = glass_note(n, mhz(81), 41)
    b = glass_note(n, mhz(88), 42)
    i = N(0.075)
    out = pan(0.8 * a, -0.15)
    out[:, i:] += pan(1.0 * b[:n - i], 0.15)
    out = eq(out, [('highshelf', 6000, 0.7, -4.0)], pad=N(0.05))
    return finish_sfx(verb(out, 'room', 0.25), 0.40, -15.5, 0.10)


def mallet(n, f, seed, tau=0.045, ratios=((1, 1, 1.0), (3.99, .22, .27), (9.0, .05, .11)), contact=0.0015):
    r = RNG(seed)
    parts = [(f * q, a, tau * dk) for q, a, dk in ratios]
    y = modal(n, parts, seed, att=contact)
    t = tvec(n)
    c = eq(r.standard_normal(n), [('lp', 2000, 0.7)], pad=N(0.01)) * np.exp(-t / 0.003)
    return y + 0.08 * nrm(c)


def sfx_talk():
    n = N(0.12)
    y = mallet(n, mhz(69), 51, tau=0.042)
    y = eq(y, [('lp', 3500, 0.6), ('peak', 440, 1.0, 2.0)], pad=N(0.02))
    return finish_sfx(verb(pan(y, 0.0), 'room', 0.08), 0.12, -17.5, 0.035, fin=0.002)


def sfx_menu_move():
    n = N(0.06)
    t = tvec(n)
    y = modal(n, [(1150, 1, .009), (2500, .35, .005), (600, .45, .012)], 61, att=0.0005)
    c = eq(RNG(62).standard_normal(n), [('lp', 4000, 0.7)], pad=N(0.01)) * np.exp(-t / 0.0015)
    y = eq(y + 0.15 * nrm(c), [('lp', 5000, 0.6)], pad=N(0.01))
    return finish_sfx(pan(y, 0.0), 0.06, -18.0, 0.02, fin=0.001)


def sfx_menu_select():
    n = N(0.25)
    a = mallet(n, mhz(74), 71, tau=0.11)
    b = mallet(n, mhz(81), 72, tau=0.12)
    t = tvec(n)
    warm = np.sin(TAU * mhz(62) * t) * np.exp(-t / 0.08) * (1 - np.exp(-t / 0.004))
    i = N(0.055)
    out = pan(0.8 * a + 0.35 * warm, -0.1)
    out[:, i:] += pan(0.9 * b[:n - i], 0.1)
    out = eq(out, [('lp', 4500, 0.6)], pad=N(0.02))
    return finish_sfx(verb(out, 'room', 0.18), 0.25, -16.5, 0.07)


def sfx_pause():
    n = N(0.35)
    t = tvec(n)
    r = RNG(81)
    nz = svf(r.standard_normal(n), 180 + 1600 * np.exp(-t / 0.07), 0.9, 'lp')
    nz *= smooth01(t / 0.025) * np.exp(-np.maximum(t - 0.025, 0) / 0.11)
    sub = np.sin(np.cumsum(TAU * (60 + 35 * np.exp(-t / 0.05)) / SR))
    sub *= smooth01(t / 0.01) * np.exp(-t / 0.12)
    f = mhz(62)
    i = N(0.03)
    ch = np.zeros(n)
    ch[i:] = modal(n - i, [(f, 1, .25), (2.003 * f, .3, .12), (2.41 * f, .15, .08), (3.97 * f, .06, .05)], 82, att=0.003)
    ch = eq(ch, [('lp', 1500, 0.6)], pad=N(0.02))
    out = pan(0.8 * nrm(nz) + 0.7 * nrm(sub), 0.0) + pan(0.45 * nrm(ch), 0.05)
    return finish_sfx(verb(out, 'room', 0.15), 0.35, -16.5, 0.08)


def handbell(n, f, seed):
    parts = [(f, 1, .5), (2.01 * f, .35, .25), (3.0 * f, .22, .15), (4.2 * f, .08, .08), (5.43 * f, .05, .05)]
    return modal(n, parts, seed, att=0.0015) + 0.15 * fm_bell(n, f, ratio=3.5, index=0.6, itau=0.04, tau=0.3)


def sfx_save():
    n = N(0.8)
    t = tvec(n)
    r = RNG(91)
    out = np.zeros((2, n))
    for t0, a in ((0.0, 0.35), (0.06, 0.25)):         # quill taps
        i = N(t0)
        m = n - i
        u = tvec(m)
        tap = eq(r.standard_normal(m), [('bp', 3200, 1.2)], pad=N(0.01)) * np.exp(-u / 0.004) * smooth01(u / 0.0005)
        tap = nrm(tap) + 0.6 * nrm(modal(m, [(1900, 1, .006), (2650, .6, .004)], 92 + i))
        out[:, i:] += pan(a * tap, -0.2)
    for t0, mm, a, p in ((0.11, 71, 0.75, -0.1), (0.27, 76, 0.85, 0.1), (0.43, 83, 0.40, 0.2)):
        i = N(t0)
        out[:, i:] += pan(a * handbell(n - i, mhz(mm), 93 + i), p)
    out = eq(out, [('highshelf', 5000, 0.7, -3.0)], pad=N(0.05))
    out = fit(verb(out, 'hall', 0.22), n)
    return finish_sfx(out, 0.8, -15.5, 0.15)


def sfx_skill():
    n = N(1.0)
    t = tvec(n)
    r = RNG(101)
    swell = smooth01(t / 0.5) ** 1.6
    env = swell * np.exp(-np.maximum(t - 0.55, 0) / 0.25)
    bright = 0.25 + 0.55 * swell
    pad = np.zeros(n)
    for j, m in enumerate((57, 64, 69, 71, 73)):
        f = mhz(m)
        for dc in (-5.0, 4.0):
            ff = f * 2 ** (dc / 1200)
            for k in range(1, 7):
                if ff * k > 7000:
                    break
                pad += bright ** (k - 1) / k ** 1.3 * np.sin(TAU * ff * k * t + r.uniform(0, TAU))
    pad = nrm(pad) * env
    air = svf(r.standard_normal(n), 600 * (4000 / 600) ** smooth01(t / 0.55), 2.0, 'bp')
    air = nrm(air) * env
    shim = np.zeros(n)
    for m in (88, 93, 97):
        shim += np.sin(TAU * mhz(m) * t + r.uniform(0, TAU)) * (1 + 0.5 * np.sin(TAU * r.uniform(6, 8) * t))
    shim = nrm(shim) * env * smooth01((t - 0.15) / 0.4)
    out = pan(0.55 * pad, 0.0) + pan(0.22 * air, -0.2) + pan(0.10 * shim, 0.3)
    i = N(0.52)
    bell = 0.8 * fm_bell(n - i, mhz(81), 3.5, 1.2, 0.08, 0.45) + 0.4 * glass_note(n - i, mhz(81), 102)
    out[:, i:] += pan(0.55 * bell, 0.1)
    i2 = N(0.60)
    out[:, i2:] += pan(0.28 * fm_bell(n - i2, mhz(88), 3.5, 1.0, 0.06, 0.35), -0.25)
    out = eq(out, [('highshelf', 6000, 0.7, -4.0)], pad=N(0.05))
    out = fit(verb(out, 'hall', 0.3), n)
    return finish_sfx(out, 1.0, -15.0, 0.2, fin=0.005)


def sfx_levelup():
    n = N(1.5)
    t = tvec(n)
    r = RNG(111)
    out = np.zeros((2, n))
    notes = (62, 66, 69, 74, 78, 81, 86)
    times = (0.0, 0.07, 0.14, 0.21, 0.28, 0.35, 0.45)
    for j, (m, t0) in enumerate(zip(notes, times)):
        i = N(t0)
        v = 0.6 + 0.06 * j
        y = pluck(m, v, 112 + j, 'harp', dur=(n - i) / SR)
        out[:, i:] += pan(y[:n - i], -0.45 + 0.15 * j)
    i = N(0.0)
    out += pan(0.5 * pluck(50, 0.7, 120, 'harp', dur=1.5)[:n], -0.2)
    shim = np.zeros(n)
    for m in (86, 90, 93, 98):
        shim += np.sin(TAU * mhz(m) * t + r.uniform(0, TAU)) * (1 + 0.6 * np.sin(TAU * r.uniform(5.5, 8.0) * t))
    shim = nrm(shim) * smooth01((t - 0.25) / 0.5) * np.exp(-np.maximum(t - 0.8, 0) / 0.4)
    out += pan(0.06 * shim, 0.25)
    for _ in range(14):                                  # sparkle grains
        t0 = r.uniform(0.3, 1.1)
        i = N(t0)
        f = mhz(int(r.choice([86, 88, 90, 93, 95, 98])))
        g = modal(n - i, [(f, 1, 0.06), (f * 2.76, 0.2, 0.02)], int(r.integers(1 << 30)))
        out[:, i:] += pan(g * 0.07 * math.exp(-(t0 - 0.3) / 0.5), r.uniform(-0.7, 0.7))
    out = eq(out, [('highshelf', 6000, 0.7, -3.0)], pad=N(0.05))
    out = fit(verb(out, 'hall', 0.3), n)
    return finish_sfx(out, 1.5, -15.0, 0.3)


def sfx_door():
    n = N(0.6)
    t = tvec(n)
    r = RNG(121)
    imp = np.zeros(n)
    tc, end = 0.004, 0.36
    while tc < end:
        x = tc / end
        rate = 48 + 70 * math.sin(math.pi * x) ** 0.8 + 18 * math.sin(TAU * 3.3 * x)
        a = float(smooth01(x / 0.12) * (1 - smooth01((x - 0.8) / 0.2))) * (0.55 + 0.45 * r.random())
        imp[N(tc)] += a
        tc += (1.0 / rate) * (1 + 0.10 * r.standard_normal())
    body = modal(N(0.06), [(540, 1, .016), (830, .7, .014), (1210, .8, .011), (1760, .5, .008),
                           (2480, .3, .006), (3350, .15, .004)], 122)
    creak = conv1(imp, body)[:n]
    fr = eq(r.standard_normal(n), [('bp', 900, 0.8)], pad=N(0.02)) * boxsmooth(imp, N(0.02)) * 20
    creak = nrm(creak) + 0.15 * nrm(fr)
    i = N(0.40)
    m = n - i
    u = tvec(m)
    thud = modal(m, [(92, 1, .09), (155, .7, .06), (232, .5, .045), (380, .3, .03), (610, .15, .02)], 123, att=0.0008)
    click = eq(r.standard_normal(m), [('lp', 1200, 0.7)], pad=N(0.02)) * np.exp(-u / 0.012)
    close = nrm(thud) + 0.35 * nrm(click)
    j = N(0.425)
    latch = modal(n - j, [(2100, .5, .010), (3350, .3, .006), (1450, .4, .012)], 124)
    out = pan(0.55 * creak, -0.25)
    out[:, i:] += pan(1.0 * close, 0.05)
    out[:, j:] += pan(0.25 * latch, 0.15)
    out = fit(verb(out, 'room', 0.18), n)
    return finish_sfx(out, 0.6, -16.0, 0.08)


def sfx_step():
    n = N(0.12)
    t = tvec(n)
    r = RNG(131)
    dirt = eq(r.standard_normal(n), [('lp', 350, 0.7)], pad=N(0.03)) * smooth01(t / 0.002) * np.exp(-t / 0.018)
    sub = np.sin(TAU * 75 * t) * np.exp(-t / 0.015) * (1 - np.exp(-t / 0.002))
    gr = np.zeros((2, n))
    gl = N(0.0012)
    win = np.hanning(gl)
    for _ in range(40):
        t0 = 0.003 + r.exponential(0.02)
        if t0 > 0.09:
            continue
        i = N(t0)
        g = r.standard_normal(gl) * win * r.uniform(0.2, 1.0) * math.exp(-t0 / 0.03)
        p = r.uniform(-0.3, 0.3)
        gr[:, i:i + gl] += pan(g, p)[:, :min(gl, n - i)]
    gr = eq(gr, [('bp', 3500, 0.8), ('lp', 7000)], pad=N(0.01))
    dirt = boxsmooth(dirt, N(0.0015))           # round off the heel transient
    # a soft, low footfall: mostly the dull thud, a little grit, and quiet, since it plays three times a second
    out = pan(0.6 * nrm(dirt) + 0.18 * nrm(sub), 0.0) + 0.1 * nrm(gr)
    return finish_sfx(out, 0.12, -30.0, 0.025)


# --------------------------------------------------------------------------
# music engine
# --------------------------------------------------------------------------
class Song:
    """Events are rendered into loop-length buses plus a tail; at the end the
    tail is folded back onto the head, so the last bars ring into the first."""

    def __init__(self, L, tail):
        self.L = L
        self.n = L + tail
        self.bus = {}

    def add(self, bus, t, x):
        if x.ndim == 1:
            x = pan(x, 0.0)
        b = self.bus.setdefault(bus, np.zeros((2, self.n)))
        i = max(0, N(t))
        m = min(x.shape[1], self.n - i)
        if m > 0:
            b[:, i:i + m] += x[:, :m]

    def looped(self, name):
        b = self.bus[name]
        out = b[:, :self.L].copy()
        rest = b[:, self.L:]
        while rest.shape[1] > 0:
            m = min(self.L, rest.shape[1])
            out[:, :m] += rest[:, :m]
            rest = rest[:, m:]
        return out

    def mix(self, levels, sends, ir, wet=1.0, pre=None):
        L = self.L
        dry = np.zeros((2, L))
        snd = np.zeros((2, L))
        for name, lv in levels.items():
            if name not in self.bus:
                continue
            x = self.looped(name)
            if pre and name in pre:
                x = pre[name](x)
            dry += lv * x
            snd += lv * sends.get(name, 0.0) * x
        return dry + wet * conv_circ(snd, ir)


def body_ir():
    n = N(0.12)
    y = modal(n, [(98, .5, .02), (204, .6, .025), (290, .3, .02), (390, .35, .015), (560, .2, .012)], 7, att=0.0003)
    y = 0.35 * y / np.sqrt(np.sum(y ** 2) + 1e-12)
    y[0] += 1.0
    return y


def periodic_hz(f, L):
    """Round a frequency so it completes a whole number of cycles per loop."""
    T = L / SR
    return max(1, round(f * T)) / T


def finish_music(x, target=-21.0):
    x = eq(x, [('hp', 32, 0.7), ('highshelf', 8500, 0.7071, -3.0), ('lp', 13000, 0.6)], circular=True)
    k = eq(x, KW, circular=True)
    x *= 10 ** ((target - 10 * math.log10(np.mean(k ** 2))) / 20.0)
    th = 0.6
    ax = np.abs(x)
    if ax.max() > th:                    # gentle memoryless knee: keeps the loop circular
        x = np.sign(x) * np.where(ax > th, th + (CEIL - th) * np.tanh((ax - th) / (CEIL - th)), ax)
    # Start the file at a quiet near-zero point 15-90 ms before the first
    # downbeat (a rotation, so the loop stays sample-exact and continuous).
    L = x.shape[1]
    a, b = L - N(0.09), L - N(0.015)
    seg = x[:, a:b]
    prev = x[:, a - 1:b - 1]
    score = np.abs(seg).sum(axis=0) + 0.5 * np.abs(seg - prev).sum(axis=0)
    i = a + int(np.argmin(score))
    return np.roll(x, -i, axis=1)


# ---------------------------- village theme -------------------------------
THEME_CH = {    # bass, guitar voicing, pad voicing
    'Dm':   (38, [50, 57, 62, 65, 69], [53, 57, 62]),
    'C':    (36, [48, 55, 60, 64, 67], [52, 55, 60]),
    'G':    (43, [50, 55, 59, 62, 67], [50, 55, 59]),
    'F':    (41, [48, 53, 57, 60, 65], [53, 57, 60]),
    'Am':   (45, [52, 57, 60, 64, 69], [52, 57, 60]),
    'Em':   (40, [52, 55, 59, 62, 64], [50, 55, 59]),
    'Asus': (45, [52, 57, 62, 64, 69], [52, 57, 62]),
}
THEME_PROG = ['Dm', 'Dm', 'C', 'G', 'Dm', 'F', 'C', 'Am',
              'Dm', 'Dm', 'C', 'G', 'F', 'C', 'Em', 'A~',
              'F', 'C', 'G', 'Dm', 'F', 'C', 'G', 'A~']
THEME_MEL = [
    [(None, 3)], [(None, 2), (69, .5), (72, .5)],
    [(74, 1.5), (72, .5), (69, 1)], [(71, 2), (67, 1)],
    [(69, 1.5), (67, .5), (65, 1)], [(64, 1), (65, 1), (69, 1)],
    [(67, 2), (64, 1)], [(64, 3)],
    [(None, 1), (69, .5), (72, .5), (74, 1)], [(77, 1.5), (76, .5), (74, 1)],
    [(72, 1), (74, 1), (76, 1)], [(74, 2), (71, 1)],
    [(72, 1.5), (69, .5), (65, 1)], [(67, 1), (69, 1), (72, 1)],
    [(71, 1.5), (69, .5), (67, 1)], [(69, 3)],
    [(72, 1.5), (74, .5), (72, 1)], [(76, 2), (74, 1)],
    [(74, 1.5), (71, .5), (67, 1)], [(69, 2), (72, .5), (76, .5)],
    [(77, 1.5), (76, .5), (74, 1)], [(76, 1), (74, 1), (72, 1)],
    [(71, 1.5), (69, .5), (67, 1)], [(69, 2), (None, 1)],
]


def melody_notes(bars, beat, bpb, rng, base_vel=0.72, start_bar=0, legato=0.97):
    out = []
    for b, cells in enumerate(bars):
        pos = 0.0
        for m, d in cells:
            if m is not None:
                v = base_vel + 0.012 * (m - 69) + rng.normal(0, 0.03)
                t0 = ((start_bar + b) * bpb + pos) * beat + rng.normal(0, 0.004)
                out.append((max(0.0, t0), d * beat * legato, m, float(np.clip(v, 0.3, 1.0))))
            pos += d
    return out


def song_theme():
    r = RNG(1001)
    beat = 60.0 / 86.4
    bar = 3 * beat
    L = N(24 * bar)
    S = Song(L, N(10))
    sd = 2000
    for b, name in enumerate(THEME_PROG):
        halves = [('Asus', 'Asus', 'Asus', 'Am', 'Am', 'Am')] if name == 'A~' else [(name,) * 6]
        names = halves[0]
        pat = [0, 2, 3, 4, 3, 2] if b < 16 else [0, 2, 4, 3, 1, 3]
        velp = [0.9, 0.55, 0.68, 0.55, 0.62, 0.5]
        for e in range(6):
            bass, gv, _ = THEME_CH[names[e]]
            m = gv[pat[e]]
            t0 = (b * 3 + 0.5 * e) * beat + r.normal(0, 0.006)
            v = float(np.clip(velp[e] + r.normal(0, 0.05), 0.2, 1.0))
            sd += 1
            S.add('gtr', max(0, t0), pan(pluck(m, v, sd, 'guitar'), -0.45 + 0.02 * (m - 50)))
        bass = THEME_CH[names[0]][0]
        sd += 1
        S.add('bass', b * bar, pan(pluck(bass, 0.85, sd, 'bass', dur=bar + 0.3, off=bar - 0.1), 0.0))
        if b >= 16 and b % 2 == 1:
            sd += 1
            S.add('bass', b * bar + 2 * beat, pan(pluck(bass + 7, 0.5, sd, 'bass', dur=beat + 0.3, off=beat - 0.05), 0.0))
    # pad: merge repeated chords
    spans = []
    for b, name in enumerate(THEME_PROG):
        segs = [('Asus', b * 3, 1.5), ('Am', b * 3 + 1.5, 1.5)] if name == 'A~' else [(name, b * 3, 3)]
        for nm, st, d in segs:
            if spans and spans[-1][0] == nm and abs(spans[-1][1] + spans[-1][2] - st) < 1e-9:
                spans[-1][2] += d
            else:
                spans.append([nm, st, d])
    for k, (nm, st, d) in enumerate(spans):
        S.add('pad', st * beat, pad_chord(THEME_CH[nm][2], d * beat + 0.3, 300 + k, att=0.7, rel=1.2, bright=0.5))
    # flute melody
    notes = melody_notes(THEME_MEL, beat, 3, r)
    S.add('flute', 0.0, pan(flute(notes, S.n, 77), 0.15))
    # hand percussion from bar 3
    for b in range(2, 24):
        sd += 1
        S.add('drum', b * bar + r.normal(0, 0.004), pan(hand_drum(0.75, sd, 112, 0.6, 0.3), -0.1))
        sd += 1
        S.add('drum', (b * 3 + 2.5) * beat, pan(hand_drum(0.32, sd, 150, 0.4, 0.6), -0.05))
        if b >= 16:
            sd += 1
            S.add('drum', (b * 3 + 1.5) * beat, pan(hand_drum(0.22, sd, 140, 0.35, 0.6), -0.15))
        for e, v in enumerate([0.5, 0.3, 0.7, 0.3, 0.6, 0.35]):
            sd += 1
            S.add('shk', (b * 3 + 0.5 * e) * beat + r.normal(0, 0.005), pan(shaker(v, sd), 0.45))
    bir = body_ir()
    pre = {'gtr': lambda x: conv_circ(x, bir)}
    lv = {'gtr': 0.50, 'bass': 0.45, 'pad': 0.20, 'flute': 0.24, 'drum': 0.40, 'shk': 0.40}
    sends = {'gtr': 0.35, 'bass': 0.08, 'pad': 0.55, 'flute': 0.50, 'drum': 0.25, 'shk': 0.3}
    x = S.mix(lv, sends, irs()['theme'], wet=0.6, pre=pre)
    return finish_music(x, -22.5)


# ------------------------------ forest ------------------------------------
FOREST_CH = {
    'Am': [57, 60, 64], 'F': [53, 57, 60], 'Dm': [53, 57, 62], 'Em': [52, 55, 59], 'E': [52, 56, 59],
}
FOREST_PROG = ['Am', 'Am', 'F', 'F', 'Dm', 'Dm', 'Em', 'Em', 'Am', 'Am', 'F', 'E']
FOREST_PLUCK = [   # (bar, beat, midi, vel)
    (0, 0, 45, .8), (0, 1, 69, .7), (0, 2.5, 67, .55),
    (1, 0, 64, .6), (1, 2, 60, .35),
    (2, 0, 41, .75), (2, 1, 65, .65),
    (3, 0, 62, .6), (3, 2.5, 57, .35),
    (4, 0, 38, .75), (4, 1, 64, .6), (4, 2.5, 62, .5),
    (5, 0, 60, .55), (5, 2, 57, .3),
    (6, 0, 40, .75), (6, 1, 59, .5), (6, 2, 62, .45), (6, 3, 64, .4),
    (7, 1, 55, .4),
    (8, 0, 45, .8), (8, 1, 72, .6), (8, 2.5, 71, .5),
    (9, 0, 69, .55), (9, 2, 64, .4),
    (10, 0, 41, .75), (10, 1, 65, .5), (10, 2.5, 60, .4),
    (11, 0, 40, .75), (11, 1, 56, .5), (11, 2, 59, .45), (11, 3, 62, .35),
]


def wind(L, seed):
    r = RNG(seed)
    T = L / SR
    t = tvec(L)
    freqs = np.fft.rfftfreq(L, 1.0 / SR)
    out = np.zeros((2, L))
    layers = [(260, 160, 3, 0.7), (520, 220, 5, 0.8), (880, 300, 7, 0.6), (1500, 600, 4, 0.5), (2600, 1200, 6, 0.3)]
    for ch in range(2):
        for j, (fc, bw, cyc, g) in enumerate(layers):
            mag = np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
            X = (r.standard_normal(len(freqs)) + 1j * r.standard_normal(len(freqs))) * mag
            X[0] = 0
            x = np.fft.irfft(X, L)
            x /= np.std(x)
            ph1, ph2 = r.uniform(0, TAU, 2)
            env = (0.55 + 0.45 * np.sin(TAU * cyc * t / T + ph1)) * (0.75 + 0.25 * np.sin(TAU * (2 * cyc + 1) * t / T + ph2))
            out[ch] += g * x * env ** 1.5 / (1 + j * 0.3)
    return out


def drone(L, seed):
    r = RNG(seed)
    T = L / SR
    t = tvec(L)
    out = np.zeros((2, L))
    for ch in range(2):
        for base, ga in ((mhz(33), 1.0), (mhz(40), 0.6), (mhz(45), 0.35)):
            for dc in (-4.0, 3.0):
                f = base * 2 ** (dc / 1200)
                for k in range(1, 9):
                    fk = periodic_hz(f * k, L)
                    cyc = int(r.integers(1, 4))
                    lfo = 0.6 + 0.4 * np.sin(TAU * cyc * t / T + r.uniform(0, TAU))
                    out[ch] += ga * lfo * (0.8 ** (k - 1)) / k * np.sin(TAU * fk * t + r.uniform(0, TAU))
    return out


def song_forest():
    r = RNG(2001)
    beat = 60.0 / 64.0
    bar = 4 * beat
    L = N(12 * bar)
    S = Song(L, N(10))
    sd = 3000
    for b, bt, m, v in FOREST_PLUCK:
        sd += 1
        t0 = (b * 4 + bt) * beat + r.normal(0, 0.008)
        S.add('pluck', t0, pan(pluck(m, v, sd, 'forest'), float(r.uniform(-0.4, 0.4))))
        if m >= 60 and r.random() < 0.35:          # soft octave echo
            sd += 1
            S.add('pluck', t0 + 1.5 * beat, pan(pluck(m + 12, v * 0.35, sd, 'forest'), float(r.uniform(-0.6, 0.6))))
    spans = []
    for b, nm in enumerate(FOREST_PROG):
        if spans and spans[-1][0] == nm:
            spans[-1][2] += 4
        else:
            spans.append([nm, b * 4, 4])
    for k, (nm, st, d) in enumerate(spans):
        S.add('pad', st * beat, pad_chord(FOREST_CH[nm], d * beat + 0.5, 400 + k, att=2.5, rel=3.0, bright=0.4, nh=5))
    fl = [(17, 3.0, 64), (20.5, 1.5, 62), (22, 2.0, 60), (24.5, 4.0, 59),
          (37, 2.0, 64), (39, 1.0, 65), (40, 2.5, 64), (43, 4.0, 57)]
    notes = [(st * beat, d * beat * 0.97, m, 0.6) for st, d, m in fl]
    S.add('flute', 0.0, pan(flute(notes, S.n, 88, vib_rate=4.6, vib_depth=0.003, breath=1.6), -0.2))
    tt = 1.5
    while tt < 12 * bar - 1.0:                     # distant chimes
        f = mhz(int(r.choice([81, 84, 86, 88, 91])))
        y = modal(N(3.0), [(f, 1, .9), (f * 2.76, .3, .3), (f * 5.40, .1, .12), (f * 0.5, .15, 1.2)], int(r.integers(1 << 30)), att=0.002)
        S.add('chime', tt, pan(y * r.uniform(0.5, 1.0), float(r.uniform(-0.8, 0.8))))
        if r.random() < 0.5:
            y2 = modal(N(3.0), [(f * 1.5, 1, .8), (f * 1.5 * 2.76, .25, .25)], int(r.integers(1 << 30)), att=0.002)
            S.add('chime', tt + 0.35, pan(y2 * 0.4, float(r.uniform(-0.8, 0.8))))
        tt += 4.5 + r.uniform(-1.2, 1.2)
    for b in (0, 4, 8):
        sd += 1
        S.add('drum', b * bar, pan(hand_drum(0.7, sd, 62, 1.0, 0.1), 0.0))
    S.bus['wind'] = np.concatenate([wind(L, 2101), np.zeros((2, S.n - L))], axis=1)
    S.bus['drone'] = np.concatenate([drone(L, 2102), np.zeros((2, S.n - L))], axis=1)
    lv = {'pluck': 0.55, 'pad': 0.20, 'flute': 0.24, 'chime': 0.05, 'drum': 0.35, 'wind': 0.035, 'drone': 0.05}
    sends = {'pluck': 0.6, 'pad': 0.7, 'flute': 0.8, 'chime': 3.0, 'drum': 0.9, 'wind': 0.3, 'drone': 0.2}
    x = S.mix(lv, sends, irs()['forest'], wet=0.7)
    return finish_music(x, -23.0)


# ------------------------------- title ------------------------------------
TITLE_CH = {
    'F':    [41, 48, 53, 57, 60, 65], 'Bb': [46, 53, 58, 62, 65, 70], 'C': [36, 43, 48, 52, 55, 60],
    'Dm':   [38, 45, 50, 53, 57, 62], 'Gm7': [43, 50, 53, 58, 62, 65], 'F/A': [45, 48, 53, 57, 60, 65],
    'Csus': [36, 43, 48, 53, 55, 60],
}
TITLE_PROG = ['F', 'Bb', 'F', 'C', 'Dm', 'Bb', 'Gm7', 'C', 'F', 'Bb', 'F/A', 'Bb', 'Gm7', 'Csus']
TITLE_MEL = [
    [(77, 1.5), (76, .5), (72, 1)], [(74, 2), (70, 1)], [(72, 1.5), (70, .5), (69, 1)], [(67, 2), (None, 1)],
    [(69, 1.5), (72, .5), (74, 1)], [(77, 2), (74, 1)], [(74, 1.5), (72, .5), (70, 1)], [(72, 3)],
    [(77, 1.5), (76, .5), (72, 1)], [(74, 2), (70, 1)], [(72, 1.5), (70, .5), (69, 1)],
    [(74, 1.5), (72, .5), (70, 1)], [(69, 1.5), (70, .5), (67, 1)], [(67, 2), (None, 1)],
]


def song_title():
    r = RNG(3001)
    beat = 60.0 / 72.0
    bar = 3 * beat
    L = N(14 * bar)
    S = Song(L, N(10))
    sd = 4000
    for b, nm in enumerate(TITLE_PROG):
        vc = TITLE_CH[nm]
        for e in range(6):
            m = vc[e] if not (nm == 'Csus' and e >= 3) else [36, 43, 48, 52, 55, 60][e]
            t0 = (b * 3 + 0.5 * e) * beat + r.normal(0, 0.007)
            v = float(np.clip((0.75 if e == 0 else 0.48 - 0.03 * e) + r.normal(0, 0.04), 0.2, 1.0))
            sd += 1
            S.add('harp', max(0.0, t0), pan(pluck(m, v, sd, 'harp'), -0.5 + 0.025 * (m - 41)))
    # harp leads the motif (bars 1-4), doubles the flute softly in bars 9-11
    lead = melody_notes(TITLE_MEL[:4], beat, 3, r, base_vel=0.85, legato=1.0)
    dbl = melody_notes(TITLE_MEL[8:11], beat, 3, r, base_vel=0.45, start_bar=8, legato=1.0)
    for t0, d, m, v in lead + dbl:
        sd += 1
        S.add('harpm', t0, pan(pluck(m, v, sd, 'harp'), 0.1))
    notes = melody_notes(TITLE_MEL[4:], beat, 3, r, base_vel=0.74, start_bar=4)
    S.add('flute', 0.0, pan(flute(notes, S.n, 99, vib_rate=5.2), 0.2))
    spans = []
    for b, nm in enumerate(TITLE_PROG):
        spans.append([nm, b * 3, 3])
    for k, (nm, st, d) in enumerate(spans):
        vc = TITLE_CH[nm]
        S.add('pad', st * beat, pad_chord([vc[0] + 12, vc[3], vc[4]], d * beat + 0.3, 500 + k, att=0.9, rel=1.4, bright=0.45))
    lv = {'harp': 0.34, 'harpm': 0.80, 'flute': 0.22, 'pad': 0.20}
    sends = {'harp': 0.45, 'harpm': 0.45, 'flute': 0.55, 'pad': 0.6}
    x = S.mix(lv, sends, irs()['title'], wet=0.6)
    return finish_music(x, -23.0)


# --------------------------------------------------------------------------
SFX = {
    'hit': sfx_hit, 'kill': sfx_kill, 'hurt': sfx_hurt, 'pickup': sfx_pickup, 'talk': sfx_talk,
    'levelup': sfx_levelup, 'door': sfx_door, 'menu_move': sfx_menu_move,
    'menu_select': sfx_menu_select, 'pause': sfx_pause, 'save': sfx_save, 'skill': sfx_skill,
    'step': sfx_step,
}
MUSIC = {'theme': song_theme, 'forest': song_forest, 'title': song_title}


def build(root):
    out = os.path.join(root, 'assets', 'sounds')
    os.makedirs(out, exist_ok=True)
    for name, fn in list(SFX.items()) + list(MUSIC.items()):
        x = fn()
        write_wav(os.path.join(out, name + '.wav'), x)
        print('wrote', name, '%.2fs' % (x.shape[1] / SR))


if __name__ == '__main__':
    build(sys.argv[1])
