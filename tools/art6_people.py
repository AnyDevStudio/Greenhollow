# Greenhollow's people, in layers a player can choose between: a body (skin and clothes), hair (style and color) and
# what they carry (sword, bow or staff). Each layer is a sheet of the same 12 frames per look, so the game stacks
# them on one spot and plays the same animation on each. Also the townsfolk who walk about, and the quest givers.
import math, os, sys, zlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art2 as P
import art4 as C
from art4 import Sheet, INK

FW, FH = 120, 160
DIRS = (('down', (0, 1, 0, -1)), ('up', (0, -1, 0, 1)), ('side', (0, 1, 0, -1)))  # 12 frames: 4 down, 4 up, 4 side

SKINS = [('#f0d2b0', '#d2ad8b', '#e7a98e'), ('#d6ac8c', '#a87a64', '#c98a72'), ('#8f5f43', '#6b4532', '#a8644e')]
OUTFITS = [  # top (light, shade, edge), bottom (light, shade), cape (main, shade, back)
    (('#2f6b66', '#1e4a4c', '#6ba88d'), ('#34395a', '#232642'), ('#7d3250', '#642541', '#5a2140')),
    (('#a8743a', '#7a4f27', '#d4a25c'), ('#3b3448', '#28222f'), ('#3f6b4a', '#2c4e36', '#24402c')),
    (('#6a3d6e', '#4a2a4e', '#9a6aa0'), ('#2f2f3e', '#1f1f2a'), ('#c79b42', '#9c7630', '#8a6a2c')),
    (('#4c6b3a', '#33502a', '#7e9c5c'), ('#4a3a2c', '#33281f'), ('#7b2f2f', '#5a2222', '#4e1d1d')),
]
HAIRS = [('#2d2230', '#4b3a44'), ('#5a3a26', '#83593a'), ('#c79a48', '#e8c97a'), ('#8a3b2a', '#b85e3e')]
STYLES = ('short', 'long', 'tied')
GEAR = ('sword', 'bow', 'staff')


def look(skin=0, outfit=0, hair=0, style='short', **extra):
    top, bot, cape = OUTFITS[outfit]
    d = dict(skin=SKINS[skin], top=top, bot=bot, cape=cape, hair=HAIRS[hair], style=style, boot='#3e2c2a', belt='#5c3f2b', buckle='#c79b42')
    d.update(extra)
    return d


def hair_shape(style, d, hx, hy, R):
    "The outline of the hair for a style, seen from one side."
    if style == 'long':
        if d == 'down':
            return [(hx - R - 4, hy + R * .95), (hx - R - 5, hy - 14), (hx - R * .6, hy - R - 3), (hx, hy - R - 6), (hx + R * .6, hy - R - 3), (hx + R + 5, hy - 14), (hx + R + 4, hy + R * .95),
                    (hx + R * .74, hy + R), (hx + R * .78, hy - 4), (hx + R * .42, hy - 6), (hx + R * .16, hy - 12), (hx - R * .2, hy - 6), (hx - R * .55, hy - 10), (hx - R * .78, hy - 4), (hx - R * .74, hy + R)]
        if d == 'up':
            return [(hx - R - 4, hy + R * 1.05), (hx - R - 5, hy - 14), (hx - R * .6, hy - R - 3), (hx, hy - R - 6), (hx + R * .6, hy - R - 3), (hx + R + 5, hy - 14), (hx + R + 4, hy + R * 1.05),
                    (hx + R * .5, hy + R * 1.3), (hx, hy + R * 1.18), (hx - R * .5, hy + R * 1.3)]
        return [(hx - R - 6, hy + R * 1.1), (hx - R - 5, hy - 12), (hx - R * .55, hy - R - 3), (hx + R * .1, hy - R - 6), (hx + R * .72, hy - R * .72), (hx + R + 2, hy - 12),
                (hx + R * .55, hy - 8), (hx + R * .1, hy - 13), (hx - R * .12, hy + 2), (hx - R * .25, hy + R * 1.1)]
    # short and tied share the cap of hair; tied adds a knot
    if d == 'down':
        return [(hx - R - 2, hy + 10), (hx - R - 3, hy - 14), (hx - R * .6, hy - R - 3), (hx, hy - R - 6), (hx + R * .6, hy - R - 3), (hx + R + 3, hy - 14), (hx + R + 2, hy + 10),
                (hx + R * .76, hy - 7), (hx + R * .42, hy - 3), (hx + R * .16, hy - 12), (hx - R * .2, hy - 5), (hx - R * .55, hy - 10), (hx - R * .8, hy - 3)]
    if d == 'up':
        return [(hx - R - 2, hy + 14), (hx - R - 3, hy - 14), (hx - R * .6, hy - R - 3), (hx, hy - R - 6), (hx + R * .6, hy - R - 3), (hx + R + 3, hy - 14), (hx + R + 2, hy + 14),
                (hx + R * .5, hy + R * .96), (hx, hy + R * .8), (hx - R * .5, hy + R * .96)]
    return [(hx - R - 3, hy + 18), (hx - R - 4, hy - 12), (hx - R * .55, hy - R - 3), (hx + R * .1, hy - R - 6), (hx + R * .72, hy - R * .72), (hx + R + 2, hy - 12),
            (hx + R * .55, hy - 8), (hx + R * .1, hy - 13), (hx - R * .12, hy + 2), (hx - R * .4, hy + R * .8), (hx - R * .86, hy + R * .72)]


