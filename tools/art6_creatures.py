# Greenhollow's creatures, pets and small effects, painted the way art4 paints: wobbling ink, flat coats of gouache,
# a dusk light from the upper left (light coat top-left, darker coat low and to the right), simple dot eyes with a glint.
# Every creature faces right and stands on a fixed ground line inside its frame. Run: python3 art6_creatures.py <out_dir>
import json, math, os, random, sys, time, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import art4 as C
import art2 as P

INK = C.INK
GLINT = '#f2ead8'
def sd(*a): return zlib.crc32(repr(a).encode()) & 0xffff

# ---- geometry
def mid(a, b, t=.5): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
def rot1(p, a, o):
    c, s = math.cos(a), math.sin(a); x, y = p[0]-o[0], p[1]-o[1]
    return (o[0]+x*c-y*s, o[1]+x*s+y*c)
def rot(pts, a, o): return [rot1(p, a, o) for p in pts]
def ell(cx, cy, rx, ry, n=10, a0=0.0):
    return [(cx+math.cos(a0+2*math.pi*i/n)*rx, cy+math.sin(a0+2*math.pi*i/n)*ry) for i in range(n)]
def limb(path, widths):
    "An outline around a thick polyline: the shape of a leg, a tail, an arm. Rounded caps at both ends."
    p = np.array(path, float); w = np.array(widths, float)/2
    d = np.gradient(p, axis=0); l = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)[:, None]; d = d/l
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    L = p+n*w[:, None]; R = p-n*w[:, None]
    e0 = p[0]-d[0]*w[0]*.8; e1 = p[-1]+d[-1]*w[-1]*.8
    return [tuple(e0)]+[tuple(q) for q in L]+[tuple(e1)]+[tuple(q) for q in R[::-1]]
def ik(root, tgt, a, b, side):
    "Two-bone joint: where the knee goes so that the paw lands on its mark. side +1 bends back, -1 forward."
    dx, dy = tgt[0]-root[0], tgt[1]-root[1]; d = math.hypot(dx, dy)
    if d >= a+b-.01: return mid(root, tgt, a/(a+b))
    ca = (a*a+d*d-b*b)/(2*a*max(d, 1e-6)); A = math.acos(max(-1, min(1, ca))); ang = math.atan2(dy, dx)+side*A
    return (root[0]+math.cos(ang)*a, root[1]+math.sin(ang)*a)
def leafpts(b, ang, L, W):
    "A pointed leaf (or a leaf-shaped ear) from base b along screen angle ang."
    d = (math.cos(ang), math.sin(ang)); n = (-d[1], d[0])
    P_ = lambda t, w: (b[0]+d[0]*L*t+n[0]*W*w, b[1]+d[1]*L*t+n[1]*W*w)
    return [P_(0, -.55), P_(.33, -1), P_(.72, -.72), P_(1, 0), P_(.72, .72), P_(.33, 1), P_(0, .55)]

class Pen:
    "Draws on an art4 Sheet in local units: origin on the ground under the creature, x right, y up is negative, scaled by k."
    def __init__(s, sheet, ox, oy, k=1.0):
        s.s = sheet; s.ox, s.oy, s.k = ox, oy, k; s.lk = .55+.45*k
    def T(s, pts): return [(s.ox+x*s.k, s.oy+y*s.k) for x, y in pts]
    def shape(s, pts, col, lw=2.6, wob=.8, smooth=True): return s.s.shape(s.T(pts), col, lw*s.lk, wob, smooth)
    def fill(s, pts, col, clip=None, wob=.8, alpha=255, smooth=True):
        p = s.s.curve(s.T(pts), True, wob) if smooth else s.s.rough(s.T(pts), wob)
        return s.s.fill(p, col, alpha, clip)
    def stroke(s, pts, w=2.2, col=INK, wob=.5, clip=None, alpha=255): s.s.stroke(s.T(pts), w*s.lk, col, wob, clip, alpha)
    def outline(s, pts, w=2.4, col=INK, wob=.6, clip=None):
        s.s.line(s.s.curve(s.T(pts), True, wob), w*s.lk, col, closed=True, taper=False, clip=clip)

def eye(pn, x, y, r=1.0, shut=False, glint=GLINT):
    if shut:
        pn.stroke([(x-4*r, y+1.5*r), (x, y-2.5*r), (x+4*r, y+1.5*r)], 2.4*max(r, .7), wob=.15); return
    pn.fill([(x-4*r, y+1*r), (x, y-6*r), (x+4*r, y+1*r), (x, y+8*r)], INK, wob=.12)
    pn.fill([(x-2.2*r, y-1*r), (x-.4*r, y-3.4*r), (x+.8*r, y-1.2*r), (x-1*r, y+.8*r)], glint, wob=0)
def heart(pn, x, y, r, col='#c24a5a'):
    p, m = pn.shape([(x, y-r*.35), (x-r*.55, y-r*.95), (x-r*1.05, y-r*.6), (x-r*.9, y), (x, y+r*.85), (x+r*.9, y), (x+r*1.05, y-r*.6), (x+r*.55, y-r*.95)], col, lw=2.2, wob=.3)
    pn.fill([(x-r*.8, y-r*.55), (x-r*.55, y-r*.8), (x-r*.3, y-r*.6), (x-r*.6, y-r*.25)], '#ec9c92', clip=m, wob=0)
def puff(pn, x, y, r, rng, col='#8c8172', light='#b3a891'):
    p, m = pn.shape(ell(x, y, r, r*.72, 9, rng.uniform(0, 1)), col, lw=2.2, wob=1.2)
    pn.fill(ell(x-r*.3, y-r*.35, r*.6, r*.4, 7), light, clip=m, wob=.6)

def frame_strip(frames, fw, fh):
    out = np.zeros((fh, fw*len(frames), 4), dtype=np.uint8)
    for i, f in enumerate(frames): P.over(out, f, i*fw, 0)
    return out
def grid(rows, fw, fh):
    out = np.zeros((fh*len(rows), fw*max(len(r) for r in rows), 4), dtype=np.uint8)
    for j, row in enumerate(rows):
        for i, f in enumerate(row): P.over(out, f, i*fw, j*fh)
    return out

# =====================================================================================  slime
SLIME_LOOKS = [('#3f9a8d', '#266f70', '#8ed1b4'), ('#4f78b4', '#2f4c86', '#a6c6ea'), ('#ad424c', '#71263a', '#e9a093')]
SLIME_BASE = 101
def slime(look, i):
    "art4's jelly, recoloured, its face turned to the right; frame 0 rest, 1 squash, 2 stretch."
    col, dk, li = SLIME_LOOKS[look]
    rx, ry, cy = [(12, 10, 18), (14, 7.4, 20.2), (10, 12.6, 15.4)][i]
    s = C.Sheet(120, 120, sd('slime', look, i)); k = 3.75; rx, ry, cy = rx*k, ry*k, cy*k; base = SLIME_BASE; cx = 60
    pts = [(cx-rx, base), (cx-rx*1.02, cy+ry*.1), (cx-rx*.66, cy-ry*.76), (cx, cy-ry), (cx+rx*.66, cy-ry*.76), (cx+rx*1.02, cy+ry*.1), (cx+rx, base), (cx+rx*.5, base+5), (cx, base+1), (cx-rx*.5, base+5)]
    p, m = s.shape(pts, col, lw=3.6, wob=1.1)
    s.fill(s.curve([(cx+rx*.05, cy+ry), (cx+rx*.8, cy-ry*.4), (cx+rx*1.3, cy), (cx+rx*1.2, base+8), (cx-rx*.8, base+8), (cx-rx, base-rx*.12)], True, 2), dk, clip=m)
    s.fill(s.curve([(cx-rx*.74, cy-ry*.3), (cx-rx*.5, cy-ry*.74), (cx-rx*.08, cy-ry*.84), (cx-rx*.3, cy-ry*.5), (cx-rx*.6, cy-ry*.05)], True, 1), li, clip=m)
    # a few drops of jelly left on the ground when it squashes
    if i == 1:  # a couple of drops of jelly squeezed out at its feet
        for x, r_ in ((cx-rx*.62, 3.2), (cx+rx*.7, 2.6)): s.shape([(x-r_, base+9), (x, base+9-r_*1.6), (x+r_, base+9), (x, base+10.5)], dk, lw=1.8, wob=.2)
    pn = Pen(s, 0, 0)
    ey = cy-ry*.08; e1, e2 = cx+rx*.02, cx+rx*.5; mx = (e1+e2)/2
    for ex, sc in ((e1, 1.6), (e2, 1.4)): eye(pn, ex, ey, sc)
    if look == 2:
        # angry: brows pulled down toward the middle, a frown and one small fang
        s.stroke([(e1-11, ey-17), (e1-2, ey-14), (e1+8, ey-9)], 4.2, wob=.2); s.stroke([(e2-8, ey-9), (e2+2, ey-14), (e2+10, ey-18)], 4.2, wob=.2)
        s.stroke([(mx-10, ey+21), (mx, ey+15), (mx+10, ey+21)], 2.6, wob=.2)
        s.shape([(mx+2, ey+16.5), (mx+7, ey+18.5), (mx+5, ey+24)], '#efe6cc', lw=1.6, wob=0)
    else:
        s.stroke([(mx-8, ey+16), (mx, ey+19+i), (mx+8, ey+16)], 2.4)
        s.fill(s.curve([(e1-14, ey+10), (e1-8, ey+8), (e1-5, ey+12), (e1-11, ey+14)], True, .3), '#e08a86' if look == 0 else '#c98ab0', alpha=150, clip=m)
    return s.done(.05)
def slime_sheet(): return grid([[slime(l, i) for i in range(3)] for l in range(3)], 120, 120)

# =====================================================================================  hopper
# The meadow hopper: a round fawn-coloured hopper with leaf-shaped ears, a sprig of leaves on its crown and a ringed, curled tail.
HOP = dict(base='#bb8b58', dark='#8a5e3a', light='#e2bb83', cream='#efe0c0', ear='#d79c86', far='#8a5e3a',
           leaf='#5b8a46', leafd='#3c6234', leafl='#a2c466', ring='#5e3e2a')
