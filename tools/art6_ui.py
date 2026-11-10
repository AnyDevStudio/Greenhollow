# The new screens' pieces: color swatches and a letter grid for making a character, panels, the mana drop, the
# class skill icons, and arrows turned to fly up and down.
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art4 as D
import art5 as U
import art6_people as PE

LETTERS = [chr(ord('A') + k) for k in range(26)] + [str(k) for k in range(10)]
GRID_COLS, GRID_ROWS, CELL_W, CELL_H = 10, 4, 72, 64


def swatch(col, size=56):
    s = D.Sheet(size, size, sum(map(ord, col)) % 997)
    c = size / 2; r = size / 2 - 6
    pts = [(c + math.cos(a) * r, c + math.sin(a) * r) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    p, m = s.shape(pts, col, lw=3, wob=.6)
    s.fill(s.curve([(c - r * .6, c - r * .2), (c - r * .2, c - r * .65), (c + r * .1, c - r * .55), (c - r * .3, c - r * .1)], True, .4), '#ffffff', alpha=70, clip=m)
    return s.done(.03)


def letters():
    "The letter grid: A to Z, then 0 to 9, then a rub-out and OK, each in its own cell."
    W, H = GRID_COLS * CELL_W, GRID_ROWS * CELL_H
    im = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(U.BODY, 64); small = ImageFont.truetype(U.BODY, 40)
    cells = LETTERS + ['DEL', 'DEL', 'OK', 'OK']
    for n, ch in enumerate(cells):
        r, c = divmod(n, GRID_COLS)
        if ch in ('DEL', 'OK') and cells[n - 1] == ch: continue
        span = 2 if ch in ('DEL', 'OK') else 1
        x, y = c * CELL_W * 2 + CELL_W * span, r * CELL_H * 2 + CELL_H
        col = U.rgb(U.GOLD) if ch in ('DEL', 'OK') else U.rgb(U.PAPER)
        d.text((x, y), ch, font=small if span == 2 else f, fill=col, anchor='mm', stroke_width=5, stroke_fill=U.INK)
    return np.asarray(im.resize((W, H), Image.LANCZOS)).copy()


def cell_ring(w=CELL_W, h=CELL_H):
    s = D.Sheet(w, h, 9)
    p = s.rough([(4, 4), (w - 4, 4), (w - 4, h - 4), (4, h - 4)], 1)
    s.line(p, 7, D.INK, closed=True, taper=False); s.line(p, 4, '#E9C467', closed=True, taper=False)
    return s.done(.02)


def mana():
    s = D.Sheet(120, 120, 77)
    p, m = s.shape([(60, 10), (88, 56), (96, 80), (84, 104), (60, 112), (36, 104), (24, 80), (32, 56)], '#3f6fb0', lw=4, wob=.8)
    s.fill(s.curve([(64, 110), (92, 86), (96, 60), (120, 80), (110, 120)], True, 1.4), '#2a4c80', clip=m)
    s.fill(s.curve([(40, 70), (48, 52), (58, 44), (52, 66), (44, 84)], True, 1), '#a9d0ff', clip=m)
    return s.done(.05)


def class_skill_icon(c, k):
    "The class branch: sword skills, bow skills or fire skills, on the branch's own colored stone."
    s = D.Sheet(112, 112, 140 + c * 3 + k)
    s.shape([(10, 56), (22, 22), (56, 8), (90, 22), (102, 56), (90, 90), (56, 104), (22, 90)], ('#3a4a5e', '#3d4a33', '#5e3a2a')[c], lw=3.4, wob=.8)
    if c == 0:
        return np.asarray(Image.fromarray(U.skill_icon((0, 1, 2)[k]))).copy()
    if c == 1:
        if k in (0, 2):
            pts = [(34, 20), (62, 34), (74, 56), (62, 78), (34, 92)]
            s.line(s.curve(pts, False, .3), 7, D.INK); s.line(s.curve(pts, False, .3), 4, '#8a5a32'); s.stroke([(34, 22), (34, 90)], 1.4, '#efe6cc', wob=.1)
            if k == 2:
                for y in (40, 56, 72): s.stroke([(70, y), (96, y - 2)], 3, '#8ed1b4')
            else:
                s.shape([(54, 50), (80, 56), (54, 62)], '#efe6cc', lw=2, wob=.3)
        else:
            for dy in (-12, 12):
                s.stroke([(22, 58 + dy), (82, 50 + dy)], 4, '#c9a46a')
                s.shape([(82, 44 + dy), (96, 49 + dy), (82, 56 + dy)], '#cfd3d8', lw=2, smooth=False, wob=.3)
                s.shape([(18, 54 + dy), (28, 58 + dy), (18, 64 + dy)], '#c0485a', lw=1.6, smooth=False, wob=.3)
    else:
        if k == 2:
            p, m = s.shape([(56, 22), (76, 54), (82, 72), (72, 90), (56, 96), (40, 90), (30, 72), (36, 54)], '#3f6fb0', lw=3, wob=.7)
            s.fill(s.curve([(44, 62), (50, 48), (58, 42), (54, 60), (48, 74)], True, .8), '#a9d0ff', clip=m)
        else:
            sc = 1.0 if k == 0 else 1.25
            pts = [(56, 18), (70, 42), (84, 50), (80, 74), (64, 92), (48, 92), (32, 74), (28, 52), (42, 44)]
            pts = [(56 + (x - 56) * sc, 60 + (y - 60) * sc) for x, y in pts]
            p, m = s.shape(pts, '#e0702a', lw=3, wob=.9)
            s.fill(s.curve([(44, 70), (52, 50), (60, 40), (68, 58), (64, 82), (50, 84)], True, .8), '#f6c34a', clip=m)
            if k == 1:
                for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
                    s.stroke([(56 + math.cos(a) * 40, 62 + math.sin(a) * 40), (56 + math.cos(a) * 50, 62 + math.sin(a) * 50)], 2.4, '#f6c34a')
    return s.done(.05)


def build(root, creatures_dir=None):
    A = f'{root}/assets'; UI = f'{A}/ui'; os.makedirs(UI, exist_ok=True)
    for k, (c0, _, _) in enumerate(PE.SKINS): D.save(swatch(c0), f'{UI}/sw_skin{k}.png')
    for k, (top, _, _) in enumerate(PE.OUTFITS): D.save(swatch(top[0]), f'{UI}/sw_outfit{k}.png')
    for k, (h0, _) in enumerate(PE.HAIRS): D.save(swatch(h0), f'{UI}/sw_hair{k}.png')
    D.save(letters(), f'{UI}/letters.png'); D.save(cell_ring(), f'{UI}/cell.png'); D.save(cell_ring(CELL_W * 2, CELL_H), f'{UI}/cell2.png')
    D.save(mana(), f'{UI}/mana.png')
    for c in range(3):
        for k in range(3): D.save(class_skill_icon(c, k), f'{UI}/cskill{c}_{k}.png')
    # the shared branches keep art5's icons, renumbered after the class branch
    shared = {3: 3, 4: 4, 5: 5, 6: 7, 7: 8, 8: 6}
    for k, src in shared.items(): D.save(U.skill_icon(src), f'{UI}/skill{k}.png')
    D.save(D.panel(420, 450), f'{UI}/panel_create.png'); D.save(D.panel(390, 160), f'{UI}/panel_grid.png'); D.save(D.panel(230, 55), f'{UI}/panel_p2.png')
    D.save(D.panel(690, 450), f'{UI}/panel_journal.png'); D.save(D.panel(560, 370), f'{A}/panel_bag.png')
    if creatures_dir and os.path.exists(f'{creatures_dir}/arrow.png'):
        arrow = Image.open(f'{creatures_dir}/arrow.png')
        frames = [arrow.crop((k * 96, 0, (k + 1) * 96, 32)) for k in range(2)]
        for name, angle in (('arrow_up', 90), ('arrow_down', -90)):
            out = Image.new('RGBA', (64, 96), (0, 0, 0, 0))
            for k, fr in enumerate(frames): out.alpha_composite(fr.rotate(angle, expand=True), (k * 32, 0))
            out.save(f'{A}/{name}.png')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