def draw_hair(s, L, d, hx, hy, R):
    H0, H1 = L['hair']
    if L['style'] == 'tied':  # a knot of hair, drawn first so the cap overlaps its base
        bx, by = (hx - R * .62, hy - R * .7) if d == 'side' else (hx, hy - R - 8)
        s.shape([(bx - 13, by + 2), (bx - 9, by - 11), (bx + 9, by - 11), (bx + 13, by + 2), (bx, by + 10)], H0, lw=2.8, wob=.6)
        s.stroke([(bx - 6, by - 6), (bx + 3, by - 2)], 1.4, H1)
    p, mk = s.shape(hair_shape(L['style'], d, hx, hy, R), H0, lw=3.2, wob=.7)
    s.fill(s.curve([(hx - R * .7, hy - R * .56), (hx - R * .15, hy - R * .9), (hx + R * .26, hy - R * .84), (hx - R * .1, hy - R * .62), (hx - R * .6, hy - R * .3)], True, 1), H1, clip=mk)
    for k in range(3):
        a = -1 + k
        s.stroke([(hx + a * R * .3, hy - R * .9), (hx + a * R * .5, hy - R * .5)], 1.3, '#191216', clip=mk)


def draw_gear(s, kind, d, cx, dy, leg):
    "What the hero carries in hand. From the side a sword points forward, a bow or staff is held out in front."
    sw = leg * 6
    if d == 'down':
        x, y = cx + 34, 122 + sw + dy
    elif d == 'up':
        x, y = cx - 34, 122 - sw + dy
    else:
        x, y = (cx + 18 - leg * 8, 128 + dy) if kind == 'sword' else (cx + 34 - leg * 4, 126 + dy)
    if d == 'side' and kind == 'sword':
        # the same sword, turned about the grip so the blade points ahead at hand height
        turn = math.radians(72)
        def rot(points):
            return [(x + (px - x) * math.cos(turn) - (py - y) * math.sin(turn), y + (px - x) * math.sin(turn) + (py - y) * math.cos(turn)) for px, py in points]
        s.shape(rot([(x - 3, y - 64), (x + 3, y - 64), (x + 4, y - 12), (x, y - 6), (x - 4, y - 12)]), '#c9ccd2', lw=2.4, smooth=False, wob=.4)
        s.shape(rot([(x - 13, y - 12), (x + 13, y - 12), (x + 13, y - 6), (x - 13, y - 6)]), '#c79b42', lw=2.2, smooth=False, wob=.3)
        s.shape(rot([(x - 4, y - 6), (x + 4, y - 6), (x + 4, y + 10), (x - 4, y + 10)]), '#5c3f2b', lw=2, smooth=False, wob=.3)
        return
    if kind == 'sword':
        s.shape([(x - 3, y - 64), (x + 3, y - 64), (x + 4, y - 12), (x, y - 6), (x - 4, y - 12)], '#c9ccd2', lw=2.4, smooth=False, wob=.4)
        s.stroke([(x, y - 60), (x, y - 16)], 1.2, '#f2f0e8')
        s.shape([(x - 13, y - 12), (x + 13, y - 12), (x + 13, y - 6), (x - 13, y - 6)], '#c79b42', lw=2.2, smooth=False, wob=.3)
        s.shape([(x - 4, y - 6), (x + 4, y - 6), (x + 4, y + 10), (x - 4, y + 10)], '#5c3f2b', lw=2, smooth=False, wob=.3)
        s.shape([(x - 6, y + 9), (x + 6, y + 9), (x + 5, y + 16), (x - 5, y + 16)], '#c79b42', lw=2, wob=.3)
    elif kind == 'bow':
        pts = [(x + 2, y - 58), (x + 16, y - 34), (x + 20, y - 4), (x + 16, y + 24), (x + 2, y + 46)]
        s.line(s.curve(pts, False, .3), 6.4, INK)
        s.line(s.curve(pts, False, .3), 3.6, '#8a5a32')
        s.stroke([(x + 2, y - 56), (x + 1, y + 44)], 1.2, '#efe6cc', wob=.1)
        s.shape([(x + 12, y - 8), (x + 22, y - 8), (x + 22, y + 6), (x + 12, y + 6)], '#5c3f2b', lw=1.8, smooth=False, wob=.3)
    else:
        s.shape([(x - 3, y - 70), (x + 3, y - 70), (x + 4, y + 30), (x - 4, y + 30)], '#6b4a2e', lw=2.4, smooth=False, wob=.6)
        s.stroke([(x - 1, y - 60), (x - 1, y + 20)], 1.2, '#9a7148')
        s.shape([(x - 12, y - 78), (x, y - 96), (x + 12, y - 78), (x, y - 64)], '#5fbfa6', lw=2.6, wob=.5)
        s.fill(s.curve([(x - 5, y - 82), (x, y - 90), (x + 3, y - 82), (x, y - 76)], True, .3), '#d8f5e6')
        s.stroke([(x - 10, y - 66), (x - 4, y - 72), (x + 4, y - 72), (x + 10, y - 66)], 2, '#c79b42')