HOP_BASE = 108
HOP_POSES = [  # idle 0-1, hop 2-5
    dict(lift=0, sq=1.0, t=0, ear=.12, hind=(-6, -5), fore=(17, -4), tail=0),
    dict(lift=0, sq=.965, t=.02, ear=.22, hind=(-6, -5), fore=(17, -4), tail=.12),
    dict(lift=0, sq=.84, t=.07, ear=.5, hind=(-4, -5), fore=(15, -4), tail=-.12),       # crouch
    dict(lift=8, sq=1.1, t=-.38, ear=.75, hind=(-30, -5), fore=(18, -32), tail=.3),     # launch: hind feet still pushing on the ground
    dict(lift=15, sq=1.0, t=-.04, ear=.55, hind=(-12, -21), fore=(27, -22), tail=.18),   # in the air, legs tucked
    dict(lift=1, sq=.9, t=.2, ear=.22, hind=(-16, -13), fore=(24, -4), tail=-.2),        # landing on the forepaws
]
def hopper(i):
    po = HOP_POSES[i]; c = HOP
    s = C.Sheet(120, 120, sd('hopper', i)); pn = Pen(s, 62, HOP_BASE)
    sq, t, lift = po['sq'], po['t'], po['lift']
    rx, ry = 24/math.sqrt(sq), 19*sq; bx = -6; by = -8-ry-lift; Bc = (bx, by)
    r = lambda p: rot1(p, t, Bc)
    hc = r((bx+21, by-13*sq)); hx, hy = hc
    ear_t = po['ear']-t
    def ear(base, scale, col, inner):
        a = -math.pi/2-ear_t*scale
        q = leafpts(base, a, 30*scale, 7*scale); pp, mm = pn.shape(q, col, lw=2.6, wob=.5)
        pn.fill(leafpts(mid(base, q[3], .12), a, 30*scale*.8, 3.2*scale), inner, clip=mm, wob=.3)
        pn.stroke([mid(base, q[3], .25), mid(base, q[3], .85)], 1.3, c['dark'], clip=mm, wob=.2)
    # far ear and far feet, behind everything
    ear((hx+3, hy-11), .92, c['dark'], '#a8705c')
    hf = po['hind']; ff = po['fore']
    pn.shape(ell(hf[0]+7, hf[1]-1, 10, 4.6, 8), c['far'], lw=2.4, wob=.4)
    pn.shape(ell(ff[0]+5, ff[1]-1, 5.4, 4, 7), c['far'], lw=2.2, wob=.3)
    # the ringed tail, curled up behind
    tr = r((bx-rx*.85, by+2)); ta = po['tail']-t*.5
    path = rot([tr, (tr[0]-11, tr[1]-1), (tr[0]-19, tr[1]-11), (tr[0]-18, tr[1]-24), (tr[0]-10, tr[1]-29)], ta, tr)
    tp, tm = pn.shape(limb(path, [9, 13, 13.5, 11, 7]), c['cream'], lw=2.6, wob=.6)
    for k in range(1, 5):
        a_, b_ = path[k-1], path[k]; m_ = mid(a_, b_, .55); d = (b_[0]-a_[0], b_[1]-a_[1]); l = math.hypot(*d); n = (-d[1]/l, d[0]/l)
        pn.stroke([(m_[0]+n[0]*9, m_[1]+n[1]*9), (m_[0]-n[0]*9, m_[1]-n[1]*9)], 4.6, c['ring'], clip=tm, wob=.3)
    pn.fill([(tr[0]-30, tr[1]+4), (tr[0]-8, tr[1]+2), (tr[0]+4, tr[1]+10), (tr[0]-30, tr[1]+14)], '#c9b48e', clip=tm, alpha=200)
    # body
    bp, bm = pn.shape(rot(ell(bx, by, rx, ry, 10, .3), t, Bc), c['base'], lw=3.2, wob=.8)
    pn.fill(rot([(bx-rx*1.3, by+ry*.25), (bx, by+ry*.42), (bx+rx*1.3, by+ry*.05), (bx+rx*1.3, by+ry*1.6), (bx-rx*1.3, by+ry*1.6)], t, Bc), c['dark'], clip=bm)
    pn.fill(rot([(bx-rx*.75, by-ry*.3), (bx-rx*.35, by-ry*.82), (bx+rx*.2, by-ry*.88), (bx-rx*.15, by-ry*.55), (bx-rx*.6, by-ry*.05)], t, Bc), c['light'], clip=bm)
    pn.fill(rot([(bx+rx*.35, by+ry*.05), (bx+rx*.95, by-ry*.1), (bx+rx*.9, by+ry*.75), (bx+rx*.4, by+ry*.8)], t, Bc), c['cream'], clip=bm)
    # near haunch, hind foot and forepaw
    th = r((bx-rx*.42, by+ry*.25))
    pn.shape(limb([th, (hf[0]-2, hf[1]-3)], [12, 7]), c['base'], lw=2.4, wob=.4)
    fp, fm = pn.shape(ell(hf[0], hf[1], 11.5, 5, 8), c['base'], lw=2.6, wob=.4)
    pn.fill(ell(hf[0]+3, hf[1]+3, 11, 3.5, 7), c['dark'], clip=fm, wob=.2)
    for dx in (6, 9.5): pn.stroke([(hf[0]+dx, hf[1]-3), (hf[0]+dx+.8, hf[1]+1.5)], 1.2, wob=.1)
    hp, hm = pn.shape(rot(ell(th[0], th[1], 12, 12.5*sq, 9, .5), t, th), c['base'], lw=2.6, wob=.6)
    pn.fill(ell(th[0]+5, th[1]+7, 12, 10, 8), c['dark'], clip=hm)
    fr = r((bx+rx*.55, by+ry*.45))
    pn.shape(limb([fr, (ff[0]-1, ff[1]-2)], [8.5, 6]), c['base'], lw=2.4, wob=.4)
    pn.shape(ell(ff[0]+1.5, ff[1]-1, 5.6, 4, 7), c['base'], lw=2.4, wob=.3)
    # head
    hd = rot([(hx-14, hy+3), (hx-11, hy-10), (hx+1, hy-15), (hx+12, hy-10), (hx+18, hy+1), (hx+15, hy+8), (hx+4, hy+12), (hx-9, hy+11)], t*.6, hc)
    hp_, hm_ = pn.shape(hd, c['base'], lw=3, wob=.6)
    pn.fill([(hx-16, hy+7), (hx+4, hy+8), (hx+20, hy+2), (hx+22, hy+16), (hx-16, hy+16)], c['dark'], clip=hm_)
    pn.fill([(hx-10, hy-6), (hx-5, hy-12), (hx+3, hy-13), (hx-2, hy-8), (hx-8, hy-2)], c['light'], clip=hm_)
    pn.fill([(hx+6, hy+3), (hx+16, hy), (hx+19, hy+6), (hx+9, hy+11)], c['cream'], clip=hm_)
    ear((hx-3, hy-12), 1.0, c['base'], c['ear'])
    # the sprig of leaves on its crown
    for a, L, col in ((-1.15, 13, c['leaf']), (-2.1, 10, c['leafl'])):
        q = leafpts((hx+2, hy-13), a, L, 4); _, lm = pn.shape(q, col, lw=1.9, wob=.2)
        pn.stroke([(hx+2, hy-13), q[3]], 1, c['leafd'], clip=lm, wob=.1)
    eye(pn, hx+6, hy-3, .9)
    pn.fill(ell(hx+17.5, hy+2, 2.6, 2, 6), '#b8606a', wob=.1)
    pn.stroke([(hx+15, hy+6), (hx+12, hy+7.5)], 1.4, '#5e3528', wob=.1)
    pn.fill(ell(hx+3, hy+6, 3.6, 2.2, 6), '#d98a7a', alpha=150, clip=hm_, wob=.2)
    return s.done(.05)
def hopper_sheet(): return frame_strip([hopper(i) for i in range(6)], 120, 120)

# =====================================================================================  four-legged engine (wolf, boar, cat, dog)
def quad(pn, sp, po):
    c = sp['col']; t = po.get('tilt', 0); dy = po.get('dy', 0); X = po.get('dx', 0)
    H0 = (sp['hip'][0]+X, sp['hip'][1]+dy); S0 = (sp['sho'][0]+X, sp['sho'][1]+dy)
    piv = H0 if po.get('pivot') == 'hip' else mid(H0, S0)
    H = rot1(H0, t, piv); S = rot1(S0, t, piv); M = mid(H, S); ct, st = math.cos(t), math.sin(t)
    B = lambda p, o: (p[0]+o[0]*ct-o[1]*st, p[1]+o[0]*st+o[1]*ct)
    rr, sr, R = sp['rr'], sp['sr'], sp['R']
    A = (S[0]+sp['neck'][0]+po.get('hx', 0), S[1]+sp['neck'][1]+po.get('hy', 0))
    legs = po.get('legs', [(0, 0)]*4)  # far hind, far front, near hind, near front: (dx, lift) from rest
    rest = [sp['hip'][0]+sp['hpx']+sp['farx'], sp['sho'][0]+sp['fpx']+sp['farx'], sp['hip'][0]+sp['hpx'], sp['sho'][0]+sp['fpx']]
    roots = [B(H, (sp['farx'], rr*.05)), B(S, (sp['farx'], sr*.2)), B(H, (0, rr*.2)), B(S, (0, sr*.35))]
    def leg(i, col, pcol):
        hind = i in (0, 2); dx, lift = legs[i]; paw = (rest[i]+X+dx, -lift); pw = sp['pw']; w = sp['lw']
        a, b = (sp['ha'], sp['hb']) if hind else (sp['fa'], sp['fb'])
        top = (paw[0], paw[1]-pw*.7); j = ik(roots[i], top, a, b, 1 if hind else -1)
        path = [roots[i], mid(roots[i], j, .5), j, top]
        wid = [rr*1.25, rr*.72, w*1.05, w*.84] if hind else [sr*.95, sr*.56, w, w*.84]
        pp, mm = pn.shape(limb(path, wid), col, lw=2.4, wob=.5)
        if i >= 2:  # the far edge of the near leg turned from the light
            pn.fill(limb([(x+w*.62, y+1) for x, y in path], [v*.62 for v in wid]), c['dark'], clip=mm, wob=.4)
        if sp.get('hoof'):
            pn.shape([(paw[0]-pw*.9, paw[1]-pw*1.3), (paw[0]+pw*.9, paw[1]-pw*1.3), (paw[0]+pw*1.2, paw[1]), (paw[0]-pw*.9, paw[1])], sp['hoof'], lw=2.2, wob=.3, smooth=False)
        else:
            pn.shape(ell(paw[0]+pw*.45, paw[1]-pw*.62, pw*1.15, pw*.64, 8), pcol, lw=2.2, wob=.3)
    tail_front = po.get('tailmode') == 'wrap'
    if not tail_front: sp['tail'](pn, sp, po, B(H, (-rr*.8, -rr*.35)))
    leg(0, c['far'], c['far']); leg(1, c['far'], c['far'])
    nape = (A[0]-R*.62, A[1]-R*.02); throat = (A[0]+R*.18, A[1]+R*.72)
    pts = [B(H, (-rr, rr*.15)), B(H, (-rr*.55, -rr*.82)), B(M, (0, -sp['back'])), B(S, (-sr*.35, -sr*.95)), nape, throat,
           B(S, (sr*.85, sr*.3)), B(S, (sr*.35, sr*sp.get('chest', .9))), B(M, (0, sp['belly'])), B(H, (rr*.45, rr*.82)), B(H, (-rr*.6, rr*.75))]
    bp, bm = pn.shape(pts, c['base'], lw=3*sp.get('lwk', 1), wob=.8)
    pn.fill([B(H, (-rr*1.5, rr*.3)), B(M, (0, sp['belly']*.25)), B(S, (sr*1.4, sr*.25)), B(S, (sr*1.4, sr*2.4)), B(H, (-rr*1.5, rr*2.4))], c['dark'], clip=bm)
    pn.fill([B(H, (-rr*.7, -rr*.5)), B(M, (0, -sp['back']-3)), B(S, (-sr*.3, -sr*1.05)), B(S, (sr*.15, -sr*.6)), B(M, (0, -sp['back']+sr*.38))], c['light'], clip=bm)
    if c.get('cream'):
        pn.fill([B(S, (sr*.2, -sr*.3)), throat, B(S, (sr*1.1, sr*.3)), B(S, (sr*.5, sr*1.1)), B(S, (-sr*.25, sr*.7))], c['cream'], clip=bm)
    if sp.get('decor'): sp['decor'](pn, sp, po, B, H, S, M, bm)
    leg(2, c['base'], c['base']); leg(3, c['base'], c['base'])
    if tail_front: sp['tail'](pn, sp, po, B(H, (-rr*.8, -rr*.35)))
    if sp.get('collar'):
        cc = sp['collar']; a_ = (A[0]-R*.62, A[1]+R*.15); b_ = (A[0]+R*.28, A[1]+R*.78)
        pn.shape(limb([a_, b_], [R*.32, R*.32]), cc, lw=2, wob=.3)
        if sp.get('tag'): pn.shape(ell(b_[0]-R*.05, b_[1]+R*.3, R*.2, R*.2, 7), sp['tag'], lw=1.8, wob=.1)
    sp['head'](pn, sp, po, A)
    return dict(H=H, S=S, A=A)

