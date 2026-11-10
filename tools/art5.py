# Greenhollow's menus and lettering: words set in OFL fonts and inked to match the art, the title painting and
# logo, the skill icons and the second hero. Built on art4's pen and paper.
import math, os, random, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art2 as P
import art4 as D

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
BODY = os.path.join(FONTS, 'IBMPlexSans-SemiBold.ttf')
DISPLAY = os.path.join(FONTS, 'ArchivoBlack-Regular.ttf')
INK = (28, 21, 18)
PAPER = '#F3EAD3'; GOLD = '#E9C467'; MINT = '#A9E2CC'; DIM = '#8C8676'; ROSE = '#E39A8C'
K = 2  # lettering is drawn twice as large and scaled down

def rgb(s): return D.rgb(s)
def save(a, p): Image.fromarray(a, 'RGBA').save(p)

# ---- pad buttons drawn inline with words
BUTTON = {'X': ('#7FA6E0', 'cross'), 'O': ('#E0857A', 'circle'), 'SQ': ('#D79BC6', 'square'), 'TRI': ('#7FC8A6', 'triangle')}
def button_glyph(d, x, y, r, kind):
    "A round pad button with its mark, at the left edge x and the vertical middle y."
    cx, cy = x + r, y
    col, mark = BUTTON[kind]
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=INK)
    d.ellipse((cx - r * .8, cy - r * .8, cx + r * .8, cy + r * .8), fill=(46, 40, 36))
    w = max(int(r * .18), 2); m = r * .38; c = rgb(col)
    if mark == 'cross':
        d.line((cx - m, cy - m, cx + m, cy + m), fill=c, width=w); d.line((cx - m, cy + m, cx + m, cy - m), fill=c, width=w)
    elif mark == 'circle':
        d.ellipse((cx - m, cy - m, cx + m, cy + m), outline=c, width=w)
    elif mark == 'square':
        d.rectangle((cx - m * .85, cy - m * .85, cx + m * .85, cy + m * .85), outline=c, width=w)
    else:
        d.polygon([(cx, cy - m), (cx + m, cy + m * .75), (cx - m, cy + m * .75)], outline=c, width=w)
    return 2 * r
def pill_glyph(d, x, y, h, word, font):
    "A long button like Options, as a dark pill with its word."
    tw = d.textlength(word, font=font); w = tw + h * 1.1
    d.rounded_rectangle((x, y - h / 2, x + w, y + h / 2), radius=h / 2, fill=INK)
    d.rounded_rectangle((x + h * .1, y - h * .4, x + w - h * .1, y + h * .4), radius=h * .4, fill=(46, 40, 36))
    d.text((x + h * .55, y), word, font=font, fill=rgb(PAPER), anchor='lm')
    return w