def person(L, d, leg, breathe=0, seed=0, part='all', gear=None, extra=None):
    "One frame of a person. part is 'all', 'body' (no hair), 'hair' or 'gear'."
    key = repr((sorted((k, v.__name__ if callable(v) else str(v)) for k, v in L.items()), d, leg, breathe, seed, part, gear))
    s = Sheet(FW, FH, zlib.crc32(key.encode()) & 0xffff)
    T, Td, Tl = L['top']; Bo, Bd = L['bot']; SK = L['skin']; dy = breathe * 2.5; cx = 60
    hx = cx + (5 if d == 'side' else 0); hy = 70 + dy; R = 31
    if part == 'hair':
        draw_hair(s, L, d, hx, hy, R)
        return s.done(.05)
    if part == 'gear':
        if d == 'up':
            draw_gear(s, gear, d, cx, dy, leg)
        else:
            draw_gear(s, gear, d, cx, dy, leg)
        return s.done(.05)
    robe = L.get('robe', False)
    if robe:
        p, m = s.shape([(cx - 22, 100 + dy), (cx - 30, 132), (cx - 37, 155), (cx, 159), (cx + 37, 155), (cx + 30, 132), (cx + 22, 100 + dy)], T, lw=3.2)
        s.fill(s.curve([(cx + 6, 100), (cx + 44, 120), (cx + 44, 160), (cx + 8, 160), (cx + 14, 130)], True, 1.4), Td, clip=m)
        for x in (-14, 4, 20): s.stroke([(cx + x, 126), (cx + x * 1.25, 154)], 1.6, clip=m)
    elif d == 'side':
        for k, (sw, col) in enumerate(((-leg * 12, Bd), (leg * 12, Bo))):
            s.shape([(cx - 9 + sw * .25, 122), (cx + 9 + sw * .25, 122), (cx + 9 + sw, 146), (cx - 7 + sw, 146)], col, lw=2.8, smooth=False, wob=.7)
            s.shape([(cx - 9 + sw, 145), (cx + 6 + sw, 143), (cx + 18 + sw, 150), (cx + 17 + sw, 157), (cx - 9 + sw, 157)], L['boot'], lw=2.8, wob=.6)
    else:
        l, rr = max(leg, 0) * 5, max(-leg, 0) * 5
        for x, lift in ((-13, rr), (13, l)):
            s.shape([(cx + x - 9, 122), (cx + x + 9, 122), (cx + x + 8, 146 - lift), (cx + x - 8, 146 - lift)], Bo if x < 0 else Bd, lw=2.8, smooth=False, wob=.7)
            s.shape([(cx + x - 11, 146 - lift), (cx + x, 142 - lift), (cx + x + 11, 146 - lift), (cx + x + 12, 156 - lift), (cx + x - 12, 156 - lift)], L['boot'], lw=2.8, wob=.6)
    sw = leg * 6

    def arm(x0, x1, ys, colr=T):
        s.shape([(x0 - 7, 98 + dy), (x0 + 7, 97 + dy), (x1 + 7, ys + dy), (x1 - 7, ys + dy)], colr, lw=2.8, wob=.7, smooth=False)
        s.shape([(x1 - 7, ys - 2 + dy), (x1 + 7, ys - 2 + dy), (x1 + 8, ys + 9 + dy), (x1, ys + 14 + dy), (x1 - 8, ys + 9 + dy)], SK[0], lw=2.4, wob=.4)
    m = None
    if d == 'side':
        arm(cx - 3, cx - 3 - leg * 12, 122, Td)
        p, m = s.shape([(cx - 19, 100 + dy), (cx, 93 + dy), (cx + 19, 101 + dy), (cx + 23, 132), (cx, 136), (cx - 24, 132)], T, lw=3.2)
        s.fill(s.curve([(cx - 30, 100), (cx - 6, 96), (cx - 12, 140), (cx - 30, 140)], True, 1.4), Td, clip=m)
    elif not robe:
        arm(cx - 31, cx - 33, 120 - sw); arm(cx + 31, cx + 33, 120 + sw, Td)
        p, m = s.shape([(cx - 24, 102 + dy), (cx, 94 + dy), (cx + 24, 102 + dy), (cx + 30, 132), (cx, 137), (cx - 30, 132)], T, lw=3.2)
        s.fill(s.curve([(cx + 8, 92), (cx + 36, 100), (cx + 36, 142), (cx + 6, 142), (cx + 16, 120)], True, 1.4), Td, clip=m)
    else:
        arm(cx - 27, cx - 31, 120 - sw); arm(cx + 27, cx + 31, 120 + sw, Td)
    CP = L['cape']
    if L.get('hero', True) and not robe:
        if d == 'down':
            s.fill(s.curve([(cx - 22, 108), (cx - 10, 104), (cx - 14, 128), (cx - 26, 126)], True, 1), Tl, clip=m)
            s.shape([(cx - 30, 124 + dy), (cx, 128 + dy), (cx + 30, 124 + dy), (cx + 30, 132 + dy), (cx, 136 + dy), (cx - 30, 132 + dy)], L['belt'], lw=2.2, wob=.5)
            s.shape([(cx - 6, 124 + dy), (cx + 6, 124 + dy), (cx + 7, 136 + dy), (cx - 7, 136 + dy)], L['buckle'], lw=2, smooth=False, wob=.4)
            s.shape([(cx - 22, 92 + dy), (cx, 99 + dy), (cx + 22, 92 + dy), (cx + 21, 104 + dy), (cx, 110 + dy), (cx - 21, 104 + dy)], CP[0], lw=2.8, wob=.7)
            s.shape([(cx + 10, 104 + dy), (cx + 20, 104 + dy), (cx + 22, 126 + dy), (cx + 14, 128 + dy)], CP[1], lw=2.4, wob=.6)
        elif d == 'up':
            c, cm = s.shape([(cx - 22, 94 + dy), (cx, 90 + dy), (cx + 22, 94 + dy), (cx + 33, 140), (cx, 146), (cx - 33, 140)], CP[0], lw=3.2)
            s.fill(s.curve([(cx + 4, 88), (cx + 40, 96), (cx + 40, 150), (cx + 8, 150), (cx + 16, 120)], True, 1.4), CP[2], clip=cm)
            for x in (-16, 2, 17): s.stroke([(cx + x * .6, 102), (cx + x * 1.2, 140)], 1.5, clip=cm)
        else:
            s.shape([(cx - 14, 94 + dy), (cx + 14, 94 + dy), (cx + 2, 108 + dy), (cx - 32 - leg * 5, 142), (cx - 44 - leg * 5, 126)], CP[0], lw=2.8)
            s.shape([(cx - 18, 92 + dy), (cx + 18, 92 + dy), (cx + 18, 104 + dy), (cx - 18, 104 + dy)], CP[0], lw=2.6, wob=.5)
            s.shape([(cx - 23, 124 + dy), (cx + 22, 124 + dy), (cx + 22, 132 + dy), (cx - 23, 132 + dy)], L['belt'], lw=2.2, smooth=False, wob=.5)
    if extra and d == 'down':
        extra(s, cx, dy)
    # head
    hp, hm = s.shape([(hx - R, hy + 1), (hx - R * .72, hy - R * .72), (hx, hy - R * .96), (hx + R * .72, hy - R * .72), (hx + R, hy + 1), (hx + R * .76, hy + R * .72), (hx, hy + R * .98), (hx - R * .76, hy + R * .72)], SK[0], lw=3.2, wob=.5)
    s.fill(s.curve([(hx + R * .2, hy + R * 1.1), (hx + R * .9, hy + R * .8), (hx + R * 1.2, hy - R * .3), (hx + R * .76, hy + R * .1)], True, 1), SK[1], clip=hm)
    blink = breathe == 1 and leg == 0 and L.get('blinks', False)
    if d == 'down':
        for ex in (-13, 13):
            if blink:
                s.stroke([(hx + ex - 5, hy + 4), (hx + ex, hy + 6), (hx + ex + 5, hy + 4)], 2.6)
            else:
                s.fill(s.curve([(hx + ex - 4, hy + 1), (hx + ex, hy - 5), (hx + ex + 4, hy + 1), (hx + ex, hy + 9)], True, 0), INK)
                s.fill(s.curve([(hx + ex - 2.6, hy - 1), (hx + ex - .6, hy - 3), (hx + ex + .4, hy - 1), (hx + ex - 1.2, hy + 1)], True, 0), '#f2ead8')
            s.fill(s.curve([(hx + ex * 1.35 - 5, hy + 11), (hx + ex * 1.35, hy + 9), (hx + ex * 1.35 + 5, hy + 11), (hx + ex * 1.35, hy + 14)], True, .3), SK[2])
        s.stroke([(hx - 4, hy + 15), (hx, hy + 17), (hx + 4, hy + 15)], 1.8, '#5e3528')
    elif d == 'side':
        if blink:
            s.stroke([(hx + 13, hy + 4), (hx + 18, hy + 6)], 2.6)
        else:
            s.fill(s.curve([(hx + 11, hy + 1), (hx + 15, hy - 5), (hx + 19, hy + 1), (hx + 15, hy + 9)], True, 0), INK)
            s.fill(s.curve([(hx + 13, hy - 1), (hx + 15, hy - 3), (hx + 16, hy - 1), (hx + 14, hy + 1)], True, 0), '#f2ead8')
        s.fill(s.curve([(hx + 4, hy + 11), (hx + 9, hy + 9), (hx + 14, hy + 11), (hx + 9, hy + 14)], True, .3), SK[2])
        s.stroke([(hx + 14, hy + 16), (hx + 20, hy + 15)], 1.8, '#5e3528')
    if part == 'all':
        draw_hair(s, L, d, hx, hy, R)
        if L.get('hat'):
            L['hat'](s, hx, hy, R, d)
    return s.done(.05)