def sit_quad(pn, sp, po):
    "Sitting: haunches on the ground, chest upright on straight forelegs, tail curled round the feet."
    c = sp['col']; rr, sr, R = sp['rr'], sp['sr'], sp['R']; hip, sho = sp['hip'], sp['sho']
    Hs = (hip[0]+9, -rr*.98); Cs = (sho[0]-3, sho[1]-sr*.55)
    A = (Cs[0]+sp['neck'][0]-1+po.get('hx', 0), Cs[1]+sp['neck'][1]-1+po.get('hy', 0))
    nape = (A[0]-R*.62, A[1]-R*.02); throat = (A[0]+R*.18, A[1]+R*.72)
    fl = (Cs[0]+2, Cs[1]+sr*.4)
    def foreleg(dxr, col, near):
        root = (fl[0]+dxr, fl[1]-2); paw = (fl[0]+dxr+3, 0); top = (paw[0], -sp['pw']*.7)
        p, m = pn.shape(limb([root, mid(root, top), top], [sr*.85, sp['lw']*1.05, sp['lw']*.86]), col, lw=2.4, wob=.4)
        if near: pn.fill(limb([(root[0]+sp['lw']*.6, root[1]), (top[0]+sp['lw']*.55, top[1])], [sr*.5, sp['lw']*.5]), c['dark'], clip=m, wob=.3)
        pn.shape(ell(paw[0]+sp['pw']*.45, -sp['pw']*.62, sp['pw']*1.15, sp['pw']*.64, 8), col, lw=2.2, wob=.3)
    foreleg(sp['farx'], c['far'], False)
    pts = [(Hs[0]-rr*1.15, Hs[1]+rr*.35), (Hs[0]-rr*.95, Hs[1]-rr*.7), (mid(Hs, Cs)[0]-sr*.55, mid(Hs, Cs)[1]-2), (Cs[0]-sr*.75, Cs[1]-sr*.45),
           nape, throat, (Cs[0]+sr*.8, Cs[1]+sr*.35), (Cs[0]+sr*.55, Cs[1]+sr*1.3), (Hs[0]+rr*1.2, -rr*.35), (Hs[0]+rr*.4, -1), (Hs[0]-rr*.7, -1.5)]
    bp, bm = pn.shape(pts, c['base'], lw=3*sp.get('lwk', 1), wob=.7)
    pn.fill([(Hs[0]-rr*.2, Hs[1]+rr*.4), (Cs[0]+sr*.2, Cs[1]+sr*.7), (Cs[0]+sr*1.4, Cs[1]), (Cs[0]+sr*1.4, 4), (Hs[0]-rr*.2, 4)], c['dark'], clip=bm)
    pn.fill([(Hs[0]-rr*.9, Hs[1]-rr*.4), (Cs[0]-sr*.7, Cs[1]-sr*.3), (Cs[0]-sr*.2, Cs[1]-sr*.6), (Cs[0]-sr*.3, Cs[1]+sr*.2), (Hs[0]-rr*.5, Hs[1])], c['light'], clip=bm)
    if c.get('cream'): pn.fill([(Cs[0]+sr*.1, Cs[1]-sr*.2), throat, (Cs[0]+sr*.95, Cs[1]+sr*.3), (Cs[0]+sr*.6, Cs[1]+sr*1.3), (Cs[0]-sr*.1, Cs[1]+sr*.8)], c['cream'], clip=bm)
    if sp['kind'] == 'cat' and sp['age'] > 0:
        for k in range(2 if sp['age'] == 1 else 3):
            q = mid((Hs[0]-rr*.95, Hs[1]-rr*.55), (Cs[0]-sr*.75, Cs[1]-sr*.3), .2+k*.3)
            pn.stroke([(q[0]-2, q[1]), (q[0]+5, q[1]+1.5), (q[0]+8, q[1]+4)], 2.2, c['stripe'], clip=bm, wob=.2)
    if sp['kind'] == 'dog':
        pn.fill([(Hs[0]-rr*1.3, Hs[1]-rr*.2), (Hs[0]-rr*.6, Hs[1]-rr*1.1), (Cs[0]-sr*.9, Cs[1]-sr*.2), (Cs[0]-sr*.2, Cs[1]+sr*.4), (Hs[0], Hs[1])], c['patch'], clip=bm, wob=1)
    # the near haunch and hind foot
    hp, hm = pn.shape(ell(Hs[0]+1, Hs[1]+1, rr*1.02, rr*.92, 9, .4), c['base'], lw=2.6, wob=.5)
    pn.fill(ell(Hs[0]+rr*.6, Hs[1]+rr*.7, rr, rr*.8, 8), c['dark'], clip=hm)
    if sp['kind'] == 'dog' and sp['age'] > 0: pn.fill(ell(Hs[0]-rr*.4, Hs[1]-rr*.5, rr*.8, rr*.6, 8), c['patch'], clip=hm, wob=.6)
    pn.shape(ell(Hs[0]+rr*.95, -sp['pw']*.62, sp['pw']*1.5, sp['pw']*.66, 8), c['base'], lw=2.2, wob=.3)
    sp['tail'](pn, sp, dict(po, tailmode='wrap'), (Hs[0]-rr*.8, Hs[1]+rr*.3))
    foreleg(0, c['base'], True)
    if sp.get('collar'):
        a_ = (A[0]-R*.62, A[1]+R*.15); b_ = (A[0]+R*.28, A[1]+R*.78)
        pn.shape(limb([a_, b_], [R*.32, R*.32]), sp['collar'], lw=2, wob=.3)
        if sp.get('tag'): pn.shape(ell(b_[0]-R*.05, b_[1]+R*.3, R*.2, R*.2, 7), sp['tag'], lw=1.8, wob=.1)
    sp['head'](pn, sp, po, A)
    return dict(A=A)

def H_(A, ha, R):
    c, s = math.cos(ha), math.sin(ha)
    return lambda pts: [(A[0]+(x*c-y*s)*R, A[1]+(x*s+y*c)*R) for x, y in pts]

# ---- wolf
WOLF = dict(base='#7c7e8c', dark='#555666', light='#a9aab8', cream='#cdc7b6', far='#4c4d5c', inner='#3b3946', mouth='#5e2430', tooth='#efe6cc')
def wolf_tail(pn, sp, po, root):
    c = sp['col']; a = po.get('tail', 0)
    path = rot([root, (root[0]-9, root[1]+4), (root[0]-18, root[1]+13), (root[0]-24, root[1]+24), (root[0]-25, root[1]+31)], a, root)
    p, m = pn.shape(limb(path, [7, 11, 12, 10, 5]), c['base'], lw=2.6, wob=.7)
    pn.fill([path[2], (path[2][0]+14, path[2][1]+4), (path[4][0]+12, path[4][1]+10), (path[4][0]-12, path[4][1]+10)], c['dark'], clip=m)
    pn.fill(ell(path[4][0], path[4][1], 7, 8, 7), '#3c3c4a', clip=m)
    pn.stroke([mid(path[1], path[2]), mid(path[2], path[3], .7)], 1.3, c['light'], clip=m)
def wolf_head(pn, sp, po, A):
    c = sp['col']; R = sp['R']; ha = po.get('ha', 0); op = po.get('open', 0); er = po.get('ear', 0); h = H_(A, ha, R)
    def ear(dx, col, inner):
        base = (-.25+dx, -.7); q = [(-.62+dx, -.5), (-.55+dx, -1.25), (-.42+dx, -1.95), (-.1+dx, -1.35), (.12+dx, -.78)]
        q = rot(q, -er, base); p, m = pn.shape(h(q), col, lw=2.4, wob=.4)
        pn.fill(h(rot([(-.48+dx, -.75), (-.42+dx, -1.65), (-.2+dx, -.9)], -er, base)), inner, clip=m, wob=.2)
    ear(.5, c['far'], '#2e2d38')
    if op > 0:
        hinge = (.35, .38)
        jaw = rot([(.15, .32), (1.25, .4), (1.85, .44), (1.82, .7), (1.05, .92), (.15, .86)], op, hinge)
        pn.shape([h([(.2, .3)])[0], h([(2.0, .34)])[0], h([jaw[2]])[0], h([jaw[4]])[0], h([(.1, .8)])[0]], c['mouth'], lw=2, wob=.3)
        jp, jm = pn.shape(h(jaw), c['base'], lw=2.4, wob=.4)
        pn.fill(h([(jaw[5][0]-.3, jaw[5][1]+.6), jaw[3], (jaw[3][0]+.4, jaw[3][1]+.5)]), c['dark'], clip=jm)
        for tx in (1.62, 1.15):
            b0 = rot1((tx, .42), op, hinge); b1 = rot1((tx+.16, .42), op, hinge); tip = rot1((tx+.08, .18), op, hinge)
            pn.shape(h([b0, tip, b1]), c['tooth'], lw=1.4, wob=0)
        top = [(-.95, .25), (-.7, -.65), (-.05, -.98), (.75, -.74), (1.45, -.44), (2.05, -.3), (2.24, .0), (2.08, .3), (1.6, .36), (.7, .4), (-.05, .92), (-.6, .85)]
    else:
        top = [(-.95, .25), (-.7, -.65), (-.05, -.98), (.75, -.74), (1.45, -.44), (2.05, -.3), (2.24, .0), (2.08, .3), (1.6, .52), (1.0, .74), (.2, .98), (-.6, .85)]
    p, m = pn.shape(h(top), c['base'], lw=2.8, wob=.5)
    pn.fill(h([(-1.3, .45), (.4, .5), (1.3, .5), (2.5, .28), (2.5, 1.3), (-1.3, 1.3)]), c['dark'], clip=m)
    pn.fill(h([(-.5, -.6), (.1, -.92), (.95, -.68), (.45, -.45), (-.3, -.3)]), c['light'], clip=m)
    pn.fill(h([(-.45, .22), (.3, .2), (.62, .52), (.25, 1.0), (-.55, .9)]), c['cream'], clip=m)
    pn.fill(h([(1.97, -.2), (2.27, -.13), (2.29, .1), (2.0, .12)]), INK, wob=.1)
    if op <= 0: pn.stroke(h([(2.04, .3), (1.55, .43), (1.08, .42)]), 1.6, wob=.2)
    ex, ey = h([(.78, -.3)])[0]
    pn.fill([(ex-3.6, ey+.6), (ex-.5, ey-2.6), (ex+3.6, ey-1.6), (ex+.6, ey+2.2)], '#d9a441', wob=.1)
    pn.fill(ell(ex+.6, ey-.2, 1.5, 1.8, 6), INK, wob=0); pn.fill(ell(ex, ey-1, .6, .6, 5), GLINT, wob=0)
    pn.stroke([(ex-4.5, ey-3.2), (ex, ey-3.6), (ex+4.6, ey-1.8)], 2.2, wob=.1)
    for q in ([(-.2, .0), (-.45, .3)], [(.05, .55), (-.2, .78)]): pn.stroke(h(q), 1.1, c['dark'], clip=m, wob=.1)
    ear(0, c['base'], c['inner'])
def wolf_decor(pn, sp, po, B, H, S, M, bm):
    c = sp['col']; rr, sr = sp['rr'], sp['sr']
    for o in ((-rr*.2, -rr*.4), (sr*.1, -sr*.3), (-6, 2)):
        b0 = B(M, o) if o == (-6, 2) else (B(H, o) if o[0] < 0 else B(S, o)); pn.stroke([b0, (b0[0]+7, b0[1]+3)], 1.2, c['dark'], clip=bm, wob=.2)
    # the ruff around the neck
    pn.fill([B(S, (-sr*.4, -sr*.6)), B(S, (sr*.5, -sr*.9)), B(S, (sr*1.1, -sr*.1)), B(S, (sr*.6, sr*.4)), B(S, (-sr*.1, sr*.1))], c['light'], clip=bm, alpha=170)
WOLF_SP = dict(col=WOLF, hip=(-30, -50), sho=(23, -53), rr=16, sr=17, back=13, belly=8, chest=1.1, R=13, neck=(13, -15),
               ha=24, hb=25, fa=23, fb=24, lw=7, pw=5.2, hpx=-2, fpx=3, farx=6, tail=wolf_tail, head=wolf_head, decor=wolf_decor)
WOLF_POSES = [
    dict(legs=[(0, 0)]*4, tail=0, ear=0),
    dict(legs=[(0, 0)]*4, dy=1.2, tail=.12, hy=1.5, ha=.06, ear=.1),
    # gallop: reach, front plant, gather, push
    dict(legs=[(-22, 6), (24, 8), (-28, 4), (28, 6)], dy=-4, tail=-.35, ha=-.05, ear=.5, dx=0),
    dict(legs=[(-2, 12), (-2, 0), (8, 14), (2, 0)], dy=-1, tilt=.06, tail=-.2, ha=.08, ear=.5),
    dict(legs=[(20, 2), (-20, 8), (24, 0), (-14, 12)], dy=1, tilt=0, tail=-.1, ha=.12, ear=.45),
    dict(legs=[(-10, 0), (14, 14), (-14, 0), (18, 12)], dy=-3, tilt=-.07, tail=-.3, ha=-.02, ear=.5),
    # bite: wind-up, lunge
    dict(legs=[(-4, 0), (6, 0), (-6, 0), (8, 0)], dy=3, tilt=.06, hx=-5, hy=6, ha=.22, open=.18, ear=.55, tail=-.2),
    dict(legs=[(-10, 0), (16, 3), (-12, 0), (18, 0)], dy=0, dx=5, tilt=-.02, hx=5, hy=-1, ha=-.12, open=.62, ear=.6, tail=-.45),
]
def wolf(i):
    s = C.Sheet(160, 120, sd('wolf', i)); pn = Pen(s, 79, 112); quad(pn, WOLF_SP, WOLF_POSES[i]); return s.done(.05)
def wolf_sheet(): return frame_strip([wolf(i) for i in range(8)], 160, 120)

# ---- boar
BOAR = dict(base='#7d5239', dark='#533525', light='#a47656', far='#4a2f21', snout='#b67f6c', tusk='#ece0c2', mane='#352620')
def boar_tail(pn, sp, po, root):
    a = po.get('tail', 0); p = rot([root, (root[0]-6, root[1]+3), (root[0]-8, root[1]+9), (root[0]-5, root[1]+12)], a, root)
    pn.stroke(p, 2.6, INK, wob=.3); pn.shape(ell(p[-1][0]-1, p[-1][1]+3, 3, 4, 6), BOAR['mane'], lw=1.8, wob=.4)
