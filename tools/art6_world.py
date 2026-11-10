# Greenhollow's wider world: the river town of Brookmere, the meadow, the cave, and the paintings of the intro story.
# Drawn with art4's pen and paper: wobbling curves, flat coats of gouache, one shade side, a light edge, thick ink.
import json, math, os, random, sys, time
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art4 as C
import art2 as P
import art3 as B

INK = C.INK
rgb = C.rgb
TILE = 64

# ---- pen and paper
def _paint(s, m, col, alpha=255, clip=None):
    "art4's paint, but only over the box the mask touches: the same picture, much faster on big sheets."
    if clip is not None: m = ImageChops.multiply(m, clip)
    bb = m.getbbox()
    if not bb: return
    m = m.crop(bb)
    if alpha < 255: m = m.point(lambda v: v * alpha // 255)
    s.im.paste(Image.new('RGBA', m.size, rgb(col) + (255,)), bb[:2], m)
C.Sheet.paint = _paint

class Sh(C.Sheet):
    def poly(s, pts, col, lw=2.6, wob=1.0): return s.shape(pts, col, lw=lw, smooth=False, wob=wob)
    def coat(s, pts, col, clip, wob=2.0, smooth=True, alpha=255):
        p = s.curve(pts, True, wob) if smooth else s.rough(pts, wob)
        return s.fill(p, col, alpha=alpha, clip=clip)
    def ink(s, p, w=2.4, clip=None): s.line(p, w, INK, closed=True, taper=False, clip=clip)

def ell(cx, cy, rx, ry, n=20, a0=0.0, a1=2 * math.pi, closed=True):
    t = np.linspace(a0, a1, n, endpoint=not closed)
    return [(cx + math.cos(a) * rx, cy + math.sin(a) * ry) for a in t]
def save(a, p): Image.fromarray(a).save(p)
def scale(img, k):
    im = Image.fromarray(img); return np.asarray(im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)).copy()
def place(dst, img, x, yb, k=1.0):
    im = scale(img, k) if k != 1 else img; P.over(dst, im, x, yb - im.shape[0]); return im
def radial(h, w, cx, cy, rx, ry, pw=2.0):
    Y, X = np.mgrid[0:h, 0:w]; return np.clip(1 - np.hypot((X - cx) / rx, (Y - cy) / ry), 0, 1) ** pw
def screen(a, g, col):
    c = np.array(rgb(col), float) / 255; b = a[..., :3].astype(float) / 255
    a[..., :3] = ((1 - (1 - b) * (1 - c * g[..., None])) * 255).astype(np.uint8)
def mix(a, g, col):
    a[..., :3] = (a[..., :3] * (1 - g[..., None]) + np.array(rgb(col), float) * g[..., None]).astype(np.uint8)
def tint(img, mul):
    o = img.copy(); o[..., :3] = np.clip(o[..., :3] * np.array(mul, float), 0, 255).astype(np.uint8); return o
def halo_behind(a, cx, cy, rx, ry, col, amt, pw=2.0):
    "A soft glow laid under a drawing, so it shines out into the air around it."
    h, w = a.shape[:2]; g = radial(h, w, cx, cy, rx, ry, pw) * amt
    o = np.zeros_like(a); o[..., :3] = rgb(col); o[..., 3] = (np.clip(g, 0, 1) * 255).astype(np.uint8)
    P.over(o, a, 0, 0); return o
def glow_from(a, alpha_src, radius, col, amt):
    "Light spilling from whatever was painted in alpha_src (an HxW 0..1 map)."
    g = P.blur(alpha_src, radius) * amt; screen(a, np.clip(g, 0, 1), col)
def sky(h, w, cols, horizon, seed, jit=.3, cell=90):
    v = np.clip(np.linspace(0, 1, h)[:, None] * np.ones((h, w)) * (h / horizon) + (P.fbm(h, w, cell, seed, 3) - .5) * jit, 0, 1)
    return np.dstack([C.bands(v, cols), np.full((h, w), 255, np.uint8)])
def mist(a, base, spread, col, amt, seed, cell=120):
    h, w = a.shape[:2]; Y = np.arange(h)[:, None]; n = P.fbm(h, w, cell, seed, 3)
    q = np.clip(1 - np.abs(Y - base) / spread, 0, 1) * np.clip((n - .28) / .34, 0, 1) * amt; mix(a, q, col)
def vignette(a, amt=.7, inner=.45, cy=540):
    h, w = a.shape[:2]; Y, X = np.mgrid[0:h, 0:w]
    v = np.clip(np.hypot((X - w / 2) / (w * .6), (Y - cy) / (h * .67)) - inner, 0, 1) * 1.3
    a[..., :3] = (a[..., :3] * (1 - np.clip(v, 0, 1)[..., None] * amt)).astype(np.uint8)
def hires(fn, ss, *args):
    "Runs one of art4's drawings on bigger paper, so a painting can show it large without blur."
    k = ss / 3; old, od = C.SS, C.Sheet.done
    def done(sh, grain=.09):
        im = sh.im.resize((round(sh.w * k), round(sh.h * k)), Image.LANCZOS); return C.gouache(np.asarray(im).copy(), sh.n & 0xffff, grain)
    C.SS = ss; C.Sheet.done = done
    try: return fn(*args)
    finally: C.SS = old; C.Sheet.done = od
def layer(sheet):
    "A big sheet finished without paper grain: the painting gets its grain once, at the end."
    return np.asarray(sheet.im.resize((sheet.w, sheet.h), Image.LANCZOS)).copy()

# ---- building parts
STONE = ('#7d7680', '#8a8390', '#6b6673', '#958e9b')
WOOD = ('#6a4a35', '#4c3529', '#8a6446')
def beam(s, a, b, wd, col='#4a3429'):
    (x0, y0), (x1, y1) = a, b; dx, dy = x1 - x0, y1 - y0; l = max(math.hypot(dx, dy), 1); nx, ny = -dy / l * wd / 2, dx / l * wd / 2
    q, m = s.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], col, lw=2.4, wob=1.2)
    r = s.r
    for _ in range(2):
        t = r.uniform(.05, .6); u = t + r.uniform(.15, .35); o = r.uniform(-.28, .28)
        s.stroke([(x0 + dx * t + nx * o * 2, y0 + dy * t + ny * o * 2), (x0 + dx * u + nx * o * 2, y0 + dy * u + ny * o * 2)], 1.1, '#231a18', wob=.5, clip=m)
    return m
def stones(s, clip, x0, y0, x1, y1, cols=STONE, rowh=(17, 23), wd=(26, 44), lw=1.6):
    r = s.r; y = y0
    while y < y1:
        h = r.randint(*rowh); x = x0 - r.randint(0, 22)
        while x < x1:
            w = r.randint(*wd); p = s.rough([(x + 1, y + 1), (x + w - 1, y + 1 + r.uniform(-1, 1)), (x + w - 1, y + h - 1), (x + 1, y + h - 1)], .9)
            s.fill(p, r.choice(cols), clip=clip); s.line(p, lw, INK, closed=True, taper=False, clip=clip); x += w
        y += h
def bricks(s, clip, x0, y0, x1, y1, col='#5a3428'):
    r = s.r; y = y0; row = 0
    while y < y1:
        s.stroke([(x0, y), (x1, y + r.uniform(-1, 1))], 1.2, col, clip=clip, wob=.4)
        x = x0 + (row % 2) * 14 + r.randint(-2, 2)
        while x < x1: s.stroke([(x, y), (x + r.uniform(-.5, .5), y + 10)], 1.1, col, clip=clip, wob=.1); x += 28
        y += 11; row += 1
def tile_rows(s, clip, W, y0, y1, inset=30, col=INK):
    r = s.r; y = y0
    while y < y1:
        off = r.randint(0, 18); ins = int((1 - (y - y0) / max(y1 - y0, 1)) * inset); x = -off + ins
        while x < W - ins:
            w0 = r.randint(25, 38)
            if r.random() < .82: s.stroke([(x + 3, y + r.uniform(-1, 1)), (x + w0 / 2, y + r.uniform(4, 7)), (x + w0 - 2, y + r.uniform(-1, 1))], r.uniform(1.3, 2.3), col, clip=clip, wob=.4)
            if r.random() < .6: s.stroke([(x + w0 - 2, y - 1), (x + w0 - 1 + r.uniform(-1, 1), y - r.uniform(10, 16))], 1.3, col, clip=clip, wob=.3)
            x += w0
        y += r.randint(18, 23)
def slate_rows(s, clip, x0, x1, y0, y1, rowh=(14, 18), col=INK, light=None):
    r = s.r; y = y0
    while y < y1:
        s.stroke([(x0, y), ((x0 + x1) / 2, y + r.uniform(-1.5, 1.5)), (x1, y)], r.uniform(1.4, 2.0), col, clip=clip, wob=.6)
        x = x0 + r.randint(0, 24)
        while x < x1:
            w = r.randint(20, 32)
            s.stroke([(x, y), (x + r.uniform(-1, 1), y - r.uniform(9, 13))], 1.2, col, clip=clip, wob=.2)
            if light and r.random() < .1: s.fill(s.rough([(x + 2, y - 12), (x + w - 2, y - 12), (x + w - 2, y - 2), (x + 2, y - 2)], .5), light, clip=clip)
            x += w
        y += r.randint(*rowh)
def planks(s, clip, x0, x1, y0, y1, step=(16, 24), col='#2f221d'):
    r = s.r; x = x0 + r.randint(4, 12)
    while x < x1:
        s.stroke([(x, y0), (x + r.uniform(-1.5, 1.5), y1)], 1.4, col, clip=clip, wob=.5)
        if r.random() < .35: k = r.uniform(y0 + 10, y1 - 10); s.stroke([(x + 5, k), (x + 9, k + 3)], 1.2, col, clip=clip, wob=.2)
        x += r.randint(*step)
def arch_pts(x0, y0, x1, y1):
    rad = (x1 - x0) / 2; cx = (x0 + x1) / 2; cy = y0 + rad
    return [(x0, y1), (x0, cy)] + [(cx - math.cos(t) * rad, cy - math.sin(t) * rad) for t in np.linspace(.2, math.pi - .2, 9)] + [(x1, cy), (x1, y1)]