def frames(L, part='body', gear=None, blinks=False):
    "The 12 frames of one look: walking down, up and to the side, four each."
    L = dict(L, blinks=blinks)
    out = []
    for d, legs in DIRS:
        for c, leg in enumerate(legs):
            out.append(person(L, d, leg, 1 if leg else 0, c, part, gear))
    return out


def lay_out(frame_list, columns):
    rows = (len(frame_list) + columns - 1) // columns
    out = np.zeros((rows * FH, columns * FW, 4), dtype=np.uint8)
    for n, f in enumerate(frame_list):
        r, c = divmod(n, columns)
        P.over(out, f, c * FW, r * FH)
    return out


def hero_body():
    "Looks numbered skin * 4 + outfit."
    return lay_out([f for skin in range(3) for outfit in range(4) for f in frames(look(skin, outfit), 'body')], 24)


def hero_hair():
    "Looks numbered style * 4 + color."
    return lay_out([f for style in STYLES for color in range(4) for f in frames(look(0, 0, color, style), 'hair')], 24)


def hero_gear():
    "Looks numbered by class: sword, bow, staff."
    return lay_out([f for kind in GEAR for f in frames(look(), 'gear', kind)], 12)


# Townsfolk walking about: whole people, no cape, each a look of one sheet.
def _apron(s, cx, dy):
    s.shape([(cx - 18, 108 + dy), (cx + 18, 108 + dy), (cx + 21, 136), (cx, 140), (cx - 21, 136)], '#ddd2b6', lw=2.6, wob=.7)