def boar_head(pn, sp, po, A):
    c = sp['col']; R = sp['R']; ha = po.get('ha', 0); h = H_(A, ha, R)
    pn.shape(h([(-.3, -.72), (-.55, -1.4), (.12, -.88)]), c['far'], lw=2.2, wob=.3)
    p, m = pn.shape(h([(-.85, -.7), (.15, -.98), (1.0, -.62), (1.72, -.28), (1.86, .3), (1.6, .66), (.9, .86), (.0, .98), (-.75, .65)]), c['base'], lw=2.9, wob=.5)
    pn.fill(h([(-1.2, .3), (.6, .45), (1.4, .35), (2.2, .4), (2.2, 1.3), (-1.2, 1.3)]), c['dark'], clip=m)
    pn.fill(h([(-.5, -.6), (.2, -.85), (.8, -.6), (.3, -.4)]), c['light'], clip=m)
    sp_, sm = pn.shape(h(ell(1.9, .1, .24, .38, 8)), c['snout'], lw=2.3, wob=.2)
    for q in ((1.95, -.06), (1.95, .24)): pn.fill(h(ell(q[0], q[1], .055, .08, 5)), INK, wob=0)
    pn.stroke(h([(1.72, .55), (1.2, .64), (.85, .6)]), 1.6, wob=.2)
    tk, tkm = pn.shape(h([(1.08, .68), (1.48, .42), (1.66, -.02), (1.6, -.5), (1.47, -.04), (1.24, .76)]), c['tusk'], lw=2.1, wob=.15)
    pn.fill(h([(1.5, .4), (1.7, -.02), (1.7, .5)]), '#b9a98a', clip=tkm, wob=0)
    ex, ey = h([(.62, -.32)])[0]; eye(pn, ex, ey, .55)
    pn.stroke([(ex-4, ey-5), (ex+.5, ey-4.6), (ex+4.6, ey-2.2)], 2.3, wob=.1)
    q = rot([(-.62, -.6), (-.95, -1.25), (-.18, -.86)], -po.get('ear', 0), (-.4, -.7)); ep, em = pn.shape(h(q), c['base'], lw=2.2, wob=.3)
    pn.fill(h([(-.6, -.68), (-.82, -1.08), (-.34, -.8)]), c['dark'], clip=em, wob=.1)
def boar_decor(pn, sp, po, B, H, S, M, bm):
    c = sp['col']; rr, sr = sp['rr'], sp['sr']; A = (S[0]+sp['neck'][0]+po.get('hx', 0), S[1]+sp['neck'][1]+po.get('hy', 0))
    line = [B(H, (-rr*.3, -rr*.78)), B(M, (0, -sp['back'])), B(S, (-sr*.35, -sr*.95)), (A[0]-sp['R']*.4, A[1]-sp['R']*.82)]
    pts = []; up = []; rj = random.Random(3)
    seg = np.concatenate([np.linspace(line[k], line[k+1], 5, endpoint=False) for k in range(3)]+[np.array([line[3]])])
    for j, q in enumerate(seg):
        a_ = seg[max(j-1, 0)]; b_ = seg[min(j+1, len(seg)-1)]; d = (b_[0]-a_[0], b_[1]-a_[1]); l = math.hypot(*d) or 1; nrm = (d[1]/l, -d[0]/l)
        rise = math.sin(math.pi*min(j/(len(seg)-1)*1.25, 1))  # bristles stand tallest over the shoulders
        hh = (rj.uniform(4, 7.5)*rise+1.5) if j % 2 else rj.uniform(.5, 2)
        up.append((q[0]+nrm[0]*hh-d[0]/l*2.5, q[1]+nrm[1]*hh-d[1]/l*2.5)); pts.append((q[0]-nrm[0]*3.5, q[1]-nrm[1]*3.5))
    _, mm = pn.shape(up+pts[::-1], c['mane'], lw=2, wob=.5, smooth=True)
    for q in seg[2:-1:2]: pn.stroke([(q[0]-1, q[1]+1), (q[0]-4, q[1]+7)], 1.3, c['mane'], wob=.2)
    r = random.Random(7)
    for _ in range(9):
        q = B(M, (r.uniform(-28, 22), r.uniform(-12, 6))); pn.stroke([q, (q[0]-4, q[1]+5)], 1.2, c['dark'], clip=bm, wob=.1)
BOAR_SP = dict(col=BOAR, hip=(-30, -37), sho=(18, -42), rr=17, sr=25, back=19, belly=17, chest=1.0, R=15.5, neck=(17, -2),
               ha=13, hb=14, fa=13, fb=14, lw=9, pw=4.6, hpx=-2, fpx=2, farx=6, hoof='#2e2420', tail=boar_tail, head=boar_head, decor=boar_decor, lwk=1.1)
def walk4(amp, lift):
    "A diagonal trot: near hind with far front, far hind with near front."
    ph = [(amp, 0), (0, 0), (-amp, 0), (0, lift)]
    out = []
    for f in range(4):
        a = ph[f]; b = ph[(f+2) % 4]
        out.append([b, a, a, b])  # far hind, far front, near hind, near front
    return out
BOAR_POSES = [dict(legs=[(0, 0)]*4, ha=.2, tail=0), dict(legs=[(0, 0)]*4, ha=.27, dy=1, hy=1.5, tail=.5, ear=.15)]
for f, L in enumerate(walk4(8, 6)): BOAR_POSES.append(dict(legs=L, ha=.2+.03*(f % 2), dy=-1 if f % 2 else 0, tail=.3*(f % 2)))
BOAR_POSES += [dict(legs=[(-14, 0), (16, 4), (-16, 0), (20, 7)], dy=3, tilt=.07, ha=.42, hx=4, hy=7, tail=-.6, ear=.5, dust=0),
               dict(legs=[(8, 6), (-6, 0), (6, 8), (-4, 0)], dy=2, tilt=.05, ha=.46, hx=5, hy=8, tail=-.7, ear=.5, dust=1)]
def boar(i):
    s = C.Sheet(160, 120, sd('boar', i)); pn = Pen(s, 78, 112); po = BOAR_POSES[i]
    if 'dust' in po:
        r = random.Random(40+po['dust'])
        for k, (x, y, rad) in enumerate(((-56, -7, 9), (-68, -14, 7), (-46, -4, 6))):
            puff(pn, x+6-po['dust']*3+r.uniform(-1, 1), y+r.uniform(-1, 1), rad-po['dust']*k*.6, r)
        for y in (-58, -44, -30): pn.stroke([(-66+po['dust']*4, y), (-50+po['dust']*4, y+.5)], 2.2, '#e8dcc0', wob=.2, alpha=200)
    quad(pn, BOAR_SP, po); return s.done(.05)
def boar_sheet(): return frame_strip([boar(i) for i in range(8)], 160, 120)

# =====================================================================================  bat
BAT = dict(base='#7a6584', dark='#4e405c', light='#a996b2', wing='#604d6f', wingd='#403452', wingl='#7d6a8e', inner='#c98a94', belly='#9a8590')
def bat(i):
    s = C.Sheet(120, 100, sd('bat', i)); pn = Pen(s, 62, 50); c = BAT
    phi = [236, 192, 148, 200][i]; bob = [3, 0, -3, -1][i]; curl = [0, .1, .25, .15][i]
    def wing(sign, sc, col, dk):
        sh = (-5*sign, -5+bob) if sign > 0 else (6, -6+bob)
        ang = math.radians(phi if sign > 0 else 180-phi)
        d = (math.cos(ang), math.sin(ang)); wr = (sh[0]+d[0]*19*sc, sh[1]+d[1]*19*sc)
        tips = []
        for off, L in ((20, 25), (-22, 23), (-62, 18)):
            a = ang+math.radians(off*(1 if sign > 0 else -1))*(1-curl*.4)
            tips.append((wr[0]+math.cos(a)*L*sc, wr[1]+math.sin(a)*L*sc))
        hip = (-3*sign if sign > 0 else 4, 9+bob)
        def notch(a, b): m_ = mid(a, b); return mid(m_, wr, .32)
        mem = [sh, wr, tips[0], notch(tips[0], tips[1]), tips[1], notch(tips[1], tips[2]), tips[2], mid(tips[2], hip, .55), hip]
        p, m = pn.shape(mem, col, lw=2.6, wob=.5, smooth=False)
        pn.fill([sh, wr, tips[1], tips[2], hip], dk, clip=m, wob=.6, alpha=150)
        for tp in tips: pn.stroke([wr, tp], 1.6, INK, wob=.2)
        pn.stroke([sh, wr], 3, INK, wob=.2)
        pn.shape(ell(wr[0], wr[1], 2.2, 2.2, 6), dk, lw=1.4, wob=0)
    wing(-1, .9, c['wingd'], '#2c2338')
    # body, ears and face
    by = bob; bp, bm = pn.shape(ell(0, 2+by, 12.5, 14, 9, .3), c['base'], lw=3, wob=.8)
    pn.fill(ell(3, 8+by, 7, 7, 7), c['belly'], clip=bm); pn.fill(ell(7, 10+by, 12, 12, 8), c['dark'], clip=bm, alpha=200); pn.fill(ell(-5, -4+by, 6, 6, 7), c['light'], clip=bm)
    for k in range(5):
        x = -6+k*3; pn.stroke([(x, 10+by), (x+1.5, 14+by)], 1.1, c['dark'], clip=bm, wob=.1)
    pn.stroke([(-3, 14+by), (-5, 19+by)], 1.8, wob=.1); pn.stroke([(3, 15+by), (2, 20+by)], 1.8, wob=.1)
    hx, hy = 7, -11+by
    for (b0, tip, b1), col in ((((hx+4, hy-6), (hx+10, hy-20), (hx+11, hy-4)), c['dark']), (((hx-7, hy-5), (hx-6, hy-21), (hx+3, hy-8)), c['base'])):
        p, m = pn.shape([b0, tip, b1], col, lw=2.4, wob=.3)
        if col == c['base']: pn.fill([mid(b0, b1, .2), mid(tip, mid(b0, b1), .2), mid(b0, b1, .8)], c['inner'], clip=m, wob=.2)
    hp, hm = pn.shape([(hx-10, hy+2), (hx-8, hy-7), (hx+1, hy-10), (hx+9, hy-6), (hx+13, hy+1), (hx+15, hy+4), (hx+9, hy+8), (hx-2, hy+9)], c['base'], lw=2.8, wob=.5)
    pn.fill(ell(hx+4, hy+8, 12, 6, 7), c['dark'], clip=hm); pn.fill(ell(hx-4, hy-6, 5, 3.5, 6), c['light'], clip=hm)
    eye(pn, hx+1, hy-1, .62); eye(pn, hx+8, hy-1.5, .5)
    pn.fill(ell(hx+14, hy+3, 1.6, 1.2, 5), '#2a2030', wob=0)
    pn.shape([(hx+5, hy+6), (hx+6.5, hy+10), (hx+7.5, hy+6)], '#efe6cc', lw=1.2, wob=0)
    pn.shape([(hx+9, hy+5.5), (hx+10, hy+9), (hx+11, hy+5.5)], '#efe6cc', lw=1.2, wob=0)
    wing(1, 1.08, c['wing'], c['wingd'])
    return s.done(.05)
def bat_sheet(): return frame_strip([bat(i) for i in range(4)], 120, 100)

# =====================================================================================  golem and its warden
GOLEM = dict(stone='#6f6a78', dark='#4a4652', light='#958fa0', bark='#6b4b36', barkd='#47301f', moss='#55743f', mossl='#88a658', mossd='#3a5232',
             eye='#e6f4a6', glow='#cfe88a', far='#4f4a59')
WARDEN = dict(stone='#5c5a6c', dark='#3b3949', light='#827e94', bark='#5e412e', barkd='#3a281c', moss='#3f6a3c', mossl='#6f9c4e', mossd='#294a2d',
              eye='#c8ff9c', glow='#7ef07a', far='#3c3a4a', core='#e9ffd6')
def stone(pn, cx, cy, rx, ry, pal, name, col=None, lw=2.8, crack=True, ang=0.0):
    r = random.Random(sd(name)); n = r.choice((7, 8, 9)); pts = []
    for i in range(n):
        a = ang+2*math.pi*i/n+r.uniform(-.2, .2); q = r.uniform(.86, 1.06); pts.append((cx+math.cos(a)*rx*q, cy+math.sin(a)*ry*q))
    p, m = pn.shape(pts, col or pal['stone'], lw=lw, wob=1.0, smooth=False)
    pn.fill(ell(cx+rx*.5, cy+ry*.5, rx, ry, 8), pal['dark'] if col is None else pal['far'], clip=m, wob=1.2)
    if col is None: pn.fill(ell(cx-rx*.35, cy-ry*.42, rx*.5, ry*.38, 7), pal['light'], clip=m, wob=.8)
    if crack:
        a = r.uniform(0, 6.28); x0, y0 = cx+math.cos(a)*rx*.2, cy+math.sin(a)*ry*.2
        pn.stroke([(x0, y0), (x0+r.uniform(-6, 6), y0+r.uniform(3, 7)), (x0+r.uniform(-9, 9), y0+r.uniform(8, 13))], 1.3, clip=m, wob=.3)
    return pts, m
def glowline(pn, pts, pal, clip, w=1.0):
    pn.stroke(pts, 9*w, pal['glow'], clip=clip, wob=.4, alpha=70)
    pn.stroke(pts, 4.2*w, INK, clip=clip, wob=.4)
    pn.stroke(pts, 2.2*w, pal['glow'], clip=clip, wob=.4)
    pn.stroke(pts, .9*w, pal['core'], clip=clip, wob=.4)