GLASS_LIT = ('#f0bd5c', '#d38f39', '#fbe3a4'); GLASS_DARK = ('#2f4b78', '#1e3158', '#5d7aa0')
def window(s, x, y, a, b, arch=False, shut=None, box=False, frame='#3a2922', lit=True, panes=2):
    r = s.r
    if shut:
        for sx in (x - 9 - a * .5, x + a + 9):
            p, m = s.poly([(sx, y - 4), (sx + a * .5, y - 4), (sx + a * .5, y + b + 4), (sx, y + b + 4)], shut, lw=2.2, wob=.8)
            for k in (1, 2): s.stroke([(sx + a * .5 * k / 3, y), (sx + a * .5 * k / 3, y + b)], 1.2, clip=m, wob=.3)
    rect = (lambda x0, y0, x1, y1: arch_pts(x0, y0, x1, y1)) if arch else (lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    s.poly(rect(x - 7, y - 7, x + a + 7, y + b + 7), frame, lw=2.6, wob=1.0)
    gl = GLASS_LIT if lit else GLASS_DARK
    g, gm = s.poly(rect(x, y, x + a, y + b), gl[0], lw=2, wob=.6)
    s.coat([(x + a + 4, y + b * .1), (x + a * .55, y + b * .36), (x + a * .25, y + b + 6), (x + a + 6, y + b + 6)], gl[1], gm, 1.4)
    t = a * .32 if arch else 0
    s.coat([(x + 4, y + 4 + t), (x + a * .38, y + 4 + t), (x + a * .3, y + b * .38), (x + 4, y + b * .44)], gl[2], gm, 1)
    for k in range(1, panes): s.stroke([(x + a * k / panes, y), (x + a * k / panes + r.uniform(-1, 1), y + b)], 3, clip=gm)
    s.stroke([(x, y + b * .5), (x + a, y + b * .5)], 3, clip=gm)
    if box:
        by = y + b + 7; s.poly([(x - 11, by), (x + a + 11, by - 1), (x + a + 8, by + 13), (x - 8, by + 13)], '#5a3f30', lw=2.4, wob=.8)
        for k in range(8):
            fx = x - 7 + k * (a + 14) / 7 + r.uniform(-2, 2); fy = by - r.uniform(3, 9)
            s.shape([(fx - 6, fy + 2), (fx, fy - 5), (fx + 6, fy + 2), (fx, fy + 6)], r.choice(('#a84f55', '#d8a24a', '#7f5a93', '#3f5f3f', '#3f5f3f')), lw=1.6, wob=.3)
def door(s, dx, bot, w, h, col='#6a4a35', dark='#4c3529', frame='#3a2922', knob=True):
    r = s.r; top = bot - h
    s.shape([(dx - 10, bot), (dx - 9, top + 16), (dx + w / 2, top - 8), (dx + w + 9, top + 16), (dx + w + 10, bot)], frame, lw=3, wob=1)
    dp, dm = s.shape([(dx - 1, bot + 1), (dx, top + 14), (dx + w / 2, top + 2), (dx + w, top + 14), (dx + w + 1, bot + 1)], col, lw=2.2, wob=.7)
    s.coat([(dx + w * .58, top - 4), (dx + w + 6, top + 6), (dx + w + 6, bot + 6), (dx + w * .7, bot + 6)], dark, dm, 1)
    for k in (.27, .5, .73): s.stroke([(dx + w * k + r.uniform(-1, 1), top + 4), (dx + w * k + r.uniform(-1, 1), bot)], 1.6, clip=dm)
    for y in (top + 26, bot - 30): s.poly([(dx, y - 4), (dx + w - 2, y - 5), (dx + w - 2, y + 3), (dx, y + 4)], '#2f2a2b', lw=1.4, wob=.5)
    if knob: s.shape(ell(dx + w * .8, bot - h * .45, 4, 4, 8), '#d7a941', lw=1.6, wob=.2)
    return dm
def chimney(s, x, top, bot, w=40, brick=False):
    r = s.r; col = '#8a4a3a' if brick else '#6d6470'
    p, m = s.poly([(x - 1, bot), (x + 1, top + 10), (x + w, top + 8), (x + w + 2, bot)], col, lw=3, wob=1.2)
    s.coat([(x + w * .62, top), (x + w + 6, top), (x + w + 6, bot + 4), (x + w * .66, bot + 4)], '#6a3428' if brick else '#544c58', m, 1)
    s.poly([(x - 7, top + 6), (x + w + 7, top + 3), (x + w + 8, top + 17), (x - 6, top + 19)], '#5a3428' if brick else '#4a4350', lw=3, wob=1)
    if brick: bricks(s, m, x, top + 28, x + w, bot, '#4a2a22')
    else:
        for y in range(top + 30, bot - 6, 15):
            for xx in range(x + r.randint(3, 9), x + w - 6, 14): s.stroke([(xx, y), (xx + 9, y + r.uniform(-1, 1))], 1.6)
def hang_sign(s, x, y, icon, side=1, board='#a07a52', span=78):
    "An iron arm from the wall, two short chains and a painted board with a picture instead of words."
    s.stroke([(x, y), (x + side * span, y + 1)], 4.6, '#2a2326', wob=.3)
    s.stroke([(x, y + 26), (x + side * span * .45, y + 2)], 3, '#2a2326', wob=.3)
    s.stroke([(x + side * span, y + 1), (x + side * (span + 6), y - 5), (x + side * (span + 1), y - 9)], 2.6, '#2a2326', wob=.2)
    a, b = x + side * 14, x + side * (span - 4); x0, x1 = min(a, b), max(a, b)
    for cx in (x0 + 6, x1 - 6): s.stroke([(cx, y + 2), (cx, y + 14)], 1.8, '#2a2326', wob=.1)
    p, m = s.poly([(x0 - 2, y + 13), (x1 + 2, y + 12), (x1 + 3, y + 58), (x0 - 1, y + 60)], board, lw=2.8, wob=.9)
    s.coat([(x0 + (x1 - x0) * .6, y + 8), (x1 + 6, y + 8), (x1 + 6, y + 66), (x0 + (x1 - x0) * .5, y + 66)], '#7b5c42', m, 1.2)
    s.line(s.rough([(x0 + 5, y + 18), (x1 - 5, y + 17), (x1 - 4, y + 53), (x0 + 5, y + 54)], .5), 1.4, '#5a3f30', closed=True, taper=False)
    icon_draw(s, (x0 + x1) / 2, y + 36, icon)
def icon_draw(s, cx, cy, kind, k=1.0):
    if kind == 'loaf':
        s.shape([(cx - 22 * k, cy + 6 * k), (cx - 16 * k, cy - 8 * k), (cx, cy - 12 * k), (cx + 16 * k, cy - 8 * k), (cx + 22 * k, cy + 6 * k), (cx, cy + 10 * k)], '#c98a3f', lw=2.2, wob=.4)
        for d in (-10, 0, 10): s.stroke([(cx + (d - 3) * k, cy - 6 * k), (cx + (d + 3) * k, cy + 2 * k)], 1.6, wob=.1)
    elif kind == 'mug':
        p, m = s.poly([(cx - 13 * k, cy - 12 * k), (cx + 11 * k, cy - 12 * k), (cx + 10 * k, cy + 14 * k), (cx - 12 * k, cy + 14 * k)], '#c9b892', lw=2.2, wob=.3)
        s.shape([(cx - 15 * k, cy - 12 * k), (cx - 6 * k, cy - 19 * k), (cx + 4 * k, cy - 16 * k), (cx + 13 * k, cy - 13 * k), (cx + 9 * k, cy - 7 * k), (cx - 12 * k, cy - 7 * k)], '#f2ead8', lw=2, wob=.4)
        s.stroke([(cx + 11 * k, cy - 6 * k), (cx + 20 * k, cy - 2 * k), (cx + 19 * k, cy + 7 * k), (cx + 10 * k, cy + 9 * k)], 3, wob=.1)
    elif kind == 'bottle':
        s.poly([(cx - 4 * k, cy - 20 * k), (cx + 4 * k, cy - 20 * k), (cx + 4 * k, cy - 13 * k), (cx - 4 * k, cy - 13 * k)], '#5c3f2b', lw=1.8, wob=.2)
        p, m = s.shape([(cx - 5 * k, cy - 14 * k), (cx + 5 * k, cy - 14 * k), (cx + 6 * k, cy - 6 * k), (cx + 15 * k, cy + 3 * k), (cx + 12 * k, cy + 14 * k), (cx, cy + 17 * k), (cx - 12 * k, cy + 14 * k), (cx - 15 * k, cy + 3 * k), (cx - 6 * k, cy - 6 * k)], '#b6c4c4', lw=2.2, wob=.3)
        s.coat([(cx - 18 * k, cy), (cx + 18 * k, cy - 2 * k), (cx + 18 * k, cy + 20 * k), (cx - 18 * k, cy + 20 * k)], '#4f9a6a', m, .6)
        s.stroke([(cx - 8 * k, cy + 2 * k), (cx - 7 * k, cy + 9 * k)], 2, '#e6f2e0', clip=m, wob=.1)
    elif kind == 'paw':
        s.shape(ell(cx, cy + 6 * k, 12 * k, 10 * k, 10), '#4a3429', lw=1.8, wob=.4)
        for dx, dy, rr in ((-14, -6, 5), (-5, -14, 5.5), (6, -14, 5.5), (15, -6, 5)): s.shape(ell(cx + dx * k, cy + dy * k, rr * k, rr * 1.15 * k, 8), '#4a3429', lw=1.6, wob=.3)
    elif kind == 'house':
        s.stroke([(cx - 12 * k, cy), (cx, cy - 11 * k), (cx + 12 * k, cy)], 3, wob=.2); s.stroke([(cx - 9 * k, cy), (cx - 9 * k, cy + 11 * k), (cx + 9 * k, cy + 11 * k), (cx + 9 * k, cy)], 3, wob=.2)
    elif kind == 'tower':
        s.stroke([(cx - 7 * k, cy + 12 * k), (cx - 7 * k, cy - 8 * k), (cx + 7 * k, cy - 8 * k), (cx + 7 * k, cy + 12 * k)], 3, wob=.2)
        s.stroke([(cx - 9 * k, cy - 8 * k), (cx - 9 * k, cy - 13 * k), (cx - 3 * k, cy - 13 * k)], 2.4, wob=.1); s.stroke([(cx + 3 * k, cy - 13 * k), (cx + 9 * k, cy - 13 * k), (cx + 9 * k, cy - 8 * k)], 2.4, wob=.1)
        s.stroke([(cx - 16 * k, cy + 12 * k), (cx + 16 * k, cy + 12 * k)], 2.4, wob=.2)
    elif kind == 'wave':
        for dy in (-6, 4):
            s.stroke([(cx - 16 * k, cy + dy * k), (cx - 8 * k, cy + (dy - 5) * k), (cx, cy + dy * k), (cx + 8 * k, cy + (dy - 5) * k), (cx + 16 * k, cy + dy * k)], 3, '#d4a24c', wob=.2)
def awning(s, x0, x1, y0, y1, c1, c2, n=7, drop=8, hem=14):
    "A striped cloth sloping out from the wall, with a scalloped hem."
    p, m = s.poly([(x0, y0), (x1, y0), (x1 + drop, y1), (x0 - drop, y1)], c1, lw=0, wob=.7)
    for i in range(0, n, 2):
        a, b = i / n, (i + 1) / n
        s.fill(s.rough([(x0 + (x1 - x0) * a, y0 - 2), (x0 + (x1 - x0) * b, y0 - 2), (x0 - drop + (x1 - x0 + 2 * drop) * b, y1 + 2), (x0 - drop + (x1 - x0 + 2 * drop) * a, y1 + 2)], .6), c2, clip=m)
    s.coat([(x0 - 20, y0 - 10), (x1 + 20, y0 - 10), (x1 + 20, y0 + (y1 - y0) * .3), (x0 - 20, y0 + (y1 - y0) * .36)], '#2a1f1c', m, 1.5, alpha=70)
    s.ink(p, 3)
    for i in range(n):
        a, b = i / n, (i + 1) / n; xa = x0 - drop + (x1 - x0 + 2 * drop) * a; xb = x0 - drop + (x1 - x0 + 2 * drop) * b
        s.shape([(xa + 1, y1), (xb - 1, y1), (xb - 2, y1 + hem * .6), ((xa + xb) / 2, y1 + hem), (xa + 2, y1 + hem * .6)], c1 if i % 2 else c2, lw=2.2, wob=.4)

# ---- Brookmere: town houses
def town_house(kind, seed):
    W, H = 384, 540; s = Sh(W, H, seed); r = s.r
    jet = 334  # where the upper storey overhangs the shop floor
    if kind == 'a':
        rd, rm, rl = '#5b2c2a', '#9a4e38', '#b8704e'; eave = 178
        chimney(s, W - 112, 2, 92)
        sag = r.uniform(3, 7)
        rp = s.curve([(-1, eave + 13), (30, 34), (W * .3, 32 + sag), (W * .7, 30 + sag * .6), (W - 30, 34), (W + 1, eave + 13), (W * .72, eave + 17), (W * .3, eave + 11)], True, 1.4)
        rk = s.fill(rp, rm)
        s.coat([(-8, eave - 48), (W * .3, eave - 36), (W * .65, eave - 52), (W + 8, eave - 42), (W + 8, eave + 30), (-8, eave + 30)], rd, rk, 3)
        s.coat([(44, 40), (W * .32, 38), (W * .4, 64), (W * .22, 100), (30, 104)], rl, rk, 3)
        tile_rows(s, rk, W, 52, eave + 2)
        s.ink(rp, 4)
        # a dormer in the middle of the roof
        dx = W / 2 - 46
        s.poly([(dx, eave - 14), (dx + 2, 82), (dx + 90, 80), (dx + 92, eave - 14)], '#c9b892', lw=2.8, wob=.8)
        window(s, dx + 22, 98, 48, 46)
        s.shape([(dx - 16, 92), (dx + 46, 46), (dx + 108, 92), (dx + 98, 100), (dx + 46, 62), (dx - 6, 100)], rd, lw=3, wob=.8)
    elif kind == 'b':
        rd, rm, rl = '#232b44', '#3c4a68', '#5b6d90'; eave = 196
        rp = s.rough([(W / 2, 4), (W + 2, eave + 12), (W - 30, eave + 16), (30, eave + 16), (-2, eave + 12)], 1.2); rk = s.fill(rp, rm)
        s.coat([(W / 2, -10), (W + 10, eave), (W + 10, eave + 30), (W / 2 + 30, eave + 30)], rd, rk, 2)
        for d in range(10, 70, 13):
            s.stroke([(W / 2 - d * .5, 4 + d), (-2 + d * .2, eave + 12 + d * .1)], 1.5, clip=rk, wob=.5)
            s.stroke([(W / 2 + d * .5, 4 + d), (W + 2 - d * .2, eave + 12 + d * .1)], 1.5, clip=rk, wob=.5)
        s.ink(rp, 4)
        # the gable end, plaster and timber, with a round window
        gp, gm = s.poly([(W / 2, 46), (W - 26, eave + 2), (W - 22, jet), (22, jet), (26, eave + 2)], '#dcc08a', lw=3, wob=1.2)
        s.coat([(W * .55, 40), (W, eave), (W, jet + 10), (W * .7, jet + 10), (W * .62, eave + 60)], '#b89c6c', gm, 3)
        s.coat([(40, eave + 20), (W * .3, eave + 6), (W * .5, eave + 24), (W * .2, eave + 54)], '#efdcac', gm, 3)
        for x in (W / 2 - 96, W / 2 + 86): beam(s, (x, eave - 20 if abs(x - W / 2) < 100 else eave), (x + r.uniform(-2, 2), jet), 13)
        beam(s, (24, eave + 6), (W - 24, eave + 5), 14)
        beam(s, (W / 2 - 92, eave + 10), (W / 2 - 150, jet - 4), 11); beam(s, (W / 2 + 92, eave + 10), (W / 2 + 150, jet - 4), 11)
        s.shape(ell(W / 2, 120, 30, 30, 16), '#3a2922', lw=2.8, wob=.6)
        g, gk = s.shape(ell(W / 2, 120, 21, 21, 14), GLASS_LIT[0], lw=2, wob=.4)
        s.coat([(W / 2 + 4, 104), (W / 2 + 26, 116), (W / 2 + 14, 144), (W / 2 - 6, 140)], GLASS_LIT[1], gk, 1)
        s.stroke([(W / 2, 99), (W / 2, 141)], 3); s.stroke([(W / 2 - 21, 120), (W / 2 + 21, 120)], 3)
        window(s, W / 2 - 54, eave + 40, 108, 66, panes=3, box=True)
        # bargeboards along the gable
        s.stroke([(W / 2, 30), (20, eave + 8)], 9, '#4a3429', wob=.5); s.stroke([(W / 2, 30), (W - 20, eave + 8)], 9, '#4a3429', wob=.5)
        s.stroke([(W / 2, 22), (14, eave + 6)], 2.2, wob=.4); s.stroke([(W / 2, 22), (W - 14, eave + 6)], 2.2, wob=.4)
        s.shape([(W / 2 - 7, 30), (W / 2, 8), (W / 2 + 7, 30)], '#4a3429', lw=2.2, wob=.3)
    else:
        rd, rm, rl = '#1d3836', '#33605a', '#4f8073'; eave = 172
        chimney(s, 46, 2, 78, 38, brick=True)
        rp = s.curve([(-1, eave + 12), (52, 30), (W - 52, 28), (W + 1, eave + 12), (W * .7, eave + 16), (W * .3, eave + 12)], True, 1.2); rk = s.fill(rp, rm)
        s.coat([(-8, eave - 44), (W * .4, eave - 30), (W + 8, eave - 50), (W + 8, eave + 30), (-8, eave + 30)], rd, rk, 3)
        s.coat([(60, 34), (W * .5, 32), (W * .44, 52), (70, 64)], rl, rk, 2)
        slate_rows(s, rk, 0, W, 48, eave + 4, light=rl)
        s.ink(rp, 4)
        for dx in (W * .22 - 34, W * .7 - 34):
            dp, dk = s.poly([(dx, eave - 6), (dx, 92), (dx + 68, 92), (dx + 68, eave - 6)], '#cbb995', lw=2.6, wob=.8)
            window(s, dx + 16, 100, 36, 50, arch=True)
            s.shape([(dx - 10, 98), (dx + 4, 74), (dx + 34, 64), (dx + 64, 74), (dx + 78, 98), (dx + 34, 86)], rd, lw=2.8, wob=.6)
    # ---- the upper storey
    if kind == 'a':
        wp = s.rough([(6, eave + 12), (W - 6, eave + 12), (W - 6, jet), (6, jet)], 1.4); wm = s.fill(wp, '#d4c19a')
        s.coat([(0, eave + 8), (W, eave + 8), (W, eave + 34), (W * .7, eave + 44), (W * .4, eave + 32), (0, eave + 44)], '#8d7d68', wm, 2.4)
        s.coat([(W * .6, eave + 60), (W, eave + 50), (W, jet), (W * .66, jet)], '#b3a17f', wm, 3)
        s.ink(wp, 3)
        for x in (8, W / 3 + 2, 2 * W / 3 - 2, W - 22): beam(s, (x + 7, eave + 12), (x + 7 + r.uniform(-2, 2), jet), 14)
        a0, a1 = W / 3 + 16, 2 * W / 3 - 16
        beam(s, (a0, eave + 26), (a1, jet - 8), 11); beam(s, (a1, eave + 26), (a0, jet - 8), 11)
        for x in (36, W - 36 - 62): window(s, x, eave + 46, 62, 72, shut='#3f6b4a', box=True)
    elif kind == 'c':
        wp = s.rough([(8, eave + 12), (W - 8, eave + 12), (W - 8, jet), (8, jet)], 1.4); wm = s.fill(wp, '#9c5f4a')
        s.coat([(0, eave + 8), (W, eave + 8), (W, eave + 32), (W * .5, eave + 40), (0, eave + 30)], '#5e3a30', wm, 2.4)
        s.coat([(W * .64, eave + 40), (W, eave + 40), (W, jet), (W * .7, jet)], '#83503f', wm, 3)
        bricks(s, wm, 8, eave + 40, W - 8, jet)
        s.ink(wp, 3)
        for x0 in (8, W - 34):
            for y in range(eave + 14, jet - 10, 30): s.poly([(x0, y), (x0 + 26, y), (x0 + 26, y + 28), (x0, y + 28)], r.choice(('#b9b2a8', '#a59e96')), lw=2, wob=.6)
        for x in (64, W - 64 - 52): window(s, x, eave + 44, 52, 80, arch=True, box=True)
        s.shape(ell(W / 2, eave + 82, 22, 22, 12), '#c9b892', lw=2.6, wob=.5); icon_draw(s, W / 2, eave + 84, 'bottle', .7)
    # the floor beam and its brackets
    beam(s, (-2, jet + 2), (W + 2, jet + r.uniform(-2, 2)), 16, '#3f2c24')
    for x in (30, W / 2, W - 30): s.poly([(x - 8, jet + 10), (x + 8, jet + 10), (x + 3, jet + 30), (x - 3, jet + 30)], '#3f2c24', lw=2.2, wob=.5)
    # ---- the shop floor
    g0, g1 = jet + 10, H - 16
    if kind == 'a':
        gp = s.rough([(14, g0), (W - 14, g0), (W - 14, g1), (14, g1)], 1.2); gm = s.fill(gp, '#7d7680')
        stones(s, gm, 14, g0, W - 14, g1, ('#857e88', '#77707e', '#8f8892', '#6e6874'))
        s.coat([(0, g0 - 4), (W, g0 - 4), (W, g0 + 26), (W * .5, g0 + 34), (0, g0 + 22)], '#3e3748', gm, 2, alpha=200)
        s.ink(gp, 3)
        # the bakery window: loaves on a shelf
        wx, wy, ww, wh = 34, g0 + 58, 150, 82
        s.poly([(wx - 9, wy - 9), (wx + ww + 9, wy - 9), (wx + ww + 9, wy + wh + 11), (wx - 9, wy + wh + 11)], '#3a2922', lw=2.8, wob=1)
        g, gk = s.poly([(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)], '#f0bd5c', lw=2, wob=.6)
        s.coat([(wx + ww * .6, wy - 4), (wx + ww + 4, wy), (wx + ww + 4, wy + wh + 4), (wx + ww * .4, wy + wh + 4)], '#d38f39', gk, 2)
        s.stroke([(wx, wy + wh * .55), (wx + ww, wy + wh * .55)], 4, '#5a3f30', clip=gk)
        for i in range(5):
            cx = wx + 18 + i * 29; cy = wy + wh * .55 - 9
            s.shape([(cx - 13, cy + 7), (cx - 9, cy - 4), (cx, cy - 7), (cx + 9, cy - 4), (cx + 13, cy + 7), (cx, cy + 9)], r.choice(('#b9823f', '#a26a32', '#c98a3f')), lw=1.8, wob=.3)
        for i in range(4):
            cx = wx + 24 + i * 34; cy = wy + wh - 12
            s.shape(ell(cx, cy, 13, 8, 10), r.choice(('#c98a3f', '#d8a24a')), lw=1.8, wob=.3)
        s.stroke([(wx + ww / 2, wy), (wx + ww / 2, wy + wh * .55)], 3)
        awning(s, wx - 8, wx + ww + 8, g0 + 16, g0 + 44, '#a8473a', '#e6d6b0', n=7)
        door(s, 248, g1, 66, 132)
        hang_sign(s, W - 22, g0 + 12, 'loaf', side=-1, span=74)
        s.poly([(214, g1 - 2), (226, g1 - 30), (236, g1 - 2)], '#6f523f', lw=1.6, wob=.3)
    elif kind == 'b':
        gp = s.rough([(16, g0), (W - 16, g0), (W - 16, g1), (16, g1)], 1.2); gm = s.fill(gp, '#3f5a4a')
        planks(s, gm, 16, W - 16, g0, g1, (14, 20), '#24352c')
        s.coat([(0, g0 - 4), (W, g0 - 4), (W, g0 + 26), (W * .5, g0 + 32), (0, g0 + 22)], '#1c2a24', gm, 2, alpha=220)
        s.coat([(W * .64, g0 + 40), (W, g0 + 40), (W, g1), (W * .74, g1)], '#33493c', gm, 3)
        s.ink(gp, 3)
        for x in (40, W - 40 - 72): window(s, x, g0 + 52, 72, 78, panes=3)
        door(s, W / 2 - 36, g1, 72, 146, '#7a3f30', '#5a2c22')
        # a lantern by the door
        lx = W / 2 + 54; s.stroke([(lx - 8, g0 + 44), (lx + 8, g0 + 44), (lx + 8, g0 + 54)], 2.6, '#2a2326', wob=.1)
        s.shape([(lx - 2, g0 + 56), (lx + 18, g0 + 56), (lx + 15, g0 + 84), (lx + 1, g0 + 84)], '#f7d67c', lw=2.4, wob=.3)
        s.poly([(lx - 4, g0 + 48), (lx + 20, g0 + 48), (lx + 16, g0 + 57), (lx, g0 + 57)], '#2a2326', lw=1.8, wob=.3)
        hang_sign(s, 20, g0 + 10, 'mug', side=1, span=80)
        # a barrel by the wall
        bx = W - 64; bp, bk = s.shape([(bx, g1 + 2), (bx - 4, g1 - 30), (bx, g1 - 58), (bx + 44, g1 - 58), (bx + 48, g1 - 30), (bx + 44, g1 + 2)], '#7a5236', lw=2.6, wob=.6)
        s.coat([(bx + 26, g1 - 64), (bx + 54, g1 - 64), (bx + 54, g1 + 6), (bx + 30, g1 + 6)], '#5a3d29', bk, 1)
        for y in (g1 - 48, g1 - 12): s.stroke([(bx - 3, y), (bx + 22, y + 3), (bx + 47, y)], 3, '#3a3236', clip=bk)
        s.shape(ell(bx + 22, g1 - 58, 22, 6, 12), '#8f6544', lw=2.2, wob=.3)
    else:
        gp = s.rough([(14, g0), (W - 14, g0), (W - 14, g1), (14, g1)], 1.2); gm = s.fill(gp, '#cbb995')
        s.coat([(0, g0 - 4), (W, g0 - 4), (W, g0 + 26), (W * .5, g0 + 34), (0, g0 + 22)], '#7d6f62', gm, 2)
        s.coat([(W * .6, g0 + 50), (W, g0 + 46), (W, g1), (W * .68, g1)], '#ab9a7c', gm, 3)
        stones(s, gm, 14, g1 - 40, W - 14, g1, ('#857e88', '#77707e', '#8f8892'), rowh=(18, 22))
        s.ink(gp, 3)
        for x0 in (14, W - 40):
            for y in range(g0 + 2, g1 - 40, 28): s.poly([(x0, y), (x0 + 26, y), (x0 + 26, y + 26), (x0, y + 26)], r.choice(('#b9b2a8', '#a59e96')), lw=2, wob=.6)
        door(s, 54, g1, 66, 120, '#4f5f7a', '#3a4660')
        hang_sign(s, 18, g0 + 8, 'bottle', side=1, span=82)
        wx, wy, ww, wh = 162, g0 + 64, 170, 78
        s.poly([(wx - 9, wy - 9), (wx + ww + 9, wy - 9), (wx + ww + 9, wy + wh + 11), (wx - 9, wy + wh + 11)], '#3a2922', lw=2.8, wob=1)
        g, gk = s.poly([(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)], '#f0bd5c', lw=2, wob=.6)
        s.coat([(wx + ww * .62, wy - 4), (wx + ww + 4, wy), (wx + ww + 4, wy + wh + 4), (wx + ww * .44, wy + wh + 4)], '#d38f39', gk, 2)
        for sy in (wy + 34, wy + wh - 2):
            s.stroke([(wx, sy), (wx + ww, sy)], 4, '#5a3f30', clip=gk)
            x = wx + 8
            while x < wx + ww - 12:
                hh = r.randint(14, 24); wd = r.randint(10, 16); col = r.choice(('#4f9a6a', '#7f5a93', '#a33c4b', '#3f6a9a', '#c79b42'))
                s.shape([(x, sy - 2), (x, sy - hh * .6), (x + wd * .3, sy - hh * .7), (x + wd * .3, sy - hh), (x + wd * .7, sy - hh), (x + wd * .7, sy - hh * .7), (x + wd, sy - hh * .6), (x + wd, sy - 2)], col, lw=1.6, wob=.3)
                x += wd + r.randint(3, 7)
        s.stroke([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], 3)
        awning(s, wx - 8, wx + ww + 8, g0 + 18, g0 + 46, '#2f6b66', '#e6d6b0', n=8)
    # the foundation stones
    x = -4
    while x < W:
        wd = r.randint(22, 36); s.shape([(x, H - 1), (x + 1, H - 17 - r.randint(0, 4)), (x + wd / 2, H - 20 - r.randint(0, 3)), (x + wd, H - 16 - r.randint(0, 4)), (x + wd + 1, H - 1)], r.choice(('#6b6673', '#7d7680', '#57525f')), lw=2.2, wob=.7); x += wd
    return s.done()

def shelter():
    "The animal shelter: a broad barn-like house with a paw on its gable, a kennel and a picket yard in front."
    W, H = 384, 440; s = Sh(W, H, 611); r = s.r; base = 344; eave = 158
    rp = s.rough([(W / 2, 6), (W + 2, eave + 14), (W - 28, eave + 18), (28, eave + 18), (-2, eave + 14)], 1.2); rk = s.fill(rp, '#4f6b48')
    s.coat([(W / 2, -10), (W + 10, eave), (W + 10, eave + 30), (W / 2 + 30, eave + 30)], '#3a5236', rk, 2)
    for d in range(10, 64, 12):
        for sg in (-1, 1):
            s.stroke([(W / 2 + sg * d * .5, 6 + d), (W / 2 + sg * (W / 2 + 2 - d * .2), eave + 14 + d * .1)], 1.5, clip=rk, wob=.6)
    s.ink(rp, 4)
    gp, gm = s.poly([(W / 2, 44), (W - 22, eave + 4), (W - 18, base), (18, base), (22, eave + 4)], '#9a6c48', lw=3, wob=1.2)
    planks(s, gm, 18, W - 18, 30, base, (18, 24), '#5a3d29')
    s.coat([(W * .56, 30), (W, eave), (W, base + 10), (W * .74, base + 10), (W * .64, eave + 70)], '#7a5236', gm, 3)
    s.coat([(36, eave + 30), (W * .3, eave + 12), (W * .4, eave + 40), (W * .2, eave + 90)], '#b5845a', gm, 3)
    s.coat([(0, eave), (W, eave), (W, eave + 26), (0, eave + 30)], '#4a3429', gm, 2, alpha=170)
    s.stroke([(W / 2, 28), (18, eave + 8)], 9, '#4a3429', wob=.5); s.stroke([(W / 2, 28), (W - 18, eave + 8)], 9, '#4a3429', wob=.5)
    # the paw sign on the gable
    s.shape(ell(W / 2, 104, 40, 38, 18), '#5a3f30', lw=3, wob=.6)
    p, pk = s.shape(ell(W / 2, 104, 31, 29, 16), '#e6d6b0', lw=2.2, wob=.5)
    s.coat([(W / 2 + 6, 74), (W / 2 + 36, 96), (W / 2 + 20, 140), (W / 2 + 2, 130)], '#cdbb92', pk, 1)
    icon_draw(s, W / 2, 106, 'paw', 1.1)
    # windows with flower boxes, and a split door with its top half open and a dog looking out
    for x in (40, W - 40 - 64): window(s, x, eave + 52, 64, 58, box=True, shut='#3f6b8a')
    dx, dw, dt = W / 2 - 42, 84, base - 140
    s.shape([(dx - 10, base), (dx - 9, dt + 16), (dx + dw / 2, dt - 10), (dx + dw + 9, dt + 16), (dx + dw + 10, base)], '#3a2922', lw=3, wob=1)
    ip, ik = s.shape([(dx, base), (dx, dt + 14), (dx + dw / 2, dt), (dx + dw, dt + 14), (dx + dw, base)], '#241a17', lw=2.2, wob=.6)
    hx, hy = W / 2, dt + 52
    s.shape([(hx - 30, hy - 14), (hx - 40, hy + 18), (hx - 30, hy + 26), (hx - 20, hy + 2)], '#7a4f27', lw=2.4, wob=.4)
    s.shape([(hx + 30, hy - 14), (hx + 40, hy + 18), (hx + 30, hy + 26), (hx + 20, hy + 2)], '#7a4f27', lw=2.4, wob=.4)
    hp, hk = s.shape([(hx - 26, hy + 8), (hx - 22, hy - 16), (hx, hy - 24), (hx + 22, hy - 16), (hx + 26, hy + 8), (hx + 14, hy + 30), (hx - 14, hy + 30)], '#c08a4a', lw=2.8, wob=.5)
    s.coat([(hx + 4, hy - 30), (hx + 32, hy - 10), (hx + 20, hy + 34), (hx + 8, hy + 30)], '#a06e38', hk, .8)
    s.shape(ell(hx, hy + 18, 13, 10, 10), '#ead8b0', lw=2, wob=.3)
    s.shape([(hx - 5, hy + 10), (hx + 5, hy + 10), (hx, hy + 15)], INK, lw=1.4, wob=.1)
    for ex in (-10, 10):
        s.fill(s.curve([(hx + ex - 3, hy - 2), (hx + ex, hy - 6), (hx + ex + 3, hy - 2), (hx + ex, hy + 3)], True, 0), INK)
        s.fill(s.curve([(hx + ex - 1.6, hy - 3), (hx + ex, hy - 5), (hx + ex + .6, hy - 3), (hx + ex - .6, hy - 2)], True, 0), '#f2ead8')
    lp, lk = s.poly([(dx, dt + 86), (dx + dw, dt + 86), (dx + dw, base), (dx, base)], '#8a6446', lw=2.6, wob=.6)
    s.coat([(dx + dw * .6, dt + 80), (dx + dw + 6, dt + 80), (dx + dw + 6, base + 4), (dx + dw * .66, base + 4)], '#6a4a35', lk, 1)
    for k in (.33, .66): s.stroke([(dx + dw * k, dt + 88), (dx + dw * k, base)], 1.6, clip=lk)
    s.poly([(dx - 4, dt + 82), (dx + dw + 4, dt + 82), (dx + dw + 4, dt + 92), (dx - 4, dt + 92)], '#4c3529', lw=2.2, wob=.5)
    x = 10
    while x < W - 10:
        wd = r.randint(22, 34); s.shape([(x, base + 2), (x + 1, base - 12), (x + wd / 2, base - 15), (x + wd, base - 11), (x + wd + 1, base + 2)], r.choice(('#6b6673', '#7d7680')), lw=2, wob=.6); x += wd
    # the kennel in the yard, a bowl, and a ball
    kx, kb = 26, 396
    s.poly([(kx + 6, kb), (kx + 6, kb - 46), (kx + 86, kb - 46), (kx + 86, kb)], '#b07a4a', lw=2.8, wob=.8)
    s.shape([(kx - 4, kb - 40), (kx + 46, kb - 84), (kx + 96, kb - 40), (kx + 86, kb - 34), (kx + 46, kb - 70), (kx + 6, kb - 34)], '#a8473a', lw=2.8, wob=.6)
    s.shape(arch_pts(kx + 28, kb - 38, kx + 64, kb), '#1e1614', lw=2.4, wob=.5)
    s.poly([(kx + 32, kb - 54), (kx + 60, kb - 54), (kx + 60, kb - 44), (kx + 32, kb - 44)], '#e6d6b0', lw=1.6, wob=.3)
    s.shape(ell(W - 92, 392, 20, 7, 12), '#3f6a9a', lw=2.2, wob=.3); s.shape(ell(W - 92, 388, 15, 4, 10), '#79a9a2', lw=1.4, wob=.2)
    s.shape(ell(W - 140, 388, 9, 9, 10), '#d8a24a', lw=2, wob=.3); s.stroke([(W - 147, 386), (W - 133, 390)], 1.4, '#a8473a', wob=.1)
    # the picket fence and its gate
    for y in (H - 64, H - 34):
        s.poly([(-2, y), (W + 2, y + r.uniform(-1, 1)), (W + 2, y + 9), (-2, y + 9)], '#d6cbaf', lw=2.2, wob=.8)
    x = 4
    while x < W - 4:
        gate = W / 2 - 40 < x < W / 2 + 34; col = '#e6dcc0' if not gate else '#c9b892'
        p, m = s.poly([(x, H - 2), (x, H - 82), (x + 7, H - 92), (x + 14, H - 82), (x + 14, H - 2)], col, lw=2.2, wob=.5)
        s.coat([(x + 9, H - 96), (x + 18, H - 96), (x + 18, H + 2), (x + 9, H + 2)], '#b3a78e', m, .5)
        x += 20
    s.stroke([(W / 2 - 40, H - 70), (W / 2 + 46, H - 30)], 5, '#8f846e', wob=.3)
    return s.done()

def guardpost():
    W, H = 192, 400; s = Sh(W, H, 621); r = s.r
    s.stroke([(96, 72), (96, 8)], 5, '#4a3429', wob=.2)
    fp, fk = s.shape([(98, 10), (150, 14), (184, 22), (160, 30), (182, 40), (138, 42), (98, 38)], '#a8473a', lw=2.4, wob=.6)
    s.coat([(98, 28), (190, 30), (190, 46), (98, 46)], '#7a2f2a', fk, 1)
    s.shape(ell(96, 9, 5, 5, 8), '#c79b42', lw=1.8, wob=.2)
    tp, tk = s.poly([(30, 112), (162, 112), (172, H - 8), (20, H - 8)], '#8a8390', lw=3.2, wob=1.4)
    stones(s, tk, 20, 112, 172, H - 8, ('#8f8892', '#7d7680', '#958e9b', '#857e88'), rowh=(18, 22), wd=(24, 38))
    s.coat([(118, 100), (180, 100), (180, H), (130, H)], '#5f5967', tk, 2, alpha=150)
    s.coat([(24, 140), (48, 130), (52, 260), (26, 300)], '#b0a9b6', tk, 2, alpha=120)
    s.ink(tp, 3.2)
    # the walk at the top with its merlons and brackets
    for x in (22, 58, 94, 130):
        s.poly([(x, 112), (x + 6, 132), (x + 18, 132), (x + 24, 112)], '#6b6673', lw=2.2, wob=.5)
    bp, bk = s.poly([(8, 70), (184, 70), (178, 116), (14, 116)], '#958e9b', lw=3, wob=1)
    stones(s, bk, 8, 70, 184, 116, ('#958e9b', '#8a8390', '#a29ba8'), rowh=(22, 24), wd=(26, 36))
    s.coat([(120, 60), (190, 60), (190, 120), (128, 120)], '#6b6673', bk, 1.5, alpha=150)
    s.ink(bp, 3)
    for i, x in enumerate((8, 54, 100, 146)):
        mp, mk = s.poly([(x, 72), (x + 1, 38), (x + 38, 38), (x + 38, 72)], '#a29ba8' if i < 2 else '#8a8390', lw=3, wob=.9)
        s.coat([(x + 26, 30), (x + 44, 30), (x + 44, 80), (x + 28, 80)], '#6b6673', mk, 1, alpha=170)
    # the town's banner, the slit and the door
    bp, bk = s.shape([(70, 120), (122, 120), (124, 214), (108, 202), (96, 222), (84, 202), (68, 214)], '#2f6b66', lw=2.8, wob=.7)
    s.coat([(100, 110), (130, 110), (130, 230), (104, 230)], '#1e4a4c', bk, 1)
    s.line(s.rough([(76, 126), (116, 126), (116, 196), (76, 196)], .5), 1.6, '#d4a24c', closed=True, taper=False, clip=bk)
    icon_draw(s, 96, 160, 'wave', .9)
    s.stroke([(64, 120), (128, 120)], 4.4, '#4a3429', wob=.2)
    for x in (42, 150): s.poly([(x - 4, 170), (x + 4, 170), (x + 4, 210), (x - 4, 210)], '#1e1614', lw=2, wob=.4)
    window(s, 82, 248, 28, 30, arch=True)
    door(s, 66, H - 8, 60, 92)
    # a torch bracket by the door
    s.stroke([(138, 312), (150, 300)], 3, '#2a2326', wob=.1)
    s.shape([(144, 300), (156, 300), (152, 286), (150, 278), (146, 288)], '#e88a2c', lw=1.8, wob=.4); s.fill(s.curve([(147, 299), (153, 299), (150, 288)], True, 0), '#f7d67c')
    a = s.done()
    return halo_behind(a, 150, 292, 34, 34, '#f2b866', .45)

def stall(kind):
    W, H = 240, 280; s = Sh(W, H, 631 if kind == 'food' else 641); r = s.r
    c1, c2 = ('#a8473a', '#efe2c4') if kind == 'food' else ('#3f5a8a', '#e6c46a')
    for x in (36, 196): s.poly([(x, 80), (x + 8, 80), (x + 8, 168), (x, 168)], '#3a2922', lw=2.2, wob=.6)
    # the counter
    tp, tk = s.poly([(20, 150), (220, 150), (232, 176), (8, 176)], '#a07a52', lw=2.8, wob=.8)
    fp, fk = s.poly([(8, 176), (232, 176), (230, H - 4), (10, H - 4)], '#8a6446', lw=3, wob=1)
    for y in (204, 234): s.stroke([(10, y), (230, y + r.uniform(-1, 1))], 1.6, clip=fk)
    s.coat([(150, 170), (240, 170), (240, H), (160, H)], '#6a4a35', fk, 2)
    cp, ck = s.poly([(22, 178), (218, 178), (214, 238), (120, 246), (26, 238)], c2 if kind == 'food' else '#7f5a93', lw=2.4, wob=.8)
    s.coat([(140, 170), (230, 170), (230, 250), (150, 250)], '#cdbb92' if kind == 'food' else '#5f4470', ck, 1.5)
    s.line(s.rough([(30, 186), (210, 186)], .5)[:60], 2.6, c1 if kind == 'food' else '#e6c46a', taper=True)
    # posts
    for x in (10, 216):
        p, m = s.poly([(x, H - 2), (x + 1, 66), (x + 14, 66), (x + 14, H - 2)], '#5a4133', lw=2.6, wob=.8)
        s.coat([(x + 8, 60), (x + 18, 60), (x + 18, H), (x + 8, H)], '#3f2c24', m, .6)
    # wares
    if kind == 'food':
        bp, bk = s.shape([(30, 150), (28, 132), (84, 132), (82, 150), (56, 156)], '#8a6a3c', lw=2.4, wob=.5)
        for k in range(3): s.stroke([(30, 138 + k * 5), (82, 138 + k * 5)], 1.1, '#5a4130', clip=bk)
        for i in range(9):
            ax = 36 + (i % 5) * 10 + (i // 5) * 5; ay = 128 - (i // 5) * 8
            s.shape(ell(ax, ay, 7, 6.5, 10), r.choice(('#a8473a', '#b8503a', '#7f9a3c')), lw=1.8, wob=.3)
        for cx in (108, 136):
            s.shape([(cx - 15, 150), (cx - 11, 138), (cx, 134), (cx + 11, 138), (cx + 15, 150), (cx, 153)], '#c98a3f', lw=2, wob=.3)
            for d in (-6, 2): s.stroke([(cx + d - 2, 139), (cx + d + 2, 146)], 1.4, wob=.1)
        ch, chk = s.poly([(158, 152), (158, 134), (198, 134), (198, 152)], '#e2b84a', lw=2.4, wob=.4)
        s.shape(ell(178, 134, 20, 6, 12), '#efd07a', lw=2, wob=.2); s.poly([(178, 134), (198, 130), (198, 140)], '#c79b42', lw=1.6, wob=.1)
        for k in range(5):
            ox = 50 + k * 34; s.stroke([(ox, 90), (ox, 100 + k % 2 * 6)], 1.2, '#5a4130', wob=.1)
            s.shape([(ox - 7, 106 + k % 2 * 6), (ox, 96 + k % 2 * 6), (ox + 7, 106 + k % 2 * 6), (ox, 116 + k % 2 * 6)], '#d9c27a' if k % 2 else '#9a4a6a', lw=1.6, wob=.3)
    else:
        for i, (px, hh, col) in enumerate(((40, 34, '#b0643a'), (70, 24, '#7d8a9a'), (96, 40, '#a35a35'))):
            s.shape([(px - 12, 150), (px - 15, 150 - hh * .5), (px - 8, 150 - hh * .85), (px - 6, 150 - hh), (px + 6, 150 - hh), (px + 8, 150 - hh * .85), (px + 15, 150 - hh * .5), (px + 12, 150)], col, lw=2.2, wob=.4)
            s.stroke([(px - 12, 150 - hh * .5), (px + 12, 150 - hh * .5)], 1.4, wob=.2)
        for j, col in enumerate(('#3f8a7a', '#c79b42', '#9a4a6a')):
            y = 148 - j * 13; x0 = 126 + j * 6
            p, m = s.poly([(x0, y), (x0 + 70, y), (x0 + 70, y - 13), (x0, y - 13)], col, lw=2.2, wob=.4)
            s.shape(ell(x0 + 70, y - 6.5, 4, 6.5, 8), col, lw=1.8, wob=.1); s.stroke([(x0 + 10, y - 9), (x0 + 60, y - 9)], 1.2, '#f2ead8', clip=m)
        s.stroke([(120, 96), (120, 106)], 1.6, '#2a2326', wob=.1)
        s.poly([(110, 106), (130, 106), (128, 128), (112, 128)], '#f7d67c', lw=2.2, wob=.3); s.poly([(108, 102), (132, 102), (128, 108), (112, 108)], '#2a2326', lw=1.6, wob=.2)
        s.shape(ell(196, 112, 14, 11, 12), '#b39a62', lw=2.2, wob=.4); s.stroke([(186, 112), (196, 106), (206, 112), (196, 118)], 1.4, '#7a6038', wob=.2)
    awning(s, 32, 208, 24, 74, c1, c2, n=7, drop=24, hem=16)
    s.shape([(110, 26), (120, 12), (130, 26)], '#5a4133', lw=2, wob=.2)
    a = s.done()
    if kind == 'goods': a = halo_behind(a, 120, 116, 40, 40, '#f2b866', .35)
    return a

# the fountain's geometry, shared with its water sheet
FX, FCY, FRX, FRY = 120, 138, 110, 34
def fountain():
    W, H = 240, 220; s = Sh(W, H, 651); r = s.r
    top = ell(FX, FCY, FRX, FRY, 18, 0, math.pi, closed=False); bot = [(x, y + 52) for x, y in top]
    wp, wk = s.poly(top + bot[::-1], '#7d7680', lw=3, wob=.8)
    s.coat([(FX + 30, FCY), (FX + FRX + 6, FCY - 4), (FX + FRX + 6, FCY + 100), (FX + 50, FCY + 100)], '#5f5967', wk, 2)
    s.coat([(FX - FRX, FCY + 4), (FX - 60, FCY + 20), (FX - 70, FCY + 60), (FX - FRX - 4, FCY + 52)], '#958e9b', wk, 2)
    for k in range(1, 8):
        a = math.pi * k / 8; x = FX + math.cos(a) * FRX; y = FCY + math.sin(a) * FRY
        s.stroke([(x, y + 4), (x + r.uniform(-1, 1), y + 26)], 1.6, clip=wk); s.stroke([(x + 8, y + 28), (x + 8, y + 50)], 1.6, clip=wk)
    s.line([(x, y + 26) for x, y in top], 1.6, INK, clip=wk)
    s.shape(ell(FX, FCY, FRX, FRY, 22), '#a29ba8', lw=3, wob=.6)
    wa, wak = s.shape(ell(FX, FCY + 2, FRX - 15, FRY - 10, 20), '#2f5e72', lw=2.4, wob=.4)
    s.coat([(FX - 100, FCY - 30), (FX + 100, FCY - 30), (FX + 100, FCY - 6), (FX - 100, FCY - 2)], '#467f8a', wak, 2)
    s.coat([(FX - 60, FCY + 14), (FX + 80, FCY + 10), (FX + 80, FCY + 40), (FX - 60, FCY + 40)], '#23465e', wak, 2)
    # the column, its bowl and the spout
    cp, ck = s.shape([(FX - 15, FCY + 2), (FX - 10, FCY - 22), (FX - 17, FCY - 38), (FX - 8, 82), (FX + 8, 82), (FX + 17, FCY - 38), (FX + 10, FCY - 22), (FX + 15, FCY + 2)], '#8a8390', lw=2.8, wob=.5)
    s.coat([(FX + 2, 76), (FX + 24, 76), (FX + 24, FCY + 8), (FX + 4, FCY + 8)], '#625c6a', ck, 1)
    bp, bk = s.shape([(FX - 48, 72), (FX + 48, 72), (FX + 32, 90), (FX, 96), (FX - 32, 90)], '#8a8390', lw=2.8, wob=.5)
    s.coat([(FX + 6, 66), (FX + 56, 66), (FX + 40, 100), (FX + 8, 100)], '#625c6a', bk, 1)
    s.shape(ell(FX, 72, 48, 12, 16), '#a29ba8', lw=2.6, wob=.4)
    s.shape(ell(FX, 72, 38, 8, 14), '#467f8a', lw=2, wob=.3)
    s.shape([(FX - 7, 72), (FX - 5, 52), (FX - 10, 46), (FX, 34), (FX + 10, 46), (FX + 5, 52), (FX + 7, 72)], '#8a8390', lw=2.4, wob=.3)
    s.shape(ell(FX, 34, 7, 6, 10), '#a29ba8', lw=2, wob=.2)
    for sg in (-1, 1):
        s.stroke([(FX + sg * 44, 76), (FX + sg * 56, 92), (FX + sg * 64, FCY - 8)], 3, '#79a9a2', wob=.3, alpha=170)
    s.fill(s.curve(ell(FX, 72, 30, 5, 10), True, .3), '#79a9a2', alpha=140)
    return s.done()
def fountain_water():
    W, H = 240, 220; out = np.zeros((H, W * 4, 4), np.uint8)
    for f in range(4):
        s = Sh(W, H, 660 + f); r = random.Random(70 + f)
        wm = s.mask(s.curve(ell(FX, FCY + 2, FRX - 17, FRY - 12, 20), True, 0))
        for k in range(3):
            rr = 20 + ((f * 9 + k * 24) % 72); al = int(220 * (1 - rr / 96))
            for a0 in (r.uniform(.1, .7), r.uniform(2.2, 2.9)):
                pts = ell(FX, FCY - 2, rr, rr * .27, 7, a0, a0 + 1.1, closed=False); s.stroke(pts, 1.8, '#d8f0e6', wob=.2, clip=wm, alpha=al)
        for sg in (-1, 1):
            for j in range(3):
                p = np.array(s.curve([(FX + sg * (42 + j * 3), 75), (FX + sg * (54 + j * 4), 92), (FX + sg * (60 + j * 4), FCY - 6)], False, 0))
                n = len(p); t0 = ((f / 4 + j * .33) % 1)
                for q in (t0, (t0 + .5) % 1):
                    a, b = int(q * n), int(min(q + .2, 1) * n)
                    if b - a > 2: s.line(p[a:b], 2.2, '#e6f6ee', alpha=230)
            hx = FX + sg * 62; ry = FCY - 4
            s.stroke(ell(hx, ry, 6 + f * 2, 2 + f * .5, 7, math.pi * 1.1, math.pi * 1.9, closed=False), 1.6, '#e6f6ee', wob=.1, alpha=200)
        for k in range(5):
            t = (f / 4 + k / 5) % 1; x = FX + (k - 2) * 4 * t; y = 34 - math.sin(t * math.pi) * 18
            s.fill(s.curve(ell(x, y, 2.2, 2.6, 6), True, 0), '#e6f6ee', alpha=220)
        for _ in range(7):
            x, y = r.uniform(FX - 80, FX + 80), r.uniform(FCY - 16, FCY + 18); s.stroke([(x - 4, y), (x + 4, y)], 1.6, '#f2fff8', clip=wm, wob=0, alpha=210)
        P.over(out, s.done(.02), f * W, 0)
    return out

def lamp():
    W, H = 110, 280; s = Sh(W, H, 671)
    bp, bk = s.poly([(32, H - 2), (34, H - 34), (76, H - 34), (78, H - 2)], '#7d7680', lw=2.8, wob=.7)
    s.coat([(58, H - 40), (84, H - 40), (84, H), (60, H)], '#5f5967', bk, 1)
    s.poly([(28, H - 36), (82, H - 36), (80, H - 26), (30, H - 26)], '#958e9b', lw=2.4, wob=.5)
    pp, pk = s.poly([(50, H - 36), (50, 104), (60, 104), (60, H - 36)], '#2f2a2e', lw=2.4, wob=.4)
    s.stroke([(52, H - 40), (52, 110)], 1.2, '#5a5560', clip=pk)
    for y in (H - 60, 150, 108): s.poly([(46, y), (64, y), (63, y + 7), (47, y + 7)], '#2f2a2e', lw=2, wob=.3)
    s.stroke([(55, 106), (40, 102), (36, 94), (42, 90)], 2.2, '#2f2a2e', wob=.1); s.stroke([(55, 106), (70, 102), (74, 94), (68, 90)], 2.2, '#2f2a2e', wob=.1)
    s.poly([(42, 98), (68, 98), (64, 108), (46, 108)], '#2f2a2e', lw=2.2, wob=.3)
    gp, gk = s.poly([(36, 52), (74, 52), (69, 96), (41, 96)], '#f7d67c', lw=2.4, wob=.4)
    s.coat([(55, 56), (60, 70), (55, 90), (50, 70)], '#fff0c0', gk, .5)
    s.coat([(64, 48), (80, 48), (76, 100), (64, 100)], '#e8a040', gk, .5)
    for x0, x1 in ((48, 50), (62, 60)): s.stroke([(x0, 52), (x1, 96)], 2.2, '#2f2a2e', wob=.1)
    s.poly([(28, 54), (55, 26), (82, 54)], '#2f2a2e', lw=2.6, wob=.4); s.stroke([(34, 50), (55, 30)], 1.4, '#5a5560', wob=.1)
    s.shape(ell(55, 22, 5, 5, 8), '#2f2a2e', lw=2, wob=.2)
    a = s.done()
    a = halo_behind(a, 55, 74, 54, 54, '#f7c46a', .55, 1.6)
    return a

def crates():
    W, H = 170, 160; s = Sh(W, H, 681); r = s.r
    bx = 102
    bp, bk = s.shape([(bx + 4, 60), (bx + 56, 60), (bx + 62, 108), (bx + 56, H - 4), (bx + 4, H - 4), (bx - 2, 108)], '#7a5236', lw=3, wob=.6)
    s.coat([(bx + 34, 50), (bx + 70, 50), (bx + 70, H), (bx + 38, H)], '#5a3d29', bk, 1)
    s.coat([(bx + 6, 66), (bx + 14, 66), (bx + 12, 146), (bx + 4, 140)], '#9a6c48', bk, 1)
    for x in (bx + 16, bx + 30, bx + 44): s.stroke([(x, 62), (x + r.uniform(-2, 2), H - 6)], 1.3, clip=bk)
    for y in (78, 140): s.stroke([(bx - 3, y), (bx + 30, y + 4), (bx + 62, y)], 4, '#3a3236', clip=bk)
    s.shape(ell(bx + 30, 60, 27, 7, 14), '#8f6544', lw=2.4, wob=.3)
    def crate(x0, y0, w, h, d=12):
        tp, tk = s.poly([(x0 + 4, y0 - d), (x0 + w - 4, y0 - d), (x0 + w, y0), (x0, y0)], '#b8925e', lw=2.4, wob=.5)
        fp, fk = s.poly([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)], '#a07a52', lw=2.8, wob=.7)
        s.coat([(x0 + w * .64, y0 - 4), (x0 + w + 6, y0 - 4), (x0 + w + 6, y0 + h + 4), (x0 + w * .7, y0 + h + 4)], '#7b5c42', fk, 1.2)
        for k in (1, 2): s.stroke([(x0, y0 + h * k / 3), (x0 + w, y0 + h * k / 3)], 1.3, clip=fk)
        s.line(s.rough([(x0 + 5, y0 + 5), (x0 + w - 5, y0 + 5), (x0 + w - 5, y0 + h - 5), (x0 + 5, y0 + h - 5)], .4), 3.2, '#5a3f30', closed=True, taper=False, clip=fk)
        s.stroke([(x0 + 7, y0 + h - 7), (x0 + w - 7, y0 + 7)], 4, '#5a3f30', clip=fk, wob=.3)
        s.stroke([(x0 + 7, y0 + h - 7), (x0 + w - 7, y0 + 7)], 1.2, INK, clip=fk, wob=.3)
    crate(6, 84, 94, 72)
    crate(20, 34, 66, 52, 10)
    sp, sk = s.shape([(4, H - 2), (2, 132), (10, 112), (26, 104), (40, 112), (46, 134), (44, H - 2)], '#b9a77c', lw=2.6, wob=.7)
    s.coat([(28, 100), (52, 110), (52, H), (30, H)], '#8f846e', sk, 1)
    s.stroke([(14, 112), (24, 116), (36, 112)], 2.2, '#5a4130', wob=.2)
    return s.done()

def bench():
    W, H = 190, 110; s = Sh(W, H, 691); r = s.r
    for x in (24, 160):
        s.poly([(x, 62), (x + 8, 62), (x + 8, 8), (x, 8)], '#2f2a2e', lw=2.2, wob=.3)
    for y in (12, 34):
        p, m = s.poly([(14, y), (176, y + r.uniform(-1, 1)), (176, y + 15), (14, y + 15)], '#8a6446', lw=2.6, wob=.7)
        s.coat([(110, y - 4), (180, y - 4), (180, y + 20), (120, y + 20)], '#6a4a35', m, 1.2)
        s.stroke([(30, y + 7), (90, y + 8)], 1, '#4f3a2c', clip=m)
    tp, tk = s.poly([(12, 58), (178, 58), (186, 72), (4, 72)], '#a07a52', lw=2.6, wob=.6)
    for k in (.33, .66): s.stroke([(12 - 8 * k, 58 + 14 * k), (178 + 8 * k, 58 + 14 * k)], 1.2, clip=tk)
    s.coat([(120, 54), (190, 54), (190, 76), (130, 76)], '#86643f', tk, 1)
    s.poly([(4, 72), (186, 72), (186, 81), (4, 81)], '#5a3f30', lw=2.4, wob=.5)
    for x, sg in ((16, -1), (166, 1)):
        s.poly([(x, 80), (x + 10, 80), (x + 12 + sg * 4, H - 2), (x - 2 + sg * 4, H - 2)], '#2f2a2e', lw=2.2, wob=.3)
        s.stroke([(x + 5, 94), (x + 5 - sg * 14, 90), (x + 5 - sg * 16, 82)], 2.4, '#2f2a2e', wob=.1)
    return s.done()

def banner_pole():
    W, H = 100, 300; s = Sh(W, H, 701)
    bp, bk = s.poly([(24, H - 2), (26, H - 38), (74, H - 38), (76, H - 2)], '#7d7680', lw=2.8, wob=.7)
    s.coat([(54, H - 44), (80, H - 44), (80, H), (56, H)], '#5f5967', bk, 1)
    pp, pk = s.poly([(45, H - 38), (46, 20), (55, 20), (56, H - 38)], '#5a4133', lw=2.6, wob=.5)
    s.coat([(51, 14), (60, 14), (60, H), (52, H)], '#3f2c24', pk, .3)
    s.shape(ell(50, 14, 7, 7, 10), '#c79b42', lw=2.2, wob=.2)
    s.poly([(12, 34), (88, 34), (88, 43), (12, 43)], '#5a4133', lw=2.4, wob=.4)
    fp, fk = s.shape([(18, 43), (50, 46), (82, 43), (86, 120), (80, 206), (66, 192), (50, 214), (34, 192), (20, 206), (16, 120)], '#2f6b66', lw=2.8, wob=.8)
    s.coat([(56, 30), (96, 30), (96, 230), (60, 230), (64, 120)], '#1e4a4c', fk, 2)
    s.coat([(18, 50), (30, 50), (28, 180), (18, 190)], '#4a8a80', fk, 1.5)
    s.line(s.curve([(26, 52), (74, 52), (74, 180), (62, 172), (50, 190), (38, 172), (26, 180)], True, .5), 1.8, '#d4a24c', closed=True, taper=False)
    s.shape(ell(50, 96, 16, 16, 12), '#d4a24c', lw=2, wob=.3)
    icon_draw(s, 50, 130, 'wave', .8)
    for x in (12, 88): s.stroke([(x, 43), (x, 58)], 2, '#c79b42', wob=.1); s.shape(ell(x, 61, 3, 4, 6), '#c79b42', lw=1.4, wob=.1)
    return s.done()

def board():
    W, H = 210, 230; s = Sh(W, H, 711); r = s.r
    for x in (26, 168):
        p, m = s.poly([(x, H - 2), (x + 1, 40), (x + 15, 40), (x + 16, H - 2)], '#5a4133', lw=2.6, wob=.7)
        s.coat([(x + 9, 30), (x + 20, 30), (x + 20, H), (x + 10, H)], '#3f2c24', m, .5)
    fp, fk = s.poly([(14, 52), (196, 52), (196, 176), (14, 176)], '#5a3f30', lw=3, wob=1)
    bp, bk = s.poly([(24, 62), (186, 62), (186, 166), (24, 166)], '#a3815a', lw=2.2, wob=.7)
    s.coat([(130, 56), (192, 56), (192, 172), (140, 172)], '#8f6a48', bk, 2)
    for _ in range(22): x, y = r.uniform(28, 182), r.uniform(66, 162); s.stroke([(x, y), (x + 2, y + 1)], 1.4, '#7a5a3c', wob=0)
    papers = ((32, 70, 46, 54, -.06, 'slime'), (86, 68, 42, 40, .05, 'text'), (138, 72, 40, 50, -.03, 'map'), (90, 114, 48, 44, -.04, 'text'), (40, 128, 38, 32, .07, 'text'), (144, 126, 34, 34, .04, 'coin'))
    for x, y, w, h, a, kind in papers:
        ca, sa = math.cos(a), math.sin(a); cx, cy = x + w / 2, y + h / 2
        q = [(cx + (dx * ca - dy * sa), cy + (dx * sa + dy * ca)) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
        p, m = s.poly(q, r.choice(('#efe4c8', '#e2d5b4', '#f2ead8')), lw=1.8, wob=.4)
        if kind == 'slime':
            s.shape([(cx - 13, cy + 12), (cx - 13, cy), (cx - 6, cy - 9), (cx + 6, cy - 9), (cx + 13, cy), (cx + 13, cy + 12)], '#3f9a8d', lw=1.8, wob=.3)
            for ex in (-5, 5): s.fill(s.curve(ell(cx + ex, cy + 1, 1.8, 2.6, 6), True, 0), INK)
            s.stroke([(cx - 14, cy - 18), (cx + 14, cy - 18)], 1.8, '#a33c4b', wob=.2, clip=m)
            s.stroke([(cx - 12, cy + 19), (cx + 10, cy + 19)], 1.2, wob=.2, clip=m)
        elif kind == 'map':
            s.stroke([(cx - 14, cy + 16), (cx - 4, cy + 4), (cx + 6, cy + 8), (cx + 12, cy - 12)], 1.4, '#7a5a3c', wob=.3, clip=m)
            s.stroke([(cx + 8, cy - 16), (cx + 16, cy - 8)], 1.8, '#a33c4b', wob=.1); s.stroke([(cx + 16, cy - 16), (cx + 8, cy - 8)], 1.8, '#a33c4b', wob=.1)
        elif kind == 'coin':
            s.shape(ell(cx, cy, 9, 9, 10), '#cfa144', lw=1.6, wob=.2)
        else:
            for k in range(int(h / 9)): yy = y + 8 + k * 8; s.stroke([(x + 6, yy), (x + w - 6 - r.uniform(0, 12), yy + w * a)], 1, '#6d6050', clip=m, wob=.3)
        s.shape(ell(cx, y + 4, 2.6, 2.6, 6), '#a33c4b', lw=1.2, wob=.1)
    rp, rk = s.poly([(4, 54), (105, 16), (206, 54), (198, 62), (105, 28), (12, 62)], '#9a4e38', lw=2.8, wob=.8)
    s.coat([(105, 10), (210, 50), (210, 66), (105, 30)], '#6b3528', rk, 1)
    s.shape([(98, 22), (105, 8), (112, 22)], '#5a4133', lw=2, wob=.2)
    return s.done()

# ---- the meadow
def blades(s, n, x0, x1, y, hmin, hmax, cols, r, ink=True, w=2.0):
    for _ in range(n):
        x = r.uniform(x0, x1); h = r.uniform(hmin, hmax); lean = r.uniform(-.35, .35) * h
        pts = [(x, y), (x + lean * .3, y - h * .5), (x + lean, y - h)]
        if ink: s.stroke(pts, w + 1.6, INK, wob=.3)
        s.stroke(pts, w, r.choice(cols), wob=.3)
def flowers_patch():
    W, H = 150, 130; s = Sh(W, H, 721); r = s.r
    blades(s, 26, 18, 132, H - 6, 30, 70, ('#4d6d40', '#688246', '#3b5a3b'), r)
    heads = []
    for i in range(11):
        x = 20 + i * 10.5 + r.uniform(-4, 4); top = r.uniform(18, 64); heads.append((x, top, r.choice(('daisy', 'poppy', 'bell', 'gold', 'daisy', 'poppy'))))
    for x, top, k in heads:
        bend = r.uniform(-8, 8); s.stroke([(x - bend * .3, H - 8), (x + bend * .3, (H + top) / 2), (x + bend, top)], 3.4, INK, wob=.3); s.stroke([(x - bend * .3, H - 8), (x + bend * .3, (H + top) / 2), (x + bend, top)], 1.8, '#4d6d40', wob=.3)
        lx = x + bend * .2; ly = (H + top) / 2 + 6; s.shape([(lx, ly), (lx + 10, ly - 7), (lx + 13, ly - 2), (lx + 4, ly + 3)], '#5b7843', lw=1.4, wob=.2)
    for x, top, k in heads:
        cx = x + 0 if False else x; cx = x + (0)
    p, m = s.shape(C.scallop(W / 2, H - 16, 62, 18, 9, 7, .25), '#3b5a3b', lw=2.6, wob=0)
    s.coat([(W / 2, H - 40), (W, H - 34), (W, H), (W / 2, H)], '#2b4530', m, 2)
    s.coat([(10, H - 30), (50, H - 36), (60, H - 24), (20, H - 18)], '#5b7843', m, 2)
    blades(s, 18, 8, 142, H - 4, 14, 34, ('#688246', '#a4a35a', '#4d6d40'), r)
    for x, top, k in heads:
        rr = random.Random(int(x * 10))
        cx = x + rr.uniform(-1, 1); cy = top
        if k == 'daisy':
            for t in range(7): a = t * 2 * math.pi / 7; s.shape(ell(cx + math.cos(a) * 6, cy + math.sin(a) * 4.5, 4.2, 3, 8), '#f2ead8', lw=1.3, wob=.1)
            s.shape(ell(cx, cy, 3.4, 3, 8), '#d8a24a', lw=1.3, wob=.1)
        elif k == 'poppy':
            s.shape([(cx - 9, cy - 2), (cx - 6, cy - 8), (cx, cy - 6), (cx + 6, cy - 8), (cx + 9, cy - 2), (cx + 5, cy + 6), (cx - 5, cy + 6)], '#b8443a', lw=1.8, wob=.2)
            s.fill(s.curve(ell(cx, cy, 2.4, 2, 6), True, 0), INK)
        elif k == 'bell':
            for j in range(3): s.shape([(cx - 4 + j * 3, cy + j * 9), (cx + j * 3, cy - 5 + j * 9), (cx + 4 + j * 3, cy + j * 9), (cx + j * 3, cy + 4 + j * 9)], '#7f6aa8', lw=1.4, wob=.1)
        else:
            for j in range(3): s.shape(ell(cx - 5 + j * 5, cy + (j % 2) * 4, 3.6, 3.4, 8), '#e2b84a', lw=1.3, wob=.1)
    return s.done()

def haystack():
    W, H = 210, 190; s = Sh(W, H, 731); r = s.r
    s.stroke([(184, 186), (156, 60)], 4.4, '#5a4133', wob=.2)
    p, m = s.shape([(8, 186), (14, 132), (42, 74), (96, 40), (150, 62), (186, 116), (198, 186), (104, 190)], '#c9a24c', lw=3.4, wob=1.4)
    s.coat([(110, 36), (170, 60), (204, 120), (206, 196), (130, 196), (150, 120)], '#a17f3a', m, 3)
    s.coat([(30, 120), (50, 78), (90, 52), (76, 90), (40, 150)], '#e2c46e', m, 3)
    for _ in range(80):
        x = r.uniform(16, 194); y = r.uniform(50, 184); a = r.uniform(-.6, .6) + (x - 105) / 120; L = r.uniform(10, 22)
        s.stroke([(x, y), (x + math.sin(a) * L * .5, y + math.cos(a) * L * .5 - 2), (x + math.sin(a) * L, y + math.cos(a) * L)], r.uniform(1, 1.6), r.choice(('#8a6a2c', '#7a5a24', '#f0d88a')), clip=m, wob=.3)
    s.stroke([(16, 140), (60, 150), (110, 152), (160, 146), (194, 136)], 4, '#6a4a2a', clip=m, wob=.6)
    s.stroke([(16, 140), (60, 150), (110, 152), (160, 146), (194, 136)], 1.4, INK, clip=m, wob=.6)
    s.poly([(96, 46), (98, 4), (106, 4), (108, 46)], '#5a4133', lw=2.4, wob=.4)
    for _ in range(9):
        x = r.uniform(6, 200); s.stroke([(x, 188), (x + r.uniform(-14, 14), 182 - r.uniform(0, 6))], 1.6, '#c9a24c', wob=.2)
    for _ in range(6): x = r.uniform(70, 140); s.stroke([(x, 44), (x + r.uniform(-12, 12), 30 + r.uniform(-4, 4))], 1.4, '#e2c46e', wob=.2)
    # a pitchfork leaning on it
    for dx in (-10, 0, 10): s.stroke([(152 + dx * .7, 64), (150 + dx, 30), (152 + dx * 1.1, 22)], 2.6, '#4a4350', wob=.1)
    s.stroke([(143, 64), (162, 64)], 3, '#4a4350', wob=.1)
    return s.done()

def stone_wall():
    W, H = 240, 110; s = Sh(W, H, 741); r = s.r
    def course(x0, x1, y0, y1, upright=False):
        x = x0
        while x < x1 - 8:
            w = r.randint(14, 22) if upright else r.randint(26, 48); w = min(w, x1 - x)
            j = r.uniform(-2, 2); top = y0 + r.uniform(-3, 3)
            if upright:
                q = [(x + 1, y1), (x + r.uniform(0, 3), top + 4), (x + w * .5, top - r.uniform(0, 4)), (x + w - r.uniform(0, 3), top + 2), (x + w - 1, y1)]
            else:
                q = [(x + 1, y1 + 1), (x + 2, top + 5), (x + w * .3, top), (x + w * .7, top + r.uniform(-1, 2)), (x + w - 2, top + 4), (x + w - 1, y1 + 1)]
            p, m = s.shape(q, r.choice(('#8a8390', '#7d7680', '#9a93a0', '#857e88')), lw=2.4, wob=.8)
            s.coat([(x + w * .55, top - 6), (x + w + 4, top - 6), (x + w + 4, y1 + 4), (x + w * .45, y1 + 4)], '#625c6a', m, 1)
            s.coat([(x + 3, top + 2), (x + w * .5, top), (x + w * .3, top + 6), (x + 3, top + 8)], '#aaa3b0', m, .8)
            if r.random() < .3: s.coat([(x + 2, top - 4), (x + w * .7, top - 4), (x + w * .5, top + 5), (x + 2, top + 6)], '#5b7843', m, 1)
            x += w
    course(6, 234, 74, H - 3)
    course(10, 230, 48, 80)
    course(16, 224, 20, 54, upright=True)
    blades(s, 26, 2, 238, H - 2, 8, 22, ('#4d6d40', '#688246', '#a4a35a'), r)
    return s.done()

def meadow_sign():
    W, H = 140, 170; s = Sh(W, H, 751)
    p, m = s.poly([(62, H - 2), (63, 20), (78, 20), (79, H - 2)], '#5a4133', lw=2.8, wob=.8)
    s.coat([(72, 10), (84, 10), (84, H), (73, H)], '#3f2c24', m, .5)
    s.shape([(58, 22), (70, 10), (82, 22)], '#3f2c24', lw=2.2, wob=.3)
    for pts, ic, cx in (([(70, 28), (118, 26), (134, 44), (118, 62), (70, 62)], 'house', 98), ([(70, 72), (22, 70), (6, 88), (22, 106), (70, 106)], 'tower', 44)):
        bp, bk = s.poly(pts, '#a07a52', lw=2.8, wob=.9)
        s.coat([(0, pts[0][1] + 22), (140, pts[0][1] + 20), (140, pts[0][1] + 50), (0, pts[0][1] + 50)], '#7b5c42', bk, 1.5)
        icon_draw(s, cx, (pts[0][1] + pts[-1][1]) / 2, ic, .9)
    blades(s, 14, 44, 98, H - 2, 10, 30, ('#4d6d40', '#688246', '#a4a35a'), s.r)
    for x in (52, 90): s.shape(ell(x, H - 22, 5, 4, 8), '#f2ead8', lw=1.3, wob=.1); s.shape(ell(x, H - 22, 2, 2, 6), '#d8a24a', lw=1, wob=.1)
    return s.done()

# ---- the cave
CAVE = ('#4f4b5c', '#3a3746', '#6a6578', '#2b2834')
def crystal(s, bx, by, ang, L, w, cols=('#3faa78', '#1f6a50', '#9df0c4')):
    ca, sa = math.sin(ang), -math.cos(ang)  # direction of growth
    px, py = -sa, ca  # across the shard
    tip = (bx + ca * L, by + sa * L)
    q = [(bx - px * w, by - py * w), (bx - px * w + ca * L * .78, by - py * w + sa * L * .78), tip, (bx + px * w + ca * L * .78, by + py * w + sa * L * .78), (bx + px * w, by + py * w)]
    p, m = s.poly(q, cols[0], lw=2.4, wob=.3)
    s.fill(s.rough([(bx, by), (bx + ca * L * .8, by + sa * L * .8), tip, q[3], q[4]], .2), cols[1], clip=m)
    s.fill(s.rough([(bx - px * w * .7, by - py * w * .7), (bx - px * w * .7 + ca * L * .7, by - py * w * .7 + sa * L * .7), (bx - px * w * .25 + ca * L * .75, by - py * w * .25 + sa * L * .75), (bx - px * w * .25, by - py * w * .25)], .2), cols[2], clip=m)
    s.ink(p, 2.4)
def crystal_cluster():
    W, H = 150, 160; s = Sh(W, H, 761)
    for bx, ang, L, w in ((52, -.5, 70, 10), (98, .55, 64, 10), (64, -.15, 104, 14), (88, .2, 84, 12), (40, -.95, 44, 8), (112, .9, 40, 8), (76, .02, 58, 11)):
        crystal(s, bx, 138, ang, L, w)
    p, m = s.shape([(14, H - 2), (20, 136), (50, 124), (96, 126), (128, 134), (138, H - 2)], CAVE[1], lw=3, wob=1)
    s.coat([(80, 120), (140, 124), (144, H), (90, H)], CAVE[3], m, 1.5); s.coat([(20, 134), (50, 126), (60, 134), (24, 146)], CAVE[0], m, 1)
    a = s.done()
    a = halo_behind(a, 75, 84, 78, 82, '#5fe0a0', .5, 1.6)
    return a
def stalagmite():
    W, H = 110, 200; s = Sh(W, H, 771); r = s.r
    p, m = s.shape([(80, H - 2), (84, 168), (92, 140), (98, 166), (106, H - 2)], CAVE[1], lw=2.6, wob=.6)
    p, m = s.shape([(10, H - 2), (16, 166), (28, 150), (26, 124), (36, 98), (40, 70), (48, 40), (52, 14), (58, 34), (62, 62), (70, 84), (68, 108), (80, 132), (78, 150), (92, 170), (96, H - 2)], CAVE[0], lw=3.2, wob=1)
    s.shape([(4, 150), (10, 120), (18, 132), (22, 154)], CAVE[1], lw=2.2, wob=.4)
    s.coat([(54, 0), (90, 120), (100, H), (62, H), (58, 100)], CAVE[3], m, 2)
    s.coat([(44, 60), (50, 30), (52, 70), (38, 140), (28, 160)], CAVE[2], m, 1.5)
    for y in (64, 104, 140, 172):
        w = 8 + (y - 12) * .26; s.stroke([(52 - w, y), (52, y + 4), (52 + w, y - 1)], 1.6, clip=m, wob=.4)
    s.stroke([(46, 40), (42, 90)], 2, '#a9a3b8', clip=m, wob=.3)
    for x in (8, 30, 78, 100): s.shape(ell(x, H - 6, r.uniform(6, 10), r.uniform(4, 6), 8), CAVE[1], lw=2, wob=.4)
    return s.done()
def cave_rock():
    W, H = 130, 110; s = Sh(W, H, 781)
    crystal(s, 92, 50, .5, 30, 6)
    p, m = s.shape([(8, H - 2), (12, 64), (36, 32), (78, 26), (112, 52), (122, H - 2)], CAVE[0], lw=3.4, wob=2)
    s.coat([(70, 24), (126, 60), (128, H + 4), (64, H + 4), (82, 66)], CAVE[3], m, 2)
    s.coat([(22, 58), (42, 38), (64, 36), (46, 58), (24, 80)], CAVE[2], m, 2)
    s.stroke([(64, 34), (74, 64), (62, 92)], 2); s.stroke([(28, 86), (48, 92), (60, 104)], 1.5)
    s.stroke([(30, 72), (44, 66), (52, 74)], 2.2, '#5fae8a', wob=.3)
    return s.done()
def minecart():
    W, H = 180, 150; s = Sh(W, H, 791); r = s.r
    ore = s.shape([(20, 48), (34, 30), (58, 22), (88, 14), (120, 22), (150, 32), (162, 48)], '#5a5566', lw=2.8, wob=1.2)[1]
    for x, y in ((48, 34), (80, 24), (112, 30), (140, 40), (66, 44), (100, 42)):
        s.shape(ell(x, y, r.uniform(8, 13), r.uniform(6, 9), 8), r.choice(('#6a6578', '#4f4b5c', '#7a7488')), lw=2, wob=.6)
    crystal(s, 96, 34, .2, 22, 5); crystal(s, 60, 38, -.4, 18, 4); s.shape(ell(128, 30, 5, 4, 8), '#d4a24c', lw=1.6, wob=.2)
    bp, bk = s.poly([(10, 44), (170, 44), (156, 118), (24, 118)], '#6a4a35', lw=3.2, wob=.9)
    for y in (64, 84, 104): s.stroke([(10 + (y - 44) * .18, y), (170 - (y - 44) * .18, y)], 1.3, clip=bk)
    s.coat([(110, 40), (180, 40), (170, 124), (118, 124)], '#4c3529', bk, 1.5)
    for x0, x1 in ((16, 30), (150, 164)): s.poly([(x0, 44), (x1, 44), (x1 - (x0 - 90) * .1 - 2, 118), (x0 - (x0 - 90) * .1 - 2, 118)], '#4a4350', lw=2.2, wob=.4)
    s.poly([(6, 38), (174, 38), (172, 50), (8, 50)], '#4a4350', lw=2.6, wob=.6)
    for x in range(24, 160, 22): s.shape(ell(x, 44, 2.2, 2.2, 6), '#8a8390', lw=1, wob=0)
    s.poly([(30, 114), (150, 114), (150, 124), (30, 124)], '#2f2a2e', lw=2.2, wob=.4)
    for cx in (50, 130):
        s.shape(ell(cx, 127.5, 21, 21, 16), '#2f2a2e', lw=2.8, wob=.4)
        s.shape(ell(cx, 126, 13, 13, 12), '#4a4350', lw=1.6, wob=.2)
        s.shape(ell(cx, 126, 4, 4, 8), '#8a8390', lw=1.4, wob=.1)
        for a in (0, 1.05, 2.1): s.stroke([(cx + math.cos(a) * 13, 126 + math.sin(a) * 13), (cx - math.cos(a) * 13, 126 - math.sin(a) * 13)], 1.6, '#1c1618', wob=0)
    return s.done()
def cave_mouth():
    W, H = 400, 330; s = Sh(W, H, 801); r = s.r
    hill = [(2, H - 2), (10, 250), (30, 180), (64, 120), (112, 78), (170, 52), (236, 50), (296, 70), (344, 112), (378, 170), (394, 240), (398, H - 2)]
    p, m = s.shape(hill, '#5c5662', lw=3.6, wob=1.6)
    s.coat([(240, 40), (330, 70), (390, 160), (404, 340), (290, 340), (300, 180)], '#45404d', m, 3)
    s.coat([(40, 160), (90, 100), (150, 72), (120, 130), (60, 200), (30, 250)], '#77707e', m, 3)
    for _ in range(14):
        x = r.uniform(20, 380); y = r.uniform(90, 300); L = r.uniform(30, 70)
        s.stroke([(x, y), (x + L * .5, y + r.uniform(-6, 6)), (x + L, y + r.uniform(-4, 8))], r.uniform(1.4, 2.2), clip=m, wob=.8)
    # the grassy brow on top
    bp, bk = s.shape([(40, 150), (70, 112), (116, 76), (170, 50), (236, 48), (298, 68), (346, 110), (370, 146), (350, 140), (300, 96), (236, 76), (170, 80), (118, 102), (70, 140)], '#3b5a3b', lw=2.6, wob=1.2)
    s.coat([(236, 40), (380, 140), (300, 120), (236, 90)], '#2b4530', bk, 2)
    for _ in range(26):
        t = r.uniform(.05, .95); x = 40 + t * 330; y = 150 - math.sin(t * math.pi) * 100 + 2
        s.stroke([(x, y), (x + r.uniform(-6, 6), y - r.uniform(8, 16))], 3.6, INK, wob=.2); s.stroke([(x, y), (x + r.uniform(-6, 6), y - r.uniform(8, 16))], 1.8, r.choice(('#5b7843', '#79914c', '#4d6d40')), wob=.2)
    # the dark mouth, with a timber frame keeping it open
    mp, mk = s.shape([(124, H - 2), (120, 250), (134, 186), (172, 146), (228, 140), (268, 176), (284, 246), (280, H - 2)], '#14111a', lw=4, wob=1.2)
    s.coat([(146, 200), (170, 170), (230, 166), (258, 200), (262, H + 4), (142, H + 4)], '#0b090f', mk, 3)
    s.coat([(170, 236), (234, 232), (246, H + 4), (160, H + 4)], '#050407', mk, 2)
    for x, y in ((196, 274), (214, 262), (206, 290)): s.fill(s.curve(ell(x, y, 3, 4, 6), True, 0), '#3f9a6a', clip=mk)
    for x0 in (134, 254):
        q, qm = s.poly([(x0, H - 4), (x0 + 1, 186), (x0 + 16, 186), (x0 + 17, H - 4)], '#5a4133', lw=2.8, wob=.8)
        s.coat([(x0 + 10, 180), (x0 + 22, 180), (x0 + 22, H), (x0 + 11, H)], '#3f2c24', qm, .5)
    s.poly([(122, 172), (284, 168), (286, 190), (124, 194)], '#6a4a35', lw=3, wob=1)
    for x, y in ((160, 179), (250, 177)): s.shape(ell(x, y, 3, 3, 6), '#2f2a2e', lw=1, wob=0)
    # rails coming out of the dark
    for x0, x1 in ((186, 168), (220, 238)): s.stroke([(x0, 262), (x1, H - 2)], 3.2, '#6a6578', wob=.2)
    for y in (276, 300, 322):
        t = (y - 262) / (H - 2 - 262); s.poly([(180 - t * 22, y - 3), (226 + t * 22, y - 3), (226 + t * 22, y + 4), (180 - t * 22, y + 4)], '#4c3529', lw=1.8, wob=.3)
    for x0, x1 in ((186, 168), (220, 238)): s.stroke([(x0, 262), (x1, H - 2)], 2.4, '#8a8390', wob=.2)
    # boulders at the foot
    for x, y, rx, ry in ((40, 312, 34, 22), (92, 320, 22, 14), (352, 310, 36, 24), (306, 322, 22, 12)):
        q, qm = s.shape(ell(x, y, rx, ry, 9), '#67626f', lw=3, wob=1.2)
        s.coat([(x, y - ry - 4), (x + rx + 6, y - 4), (x + rx, y + ry + 6), (x + 4, y + ry + 6)], '#48434f', qm, 1.5)
    # a hanging lantern on the frame
    s.stroke([(268, 192), (268, 204)], 1.6, '#2a2326', wob=0)
    s.poly([(260, 206), (276, 206), (274, 226), (262, 226)], '#f7d67c', lw=2, wob=.2); s.poly([(258, 202), (278, 202), (274, 208), (262, 208)], '#2a2326', lw=1.4, wob=.1)
    a = s.done()
    a = halo_behind(a, 268, 216, 40, 40, '#f2b866', .4)
    Y, X = np.mgrid[0:H, 0:W]; g = radial(H, W, 205, 280, 60, 40) * .35; m2 = (a[..., 3] > 0)
    screen(a, g * m2, '#3fbf80')
    return a
def cave_wall(cols=15):
    W, H = cols * 64, 300; s = Sh(W, H, 811); r = s.r
    mk = s.fill(s.rough([(0, 0), (W, 0), (W, H), (0, H)], 0), '#3a3644')
    # slabs of rock leaning on each other
    for row, (y0, y1) in enumerate(((-20, 110), (70, 200), (160, 290))):
        x = -r.randint(0, 60)
        while x < W:
            w = r.randint(90, 170); top = y0 + r.uniform(-10, 14); bot = y1 + r.uniform(-12, 10); sk = r.uniform(-16, 16)
            q = [(x, bot), (x + sk * .5 + r.uniform(-6, 6), (top + bot) / 2), (x + sk + 10, top + r.uniform(0, 12)), (x + w * .5, top + r.uniform(-8, 4)), (x + w - 6 + sk, top + r.uniform(0, 14)), (x + w + r.uniform(-4, 8), (top + bot) / 2), (x + w, bot)]
            col = r.choice(('#46414f', '#3f3a48', '#4c4757', '#423d4b'))
            p, m = s.shape(q, col, lw=2.8, wob=1.8)
            s.coat([(x + w * .6, top - 10), (x + w + 20, top - 10), (x + w + 20, bot + 10), (x + w * .5, bot + 10)], '#2e2a37', m, 3)
            s.coat([(x + 8, top + 8), (x + w * .4, top + 2), (x + w * .3, top + 26), (x + 10, top + 40)], '#5a5568', m, 2)
            for _ in range(2):
                cx = x + r.uniform(.2, .8) * w; cy = r.uniform(top + 10, bot - 10)
                s.stroke([(cx, cy), (cx + r.uniform(-10, 10), cy + r.uniform(10, 26)), (cx + r.uniform(-14, 14), cy + r.uniform(26, 44))], 1.6, clip=m, wob=.8)
            x += w - r.randint(4, 20)
    # veins of green and gold, and a few glimmers
    for k in range(9):
        x = r.uniform(0, W); y = r.uniform(30, H - 60); pts = [(x, y)]
        for j in range(5): x += r.uniform(20, 46); y += r.uniform(-18, 18); pts.append((x, y))
        col = '#5fae8a' if k % 3 else '#b49a5a'
        s.stroke(pts, 4.2, '#1c1a22', wob=1); s.stroke(pts, 2.2, col, wob=1)
        for px_, py_ in pts[1:-1:2]: s.fill(s.curve(ell(px_, py_, 2.4, 2.4, 6), True, 0), '#c8ffe0' if col == '#5fae8a' else '#f2d890')
    for x in (r.uniform(80, 300), r.uniform(560, 880)):
        for ang, L, w in ((-.4, 30, 6), (.1, 42, 8), (.5, 28, 6)): crystal(s, x + ang * 20, H - 46, ang, L, w)
    s.coat([(-10, -10), (W + 10, -10), (W + 10, 34), (W * .7, 48), (W * .3, 30), (-10, 44)], '#1c1a22', mk, 4, alpha=200)
    s.coat([(-10, H - 30), (W * .4, H - 40), (W * .8, H - 26), (W + 10, H - 36), (W + 10, H + 10), (-10, H + 10)], '#24212c', mk, 3)
    for x in range(0, W, 16):
        if r.random() < .5: s.shape(ell(x + r.uniform(0, 10), H - r.uniform(4, 16), r.uniform(5, 10), r.uniform(3, 6), 8), r.choice(('#4c4757', '#3a3644')), lw=1.8, wob=.4)
    for x0 in (200, 744):
        s.poly([(x0, H), (x0 + 1, 40), (x0 + 22, 40), (x0 + 23, H)], '#5a4133', lw=3, wob=1)
        s.poly([(x0 - 30, 28), (x0 + 54, 26), (x0 + 54, 48), (x0 - 30, 50)], '#6a4a35', lw=3, wob=1)
    a = s.done(.08)
    for x in (r.uniform(80, 300), 0): pass
    return a

# ---- skies behind the regions
def silhouettes(s, x0, x1, base, seed, col, scale=1.0, lit=None, spire=None):
    "A row of town roofs as flat cut paper: gables, hips, chimneys, the odd tower."
    r = random.Random(seed); x = x0
    while x < x1:
        w = r.uniform(46, 96) * scale; wall = r.uniform(26, 50) * scale; rh = r.uniform(22, 44) * scale; top = base - wall
        kind = r.random()
        if kind < .5: roof = [(x - 3, top), (x + w / 2, top - rh), (x + w + 3, top)]
        elif kind < .8: roof = [(x - 3, top), (x + w * .25, top - rh * .8), (x + w * .75, top - rh * .8), (x + w + 3, top)]
        else: roof = [(x - 2, top), (x + w * .2, top - rh * .4), (x + w * .8, top - rh * .4), (x + w + 2, top)]
        s.fill(s.rough([(x, base + 200), (x, top)] + roof[1:-1] + [(x + w, top), (x + w, base + 200)], .6), col)
        if r.random() < .5:
            cx = x + w * r.uniform(.2, .7); s.fill(s.rough([(cx, top - rh * .3), (cx, top - rh * .9 - 8 * scale), (cx + 9 * scale, top - rh * .9 - 8 * scale), (cx + 9 * scale, top - rh * .2)], .3), col)
        if lit:
            for _ in range(r.randint(0, 3)):
                wx = x + r.uniform(.15, .8) * w; wy = top + r.uniform(.25, .7) * wall
                s.fill(s.rough([(wx, wy), (wx + 6 * scale, wy), (wx + 6 * scale, wy + 8 * scale), (wx, wy + 8 * scale)], .2), lit)
        x += w + r.uniform(-6, 10) * scale
    if spire:
        sx, sw, sh = spire
        s.fill(s.rough([(sx, base + 100), (sx, base - sh), (sx + sw, base - sh), (sx + sw, base + 100)], .5), col)
        s.fill(s.rough([(sx - 4, base - sh), (sx + sw / 2, base - sh - sw * 1.8), (sx + sw + 4, base - sh)], .5), col)
def bridge(s, x0, x1, deck, water, arches, col):
    pts = [(x0, deck), (x1, deck), (x1, water)]
    span = (x1 - x0) / arches
    for i in range(arches - 1, -1, -1):
        a = x0 + i * span; pier = span * .16; rad = (span - pier) / 2; cx = a + pier / 2 + rad
        pts.append((a + span - pier / 2, water)); top = deck + (water - deck) * .3
        pts += [(cx + math.cos(t) * rad, water - math.sin(t) * min(rad, water - top)) for t in np.linspace(0, math.pi, 9)]
        pts.append((a + pier / 2, water))
    pts.append((x0, water)); s.fill(s.rough(pts, .4), col)
    s.fill(s.rough([(x0 - 4, deck - 7), (x1 + 4, deck - 7), (x1 + 4, deck + 1), (x0 - 4, deck + 1)], .4), col)
def backdrop_town():
    h, w = 540, 960
    a = sky(h, w, ('#34304e', '#57465f', '#8a5e62', '#bd7c5a', '#e0a464'), 400, 61)
    screen(a, radial(h, w, 620, 360, 520, 300, 1.6) * .55, '#f6cf86')
    s = Sh(w, h, 62)
    for i, (cx, cy, cw) in enumerate(((180, 120, 220), (560, 80, 300), (820, 170, 160))): cloud(s, cx, cy, cw, '#6e5470', '#e09a6c', 60 + i)
    s.fill(np.concatenate([np.stack([np.arange(-4, w + 4, 4.0), C.ridge(len(np.arange(-4, w + 4, 4.0)), 318, 22, 63)], 1), [(w + 4, h + 4), (-4, h + 4)]]), '#8a6872')
    s.fill(s.rough([(-4, 352), (w + 4, 352), (w + 4, 368), (-4, 368)], 1), '#e8b06a')
    bridge(s, 470, 940, 330, 360, 6, '#6e5468')
    silhouettes(s, -20, w + 20, 388, 64, '#5c4762', .8, spire=(210, 22, 70))
    s.fill(s.rough([(-4, 384), (w + 4, 384), (w + 4, h + 4), (-4, h + 4)], 2), '#5c4762')
    silhouettes(s, -30, w + 30, 450, 65, '#3a2f48', 1.25, lit='#f0bd5c', spire=(700, 30, 90))
    s.fill(s.rough([(-4, 446), (w + 4, 446), (w + 4, h + 4), (-4, h + 4)], 2), '#2e2640')
    P.over(a, layer(s), 0, 0)
    mist(a, 372, 40, '#e0b48e', .35, 66); mist(a, 432, 46, '#b08a8a', .3, 67)
    return C.gouache(a, 61, .08)
def backdrop_meadow():
    h, w = 540, 960
    a = sky(h, w, ('#5d7aa2', '#8597b0', '#b9b2a2', '#e2c290', '#f0d4a0'), 340, 71)
    screen(a, radial(h, w, 700, 250, 480, 300, 1.6) * .5, '#fff0c0')
    s = Sh(w, h, 72)
    for i, (cx, cy, cw) in enumerate(((220, 110, 260), (640, 70, 220), (860, 150, 180))): cloud(s, cx, cy, cw, '#efe4cc', '#bdb2b0', 70 + i)
    for i, (base, amp, col, knots) in enumerate(((300, 26, '#a8ab8e', 4), (336, 30, '#8e9c72', 5), (388, 34, '#728a56', 4), (450, 30, '#5d7646', 3))):
        xs = np.arange(-4, w + 4, 4.0); s.fill(np.concatenate([np.stack([xs, C.ridge(len(xs), base, amp, 73 + i, knots)], 1), [(w + 4, h + 4), (-4, h + 4)]]), col)
        r = random.Random(80 + i)
        if i < 3:
            for _ in range(4 + i * 2):
                x = r.uniform(0, w); y = base + r.uniform(-amp * .6, amp * .4)
                s.fill(C.scallop(x, y - 6 * (i + 1), 14 * (i + 1), 9 * (i + 1), 6, r.randrange(999), .2), ('#8e9474', '#6c7f58', '#56703f')[i])
        if i == 2:
            xs2 = np.arange(-4, w + 4, 4.0); yy = C.ridge(len(xs2), base + 24, amp, 73 + i, knots)
            s.line(np.stack([xs2, yy], 1), 2.2, '#4f6a3e', taper=False)
    P.over(a, layer(s), 0, 0)
    mist(a, 312, 40, '#f0dcb4', .35, 76); mist(a, 370, 50, '#e8d2a6', .25, 77)
    return C.gouache(a, 71, .08)
def backdrop_cave():
    h, w = 540, 960
    a = sky(h, w, ('#060508', '#0b0a0f', '#100e15', '#14121a'), 540, 81, .4)
    screen(a, radial(h, w, 600, 320, 420, 220, 2) * .14, '#2f7a5a')
    s = Sh(w, h, 82); r = random.Random(83)
    for col, n, lmax in (('#121018', 22, 220), ('#18151f', 14, 150), ('#1d1a25', 9, 100)):
        x = -20
        while x < w + 20:
            wd = r.uniform(24, 70); L = r.uniform(30, lmax)
            s.fill(s.rough([(x, -4), (x + wd, -4), (x + wd * .6, L * .6), (x + wd * .45, L), (x + wd * .3, L * .5)], 1.5), col); x += wd * r.uniform(.8, 1.6)
    for col, base, n in (('#141219', 430, 6), ('#1a1720', 470, 5)):
        for _ in range(n):
            x = r.uniform(0, w); wd = r.uniform(40, 120); ht = r.uniform(60, 200)
            s.fill(s.rough([(x - wd / 2, h + 4), (x - wd * .3, base - ht * .5), (x - wd * .05, base - ht), (x + wd * .1, base - ht * .9), (x + wd * .35, base - ht * .4), (x + wd / 2, h + 4)], 2), col)
        s.fill(s.rough([(-4, base), (w + 4, base + 6), (w + 4, h + 4), (-4, h + 4)], 3), col)
    for _ in range(18):
        x, y = r.uniform(0, w), r.uniform(120, 460); s.fill(s.curve(ell(x, y, 1.4, 1.4, 6), True, 0), r.choice(('#3f9a6a', '#2f6a52', '#5fae8a')))
    P.over(a, layer(s), 0, 0)
    mist(a, 400, 60, '#1c3a30', .25, 86)
    return C.gouache(a, 81, .07)

def light(kind):
    h, w = 540, 960; Y, X = np.mgrid[0:h, 0:w]; a = np.zeros((h, w, 4), float)
    vig = np.clip(np.hypot((X - 480) / 640, (Y - 270) / 390) - .62, 0, 1) * 1.8; fog = np.clip(1 - Y / 230, 0, 1) ** 1.6
    if kind == 'town':
        pools = sum(np.clip(1 - np.hypot((X - x) / 210, (Y - y) / 150), 0, 1) ** 1.6 for x, y in ((180, 300), (520, 220), (800, 380)))
        warm = np.clip(pools * .2 + np.clip(1 - np.hypot((X - 960) / 1000, (Y + 100) / 700), 0, 1) * .16, 0, 1)
        cool = vig * .4 + fog * .18; wc, cc = [250, 186, 108], [46, 34, 66]
    elif kind == 'meadow':
        warm = np.clip(1 - np.hypot((X - 860) / 1100, (Y + 160) / 780), 0, 1) * .26 + .04
        cool = vig * .22; wc, cc = [255, 220, 150], [70, 64, 96]
    else:
        pool = np.clip(1 - np.hypot((X - 560) / 360, (Y - 300) / 250), 0, 1) ** 1.4
        warm = pool * .2; cool = (.3 + vig * .55) * np.clip(1.15 - pool * 1.4, 0, 1); wc, cc = [96, 224, 156], [6, 8, 14]
    al = 1 - (1 - warm) * (1 - cool); m = (warm / np.maximum(warm + cool, 1e-4))[..., None]
    a[..., :3] = np.array(wc) * m + np.array(cc) * (1 - m); a[..., 3] = np.clip(al, 0, 1) * 255
    return a.astype(np.uint8)

# ---- the story paintings
SW, SH_ = 1920, 1080
def frame_trees(base, seeds, pal, gaunt=False):
    for seed, x, yb, k in seeds:
        place(base, C.tree(seed, pal, gaunt), x, yb, k)
def smoke(s, x, y, r, k=1.0):
    "Chimney smoke as a rising chain of soft puffs, each wider and fainter than the last."
    cx, cy = x, y
    for j in range(7):
        rr = (9 + j * 6) * k; cx += r.uniform(-2, 9) * k; cy -= (9 + j * 4) * k
        s.fill(s.curve(C.scallop(cx, cy, rr, rr * .75, 5, r.randrange(999), .16), True, .5), '#a99eac', alpha=int(110 - j * 13))
def cloud(s, cx, cy, cw, body, lit, seed):
    "A cloud cut from paper: lumpy on top, flat underneath, its belly caught by the low sun."
    p = C.scallop(cx, cy, cw / 2, cw * .2, max(int(cw / 60), 5), seed, .3)
    p = np.array([(x, min(y, cy + cw * .05)) for x, y in p])
    s.fill(p, lit); s.fill(p + np.array([0, -cw * .028]), body)

def story1():
    "Greenhollow at dusk: a lane between cottages, every window lit."
    W, H = SW, SH_; r = random.Random(101)
    a = sky(H, W, ('#2a2b48', '#3f3a5a', '#634f66', '#93705f', '#c3936b', '#d9a874'), 600, 101)
    screen(a, radial(H, W, 1180, 560, 900, 360, 1.6) * .4, '#f2c27e')
    s = Sh(W, H, 102)
    for i, (cx, cy, cw) in enumerate(((420, 190, 460), (1300, 130, 560), (1720, 320, 300))): cloud(s, cx, cy, cw, '#574a68', '#d0906c', 110 + i)
    for _ in range(26):
        x, y = r.uniform(0, W), r.uniform(20, 300); s.fill(s.curve(ell(x, y, 1.6, 1.6, 6), True, 0), '#efe2c4')
    xs = np.arange(-4, W + 4, 4.0)
    s.fill(np.concatenate([np.stack([xs, C.ridge(len(xs), 560, 40, 103)], 1), [(W + 4, H + 4), (-4, H + 4)]]), '#5a4f6a')
    C.treeline(s, W, 640, 104, '#3f3d57', (70, 140))
    s.fill(s.rough([(-4, 640), (W + 4, 640), (W + 4, H + 4), (-4, H + 4)], 4), '#3f3d57')
    hill = s.curve([(-40, 700), (500, 668), (1000, 690), (1500, 664), (1960, 690), (1960, 1120), (-40, 1120)], True, 3); s.fill(hill, '#3b5139')
    P.over(a, layer(s), 0, 0)
    mist(a, 630, 60, '#b8a998', .4, 105, 160)
    # far cottages and trees, then the near ones along the lane
    frame_trees(a, ((305, 600, 700, .42), (306, 1080, 696, .4), (307, 260, 706, .44)), C.VILLAGE_TREE)
    cots = [(5, 91, ('#2f4a37', '#46603f', '#5b7349'), 760, 712, .46), (6, 113, ('#4a3a5a', '#6a5478', '#7d6a8a'), 1530, 708, .44),
            (7, 50, ('#5b2c2a', '#8f4a3a', '#a05c44'), 70, 778, .74), (6, 79, ('#25334f', '#3f5777', '#4c6684'), 1180, 772, .68)]
    sm = Sh(W, H, 106); lights = []
    for w_, seed, roof, x, yb, k in cots:
        img = C.cottage(w_, seed, roof); place(a, img, x, yb, k)
        cw = w_ * 64; smoke(sm, x + (cw - 92) * k, yb - 400 * k, r, k * 1.4)
        for wx in (72 + 23, cw - 118 + 23): lights.append((x + wx * k, yb - (400 - 305) * k, k))
    frame_trees(a, ((301, 640, 790, .62), (303, 1640, 800, .66)), C.VILLAGE_TREE)
    P.over(a, layer(sm), 0, 0)
    # the lane and the near grass, kept quiet for the words below
    f = Sh(W, H, 107)
    lane = f.curve([(760, H + 20), (840, 930), (900, 830), (930, 776), (1010, 770), (1060, 830), (1110, 930), (1300, H + 20)], True, 3)
    gp = f.curve([(-40, 790), (600, 770), (1200, 786), (1960, 770), (1960, 1120), (-40, 1120)], True, 3); gm = f.fill(gp, '#33482f')
    f.line(gp[:len(gp) * 5 // 9], 4, INK)
    f.fill(f.curve([(-40, 900), (500, 870), (1100, 910), (1960, 880), (1960, 1120), (-40, 1120)], True, 4), '#2b3d29')
    lm = f.fill(lane, '#5e4e40'); f.fill(f.curve([(900, 800), (1000, 790), (1030, 900), (980, H + 20), (900, H + 20), (930, 900)], True, 3), '#6b5a48', clip=lm)
    f.line(lane[:len(lane) // 2], 3, INK)
    fence = C.fence_run(6); place(a, layer(f), 0, H)
    place(a, fence, 40, 820, .7); place(a, fence, 1290, 816, .66)
    wl = C.well_img(); place(a, wl, 972 - 85 * .62, 792, .62)
    O = C.Over(H, W)
    for _ in range(140):
        x, y = r.uniform(0, W), r.uniform(790, 1060)
        if not (700 < x < 1320 and y > 780): O.tuft(x, y, r, ('#4d6d40', '#3b5a3b', '#688246'))
    O.onto(a)
    for x, y, k in lights:
        screen(a, radial(H, W, x, y, 120 * k + 40, 90 * k + 30, 2) * .5, '#f6c070')
    screen(a, radial(H, W, 960, 760, 900, 260, 2) * .12, '#f6c070')
    vignette(a, .7, .42)
    g = np.clip((np.arange(H)[:, None] - 800) / 280, 0, 1) * .35; a[..., :3] = (a[..., :3] * (1 - g[..., None])).astype(np.uint8)
    a[..., 3] = 255
    return C.gouache(a, 108, .06)

def story2():
    "Night in the village square: the old well brims with a strange green dew."
    W, H = SW, SH_; r = random.Random(201)
    a = sky(H, W, ('#0b0f1f', '#10162a', '#151d36', '#1c2642', '#26304f'), 620, 201)
    mx, my = 1540, 190; screen(a, radial(H, W, mx, my, 260, 260, 2) * .35, '#d8dcc8')
    s = Sh(W, H, 202)
    for _ in range(90):
        x, y = r.uniform(0, W), r.uniform(10, 520); rr = r.uniform(.8, 2.2)
        s.fill(s.curve(ell(x, y, rr, rr, 6), True, 0), r.choice(('#e9e4cf', '#c8cde0', '#f2e6b8')))
    p, mk = s.shape(ell(mx, my, 54, 54, 18), '#ece4c4', lw=3, wob=.6)
    s.coat([(mx - 20, my - 30), (mx + 4, my - 20), (mx - 6, my + 4), (mx - 30, my - 6)], '#cfc6a6', mk, 2); s.coat([(mx + 14, my + 10), (mx + 34, my + 4), (mx + 30, my + 30), (mx + 12, my + 28)], '#cfc6a6', mk, 2)
    C.treeline(s, W, 600, 203, '#141a2c', (90, 170))
    s.fill(s.rough([(-4, 600), (W + 4, 600), (W + 4, H + 4), (-4, H + 4)], 4), '#141a2c')
    P.over(a, layer(s), 0, 0)
    night = (.30, .34, .52)
    for w_, seed, roof, x, yb, k in ((7, 50, ('#5b2c2a', '#8f4a3a', '#a05c44'), -60, 690, .62), (6, 79, ('#25334f', '#3f5777', '#4c6684'), 1380, 688, .6), (5, 91, ('#2f4a37', '#46603f', '#5b7349'), 420, 650, .4), (6, 113, ('#4a3a5a', '#6a5478', '#7d6a8a'), 1150, 646, .38)):
        place(a, tint(C.cottage(w_, seed, roof), night), x, yb, k)
    screen(a, radial(H, W, -60 + 95 * .62, 690 - 95 * .62, 70, 50, 2) * .35, '#f2b866')
    # the square's cobbles
    g = Sh(W, H, 204)
    gp = g.curve([(-40, 680), (600, 664), (1300, 676), (1960, 662), (1960, 1120), (-40, 1120)], True, 3); gm = g.fill(gp, '#232838')
    g.line(gp[:len(gp) * 5 // 9], 4, INK)
    for row in range(16):
        y = 690 + row * (12 + row * 2.2); rr_ = 1 - row / 16
        x = -r.uniform(0, 40)
        while x < W:
            w = r.uniform(26, 40) * (1 + row * .12)
            d = abs(x - 960) / 960
            if r.random() < .75 - d * .3: g.stroke([(x, y), (x + w * .5, y + 3 + row * .4), (x + w, y)], 1.6 + row * .08, '#141826', wob=.3, alpha=int(180 * rr_ + 40), clip=gm)
            x += w
    P.over(a, layer(g), 0, 0)
    # the well, drawn large
    k = 7 / 3; wl = hires(C.well_img, 7); x0 = 960 - wl.shape[1] / 2; yb = 790; y0 = yb - wl.shape[0]
    screen(a, radial(H, W, 960, yb - 10, 420, 90, 1.5) * .45, '#5fe0a0')
    P.over(a, tint(wl, (.55, .62, .78)), x0, y0)
    wcx, wcy = x0 + 85 * k, y0 + 151 * k
    d = Sh(W, H, 205); dr = random.Random(206)
    d.fill(d.curve(ell(wcx, wcy, 50 * k, 15 * k, 18), True, .6), '#5fd8a0'); d.fill(d.curve(ell(wcx - 6 * k, wcy - 3 * k, 30 * k, 8 * k, 14), True, .6), '#c8ffe0')
    for _ in range(46):
        ang = dr.uniform(-math.pi, 0); rad = dr.uniform(.2, 1) ** .7
        x = wcx + math.cos(ang) * 260 * rad + dr.uniform(-30, 30); y = wcy - 20 - dr.uniform(0, 1) ** 1.4 * 420 + abs(math.cos(ang)) * 40
        sz = dr.uniform(3, 8) * (1.2 - rad * .5)
        d.shape([(x, y - sz * 1.8), (x + sz, y), (x, y + sz), (x - sz, y)], dr.choice(('#9ff2c4', '#c8ffe0', '#6fe0a6')), lw=1.6, wob=.1)
    for j in range(12):
        x = x0 + dr.uniform(20, 150) * k; y = y0 + dr.uniform(46, 52) * k
        d.shape([(x, y), (x + 3, y + 7), (x, y + 10), (x - 3, y + 7)], '#9ff2c4', lw=1.2, wob=.1)
    for side in (-1, 1):
        pts = [(wcx + side * 30, wcy - 10)]
        for j in range(5): pts.append((pts[-1][0] + side * dr.uniform(10, 40), pts[-1][1] - dr.uniform(40, 70)))
        d.stroke(pts, 14, '#7ef0b0', wob=4, alpha=60); d.stroke(pts, 5, '#c8ffe0', wob=4, alpha=70)
    dl = layer(d); P.over(a, dl, 0, 0)
    glow_from(a, dl[..., 3] / 255, 22, '#5fe0a0', 1.1)
    screen(a, radial(H, W, wcx, wcy - 40, 420, 380, 2) * .4, '#5fe0a0')
    vignette(a, .78, .4)
    gg = np.clip((np.arange(H)[:, None] - 800) / 280, 0, 1) * .4; a[..., :3] = (a[..., :3] * (1 - gg[..., None])).astype(np.uint8)
    a[..., 3] = 255
    return C.gouache(a, 207, .06)

def creature(s, cx, base, w, h, kind, seed, rim=True):
    "A shadow with eyes: no two built alike, all of them only a ragged dark and two lights."
    r = random.Random(seed)
    if kind == 'lump':
        p = C.scallop(cx, base - h * .45, w * .5, h * .55, 11, seed, .14)
        p = np.array([(x, min(y, base)) for x, y in p])
    elif kind == 'tall':
        p = s.curve([(cx - w * .3, base), (cx - w * .4, base - h * .5), (cx - w * .26, base - h * .86), (cx, base - h), (cx + w * .26, base - h * .86), (cx + w * .42, base - h * .5), (cx + w * .5, base - h * .1), (cx + w * .3, base)], True, 3)
    else:
        q = [(cx - w * .5, base)]
        for t in np.linspace(-.45, .45, 9): q.append((cx + t * w, base - h * (.55 + .45 * math.cos(t * 3)) * r.uniform(.8, 1.05) - (12 if r.random() < .5 else 0)))
        q.append((cx + w * .5, base)); p = s.rough(q, 2)
    m = s.fill(p, '#06080b'); s.line(p, 3, '#020304', closed=True, taper=False)
    if kind == 'tall':
        for sg in (-1, 1): s.stroke([(cx + sg * w * .35, base - h * .6), (cx + sg * w * .55, base - h * .3), (cx + sg * w * .5, base + 4)], 10, '#06080b', wob=2)
    if rim: s.line(p[int(len(p) * .55):int(len(p) * .9)] if kind != 'lump' else p[int(len(p) * .2):int(len(p) * .45)], 2.4, '#2f7a5a', alpha=180)
    ey = base - h * (.62 if kind != 'crawler' else .55); gap = w * (.16 if kind != 'tall' else .13)
    for sg in (-1, 1):
        ex = cx + sg * gap; tilt = sg * 2
        s.fill(s.curve([(ex - 7, ey + tilt), (ex, ey - 4), (ex + 7, ey - tilt), (ex, ey + 4)], True, 0), '#d8ff9a')
        s.fill(s.curve(ell(ex, ey, 2, 2.4, 6), True, 0), '#fffbe0')
    return [(cx - gap, ey), (cx + gap, ey)]
def trunk(s, x, w, top, bot, col, shade, rim=None, seed=0):
    "A trunk rising out of the picture, roots spread over the ground."
    r = random.Random(seed); lean = r.uniform(-.06, .06) * (bot - top)
    pts = [(x - w * .5 + lean, top), (x + w * .5 + lean, top), (x + w * .46 + lean * .3, bot - 120), (x + w * .6, bot - 40), (x + w * 1.3, bot + 4), (x + w * .3, bot - 4), (x, bot + 8), (x - w * .3, bot - 2), (x - w * 1.25, bot + 6), (x - w * .58, bot - 40), (x - w * .46 + lean * .3, bot - 120)]
    p, m = s.shape(pts, col, lw=3 if w > 60 else 2.4, wob=2)
    s.coat([(x + w * .1 + lean, top - 10), (x + w + lean, top - 10), (x + w * 1.4, bot + 10), (x + w * .2, bot + 10)], shade, m, 3)
    for _ in range(int((bot - top) / 60)):
        bx = x + r.uniform(-.35, .35) * w; y0 = r.uniform(top, bot - 60); L = r.uniform(40, 120)
        s.stroke([(bx + lean * (1 - (y0 - top) / (bot - top)), y0), (bx + r.uniform(-4, 4), y0 + L)], r.uniform(1.4, 2.6), '#030506', clip=m, wob=1)
    if rim: s.line(np.array([(x - w * .46 + lean * (1 - f_), top + (bot - 120 - top) * f_) for f_ in np.linspace(.15, 1, 30)]), 2.6, rim, alpha=150)
    return m
def story3():
    "The dew runs out of the village and into the woods, and something there wakes."
    W, H = SW, SH_; r = random.Random(301)
    a = sky(H, W, ('#070c12', '#0b141b', '#0f1b23', '#14252c', '#1a3034'), 560, 301)
    s = Sh(W, H, 302)
    C.treeline(s, W, 500, 303, '#13232a', (90, 170)); s.fill(s.rough([(-4, 500), (W + 4, 500), (W + 4, H + 4), (-4, H + 4)], 4), '#13232a')
    P.over(a, layer(s), 0, 0); mist(a, 520, 70, '#2f5a50', .35, 304, 160)
    s = Sh(W, H, 305)
    C.treeline(s, W, 590, 306, '#0e1a20', (110, 210)); s.fill(s.rough([(-4, 590), (W + 4, 590), (W + 4, H + 4), (-4, H + 4)], 4), '#0e1a20')
    gp = s.curve([(-40, 650), (700, 630), (1300, 650), (1960, 630), (1960, 1120), (-40, 1120)], True, 3); s.fill(gp, '#0f191d')
    for i, x in enumerate((140, 420, 700, 1010, 1240, 1520, 1800)):
        trunk(s, x + r.uniform(-30, 30), r.uniform(26, 40), -20, 650 + r.uniform(-6, 10), '#15252b', '#101d22', seed=320 + i)
    P.over(a, layer(s), 0, 0); mist(a, 620, 70, '#24463f', .35, 307, 160)
    # middle trunks, then the creatures between them, then the trunks that half hide them
    s = Sh(W, H, 313)
    for i, (x, w) in enumerate(((330, 56), (760, 64), (1120, 50), (1460, 60))):
        trunk(s, x, w, -20, 700 + i % 2 * 12, '#0f1a1f', '#0a1216', rim='#2f7a5a', seed=330 + i)
    P.over(a, layer(s), 0, 0)
    cs = Sh(W, H, 308); eyes = []
    for cx, base, w, h, kind, sd in ((560, 718, 150, 130, 'lump', 1), (948, 700, 90, 210, 'tall', 2), (1300, 722, 190, 100, 'crawler', 3), (1660, 724, 120, 110, 'lump', 4), (236, 730, 110, 90, 'crawler', 5)):
        eyes += creature(cs, cx, base, w, h, kind, 300 + sd)
    P.over(a, layer(cs), 0, 0)
    s = Sh(W, H, 314)
    for i, (x, w, bot) in enumerate(((640, 74, 760), (1440, 80, 770), (190, 70, 770))):
        trunk(s, x, w, -20, bot, '#0b1418', '#070d10', rim='#3f9a6a', seed=340 + i)
    P.over(a, layer(s), 0, 0)
    # the dew, a glowing seep that comes up from the village and branches between the roots
    d = Sh(W, H, 309); dr = random.Random(310)
    branches = [[(640, H + 30), (720, 960), (820, 880), (900, 810), (960, 760), (1060, 728), (1180, 716)], [(900, 810), (780, 778), (660, 752), (540, 736)],
                [(960, 760), (990, 732), (950, 712)], [(1060, 728), (1200, 740), (1330, 732), (1480, 742), (1650, 738)], [(820, 880), (620, 846), (420, 800), (260, 748)]]
    for i, br in enumerate(branches):
        p = C.wobble(C.spline(br, False), 16 if i == 0 else 10, 350 + i, False, every=110); n = len(p)
        d.line(p, 18 if i == 0 else 11, '#2f9a6a', taper=True, alpha=160)
        d.line(p, 6 if i == 0 else 4, '#9ff2c4', taper=True, alpha=230)
        for _ in range(10):
            q = p[dr.randrange(n)]; d.fill(d.curve(ell(q[0] + dr.uniform(-14, 14), q[1] + dr.uniform(-6, 6), 3, 3, 6), True, 0), '#c8ffe0')
    dl = layer(d)
    fade = np.clip(1 - (np.arange(H)[:, None] - 780) / 400, .25, 1); dl[..., 3] = (dl[..., 3] * fade).astype(np.uint8)
    P.over(a, dl, 0, 0); glow_from(a, dl[..., 3] / 255, 26, '#4fd69a', 1.3)
    em = np.zeros((H, W))
    for x, y in eyes: em += radial(H, W, x, y, 26, 22, 2)
    screen(a, np.clip(em, 0, 1) * .8, '#d8ff9a')
    # near trunks framing the picture, and the canopy closing over it
    s = Sh(W, H, 315)
    trunk(s, 40, 170, -40, H + 60, '#060a0c', '#030506', rim='#1f5a46', seed=361); trunk(s, 1860, 190, -40, H + 60, '#060a0c', '#030506', seed=362)
    rr = random.Random(316)
    for x in range(-60, W + 80, 110):
        s.fill(C.scallop(x, rr.uniform(-30, 30), rr.uniform(90, 140), rr.uniform(60, 110), 8, rr.randrange(999), .2), '#070d10')
    P.over(a, layer(s), 0, 0)
    gg = np.clip((np.arange(H)[:, None] - 820) / 260, 0, 1) * .45; a[..., :3] = (a[..., :3] * (1 - gg[..., None])).astype(np.uint8)
    vignette(a, .8, .38)
    a[..., 3] = 255
    return C.gouache(a, 312, .06)

def traveler():
    "The hero setting out, seen from behind: hood down, cloak, a small pack with a bedroll, a staff."
    W, H = 300, 420; s = Sh(W, H, 401)
    s.poly([(232, 92), (240, 90), (254, 412), (246, 414)], '#5a4133', lw=2.6, wob=.5)
    for x0, top in ((118, 352), (164, 354)):
        s.poly([(x0, top), (x0 + 28, top), (x0 + 28, top + 26), (x0, top + 26)], '#34395a', lw=2.6, wob=.5)
        s.shape([(x0 - 3, top + 22), (x0 + 31, top + 22), (x0 + 32, H - 8), (x0 - 4, H - 8)], '#3e2c2a', lw=2.8, wob=.5)
    cp, ck = s.shape([(104, 146), (150, 132), (196, 146), (214, 230), (234, 362), (196, 374), (150, 368), (104, 374), (66, 362), (86, 230)], '#2f5a52', lw=3.4, wob=1.2)
    s.coat([(160, 120), (210, 140), (240, 370), (170, 380), (178, 250)], '#1f3f3c', ck, 3)
    s.coat([(202, 160), (216, 160), (240, 372), (226, 374)], '#d39a62', ck, 1.5)
    for x0, x1 in ((112, 92), (138, 128), (176, 186)): s.stroke([(x0, 270), (x1, 366)], 2, clip=ck, wob=.8)
    # the right arm reaching for the staff
    s.shape([(194, 150), (214, 160), (240, 232), (228, 244), (204, 196)], '#2f5a52', lw=2.8, wob=.6)
    s.shape(ell(236, 238, 10, 9, 8), '#d6ac8c', lw=2.2, wob=.2)
    s.stroke([(206, 168), (230, 232)], 4, '#d39a62', wob=.4, alpha=200)
    # the pack and its bedroll
    pp, pk = s.poly([(112, 178), (190, 176), (196, 272), (106, 274)], '#7a5236', lw=3, wob=1)
    s.coat([(160, 170), (200, 170), (204, 280), (164, 280)], '#5a3d29', pk, 1.5)
    s.poly([(110, 178), (192, 176), (190, 214), (112, 216)], '#8f6544', lw=2.6, wob=.7)
    s.poly([(144, 204), (158, 204), (158, 222), (144, 222)], '#c79b42', lw=2, wob=.3)
    for x in (122, 178): s.stroke([(x, 214), (x + 1, 268)], 2.2, '#4a3426', clip=pk)
    bp, bk = s.shape([(100, 158), (200, 156), (206, 176), (200, 184), (100, 186), (94, 176)], '#b9a77c', lw=2.8, wob=.6)
    s.coat([(140, 150), (210, 150), (210, 190), (140, 190)], '#8f846e', bk, 1)
    s.shape(ell(98, 171, 6, 14, 10), '#cdbb92', lw=2.2, wob=.2); s.stroke([(96, 165), (99, 171), (97, 177)], 1.2, wob=.1)
    for x in (126, 176): s.stroke([(x, 154), (x, 188)], 3.2, '#4a3426', wob=.2)
    # the hood lying on the shoulders, then the head from behind
    s.shape([(108, 140), (150, 154), (194, 140), (200, 160), (150, 176), (102, 160)], '#3a6a60', lw=2.8, wob=.7)
    s.poly([(140, 120), (162, 120), (162, 146), (140, 146)], '#d6ac8c', lw=2.4, wob=.4)
    for sg in (-1, 1): s.shape(ell(150 + sg * 33, 100, 6, 9, 8), '#d6ac8c', lw=2.2, wob=.2)
    hp, hk = s.shape([(114, 108), (115, 76), (130, 58), (150, 50), (172, 58), (187, 76), (188, 108), (180, 122), (172, 114), (166, 130), (156, 120), (148, 134), (140, 120), (130, 128), (124, 114)], '#4b3a2c', lw=3.2, wob=.6)
    s.coat([(156, 50), (196, 70), (194, 130), (164, 132), (172, 96)], '#34281f', hk, 1.5)
    s.stroke([(166, 60), (182, 74), (186, 98)], 3, '#b07a3e', clip=hk, wob=.3)
    for k in range(4): x = 130 + k * 12; s.stroke([(x, 64 + k % 2 * 4), (x + 3, 118)], 1.3, '#2a1f18', clip=hk, wob=.5)
    return s.done(.05)
def story4():
    "Dawn on the road out: a lone traveler looks toward the far woods and the town by the river."
    W, H = SW, SH_; r = random.Random(401); hz = 590
    a = sky(H, W, ('#3b466e', '#59587c', '#86708a', '#c08a86', '#e8ae88', '#f6cf96', '#fbe2ae'), hz + 20, 401)
    sx, sy = 1400, hz - 6
    screen(a, radial(H, W, sx, sy, 900, 520, 1.5) * .55, '#ffe2a8')
    s = Sh(W, H, 402)
    for i, (cx, cy, cw) in enumerate(((380, 210, 520), (1040, 120, 600), (1640, 320, 400), (640, 420, 300))): cloud(s, cx, cy, cw, '#8e6f8e', '#f6b88a', 410 + i)
    s.shape(ell(sx, sy, 70, 70, 20), '#fff1cc', lw=0, wob=.4)
    xs = np.arange(-4, W + 4, 4.0)
    s.fill(np.concatenate([np.stack([xs, C.ridge(len(xs), hz - 8, 16, 403)], 1), [(W + 4, H + 4), (-4, H + 4)]]), '#a08aa0')
    rr = random.Random(404); x = -20
    while x < 1060:
        wd = rr.randint(40, 80); ht = rr.randint(60, 120) * (1 - max(x - 700, 0) / 500); p = C.scallop(x, hz - ht * .5, wd * .7, ht * .65, rr.randint(5, 8), rr.randrange(9999), .2)
        s.fill(p, '#6d6a8e'); s.fill(s.rough([(x - 3, hz - ht * .3), (x + 3, hz - ht * .3), (x + 4, hz + 40), (x - 4, hz + 40)], 1), '#6d6a8e'); x += int(wd * rr.uniform(.8, 1.2))
    silhouettes(s, 1150, 1720, hz + 6, 405, '#857596', 1.0, lit='#ffd890', spire=(1440, 26, 86))
    bridge(s, 1020, 1210, hz - 4, hz + 22, 4, '#857596')
    s.fill(s.rough([(-4, hz + 4), (W + 4, hz + 4), (W + 4, H + 4), (-4, H + 4)], 2), '#857596')
    s.fill(s.rough([(-4, hz + 20), (W + 4, hz + 20), (W + 4, hz + 28), (-4, hz + 28)], 1), '#f6d098')
    P.over(a, layer(s), 0, 0); mist(a, hz + 10, 40, '#f2d2b0', .5, 406, 140)
    f = Sh(W, H, 407)
    for i, (y, col) in enumerate(((hz + 30, '#7c7e62'), (hz + 80, '#6b7354'), (hz + 160, '#5a6646'))):
        f.fill(f.curve([(-40, y + 20), (500, y - 10), (1000, y + 16), (1500, y - 6), (1960, y + 12), (1960, 1120), (-40, 1120)], True, 3), col)
        if i < 2:
            for _ in range(10):
                x = r.uniform(0, W); f.fill(C.scallop(x, y + 4, 22 + i * 10, 10 + i * 6, 6, r.randrange(999), .2), ('#4f5a44', '#465038')[i])
    # the road: a centre line that bends toward the town, widening as it nears the eye
    ys = np.linspace(hz + 32, H + 40, 60); d = ys - (hz + 28)
    cx = 1236 - d * .52 + np.sin(d / 120) * d * .12; hw = 2 + d * .82
    left = np.stack([cx - hw, ys], 1); right = np.stack([cx + hw, ys], 1)
    road = np.concatenate([C.wobble(left, 2, 420, False), C.wobble(right, 2, 421, False)[::-1]])
    rm = f.fill(road, '#a68d6a')
    f.fill(np.concatenate([np.stack([cx + hw * .1, ys], 1), np.stack([cx + hw * 1.05, ys], 1)[::-1]]), '#b99c74', clip=rm)
    for o_ in (-.38, .38):
        rut = np.stack([cx + hw * o_, ys], 1); f.line(rut[4:], 3.4, '#8a7255', clip=rm, alpha=150)
    f.line(C.wobble(left, 2, 420, False)[2:], 3, INK); f.line(C.wobble(right, 2, 421, False)[2:], 3, INK)
    for i in range(3, 60, 6):
        k = d[i] / d[-1]
        for side in (-1, 1):
            bx = cx[i] + side * (hw[i] + 14 + k * 40); by = ys[i]; hh = 8 + k * 80; ww = 2 + k * 9
            f.poly([(bx - ww, by), (bx - ww, by - hh), (bx + ww, by - hh - 3), (bx + ww, by)], '#5a4133', lw=1.2 + k * 2, wob=.3)
    f.fill(f.curve([(-40, 900), (500, 880), (1000, 930), (1960, 890), (1960, 1120), (-40, 1120)], True, 4), '#46503a', alpha=170)
    P.over(a, layer(f), 0, 0)
    O = C.Over(H, W)
    for _ in range(90):
        x, y = r.uniform(0, W), r.uniform(700, 1060)
        j = int(np.clip(np.searchsorted(ys, y), 0, 59))
        if abs(x - cx[j]) > hw[j] + 20: O.tuft(x, y, r, ('#7c8452', '#5b6a43', '#a4a35a'))
    O.onto(a)
    t = traveler(); k = .95; tx = 1030
    sh = np.zeros((H, W)); sh += radial(H, W, tx + 10, 786, 110, 16, 1); mix(a, np.clip(sh, 0, 1) * .45, '#4a3a3a')
    place(a, t, tx - 150 * k, 792, k)
    screen(a, radial(H, W, sx, sy, 1400, 700, 2) * .16, '#ffd8a0')
    vignette(a, .55, .45)
    gg = np.clip((np.arange(H)[:, None] - 820) / 260, 0, 1) * .3; a[..., :3] = (a[..., :3] * (1 - gg[..., None])).astype(np.uint8)
    a[..., 3] = 255
    return C.gouache(a, 408, .06)

def create_bg():
    "A quiet room for choosing who to be: wardrobe, tall mirror, a low lamp; the middle left plain for the panels."
    W, H = SW, SH_; r = random.Random(501)
    s = Sh(W, H, 502)
    wall = s.fill(s.rough([(0, 0), (W, 0), (W, H), (0, H)], 0), '#5e4a3e')
    x = 0
    while x < W:
        w = r.randint(110, 150); s.fill(s.rough([(x, 150), (x + w, 150), (x + w, 880), (x, 880)], 1), r.choice(('#5e4a3e', '#634e40', '#58463a')), clip=wall)
        s.stroke([(x + w, 150), (x + w + r.uniform(-2, 2), 880)], 2.2, '#3a2c25', wob=1); x += w
    s.coat([(-10, 150), (W + 10, 150), (W + 10, 300), (W * .6, 330), (W * .3, 290), (-10, 320)], '#4a3a31', wall, 6)
    for x in range(0, W, 240): s.poly([(x, -4), (x + 40, -4), (x + 40, 150), (x, 150)], '#3b2a24', lw=3, wob=1.2)
    s.poly([(-4, 120), (W + 4, 118), (W + 4, 160), (-4, 162)], '#3b2a24', lw=3.4, wob=1.4)
    s.poly([(-4, 870), (W + 4, 868), (W + 4, 900), (-4, 902)], '#3b2a24', lw=3.4, wob=1.4)
    s.fill(s.rough([(0, 900), (W, 900), (W, H), (0, H)], 1), '#3e2c24')
    for y in (950, 1010): s.stroke([(0, y), (W, y + r.uniform(-3, 3))], 2, '#2a1e19', wob=1)
    # the rug
    rp, rk = s.poly([(420, 1000), (1500, 1000), (1600, H + 10), (320, H + 10)], '#6d3448', lw=3.4, wob=2)
    s.line(s.rough([(450, 1016), (1470, 1016), (1556, H + 10), (366, H + 10)], 1.2), 3, '#c79b42', closed=True, taper=False, clip=rk)
    # the wardrobe
    wp, wk = s.poly([(90, 1000), (90, 260), (560, 260), (560, 1000)], '#6a4a35', lw=4, wob=1.6)
    s.coat([(400, 240), (580, 240), (580, 1010), (420, 1010)], '#4c3529', wk, 3)
    s.shape([(70, 270), (90, 210), (325, 180), (560, 210), (580, 270)], '#5a3f30', lw=4, wob=1.2)
    s.shape([(270, 210), (325, 168), (380, 210), (325, 222)], '#c79b42', lw=2.6, wob=.6)
    for x0 in (120, 330):
        dp, dk = s.poly([(x0, 290), (x0 + 200, 290), (x0 + 200, 940), (x0, 940)], '#7a5638', lw=3, wob=1)
        s.coat([(x0 + 130, 280), (x0 + 210, 280), (x0 + 210, 950), (x0 + 140, 950)], '#5e4230', dk, 2)
        for y0, y1 in ((320, 600), (640, 910)): s.line(s.rough([(x0 + 24, y0), (x0 + 176, y0), (x0 + 176, y1), (x0 + 24, y1)], 1), 2.4, '#3a2922', closed=True, taper=False, clip=dk)
    for x in (308, 342): s.shape(ell(x, 620, 7, 9, 8), '#d7a941', lw=2, wob=.2)
    for x in (110, 540): s.poly([(x - 14, 1000), (x + 14, 1000), (x + 10, 1030), (x - 10, 1030)], '#3a2922', lw=2.6, wob=.6)
    # the standing mirror
    mx, my = 1640, 560
    s.poly([(mx - 8, 900), (mx + 8, 900), (mx + 8, 1040), (mx - 8, 1040)], '#5a3f30', lw=2.6, wob=.6)
    s.stroke([(mx - 120, 1040), (mx, 1000), (mx + 120, 1040)], 10, '#5a3f30', wob=.5)
    s.shape(ell(mx, my, 200, 340, 28), '#a8803c', lw=4, wob=1.2)
    gp, gk = s.shape(ell(mx, my, 168, 306, 26), '#4f5a74', lw=3, wob=.8)
    s.coat([(mx - 170, my + 80), (mx + 170, my - 40), (mx + 170, my + 320), (mx - 170, my + 320)], '#3d465e', gk, 4)
    s.coat([(mx - 120, my - 200), (mx - 60, my - 260), (mx + 40, my - 80), (mx - 20, my - 40)], '#7d89a2', gk, 3, alpha=150)
    s.coat([(mx + 40, my - 90), (mx + 70, my - 120), (mx + 120, my - 20), (mx + 90, my + 10)], '#9aa5bb', gk, 2, alpha=120)
    s.line(np.array(ell(mx, my, 184, 322, 40)), 2.2, '#e6c46a', closed=True, taper=False)
    # a lamp on a little stand, and a window with the night in it
    tx = 1280; s.poly([(tx - 70, 760), (tx + 70, 760), (tx + 60, 780), (tx - 60, 780)], '#5a3f30', lw=3, wob=.8)
    for x in (tx - 50, tx + 46): s.poly([(x, 780), (x + 8, 780), (x + 6, 900), (x + 2, 900)], '#3a2922', lw=2.4, wob=.5)
    s.poly([(tx - 20, 760), (tx + 20, 760), (tx + 14, 700), (tx - 14, 700)], '#7a5638', lw=2.6, wob=.5)
    s.shape([(tx - 54, 700), (tx - 32, 620), (tx + 32, 620), (tx + 54, 700)], '#e6c46a', lw=2.8, wob=.6)
    wx = 760; s.poly([(wx - 14, 220), (wx + 254, 220), (wx + 254, 520), (wx - 14, 520)], '#3a2922', lw=3, wob=1)
    gp, gk = s.poly([(wx, 236), (wx + 240, 236), (wx + 240, 504), (wx, 504)], '#26304f', lw=2.4, wob=.8)
    s.coat([(wx, 400), (wx + 240, 360), (wx + 240, 520), (wx, 520)], '#1c2440', gk, 3)
    s.shape(ell(wx + 170, 300, 22, 22, 12), '#e9e2c4', lw=2, wob=.3)
    s.stroke([(wx + 120, 236), (wx + 120, 504)], 5); s.stroke([(wx, 370), (wx + 240, 370)], 5)
    for sx, sg in ((wx - 30, -1), (wx + 270, 1)):
        cp, ck = s.shape([(sx - 30 * sg, 200), (sx + 30 * sg, 200), (sx + 40 * sg, 560), (sx - 40 * sg, 560)], '#7a3448', lw=3, wob=1)
        for k in (-14, 0, 14): s.stroke([(sx + k, 210), (sx + k * 1.3, 550)], 1.8, clip=ck)
    s.poly([(wx - 80, 196), (wx + 320, 196), (wx + 320, 210), (wx - 80, 210)], '#3a2922', lw=2.4, wob=.6)
    a = layer(s)
    screen(a, radial(H, W, tx, 660, 620, 460, 1.6) * .45, '#f2b866')
    screen(a, radial(H, W, mx - 40, 420, 240, 300, 2) * .18, '#c8d0e8')
    # quiet it down so the panels read: dim and soften the middle
    mid = radial(H, W, 900, 560, 900, 560, 1.2)
    a[..., :3] = (a[..., :3] * (.62 - mid[..., None] * .12)).astype(np.uint8)
    vignette(a, .7, .38)
    a[..., 3] = 255
    return C.gouache(a, 503, .06)

# ---- the build
def sz(a): return int(a.shape[1]), int(a.shape[0])
def build(out):
    os.makedirs(out, exist_ok=True); meta = {}; t0 = time.time()
    def put(name, img, dw, dh, kind, **extra):
        save(img, os.path.join(out, name)); w, h = sz(img)
        meta[name] = dict(width=w, height=h, drawWidth=dw, drawHeight=dh, kind=kind, **extra)
        print(f'{name:22s} {w}x{h}  draw {dw}x{dh}  {time.time() - t0:5.1f}s', flush=True)
    for k, seed in (('a', 901), ('b', 902), ('c', 903)): put(f'town_house_{k}.png', town_house(k, seed), 384, 540, 'prop')
    put('shelter.png', shelter(), 384, 440, 'prop')
    put('guardpost.png', guardpost(), 192, 400, 'prop')
    put('stall_food.png', stall('food'), 192, 224, 'prop'); put('stall_goods.png', stall('goods'), 192, 224, 'prop')
    put('fountain.png', fountain(), 192, 176, 'prop')
    put('fountain_water.png', fountain_water(), 192, 176, 'sheet', frames=4, frameWidth=240, frameHeight=220, note='overlay at the fountain position and size')
    put('lamp.png', lamp(), 88, 224, 'prop'); put('crates.png', crates(), 136, 128, 'prop'); put('bench.png', bench(), 152, 88, 'prop')
    put('banner_pole.png', banner_pole(), 80, 240, 'prop'); put('board.png', board(), 168, 184, 'prop')
    put('flowers_patch.png', flowers_patch(), 120, 104, 'prop'); put('haystack.png', haystack(), 168, 152, 'prop')
    put('stone_wall.png', stone_wall(), 192, 88, 'prop'); put('meadow_sign.png', meadow_sign(), 112, 136, 'prop')
    put('cave_mouth.png', cave_mouth(), 320, 264, 'prop'); put('crystal_cluster.png', crystal_cluster(), 120, 128, 'prop')
    put('stalagmite.png', stalagmite(), 88, 160, 'prop'); put('cave_rock.png', cave_rock(), 104, 88, 'prop'); put('minecart.png', minecart(), 144, 120, 'prop')
    put('cave_wall.png', cave_wall(15), 960, 300, 'wall')
    put('backdrop_town.png', backdrop_town(), 1920, 1080, 'backdrop'); put('backdrop_meadow.png', backdrop_meadow(), 1920, 1080, 'backdrop'); put('backdrop_cave.png', backdrop_cave(), 1920, 1080, 'backdrop')
    for k in ('town', 'meadow', 'cave'): put(f'light_{k}.png', light(k), 1920, 1080, 'light')
    for i, fn in enumerate((story1, story2, story3, story4), 1): put(f'story{i}.png', fn(), 1920, 1080, 'story', captionSafe='lower 30% kept quiet')
    put('create_bg.png', create_bg(), 1920, 1080, 'background')
    with open(os.path.join(out, 'world.json'), 'w') as f:
        json.dump(dict(world=dict(width=1920, height=1080, tile=64, hero=[102, 136], cottage=[448, 400]), files=meta), f, indent=1)
    contact(out, meta)
    print(f'done in {time.time() - t0:.1f}s')

def contact(out, meta, width=2400):
    try: font = ImageFont.truetype(os.path.join(HERE, 'fonts', 'IBMPlexSans-SemiBold.ttf'), 18)
    except Exception: font = ImageFont.load_default()
    bg = (118, 118, 118); pad = 16; lab = 26
    names = [n for n in meta if meta[n]['kind'] not in ('story', 'background')]
    big = [n for n in meta if meta[n]['kind'] in ('story', 'background')]
    rows = []; row = []; x = pad
    def tile_of(n, k):
        im = Image.open(os.path.join(out, n)).convert('RGBA'); return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    tiles = []
    for n in names:
        k = .5 if meta[n]['width'] >= 900 else .8
        if n.startswith('light_'): k = .4
        tiles.append((n, tile_of(n, k)))
    for n, im in tiles:
        cw = max(im.width, int(font.getlength(f'{n}  {meta[n]["width"]}x{meta[n]["height"]}')) + 4)
        if x + cw + pad > width and row: rows.append(row); row = []; x = pad
        row.append((n, im)); x += cw + pad
    if row: rows.append(row)
    bw = (width - pad * 4) // 3
    btiles = [(n, tile_of(n, bw / 1920)) for n in big]
    brows = [btiles[i:i + 3] for i in range(0, len(btiles), 3)]
    H = pad + sum(max(im.height for _, im in r_) + lab + pad for r_ in rows + brows)
    sheet = Image.new('RGBA', (width, H), bg + (255,)); d = ImageDraw.Draw(sheet); y = pad
    for r_ in rows + brows:
        x = pad; rh = max(im.height for _, im in r_)
        for n, im in r_:
            if n.startswith('light_'):
                chk = Image.new('RGBA', im.size, (200, 200, 200, 255)); dd = ImageDraw.Draw(chk)
                for yy in range(0, im.height, 16):
                    for xx in range(0, im.width, 16):
                        if (xx // 16 + yy // 16) % 2: dd.rectangle((xx, yy, xx + 15, yy + 15), fill=(150, 150, 150, 255))
                chk.alpha_composite(im); im = chk
            lbl = f'{n}  {meta[n]["width"]}x{meta[n]["height"]}'
            sheet.alpha_composite(im, (x, y + rh - im.height)); d.text((x, y + rh + 3), lbl, fill=(20, 18, 16), font=font); x += max(im.width, int(font.getlength(lbl)) + 4) + pad
        y += rh + lab + pad
    sheet.convert('RGB').save(os.path.join(out, 'contact.png'))

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out6_world'))