def _cap(s, hx, hy, R, d):
    s.shape([(hx - R - 4, hy - R * .5), (hx - R * .7, hy - R - 8), (hx + R * .7, hy - R - 8), (hx + R + 4, hy - R * .5), (hx, hy - R * .3)], '#6a4a3a', lw=2.8, wob=.6)


FOLK = [
    look(0, 2, 1, 'long', hero=False),
    look(1, 3, 0, 'short', hero=False, extra=_apron),
    look(2, 1, 0, 'tied', hero=False),
    look(1, 0, 2, 'long', hero=False),
    look(0, 3, 3, 'short', hero=False, hat=_cap),
    look(2, 2, 1, 'tied', hero=False, extra=_apron),
]


def folk_sheet():
    out = []
    for L in FOLK:
        L2 = {k: v for k, v in L.items() if k != 'extra'}
        for d, legs in DIRS:
            for c, leg in enumerate(legs):
                out.append(person(dict(L2, blinks=True), d, leg, 1 if leg else 0, c, 'all', None, L.get('extra')))
    return lay_out(out, 24)


# The quest givers of the new places: two frames of standing and breathing, as art4's npc_sheet.
def _helmet(s, hx, hy, R, d):
    s.shape([(hx - R - 5, hy - 2), (hx - R * .8, hy - R - 6), (hx + R * .8, hy - R - 6), (hx + R + 5, hy - 2), (hx + R * .6, hy - 10), (hx - R * .6, hy - 10)], '#8a8f98', lw=3, wob=.5)
    s.stroke([(hx - R * .6, hy - R - 2), (hx + R * .6, hy - R - 2)], 1.6, '#d6dae0')
    s.shape([(hx - 4, hy - R - 18), (hx + 4, hy - R - 18), (hx + 3, hy - R - 4), (hx - 3, hy - R - 4)], '#a33c4b', lw=2, smooth=False, wob=.3)