def moss(pn, pts, pal, drips=()):
    p, m = pn.shape(pts, pal['moss'], lw=2.6, wob=1.2)
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]; x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pn.fill([(x0-4, y1+4), (x0+(x1-x0)*.4, y0+(y1-y0)*.55), (x1+4, y0+(y1-y0)*.3), (x1+4, y1+4)], pal['mossd'], clip=m, wob=1.4)
    pn.fill([(x0+(x1-x0)*.08, y0+(y1-y0)*.45), (x0+(x1-x0)*.3, y0-2), (x0+(x1-x0)*.6, y0), (x0+(x1-x0)*.35, y0+(y1-y0)*.4)], pal['mossl'], clip=m, wob=1)
    r = random.Random(sd(round(x0), round(y0)))
    for _ in range(int((x1-x0)/5)):
        x = r.uniform(x0+4, x1-4); y = r.uniform(y0+2, y1-3); pn.fill(ell(x, y, 1.4, 1.1, 5), r.choice((pal['mossl'], pal['mossd'])), clip=m, wob=0)
    return m
GOLEM_REST = dict(nel=(18, -56), nfi=(24, -30), fel=(-42, -58), ffi=(-46, -32))
def golem_draw(pn, pal, po, warden=False):
    dy = po.get('dy', 0); t = po.get('tilt', 0); hipc = (0, -40+dy)
    R = lambda p: rot1((p[0], p[1]+dy), t, hipc)
    torso = R((-6, -72)); head = R((22, -98)); shN = R((4, -82)); shF = R((-30, -88))
    tx, ty = torso
    def arm(sh, el, fi, near, tag):
        col = pal['stone'] if near else pal['far']
        el = (el[0], el[1]+dy*.5); fi = (fi[0], fi[1]+dy*.3)
        path = [sh, mid(sh, el), el, mid(el, fi, .6), fi]
        p, m = pn.shape(limb(path, [24, 19, 17, 19, 18]), col, lw=3, wob=.9)
        pn.fill(limb([(x+7, y+3) for x, y in path], [14, 12, 11, 12, 12]), pal['dark'] if near else '#2f2c38', clip=m, wob=.8)
        if near:
            pn.fill(limb([(x-6, y-4) for x, y in path[:3]], [8, 6, 5]), pal['light'], clip=m, wob=.6)
            pn.stroke([mid(sh, el, .35), (mid(sh, el, .55)[0]+4, mid(sh, el, .55)[1]), mid(sh, el, .75)], 1.3, clip=m, wob=.3)
        # a band of bark bound round the forearm
        a = mid(el, fi, .45); d = (fi[0]-el[0], fi[1]-el[1]); l = math.hypot(*d) or 1; n = (-d[1]/l*11, d[0]/l*11); u = (d[0]/l*4, d[1]/l*4)
        band = [(a[0]-n[0]-u[0], a[1]-n[1]-u[1]), (a[0]+n[0]-u[0], a[1]+n[1]-u[1]), (a[0]+n[0]+u[0], a[1]+n[1]+u[1]), (a[0]-n[0]+u[0], a[1]-n[1]+u[1])]
        pn.fill(band, pal['bark'] if near else pal['barkd'], clip=m, wob=.4, smooth=False)
        pn.stroke([band[0], band[1]], 1.6, clip=m, wob=.2); pn.stroke([band[3], band[2]], 1.6, clip=m, wob=.2)
        _, km = stone(pn, fi[0]+2, fi[1]+1, 17, 15, pal, tag+'k', None if near else pal['far'], lw=3)
        if near:
            for k in (-6, 0, 6): pn.stroke([(fi[0]+k+4, fi[1]-12), (fi[0]+k+5, fi[1]-4)], 1.4, clip=km, wob=.2)
            if warden: glowline(pn, [(fi[0]-9, fi[1]-6), (fi[0]-2, fi[1]+1), (fi[0]+5, fi[1]-2), (fi[0]+10, fi[1]+5)], pal, km, .8)
    def leg(x, dx, lift, near):
        top = R((x, -44)); f = (x+dx, -lift); col = pal['stone'] if near else pal['far']
        pts = [(top[0]-15, top[1]), (top[0]+13, top[1]-1), (f[0]+12, f[1]-14), (f[0]+19, f[1]-6), (f[0]+18, f[1]), (f[0]-14, f[1]), (f[0]-15, f[1]-13)]
        p, m = pn.shape(pts, col, lw=3, smooth=False, wob=1.2)
        pn.fill([(top[0]+3, top[1]-4), (top[0]+22, top[1]), (f[0]+24, f[1]+3), (f[0]+4, f[1]+3)], pal['dark'] if near else '#2f2c38', clip=m, wob=1)
        pn.stroke([(f[0]-13, f[1]-13), (f[0]+12, f[1]-14)], 1.6, clip=m, wob=.5)
        for k in (5, 11): pn.stroke([(f[0]+k, f[1]-1), (f[0]+k+1, f[1]-6)], 1.2, clip=m, wob=.1)
    ar = po['arms']; lg = po['legs']
    leg(8, lg[1][0], lg[1][1], False)
    arm(shF, ar['fel'], ar['ffi'], False, 'F')
    leg(-14, lg[0][0], lg[0][1], True)
    # torso: one hunched boulder, a sash of bark wrapped across it, moss grown over its back
    tp, tm = stone(pn, tx, ty, 39, 33, pal, 'torso', lw=3.4, crack=False, ang=.2)
    pn.stroke([(tx-26, ty+2), (tx-20, ty+12), (tx-23, ty+22)], 1.6, clip=tm, wob=.4); pn.stroke([(tx+14, ty+20), (tx+22, ty+26)], 1.4, clip=tm, wob=.3)
    sash = rot([(tx-30, ty-22), (tx-8, ty-6), (tx+14, ty+14), (tx+34, ty+30)], t, torso)
    pn.fill(limb(sash, [15, 15, 15, 15]), pal['bark'], clip=tm, wob=.8)
    pn.fill(limb([(x+3, y+4) for x, y in sash], [8, 8, 8, 8]), pal['barkd'], clip=tm, wob=.6)
    for side in (-7, 7):
        pn.stroke([(x+side*.7, y-side*.7) for x, y in sash], 1.8, clip=tm, wob=.5)
    for k in range(5):
        q = mid(sash[0], sash[-1], .12+k*.19); pn.stroke([(q[0]-4, q[1]+4), (q[0]+3, q[1]-3)], 1.1, clip=tm, wob=.2)
    if warden:
        glowline(pn, [(tx-30, ty+2), (tx-22, ty+8), (tx-26, ty+18), (tx-14, ty+24)], pal, tm, 1)
        glowline(pn, [(tx+2, ty+30), (tx+6, ty+22), (tx+14, ty+26)], pal, tm, .8)
        cx_, cy_ = tx+4, ty+4
        for rad, al in ((19, 30), (14, 40), (10, 55)): pn.fill(ell(cx_, cy_, rad, rad*1.12, 9), pal['glow'], alpha=al, clip=tm, wob=1.2)
        _, gm = pn.shape([(cx_, cy_-11), (cx_+7, cy_), (cx_, cy_+11), (cx_-7, cy_)], pal['glow'], lw=2.4, wob=.2, smooth=False)
        pn.fill([(cx_-1, cy_-7), (cx_+3, cy_-1), (cx_-1, cy_+3), (cx_-3, cy_-2)], pal['core'], clip=gm, wob=0)
    mtop = [(-40, -2), (-38, -20), (-26, -32), (-8, -36), (8, -34), (18, -28), (14, -22), (8, -24), (4, -16), (-2, -24), (-12, -22), (-17, -12), (-22, -22), (-30, -16), (-33, -4)]
    moss(pn, rot([(tx+x, ty+y) for x, y in mtop], t, torso), pal)
    # head: a smaller stone set forward of the shoulders, a heavy brow, two lit eyes looking right
    hx, hy = head
    if warden:
        for side, (bx_, sg) in enumerate(((hx-9, -1), (hx+4, 1))):
            base = (bx_, hy-8); tip = (bx_+sg*12-4, hy-44); midp = mid(base, tip, .5); colb = pal['bark'] if side else pal['barkd']
            pn.shape(limb([base, (bx_+sg*2, hy-24), tip], [7, 5, 3]), colb, lw=2.4, wob=.5)
            br = (midp[0]+sg*14, midp[1]-13)
            pn.shape(limb([midp, (midp[0]+sg*10, midp[1]-6), br], [4, 3, 2]), colb, lw=2, wob=.4)
            for lf, a in ((tip, -1.9), (br, -1.2 if sg > 0 else -2.0)): pn.shape(leafpts(lf, a, 8, 3.2), pal['mossl'], lw=1.6, wob=.2)
    hp, hm = stone(pn, hx, hy, 17, 14, pal, 'head', lw=3, crack=False, ang=.4)
    pn.fill([(hx-20, hy+6), (hx+2, hy+9), (hx+22, hy+4), (hx+22, hy+20), (hx-20, hy+20)], pal['dark'], clip=hm, wob=.6)
    pn.shape([(hx-6, hy-6), (hx+6, hy-9), (hx+19, hy-6), (hx+18, hy-1), (hx+5, hy-3), (hx-5, hy-1)], pal['dark'], lw=2.2, wob=.4)
    for ex, ey, rr_ in ((hx+5, hy+2, 1.0), (hx+14, hy+1.5, .82)):
        pn.fill(ell(ex, ey, 6*rr_+2, 4.4*rr_+2, 8), pal['eye'], alpha=70)
        pn.fill([(ex-4*rr_, ey), (ex, ey-2.6*rr_), (ex+4*rr_, ey-.4), (ex, ey+2.4*rr_)], INK, wob=.1)
        pn.fill([(ex-2.8*rr_, ey), (ex, ey-1.6*rr_), (ex+2.8*rr_, ey-.3), (ex, ey+1.5*rr_)], pal['eye'], wob=0)
    pn.stroke([(hx+6, hy+9), (hx+12, hy+8.5), (hx+17, hy+9.5)], 1.6, clip=hm, wob=.2)
    if warden: glowline(pn, [(hx-13, hy-4), (hx-7, hy+2), (hx-9, hy+9)], pal, hm, .7)
    moss(pn, [(hx-17, hy-2), (hx-15, hy-11), (hx-5, hy-15), (hx+6, hy-14), (hx+10, hy-10), (hx+4, hy-9), (hx+1, hy-5), (hx-4, hy-9), (hx-9, hy-1)], pal)
    if not warden:
        for a, L, col in ((-1.25, 11, pal['mossl']), (-2.2, 9, pal['moss'])):
            q = leafpts((hx-4, hy-13), a, L, 3.8); _, lm = pn.shape(q, col, lw=1.8, wob=.2); pn.stroke([(hx-4, hy-13), q[3]], 1, pal['mossd'], clip=lm, wob=.1)
    arm(shN, ar['nel'], ar['nfi'], True, 'N')
    moss(pn, [(shN[0]-12, shN[1]+3), (shN[0]-10, shN[1]-7), (shN[0]+1, shN[1]-11), (shN[0]+11, shN[1]-6), (shN[0]+12, shN[1]+2), (shN[0]+6, shN[1]), (shN[0]+3, shN[1]+6), (shN[0]-2, shN[1]+1), (shN[0]-7, shN[1]+5)], pal)
    return po
def golem_poses():
    rest = GOLEM_REST; out = []
    out.append(dict(arms=dict(rest), legs=[(0, 0), (0, 0)]))
    out.append(dict(arms=dict(nel=(18, -54), nfi=(25, -27), fel=(-42, -56), ffi=(-47, -29)), legs=[(0, 0), (0, 0)], dy=2))
    nd = [10, 3, -10, -3]; nl = [0, 0, 0, 9]; fd = [-10, -3, 10, 3]; fl = [0, 9, 0, 0]; bob = [1, -2, 1, -2]; sw = [-9, -2, 9, 2]
    for f in range(4):
        a = dict(nel=(rest['nel'][0]+sw[f]*.5, rest['nel'][1]), nfi=(rest['nfi'][0]+sw[f], rest['nfi'][1]-abs(sw[f])*.4),
                 fel=(rest['fel'][0]-sw[f]*.35, rest['fel'][1]), ffi=(rest['ffi'][0]-sw[f]*.6, rest['ffi'][1]-abs(sw[f])*.3))
        out.append(dict(arms=a, legs=[(nd[f], nl[f]), (fd[f], fl[f])], dy=bob[f], tilt=.02*(1 if f in (0, 3) else -1)))
    out.append(dict(arms=dict(nel=(-2, -118), nfi=(8, -142), fel=(-32, -120), ffi=(-16, -144)), legs=[(-4, 0), (6, 0)], dy=-3, tilt=-.1))
    out.append(dict(arms=dict(nel=(34, -54), nfi=(44, -16), fel=(20, -58), ffi=(30, -16)), legs=[(-8, 0), (10, 0)], dy=6, tilt=.17, impact=True))
    return out