def label(text, size, color=PAPER, font=BODY, outline=.11, shadow=True, width=None):
    """Words in a color with a soft ink edge, so they read over any painting. [X] [O] [SQ] [TRI] become pad
    buttons and [OPT] the Options pill. A width wraps the words onto more lines."""
    s = size * K; f = ImageFont.truetype(font, s); small = ImageFont.truetype(BODY, int(s * .46))
    parts = re.split(r'(\[(?:X|O|SQ|TRI|OPT)\])', text)
    def measure(words):
        probe = ImageDraw.Draw(Image.new('L', (8, 8)))
        total = 0
        for p in words:
            m = re.fullmatch(r'\[(X|O|SQ|TRI|OPT)\]', p)
            if m: total += (probe.textlength('OPTIONS', font=small) + s * .66 * 1.1 if m.group(1) == 'OPT' else s * 1.12) + s * .18
            else: total += probe.textlength(p, font=f)
        return total
    lines = [parts]
    if width:
        lines = []; cur = []
        for p in parts:
            for tok in (re.split(r'(\s+)', p) if not p.startswith('[') else [p]):
                if not tok: continue
                if cur and measure(cur + [tok]) > width * K and tok.strip(): lines.append(cur); cur = [tok.lstrip()]
                else: cur.append(tok)
        lines.append(cur)
    lh = int(s * 1.28); W = int(max(measure(l) for l in lines) + s * .6); H = lh * len(lines) + int(s * .4)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    stroke = max(int(s * outline), 1)
    for li, words in enumerate(lines):
        x = s * .3; y = s * .2 + li * lh + lh / 2
        for p in words:
            m = re.fullmatch(r'\[(X|O|SQ|TRI|OPT)\]', p)
            if m:
                k = m.group(1)
                if k == 'OPT': x += pill_glyph(d, x, y, s * .66, 'OPTIONS', small) + s * .18
                else: x += button_glyph(d, x, y, s * .56, k) + s * .18
                continue
            if shadow: d.text((x + s * .05, y + s * .07), p, font=f, fill=INK + (150,), anchor='lm', stroke_width=stroke, stroke_fill=INK + (150,))
            d.text((x, y), p, font=f, fill=rgb(color), anchor='lm', stroke_width=stroke, stroke_fill=INK)
            x += d.textlength(p, font=f)
    a = np.asarray(im.resize((W // K, H // K), Image.LANCZOS)).copy()
    return a

def logo():
    "GREENHOLLOW in heavy letters, painted gold over ink, a little uneven like a hand-cut sign."
    s = 230; f = ImageFont.truetype(DISPLAY, s); word = 'Greenhollow'
    probe = ImageDraw.Draw(Image.new('L', (8, 8))); tw = int(probe.textlength(word, font=f))
    W, H = tw + 160, s + 200
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).text((80, H // 2 + 10), word, font=f, fill=255, anchor='lm')
    a = np.asarray(m, float) / 255
    # shake the outline a little so no edge is ruler straight
    rng = np.random.RandomState(4); Y, X = np.mgrid[0:H, 0:W]
    nx = P.fbm(H, W, 40, 11, 2) - .5; ny = P.fbm(H, W, 40, 12, 2) - .5
    sx = np.clip(X + nx * 6, 0, W - 1).astype(int); sy = np.clip(Y + ny * 6, 0, H - 1).astype(int); a = a[sy, sx]
    fill = a > .5
    ink = np.asarray(Image.fromarray((fill * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(25)), float) > 0
    out = np.zeros((H, W, 4), np.uint8)
    sh = np.roll(np.roll(ink, 10, 0), 6, 1); out[sh] = (14, 10, 9, 150)
    out[ink] = INK + (255,)
    gold = np.array(rgb('#E7C063'), float); dark = np.array(rgb('#B98A3A'), float); light = np.array(rgb('#F7E3A0'), float)
    band = (Y > H // 2 + 18 + (nx * 18)).astype(float)[..., None]
    col = gold * (1 - band) + dark * band
    top = ((Y < H // 2 - 50 + ny * 16) & fill)
    c = col.copy(); c[top] = light
    out[fill, :3] = c[fill].astype(np.uint8); out[fill, 3] = 255
    out = D.gouache(out, 9, .07)
    return np.asarray(Image.fromarray(out, 'RGBA').resize((W // 2, H // 2), Image.LANCZOS)).copy()

def title_painting():
    "The village at dusk seen from the hill, with the woods beyond: the picture behind the title menu."
    W, H = 1920, 1080
    sky = D.backdrop('village')
    base = np.asarray(Image.fromarray(sky, 'RGBA').resize((W, H), Image.LANCZOS)).copy()
    s = D.Sheet(W, H, 77); s.im = Image.new('RGBA', (W * D.SS, H * D.SS), (0, 0, 0, 0)); r = s.r
    # the near hill and the far woods as flat painted shapes
    D.treeline(s, W, 640, 51, '#2b3a3a', (90, 170))
    s.fill(s.rough([(-8, 690), (W + 8, 690), (W + 8, H + 8), (-8, H + 8)], 4), '#2b3a3a')
    hill = s.curve([(-40, 860), (420, 760), (980, 800), (1500, 740), (1960, 790), (1960, 1120), (-40, 1120)], True, 3)
    s.fill(hill, '#3b5139'); s.line(hill[:len(hill) * 5 // 7], 4, '#1c1512', taper=True)
    s.fill(s.curve([(-40, 960), (600, 900), (1200, 960), (1960, 900), (1960, 1120), (-40, 1120)], True, 4), '#2f4430')
    a = np.asarray(s.im.resize((W, H), Image.LANCZOS)); P.over(base, a, 0, 0)
    # cottages and trees standing on the hill, from the game's own drawings
    for img, x, y, sc in ((D.cottage(7, 50, ('#5b2c2a', '#8f4a3a', '#a05c44')), 190, 822, .5), (D.cottage(6, 79, ('#25334f', '#3f5777', '#4c6684')), 1500, 790, .46)):
        im = Image.fromarray(img, 'RGBA'); im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        P.over(base, np.asarray(im), x, y - im.height)
    for seed, x, y, sc in ((301, -110, 1080, 1.2), (303, 1660, 1080, 1.3), (302, 470, 880, .5), (304, 1300, 860, .48)):
        t = Image.fromarray(D.tree(seed, D.VILLAGE_TREE), 'RGBA'); t = t.resize((int(t.width * sc), int(t.height * sc)), Image.LANCZOS)
        P.over(base, np.asarray(t), x, y - t.height)
    # mist over the valley and a little warm light from the windows
    Y, X = np.mgrid[0:H, 0:W]
    mist = np.clip(1 - np.abs(Y - 720) / 120, 0, 1) * np.clip((P.fbm(H, W, 160, 3, 3) - .3) / .4, 0, 1) * .45
    base[..., :3] = (base[..., :3] * (1 - mist[..., None]) + np.array(rgb('#b9aa98')) * mist[..., None]).astype(np.uint8)
    warm = (np.clip(1 - np.hypot((X - 300) / 420, (Y - 760) / 240), 0, 1) ** 2 + np.clip(1 - np.hypot((X - 1600) / 420, (Y - 740) / 240), 0, 1) ** 2) * .22
    base[..., :3] = np.clip(base[..., :3] * (1 - warm[..., None]) + np.array((246, 196, 120)) * warm[..., None], 0, 255).astype(np.uint8)
    vig = np.clip(np.hypot((X - 960) / 1150, (Y - 540) / 720) - .45, 0, 1) * 1.3
    base[..., :3] = (base[..., :3] * (1 - vig[..., None] * .75)).astype(np.uint8)
    base[..., 3] = 255
    return D.gouache(base, 33, .06)

def dim():
    a = np.zeros((8, 8, 4), np.uint8); a[..., :3] = (12, 9, 10); a[..., 3] = 172; return a

def pointer():
    "A small inked leaf that points at the chosen line."
    s = D.Sheet(64, 48, 3)
    p, m = s.shape([(6, 24), (24, 8), (58, 24), (24, 40)], '#E9C467', lw=3)
    s.fill(s.curve([(20, 26), (40, 24), (58, 24), (30, 38)], True, .5), '#B98A3A', clip=m)
    s.stroke([(10, 24), (50, 24)], 1.6, '#7a5a26')
    return s.done(.04)

def ring(size=148, col='#E9C467'):
    s = D.Sheet(size, size, 5); c = size / 2; r = size / 2 - 8
    pts = [(c + math.cos(a) * r, c + math.sin(a) * r) for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]
    p = s.curve(pts, True, 1.2); s.line(p, 9, D.INK, closed=True, taper=False); s.line(p, 5, col, closed=True, taper=False)
    return s.done(.03)

# ---- the nine skills
def skill_icon(k):
    s = D.Sheet(112, 112, 40 + k); r = s.r
    s.shape([(10, 56), (22, 22), (56, 8), (90, 22), (102, 56), (90, 90), (56, 104), (22, 90)], ('#3a4a5e', '#5a3940', '#3d4a33')[k // 3], lw=3.4, wob=.8)
    if k in (0, 2):  # a blade, and a heavier one
        wdt = 9 if k == 0 else 15
        p, m = s.shape([(32, 82), (70, 30 - (k == 2) * 6), (80 + (k == 2) * 4, 22), (78, 36), (40, 88)], '#cfd3d8', lw=2.6, smooth=False, wob=.4)
        s.fill(s.rough([(56, 52), (82, 22), (86, 30), (60, 60)], .4), '#9aa1aa', clip=m)
        s.shape([(24, 78), (46, 96), (50, 90), (30, 72)], '#6a4a35', lw=2.4, smooth=False, wob=.4)
        s.shape([(18, 90), (26, 98), (34, 92), (26, 84)], '#E9C467', lw=2, wob=.3)
        if k == 2: s.stroke([(70, 40), (86, 56)], 4, '#E9C467'); s.stroke([(64, 34), (74, 26)], 3, '#E9C467')
    elif k == 1:  # a wide sweep
        a = np.linspace(-2.4, -.2, 30); arc = np.stack([56 + np.cos(a) * 38, 70 + np.sin(a) * 38], 1)
        s.line(arc, 9, '#efe6cc'); s.line(arc, 3, '#8ed1b4')
        s.shape([(46, 74), (66, 74), (62, 96), (50, 96)], '#cfd3d8', lw=2.4, smooth=False, wob=.4)
    elif k in (3, 5):  # a heart, then a bigger one with a band
        sc = .78 if k == 3 else 1.0
        pts = [(56, 44), (46, 30), (28, 30), (20, 46), (28, 64), (56, 90), (84, 64), (92, 46), (84, 30), (66, 30)]
        pts = [(56 + (x - 56) * sc, 60 + (y - 60) * sc) for x, y in pts]
        p, m = s.shape(pts, '#c0485a', lw=3.2, wob=.8); s.fill(s.curve([(30, 44), (40, 36), (48, 40), (36, 50)], True, .4), '#f0b0a0', clip=m)
        if k == 5: s.stroke([(30, 58), (56, 66), (82, 58)], 4, '#E9C467', clip=m)
    elif k == 4:  # a heart with a leaf: health that comes back
        p, m = s.shape([(52, 46), (44, 34), (28, 34), (22, 48), (30, 64), (52, 84), (74, 64), (80, 48), (74, 34), (60, 34)], '#c0485a', lw=3, wob=.8)
        s.shape([(62, 70), (80, 50), (98, 58), (84, 82)], '#6ba86b', lw=2.6, wob=.6); s.stroke([(66, 72), (90, 58)], 1.6, '#2f4a37')
    elif k == 6:  # quick hands: three swift lines and a feather
        p, m = s.shape([(30, 84), (74, 30), (86, 34), (44, 88)], '#e8e0cc', lw=2.6, wob=.6)
        for i in range(5): s.stroke([(46 + i * 7, 74 - i * 9), (60 + i * 7, 74 - i * 9 - 4)], 1.5, '#8f8672', clip=m)
        for y in (40, 54, 68): s.stroke([(16, y), (36, y - 2)], 3.2, '#8ed1b4')
    elif k == 7:  # a keen eye
        p, m = s.shape([(16, 56), (40, 36), (72, 36), (96, 56), (72, 76), (40, 76)], '#efe6cc', lw=3, wob=.6)
        s.shape([(42, 56), (56, 42), (70, 56), (56, 70)], '#5a9a8a', lw=2.2, wob=.4); s.fill(s.curve([(50, 56), (56, 50), (62, 56), (56, 62)], True, 0), '#1c1512')
    else:  # a coin with a gleam
        p, m = s.shape([(24, 56), (32, 32), (56, 22), (80, 32), (88, 56), (80, 80), (56, 90), (32, 80)], '#cfa144', lw=3, wob=.6)
        s.stroke([(56, 40), (56, 72)], 6, '#6f4f20'); s.stroke([(40, 34), (50, 30)], 3, '#f1dca0', clip=m)
        s.stroke([(86, 22), (96, 12)], 3, '#f1dca0'); s.stroke([(90, 30), (102, 30)], 2.4, '#f1dca0')
    return s.done(.05)
def lock_veil():
    s = D.Sheet(112, 112, 60)
    s.fill(s.curve([(10, 56), (22, 22), (56, 8), (90, 22), (102, 56), (90, 90), (56, 104), (22, 90)], True, .8), '#120e10', alpha=190)
    s.shape([(40, 56), (72, 56), (72, 82), (40, 82)], '#8c8676', lw=2.6, smooth=False, wob=.4)
    a = np.linspace(math.pi, 2 * math.pi, 16); s.line(np.stack([56 + np.cos(a) * 11, 56 + np.sin(a) * 13], 1), 4, '#8c8676')
    return s.done(.03)

SKILLS = [
    ('Sharp Edge', 'Your sword hits 1 harder.'),
    ('Wide Arc', 'Your swing reaches farther.'),
    ('Heavy Blow', 'Your sword hits 2 harder.'),
    ('Tough', '4 more health.'),
    ('Second Wind', 'Slowly heal when hurt.'),
    ('Stout Heart', '6 more health.'),
    ('Quick Hands', 'Swing your sword faster.'),
    ('Keen Eye', 'Slimes give half again as much XP.'),
    ('Gold Finder', 'Slimes drop 5 gold.'),
]
BRANCHES = ['Blade', 'Heart', 'Hunter']

def build(root):
    A = f'{root}/assets'; U = f'{A}/ui'; os.makedirs(U, exist_ok=True)
    save(D.person_sheet('hero2'), f'{A}/hero2.png')
    save(logo(), f'{U}/logo.png'); save(title_painting(), f'{U}/title.png'); save(dim(), f'{U}/dim.png')
    save(pointer(), f'{U}/pointer.png'); save(ring(), f'{U}/ring.png'); save(lock_veil(), f'{U}/lock.png')
    save(D.panel(380, 330), f'{U}/panel_pause.png'); save(D.panel(790, 450), f'{U}/panel_skills.png'); save(D.panel(330, 44), f'{U}/panel_toast.png')
    for k in range(9): save(skill_icon(k), f'{U}/skill{k}.png')

def write_labels(root, labels):
    "labels: {name: (text, size, color, width)} written as assets/ui/t_<name>.png. Returns each picture's size."
    U = f'{root}/assets/ui'; os.makedirs(U, exist_ok=True); sizes = {}
    for name, (text, size, color, width) in labels.items():
        a = label(text, size, color, width=width); save(a, f'{U}/t_{name}.png'); sizes[name] = (a.shape[1], a.shape[0])
    return sizes