def _miner(s, hx, hy, R, d):
    s.shape([(hx - R - 4, hy - 4), (hx - R * .8, hy - R - 4), (hx + R * .8, hy - R - 4), (hx + R + 4, hy - 4)], '#c7a23e', lw=3, wob=.5)
    s.shape([(hx - 8, hy - R + 2), (hx + 8, hy - R + 2), (hx + 8, hy - R - 10), (hx - 8, hy - R - 10)], '#f4e5a0', lw=2, smooth=False, wob=.3)


def _hat(s, hx, hy, R, d):
    s.shape([(hx - R - 12, hy - R * .55), (hx + R + 12, hy - R * .55), (hx + R * .6, hy - R * .75), (hx + R * .5, hy - R - 16), (hx - R * .5, hy - R - 16), (hx - R * .6, hy - R * .75)], '#4a3a5a', lw=3, wob=.6)
    s.stroke([(hx - R * .55, hy - R * .8), (hx + R * .55, hy - R * .8)], 3, '#c79b42')


def _armor(s, cx, dy):
    s.shape([(cx - 25, 100 + dy), (cx, 95 + dy), (cx + 25, 100 + dy), (cx + 27, 128), (cx, 134), (cx - 27, 128)], '#8a8f98', lw=3, wob=.6)
    s.stroke([(cx, 100 + dy), (cx, 130)], 1.6, '#d6dae0')
    s.shape([(cx - 8, 108 + dy), (cx + 8, 108 + dy), (cx + 8, 122 + dy), (cx, 128 + dy), (cx - 8, 122 + dy)], '#a33c4b', lw=2, wob=.4)


QUEST = {
    'rhea': (look(1, 0, 3, 'tied', hero=False, hat=_helmet), _armor),
    'odo': (look(0, 1, 1, 'short', hero=False, hat=_hat), _apron),
    'pell': (look(2, 3, 2, 'long', hero=False), None),
    'dunn': (look(1, 1, 0, 'short', hero=False, hat=_miner), None),
}


def quest_sheet(name):
    L, extra = QUEST[name]
    out = np.zeros((FH, FW * 2, 4), dtype=np.uint8)
    for i, b in enumerate((0, 1)):
        P.over(out, person(dict(L, blinks=True), 'down', 0, b, i, 'all', None, extra), i * FW, 0)
    return out


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    C.save(hero_body(), f'{out_dir}/hero_body.png')
    C.save(hero_hair(), f'{out_dir}/hero_hair.png')
    C.save(hero_gear(), f'{out_dir}/hero_gear.png')
    C.save(folk_sheet(), f'{out_dir}/folk.png')
    for name in QUEST: C.save(quest_sheet(name), f'{out_dir}/{name}.png')


if __name__ == '__main__':
    build(sys.argv[1])