GOLEM_POSES = golem_poses()
def impact(pn, pal, warden, seed, back):
    r = random.Random(seed)
    if back:
        for x, y, rad in ((76, -17, 6.5), (4, -13, 6)): puff(pn, x+r.uniform(-1, 1), y, rad, r)
        return
    for x, y, rad in ((70, -7, 8), (22, -6, 6.5)): puff(pn, x, y, rad, r)
    for a in (-2.7, -2.15, -1.0, -.45):
        x0, y0 = 40+math.cos(a)*28, -14+math.sin(a)*24; pn.stroke([(x0, y0), (x0+math.cos(a)*10, y0+math.sin(a)*10)], 2.6, '#e8dcc0' if not warden else pal['glow'], wob=.1)
    for k in range(5):
        x = r.uniform(6, 78); y = r.uniform(-56, -36); s_ = r.uniform(2.5, 4.5)
        pn.shape([(x-s_, y), (x, y-s_), (x+s_*1.2, y+s_*.3), (x+s_*.2, y+s_)], pal['stone'], lw=1.8, smooth=False, wob=.2)
    for dx, L in ((-14, -16), (14, 16)): pn.stroke([(40+dx, -1), (40+dx+L*.5, 0), (40+dx+L, -1.5)], 2, wob=.4)
def golem(i, warden=False):
    pal = WARDEN if warden else GOLEM
    if warden: s = C.Sheet(240, 260, sd('warden', i)); pn = Pen(s, 112, 253, 1.45)
    else: s = C.Sheet(160, 180, sd('golem', i)); pn = Pen(s, 74, 174, 1.0)
    po = GOLEM_POSES[i]
    if po.get('impact'): impact(pn, pal, warden, 9+warden, True)
    golem_draw(pn, pal, po, warden)
    if po.get('impact'): impact(pn, pal, warden, 9+warden, False)
    return s.done(.05)
def golem_sheet(warden=False):
    fw, fh = (240, 260) if warden else (160, 180)
    return frame_strip([golem(i, warden) for i in range(8)], fw, fh)

# =====================================================================================  pets
CAT = dict(base='#cf8f4e', dark='#9c6232', light='#ecc184', cream='#f0e0c0', far='#8a582e', stripe='#844c27', nose='#c96f72', inner='#e2a096')
DOG = dict(base='#ddcba7', dark='#ad9878', light='#f3e8cc', cream=None, far='#9c876a', patch='#9a6440', patchd='#6e4429', ear='#7c4d2f', nose=INK, tongue='#d9707a')
def cat_tail(pn, sp, po, root):
    c = sp['col']; a = po.get('tail', 0); L = sp['tailk']
    if po.get('tailmode') == 'wrap':
        g = -3.2
        path = [root, (root[0]-9, root[1]+6), (root[0]-6, g), (root[0]+12*L, g+.5), (root[0]+30*L, g-1.5)]
    else:
        path = rot([root, (root[0]-9*L, root[1]-3*L), (root[0]-15*L, root[1]-14*L), (root[0]-14*L, root[1]-27*L), (root[0]-7*L, root[1]-33*L)], a, root)
    p, m = pn.shape(limb(path, [5.5, 5, 4.8, 4.5, 4]), c['base'], lw=2.4, wob=.5)
    if sp['age'] > 0:
        for k in range(1, 5):
            q = mid(path[k-1], path[k], .6); pn.fill(ell(q[0], q[1], 3.2, 3.2, 6), c['stripe'], clip=m, wob=.3)
    pn.fill(ell(path[-1][0], path[-1][1], 4.5, 4.5, 6), c['stripe'] if sp['age'] else c['dark'], clip=m, wob=.3)
def cat_head(pn, sp, po, A):
    c = sp['col']; R = sp['R']; ha = po.get('ha', 0); h = H_(A, ha, R); happy = po.get('happy')
    def ear(base, tip, b1, col, inner):
        p, m = pn.shape(h([base, tip, b1]), col, lw=2.4, wob=.25)
        pn.fill(h([mid(base, b1, .25), mid(tip, mid(base, b1), .22), mid(base, b1, .8)]), inner, clip=m, wob=.15)
    ear((.25, -.7), (.78, -1.62), (.95, -.38), c['dark'], '#b07468')
    hd = [(-1.0, .1), (-.82, -.68), (0, -.98), (.8, -.74), (1.12, -.06), (.98, .52), (.32, .84), (-.58, .72)]
    p, m = pn.shape(h(hd), c['base'], lw=2.8, wob=.4)
    pn.fill(h([(-1.3, .5), (.2, .55), (1.0, .2), (1.4, .2), (1.4, 1.3), (-1.3, 1.3)]), c['dark'], clip=m)
    pn.fill(h([(-.72, -.3), (-.45, -.75), (.1, -.86), (-.25, -.5)]), c['light'], clip=m)
    pn.fill(h([(-.05, .18), (.55, .05), (1.0, .2), (.85, .7), (.2, .74)]), c['cream'], clip=m)
    if sp['age'] > 0:
        for x in (-.32, -.12, .08): pn.stroke(h([(x, -.95), (x+.04, -.62)]), 1.4*(.6+sp['age']*.2), c['stripe'], clip=m, wob=.1)
    ear((-.78, -.52), (-.55, -1.7), (-.02, -.88), c['base'], c['inner'])
    es = sp['eye']
    for (x, y), r_ in (((.0, -.1), es), ((.68, -.14), es*.82)):
        ex, ey = h([(x, y)])[0]; eye(pn, ex, ey, r_, shut=happy)
    nx, ny = h([(.48, .2)])[0]
    pn.fill([(nx-1.8, ny-1), (nx+1.8, ny-1), (nx, ny+1.4)], c['nose'], wob=0)
    pn.stroke([(nx-3, ny+2.6), (nx-1.3, ny+3.6), (nx, ny+2.2), (nx+1.3, ny+3.6), (nx+3, ny+2.6)], 1.1, '#5e3528', wob=.05)
    pn.fill(h(ell(-.2, .38, .17, .1, 6)), '#e08a7e', alpha=140, clip=m, wob=0)
    if sp['age'] == 2:
        for dy_ in (-.02, .14):
            a0 = h([(.95, .3+dy_)])[0]; a1 = h([(1.55, .22+dy_*1.8)])[0]; pn.stroke([a0, a1], .9, '#3a2a22', wob=.1)
            b0 = h([(-.3, .38+dy_)])[0]; b1 = h([(-.85, .32+dy_*2)])[0]; pn.stroke([b0, b1], .9, '#3a2a22', wob=.1)
def cat_decor(pn, sp, po, B, H, S, M, bm):
    c = sp['col']; rr, sr = sp['rr'], sp['sr']
    if sp['age'] == 0: return
    n = 2 if sp['age'] == 1 else 3
    for k in range(n):
        q = mid(B(H, (-rr*.1, 0)), B(S, (-sr*.6, 0)), (k+.5)/n)
        top = (q[0], q[1]-sp['back']-6); pn.stroke([top, (q[0]-1.5, q[1]-sp['back']+1), (q[0]-.5, q[1]-sp['back']+5)], 2.6 if sp['age'] == 2 else 2.2, c['stripe'], clip=bm, wob=.2)
    pn.stroke([B(H, (-rr*.7, -rr*.6)), B(H, (-rr*.2, -rr*.2)), B(H, (-rr*.1, rr*.25))], 2.2, c['stripe'], clip=bm, wob=.3)
def dog_tail(pn, sp, po, root):
    c = sp['col']; a = po.get('tail', 0); L = sp['tailk']
    if po.get('tailmode') == 'wrap':
        path = [root, (root[0]-10*L, root[1]+8), (root[0]-20*L, -3.5)]
        pn.shape(limb(path, [5.5, 5, 4]), c['base'], lw=2.4, wob=.4); return
    path = rot([root, (root[0]-6*L, root[1]-7*L), (root[0]-8*L, root[1]-16*L), (root[0]-4*L, root[1]-23*L)], a, root)
    p, m = pn.shape(limb(path, [6, 5.5, 4.6, 3.4]), c['base'], lw=2.4, wob=.4)
    pn.fill(ell(path[-1][0], path[-1][1], 5, 5, 6), c['light'], clip=m, wob=.2)
def dog_head(pn, sp, po, A):
    c = sp['col']; R = sp['R']; ha = po.get('ha', 0); h = H_(A, ha, R); happy = po.get('happy'); ek = sp['eark']
    pn.shape(h([(.3, -.8), (.75, -.95), (1.0, -.55), (.82, -.1)]), c['patchd'], lw=2.2, wob=.3)
    hd = [(-1.0, .1), (-.75, -.72), (0, -1.0), (.72, -.8), (1.02, -.38), (1.48, -.22), (1.78, .06), (1.66, .44), (1.1, .66), (.25, .86), (-.6, .72)]
    p, m = pn.shape(h(hd), c['base'], lw=2.8, wob=.4)
    pn.fill(h([(-1.3, .45), (.3, .55), (1.2, .5), (2, .38), (2, 1.3), (-1.3, 1.3)]), c['dark'], clip=m)
    pn.fill(h([(-.7, -.4), (-.4, -.8), (.1, -.9), (-.3, -.55)]), c['light'], clip=m)
    if sp['age'] > 0: pn.fill(h([(-.2, -1.1), (.55, -1.0), (.6, -.4), (.15, -.25), (-.15, -.6)]), c['patch'], clip=m)
    if happy:
        pn.shape(h([(1.15, .48), (1.5, .5), (1.52, 1.0), (1.32, 1.12), (1.15, .9)]), c['tongue'], lw=1.8, wob=.15)
        pn.stroke(h([(1.66, .44), (1.35, .55), (1.0, .5)]), 1.4, wob=.1)
    else:
        pn.stroke(h([(1.62, .44), (1.32, .52), (1.05, .46)]), 1.4, wob=.1)
    pn.fill(h(ell(1.62, .0, .2, .15, 7)), c['nose'], wob=.1); pn.fill(h(ell(1.55, -.05, .06, .04, 5)), '#6a6070', wob=0)
    es = sp['eye']
    for (x, y), r_ in (((.12, -.22), es), ((.82, -.28), es*.8)):
        ex, ey = h([(x, y)])[0]; eye(pn, ex, ey, r_, shut=happy)
    pn.fill(h(ell(-.1, .3, .17, .1, 6)), '#e08a7e', alpha=130, clip=m, wob=0)
    # the near ear flops down over the side of the head
    flop = po.get('ear', 0)
    q = rot([(-.62, -.72), (-.15, -.86), (-.1, -.3), (-.25, .35*ek), (-.55, .5*ek), (-.85, .2)], -flop, (-.4, -.8))
    ep, em = pn.shape(h(q), c['ear'], lw=2.4, wob=.3)
    pn.fill(h([(-.3, -.9), (.1, -.6), (0, .6), (-.3, .2)]), c['patchd'], clip=em, wob=.3)
def dog_decor(pn, sp, po, B, H, S, M, bm):
    c = sp['col']; rr, sr = sp['rr'], sp['sr']
    if sp['age'] == 0:
        pn.fill([B(H, (-rr*.6, -rr*.9)), B(M, (0, -sp['back']-3)), B(M, (6, 0)), B(H, (-rr*.2, -rr*.1))], c['patch'], clip=bm); return
    p = [B(H, (-rr*.95, -rr*.7)), B(M, (-4, -sp['back']-4)), B(S, (-sr*.6, -sr*1.0)), B(S, (-sr*.2, -sr*.2)), B(M, (2, 4)), B(H, (-rr*.1, -rr*.05))]
    pn.fill(p, c['patch'], clip=bm, wob=1.2)
    pn.fill([B(M, (-6, -sp['back']-6)), B(S, (-sr*.6, -sr*1.2)), B(S, (-sr*.3, -sr*.1)), B(M, (6, 6)), B(M, (-4, 2))], c['patchd'], clip=bm, alpha=110, wob=1)
def pet_spec(kind, age):
    hs = (1.42, 1.18, 1.0)[age]; lk = (.78, .9, 1.0)[age]
    if kind == 'cat':
        sp = dict(col=CAT, kind='cat', age=age, hip=(-17, -27*lk), sho=(14, -28*lk), rr=13, sr=12, back=7, belly=6, R=14.5*hs,
                  neck=(8, -10-(hs-1)*7), ha=12*lk, hb=12.5*lk, fa=11.5*lk, fb=12*lk, lw=6.4, pw=4.6, hpx=0, fpx=2, farx=5,
                  tail=cat_tail, head=cat_head, decor=cat_decor, tailk=(.6, .85, 1.0)[age], eye=(1.0, .86, .78)[age], lwk=.95)
        if age == 2: sp.update(collar='#a33c4b', tag='#d7a941')
    else:
        sp = dict(col=DOG, kind='dog', age=age, hip=(-19, -31*lk), sho=(16, -33*lk), rr=14, sr=14, back=6.5, belly=8, R=15*hs,
                  neck=(9, -11-(hs-1)*7), ha=14*lk, hb=14.5*lk, fa=13.5*lk, fb=14*lk, lw=7.4, pw=5.2, hpx=0, fpx=2, farx=5,
                  tail=dog_tail, head=dog_head, decor=dog_decor, tailk=(.7, .9, 1.0)[age], eye=(1.0, .86, .8)[age], eark=(1.25, 1.1, 1.0)[age], lwk=.95)
        if age >= 1: sp.update(collar='#3f6b8a')
        if age == 2: sp.update(tag='#d7a941')
    return sp
PET_K = (.7, .85, 1.0)
def pet_poses(kind):
    o = [dict(legs=[(0, 0)]*4, tail=0, ear=0), dict(legs=[(0, 0)]*4, dy=1, hy=1, ha=.05, tail=.18, ear=.08)]
    for f, L in enumerate(walk4(6, 6)): o.append(dict(legs=L, dy=-1 if f % 2 else 0, ha=.03*(f % 2), tail=.12*(1 if f < 2 else -1), ear=.1*(f % 2)))
    if kind == 'cat':
        o.append(dict(sit=True, ha=-.04))
        o.append(dict(legs=[(0, 0), (0, 0), (0, 0), (0, 0)], dy=-1, tail=.42, ha=-.08, happy=True, heart=True))
    else:
        o.append(dict(sit=True, ha=-.06, ear=.1))
        o.append(dict(legs=[(0, 0), (8, 9), (0, 0), (10, 11)], dy=-1, tilt=-.14, pivot='hip', tail=-.25, ha=-.1, happy=True, heart=True, ear=-.25))
    return o
def pet(kind, age, i):
    s = C.Sheet(112, 96, sd('pet', kind, age, i)); k = PET_K[age]; pn = Pen(s, 54 if kind == 'cat' else 50, 90, k)
    sp = pet_spec(kind, age); po = pet_poses(kind)[i]
    if kind == 'dog' and i in (2, 3, 4, 5): po = dict(po, tail=po['tail']*2.4)
    g = sit_quad(pn, sp, po) if po.get('sit') else quad(pn, sp, po)
    if po.get('heart'):
        A = g['A']; hr = 5.5/k**.5; hy = max(A[1]-sp['R']*1.9-6/k, (5-pn.oy)/k+hr)  # keep the heart inside the frame
        heart(pn, A[0]+sp['R']*.4, hy, hr)
    return s.done(.05)
PET_LOOKS = [('cat', 0), ('cat', 1), ('cat', 2), ('dog', 0), ('dog', 1), ('dog', 2)]
def pets_sheet(): return grid([[pet(kd, ag, i) for i in range(8)] for kd, ag in PET_LOOKS], 112, 96)

# =====================================================================================  effects
def arrow(i):
    s = C.Sheet(96, 32, sd('arrow', i)); pn = Pen(s, 0, 0); bend = (0, 1.4)[i]; y = 16
    for yy, x0 in ((12, 2), (20, 6)): pn.stroke([(x0, yy+bend*.3), (x0+12, yy)], 1.6, '#e8dcc0', wob=.1, alpha=150)
    sh = [(14, y), (44, y+bend), (74, y)]
    pn.shape(limb(sh, [4.4, 4.4, 4.4]), '#8a6440', lw=2, wob=.2)
    pn.stroke([(18, y+1.2+bend*.3), (44, y+1.4+bend), (70, y+1.2)], 1.2, '#5c3f2b', wob=.1)
    for dy_, col in ((-1, '#a33c4b'), (1, '#74293c')):
        fl = [(10, y+dy_), (14+bend*.5, y+dy_*9), (30, y+dy_*8.5), (30, y+dy_*1.5)]
        _, fm = pn.shape(fl, col, lw=2, wob=.2, smooth=False)
        for x in (17, 22, 27): pn.stroke([(x, y+dy_*2), (x-3, y+dy_*7.5)], .9, '#3c1a24', clip=fm, wob=.05)
    pn.stroke([(31, y-2.4), (31, y+2.4)], 2.2, '#d7a941', wob=0); pn.stroke([(34, y-2.4), (34, y+2.4)], 2.2, '#d7a941', wob=0)
    _, hm = pn.shape([(71, y-7), (91, y), (71, y+7), (74, y)], '#a9acb8', lw=2.2, smooth=False, wob=.15)
    pn.fill([(70, y+.5), (92, y+.3), (70, y+9)], '#6c6f7e', clip=hm, wob=0, smooth=False); pn.stroke([(74, y-3.4), (84, y-1.6)], 1.2, '#e6e6ee', wob=0)
    return s.done(.03)
def fireball(i):
    s = C.Sheet(96, 96, sd('fire', i)); pn = Pen(s, 0, 0); r = random.Random(30+i); cx, cy = 63, 48
    def ball(scale, ox, oy, jit, tongues):
        pts = []
        for a in np.linspace(-1.75, 1.75, 7): rad = 21*scale*(1+r.uniform(-jit, jit)); pts.append((cx+ox+math.cos(a)*rad, cy+oy+math.sin(a)*rad))
        tips = [(cx+ox-21*scale-tl*scale*.82, cy+oy+ty*scale) for tl, ty in tongues]
        back = []  # tongues listed top to bottom, with a valley between each pair
        for k, tp in enumerate(tips):
            back.append(tp)
            if k < len(tips)-1: back.append((cx+ox-14*scale+r.uniform(-2, 2), (tp[1]+tips[k+1][1])/2))
        # front arc runs top to bottom on the right, then the trailing tongues come back from bottom to top
        return pts+[(cx+ox-8*scale, cy+oy+21*scale)]+list(reversed(back))+[(cx+ox-8*scale, cy+oy-21*scale)]
    flick = [(0, 0, 0), (3, -4, 3), (-3, 3, -2)][i]
    tongues = [(30+flick[0]*2, -15+flick[1]), (42+flick[2]*2, 1+flick[1]*.5), (26-flick[0], 15+flick[2])]
    p, m = pn.shape(ball(1.0, 0, 0, .06, tongues), '#b4401e', lw=2.6, wob=.8)
    pn.fill(ball(.74, 4, 1, .08, [(t[0]*.8, t[1]*.8) for t in tongues]), '#e88a2c', clip=m, wob=.8)
    pn.fill(ball(.44, 8, 0, .1, [(t[0]*.5, t[1]*.6) for t in tongues]), '#f7d67c', clip=m, wob=.6)
    pn.fill(ell(cx+7, cy-3, 5, 4, 7), '#fff4d4', clip=m, wob=.3)
    for k in range(3):
        x = 14+r.uniform(-4, 10)+k*6; y = cy+r.uniform(-24, 24); rr_ = r.uniform(1.8, 3)
        pn.shape(ell(x, y, rr_, rr_, 6), '#f0a040', lw=1.2, wob=.1)
    return s.done(.03)
def claw(i):
    s = C.Sheet(96, 96, sd('claw', i)); pn = Pen(s, 0, 0); r = random.Random(50+i)
    t0, t1, W = [(0, .55, 7), (0, 1, 10), (.3, 1, 5)][i]
    for k, off in enumerate((-15, 0, 15)):
        p0 = (16+off*.7, 20-off*.7); p2 = (78+off*.7, 76-off*.7); p1 = (58+off*.7, 26-off*.7)
        ts = np.linspace(t0, t1, 28)
        c_ = [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in ts]
        u = (ts-t0)/(t1-t0); wd = [max(W*(.9 if k == 1 else .75)*math.sin(math.pi*v)**.7, .4) for v in u]
        pts = limb(c_, wd)
        if i == 2:
            for a_, b_ in ((0, 11), (14, 28)):
                seg = limb(c_[a_:b_], wd[a_:b_]); s.fill(s.curve(pn.T(seg), True, .3), '#f6ecc8'); s.line(s.curve(pn.T(seg), True, .3), 2, INK, closed=True, taper=False)
        else:
            q = s.curve(pn.T(pts), True, .3); s.fill(q, '#f6ecc8'); s.line(q, 2.4, INK, closed=True, taper=False)
            pn.stroke(c_[3:-3], 1.6, '#e0b04a', wob=.1)
    if i >= 1:
        for k in range(4 if i == 1 else 6):
            x = r.uniform(14, 84); y = r.uniform(14, 84); a = r.uniform(2, 4.5)
            pn.shape([(x, y-a), (x+a*.3, y-a*.3), (x+a, y), (x+a*.3, y+a*.3), (x, y+a), (x-a*.3, y+a*.3), (x-a, y), (x-a*.3, y-a*.3)], '#f3d27a', lw=1.2, smooth=False, wob=0)
    return s.done(.03)

# =====================================================================================  icons
def icon6(n):
    s = C.Sheet(120, 120, {'fur': 61, 'treat': 62, 'hammer': 63, 'crystal': 64, 'meat': 65}[n]); pn = Pen(s, 0, 0); r = s.r
    if n == 'fur':
        # a soft lock of fur, like the tip of a tail: wavy edges, strands flowing up into a curl
        back = [(52, 96), (40, 84), (36, 66), (42, 50), (36, 40), (46, 30), (50, 18), (60, 26), (58, 34), (66, 30)]
        pn.shape(back, '#7a6d63', lw=2.8, wob=.6)
        tuft = [(44, 98), (32, 86), (28, 70), (34, 56), (30, 44), (40, 40), (46, 30), (56, 22), (68, 14), (78, 14), (84, 22), (76, 22), (70, 28), (78, 34),
                (88, 44), (90, 58), (96, 70), (90, 84), (80, 98)]
        _, m = pn.shape(tuft, '#a59584', lw=3.4, wob=.7)
        pn.fill([(64, 40), (96, 52), (100, 100), (62, 104), (78, 76)], '#7a6d63', clip=m, wob=1.2)
        pn.fill([(34, 70), (38, 52), (50, 36), (56, 34), (46, 54), (42, 76)], '#d6c8b2', clip=m, wob=.8)
        r2 = random.Random(5)
        for k in range(11):
            x = 38+k*4.6+r2.uniform(-1, 1); y = 96-r2.uniform(0, 6)
            pts = [(x, y), (x+(k-5)*.8+r2.uniform(-2, 2), y-24), (x+(k-5)*1.1+8, y-46-r2.uniform(0, 10)), (66+k*1.2, 24+r2.uniform(0, 6))]
            pn.stroke(pts[:3+(k % 2)], r2.uniform(.9, 1.5), '#5e524c' if k % 3 else '#e2d6c0', clip=m, wob=.4)
        pn.shape([(42, 92), (78, 92), (80, 106), (40, 106)], '#7d3250', lw=2.8, smooth=False, wob=.6)
        pn.stroke([(44, 99), (76, 99)], 1.4, '#c79b42', wob=.3)
    elif n == 'treat':
        b = [(-26, -10), (26, -10), (30, -20), (40, -22), (47, -13), (41, 0), (47, 13), (40, 22), (30, 20), (26, 10), (-26, 10), (-30, 20), (-40, 22), (-47, 13), (-41, 0), (-47, -13), (-40, -22), (-30, -20)]
        b = rot([(60+x*1.08, 62+y*1.08) for x, y in b], -.62, (60, 62))
        p, m = pn.shape(b, '#c99a5a', lw=3.6, wob=.8)
        pn.fill(rot([(30, 72), (100, 60), (110, 100), (20, 100)], -.62, (60, 62)), '#946232', clip=m)
        pn.fill(rot([(20, 46), (44, 40), (52, 50), (26, 56)], -.62, (60, 62)), '#ecc88a', clip=m)
        for x, y in ((48, 62), (60, 58), (72, 62), (60, 68)):
            q = rot1((x, y), -.62, (60, 62)); pn.fill(ell(q[0], q[1], 2.2, 2.2, 6), '#7a4e2a', clip=m, wob=0)
        for _ in range(7):
            q = rot1((r.uniform(26, 94), r.uniform(52, 72)), -.62, (60, 62)); pn.fill(ell(q[0], q[1], 1.6, 1.1, 5), '#f4e4be', clip=m, wob=0)
    elif n == 'hammer':
        hp = [(28, 106), (50, 72), (76, 36)]
        p, m = pn.shape(limb(hp, [12, 11, 10]), '#8a6440', lw=3, wob=.4)
        pn.fill([(40, 110), (90, 30), (100, 40), (50, 116)], '#5c3f2b', clip=m)
        for k in range(4):
            a = mid(hp[0], hp[1], .1+k*.16); pn.stroke([(a[0]-7, a[1]-3), (a[0]+5, a[1]+5)], 3.4, '#4a3229', wob=.1)
        hd = rot([(50, 26), (98, 26), (98, 48), (50, 48)], -.95+math.pi/2*0+.62, (74, 37))
        hd = rot([(46, 28), (102, 26), (104, 46), (66, 48), (50, 46)], .58, (76, 37))
        _, hm = pn.shape(hd, '#7d7f8c', lw=3.4, smooth=False, wob=.6)
        pn.fill(rot([(40, 38), (110, 36), (110, 56), (40, 56)], .58, (76, 37)), '#545665', clip=hm, smooth=False)
        pn.fill(rot([(50, 29), (92, 28), (92, 32), (50, 34)], .58, (76, 37)), '#c3c5ce', clip=hm, smooth=False, wob=.3)
        pn.stroke(rot([(92, 27), (93, 47)], .58, (76, 37)), 1.6, wob=.1, clip=hm)
    elif n == 'crystal':
        pn.shape([(18, 104), (30, 90), (60, 86), (92, 90), (104, 104), (60, 112)], '#5a5664', lw=3, smooth=False, wob=1)
        def prism(cx, by, w, h, ang, nm):
            pts = rot([(cx, by-h), (cx+w, by-h+w*.9), (cx+w, by), (cx, by+w*.5), (cx-w, by), (cx-w, by-h+w*.9)], ang, (cx, by))
            _, m = pn.shape(pts, '#4fae6a', lw=3, smooth=False, wob=.4)
            pn.fill(rot([(cx, by-h), (cx+w+2, by-h+w*.9), (cx+w+2, by+2), (cx, by+w*.5)], ang, (cx, by)), '#2c7452', clip=m, smooth=False, wob=0)
            pn.fill(rot([(cx-w+2, by-h+w*.9+2), (cx-2, by-h+6), (cx-2, by-6), (cx-w+2, by-4)], ang, (cx, by)), '#a8ecb0', clip=m, smooth=False, wob=0)
            pn.stroke(rot([(cx, by-h), (cx, by+w*.5)], ang, (cx, by)), 1.6, INK, clip=m, wob=.1)
            return m
        prism(36, 98, 10, 34, -.42, 'a'); prism(86, 98, 9, 28, .45, 'b'); m = prism(60, 96, 15, 76, 0, 'c')
        pn.fill([(53, 36), (57, 30), (57, 62), (53, 66)], '#eaffe8', clip=m, wob=0, smooth=False)
        for x, y, a in ((88, 28, 6), (26, 44, 4.5), (98, 60, 3.5)):
            pn.shape([(x, y-a), (x+a*.3, y-a*.3), (x+a, y), (x+a*.3, y+a*.3), (x, y+a), (x-a*.3, y+a*.3), (x-a, y), (x-a*.3, y-a*.3)], '#d9ffcf', lw=1.4, smooth=False, wob=0)
    elif n == 'meat':
        bp = [(24, 100), (44, 80)]
        pn.shape(limb(bp, [10, 11]), '#e8dcc0', lw=3, wob=.3)
        for q in ((19, 96), (27, 104)): pn.shape(ell(q[0], q[1], 7.5, 7.5, 8), '#e8dcc0', lw=3, wob=.3)
        pn.fill(ell(23, 102, 8, 5, 6), '#bfae8c', wob=.2, alpha=180)
        mt = rot(ell(70, 52, 38, 30, 10, .2), -.7, (70, 52))
        p, m = pn.shape(mt, '#a8483c', lw=3.6, wob=1)
        pn.fill(rot(ell(84, 66, 36, 26, 9), -.7, (70, 52)), '#73302a', clip=m)
        pn.fill(rot(ell(56, 40, 16, 9, 8), -.7, (70, 52)), '#d77a64', clip=m)
        pn.stroke([(42, 80), (48, 70), (58, 72)], 4, '#efd9b8', clip=m, wob=.4)
        for a, b_ in (((62, 34), (82, 46)), ((74, 30), (92, 40))): pn.stroke([a, b_], 1.6, '#5e2420', clip=m, wob=.2)
        pn.stroke([(50, 32), (56, 26)], 2.8, '#f6d6c4', clip=m, wob=.1)
    out = s.done(.05)
    if n == 'crystal':  # a soft light around it, laid underneath the paint
        Y, X = np.mgrid[0:120, 0:120]; d = np.hypot((X-60)/52, (Y-60)/56); g = np.zeros((120, 120, 4), np.uint8)
        g[..., :3] = C.rgb('#8ef58a'); g[..., 3] = (np.clip(1-d, 0, 1)**1.8*150).astype(np.uint8); P.over(g, out, 0, 0); out = g
    return out

# =====================================================================================  manifest and contact sheet
def anim(frames, fps, loop=True): return dict(frames=frames, fps=fps, loop=loop)
MANIFEST = {
    'slime': dict(file='slime.png', frameWidth=120, frameHeight=120, columns=3, rows=3, framesPerLook=3, looks=['green', 'blue', 'crimson'],
                  animations=dict(idle=anim([0], 1), hop=anim([0, 1, 2, 1], 8), squash=anim([1], 1, False)), drawWidth=96, drawHeight=96, baselineY=106),
    'hopper': dict(file='hopper.png', frameWidth=120, frameHeight=120, columns=6, rows=1, framesPerLook=6, looks=['meadow'],
                   animations=dict(idle=anim([0, 1], 3), hop=anim([2, 3, 4, 5], 10)), drawWidth=84, drawHeight=84, baselineY=HOP_BASE),
    'wolf': dict(file='wolf.png', frameWidth=160, frameHeight=120, columns=8, rows=1, framesPerLook=8, looks=['grey'],
                 animations=dict(idle=anim([0, 1], 3), run=anim([2, 3, 4, 5], 12), bite=anim([6, 7], 8, False)), drawWidth=136, drawHeight=102, baselineY=112),
    'boar': dict(file='boar.png', frameWidth=160, frameHeight=120, columns=8, rows=1, framesPerLook=8, looks=['brown'],
                 animations=dict(idle=anim([0, 1], 3), walk=anim([2, 3, 4, 5], 8), charge=anim([6, 7], 10)), drawWidth=144, drawHeight=108, baselineY=112),
    'bat': dict(file='bat.png', frameWidth=120, frameHeight=100, columns=4, rows=1, framesPerLook=4, looks=['cave'],
                animations=dict(flap=anim([0, 1, 2, 3], 12)), drawWidth=84, drawHeight=70, baselineY=None, note='hovers; frame centre is the body'),
    'golem': dict(file='golem.png', frameWidth=160, frameHeight=180, columns=8, rows=1, framesPerLook=8, looks=['stonebark'],
                  animations=dict(idle=anim([0, 1], 2), walk=anim([2, 3, 4, 5], 6), slam=anim([6, 7], 5, False)), drawWidth=144, drawHeight=162, baselineY=174),
    'warden': dict(file='warden.png', frameWidth=240, frameHeight=260, columns=8, rows=1, framesPerLook=8, looks=['warden'],
                   animations=dict(idle=anim([0, 1], 2), walk=anim([2, 3, 4, 5], 5), slam=anim([6, 7], 4, False)), drawWidth=240, drawHeight=260, baselineY=253),
    'pets': dict(file='pets.png', frameWidth=112, frameHeight=96, columns=8, rows=6, framesPerLook=8,
                 looks=['kitten', 'young cat', 'adult cat', 'puppy', 'young dog', 'adult dog'],
                 animations=dict(idle=anim([0, 1], 3), walk=anim([2, 3, 4, 5], 9), sit=anim([6], 1), happy=anim([7], 1)), drawWidth=84, drawHeight=72, baselineY=90),
    'arrow': dict(file='arrow.png', frameWidth=96, frameHeight=32, columns=2, rows=1, framesPerLook=2, looks=['wood'],
                  animations=dict(fly=anim([0, 1], 12)), drawWidth=72, drawHeight=24, baselineY=None, note='points right; tip at x=91'),
    'fireball': dict(file='fireball.png', frameWidth=96, frameHeight=96, columns=3, rows=1, framesPerLook=3, looks=['fire'],
                     animations=dict(fly=anim([0, 1, 2], 12)), drawWidth=72, drawHeight=72, baselineY=None, note='travels right'),
    'bite': dict(file='bite.png', frameWidth=96, frameHeight=96, columns=3, rows=1, framesPerLook=3, looks=['claw'],
                 animations=dict(hit=anim([0, 1, 2], 18, False)), drawWidth=84, drawHeight=84, baselineY=None),
}
ICONS = ['fur', 'treat', 'hammer', 'crystal', 'meat']
for n in ICONS:
    MANIFEST[n] = dict(file=f'{n}.png', frameWidth=120, frameHeight=120, columns=1, rows=1, framesPerLook=1, looks=['icon'], animations=dict(still=anim([0], 1)), drawWidth=60, drawHeight=60, baselineY=None)

def contact(out_dir, sheets):
    W = 2400; bg = (31, 42, 51, 255)
    try: F = ImageFont.truetype(os.path.join(HERE, 'fonts', 'IBMPlexSans-SemiBold.ttf'), 22); Fs = ImageFont.truetype(os.path.join(HERE, 'fonts', 'IBMPlexSans-SemiBold.ttf'), 16)
    except Exception: F = Fs = ImageFont.load_default()
    blocks = []
    for name, arr in sheets.items():
        m = MANIFEST[name]; im = Image.fromarray(arr); sc = min(1.0, (W-40)/im.width)
        if name in ICONS: continue
        blocks.append((f'{name}.png  {im.width}x{im.height}  frame {m["frameWidth"]}x{m["frameHeight"]}', im, sc, m, name))
    icons = [Image.fromarray(sheets[n]) for n in ICONS]
    # layout: each sheet, then its animations (look 0) frame by frame, with frame boxes and the ground line marked
    rows = []
    for label, im, sc, m, name in blocks:
        fw, fh = m['frameWidth'], m['frameHeight']; cols = m['columns']
        def cell(look, f):
            idx = look*m['framesPerLook']+f; return im.crop(((idx % cols)*fw, (idx//cols)*fh, (idx % cols+1)*fw, (idx//cols+1)*fh))
        strips = []
        for an, a in m['animations'].items():
            if len(a['frames']) < 2: continue
            strips.append((f'{an} {a["frames"]} @{a["fps"]}fps', [cell(0, f) for f in a['frames']]))
        rows.append((label, im, sc, strips, m))
    H = 30;
    for label, im, sc, strips, m in rows:
        H += 34+int(im.height*sc)+14
        if strips: H += 26+max(m['frameHeight'] for _ in strips)+18
    H += 34+130
    cv = Image.new('RGBA', (W, H), bg); d = ImageDraw.Draw(cv); y = 20
    for label, im, sc, strips, m in rows:
        d.text((20, y), label, font=F, fill=(232, 220, 192, 255)); y += 34
        fw, fh = int(m['frameWidth']*sc), int(m['frameHeight']*sc); sim = im.resize((int(im.width*sc), int(im.height*sc)), Image.LANCZOS) if sc != 1 else im
        for gx in range(0, sim.width, max(fw, 1)):
            for gy in range(0, sim.height, max(fh, 1)): d.rectangle((20+gx, y+gy, 20+gx+fw-1, y+gy+fh-1), outline=(52, 66, 78, 255))
        cv.alpha_composite(sim, (20, y))
        y += sim.height+14
        if strips:
            x = 20; fw0, fh0 = m['frameWidth'], m['frameHeight']
            for an, frames in strips:
                if x+len(frames)*fw0 > W-20: break
                d.text((x, y), an, font=Fs, fill=(166, 147, 106, 255))
                for k, f in enumerate(frames):
                    fx = x+k*fw0; d.rectangle((fx, y+24, fx+fw0-1, y+24+fh0-1), outline=(52, 66, 78, 255))
                    if m.get('baselineY'): d.line((fx, y+24+m['baselineY'], fx+fw0-1, y+24+m['baselineY']), fill=(90, 70, 60, 255))
                    cv.alpha_composite(f, (fx, y+24))
                x += len(frames)*fw0+40
            y += 26+fh0+18
    d.text((20, y), 'icons: ' + ', '.join(ICONS) + '  (120x120)', font=F, fill=(232, 220, 192, 255)); y += 34
    for k, ic in enumerate(icons): cv.alpha_composite(ic, (20+k*140, y))
    cv.save(os.path.join(out_dir, 'contact.png'))

def build(out_dir):
    os.makedirs(out_dir, exist_ok=True); t0 = time.time()
    sheets = dict(slime=slime_sheet(), hopper=hopper_sheet(), wolf=wolf_sheet(), boar=boar_sheet(), bat=bat_sheet(),
                  golem=golem_sheet(False), warden=golem_sheet(True), pets=pets_sheet(),
                  arrow=frame_strip([arrow(i) for i in range(2)], 96, 32), fireball=frame_strip([fireball(i) for i in range(3)], 96, 96),
                  bite=frame_strip([claw(i) for i in range(3)], 96, 96))
    for n in ICONS: sheets[n] = icon6(n)
    for name, arr in sheets.items():
        m = MANIFEST[name]; h, w = arr.shape[:2]
        assert (w, h) == (m['frameWidth']*m['columns'], m['frameHeight']*m['rows']), (name, w, h)
        C.save(arr, os.path.join(out_dir, m['file']))
    man = dict(about='Greenhollow creatures, pets and effects. Frames run left to right, top to bottom; row = look where a sheet has several looks. '
                     'Animation frame numbers are within one look: absolute frame = look*framesPerLook + n. Creatures face RIGHT (mirror for left). '
                     'baselineY is the pixel row of the ground line inside a frame. drawWidth/drawHeight are suggested on-screen sizes in the 1920x1080 world.',
               world=dict(width=1920, height=1080, hero=dict(drawWidth=102, drawHeight=136), slime=dict(drawWidth=96, drawHeight=96)),
               facing='right', sheets=MANIFEST)
    with open(os.path.join(out_dir, 'creatures.json'), 'w') as f: json.dump(man, f, indent=2)
    contact(out_dir, sheets)
    return time.time()-t0

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out6_creatures')
    print('built in %.1fs' % build(out))
