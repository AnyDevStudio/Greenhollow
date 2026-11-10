# The painted grounds of the new places: Brookmere's cobbled streets, the open meadow and the cave floor. The same
# brush as art4's village and forest grounds: flat coats in a few bands, dragged edges, ink where things meet.
import math, os, random, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art2 as P
import art3 as B
import art4 as C
from art4 import INK, bands, field, inkedge, stamp, Over, flat_shadow, gouache, save, rgb

TX = B.TX
# ground and object cell names of the new maps, numbered after art.INDEX's
N = dict(cobble=40, road=41, plaza=42, meadow=43, mflower=44, cavefloor=45, cavevoid=46, glow=47, pool=48, river=49, bank=50, dirt=51, solid=60)

MEADOW = ('#3f5f3c', '#4e7244', '#628a4c', '#7c9e56')
STONE = ('#55524f', '#625e58', '#6f6a62', '#7c766c')
CAVE = ('#1a1a20', '#222129', '#2a2832', '#33303a')


def _mask(g, want): return B.cells(g, set(want)) > 0


def ground_town(root, g, o, W, H, name='town_ground'):
    h, w = H * TX, W * TX; r = random.Random(51)
    G = np.dstack([bands(field(h, w, 61, 60), C.GRASS), np.full((h, w), 255, np.uint8)])
    paved = B.organic(B.cells(g, {N['cobble'], N['plaza'], N['road']}), 61, 6, .3)
    base = bands(field(h, w, 62, 50), STONE); G[paved, :3] = base[paved]
    # cobbles: little rounded stones laid in loose rows, each with an ink rim and a lit top
    O = Over(h, w)
    y = 6
    while y < h:
        x = (y // 14 % 2) * 9 - 6
        while x < w:
            cx, cy = x + r.uniform(-2, 2), y + r.uniform(-2, 2)
            if 0 <= int(cy) < h and 0 <= int(cx) < w and paved[int(cy), int(cx)]:
                col = r.choice(('#6d685f', '#7a7469', '#615c55', '#857e70', '#6a6058'))
                O.dab(cx, cy, r.uniform(6.5, 8.5), r.uniform(5, 6.5), col, INK, r.randrange(9999))
                O.dab(cx - 1.5, cy - 2, 3, 1.6, '#9a9384', None, r.randrange(9999))
            x += r.uniform(15, 19)
        y += r.uniform(12, 14)
    O.onto(G)
    plaza = _mask(g, [N['plaza']])
    if plaza.any():
        ring = inkedge(plaza, 63, 2.5, .04, .1); stamp(G, ring, '#3a3530')
    river = B.organic(B.cells(g, {N['river']}), 64, 10, .35)
    d = P.blur(river.astype(float), 18); wv = np.clip(1 - np.clip((d - .42) / .55, 0, 1) + (P.fbm(h, w, 24, 65, 2) - .5) * .34, 0, 1)
    c = bands(wv, ('#23465e', '#2f5e72', '#467f8a', '#79a9a2')); G[river, :3] = c[river]
    bank = B.organic(np.clip(P.blur(B.cells(g, {N['river']}), 12) * 2.2, 0, 1), 66, 4, .25) & ~river & ~paved
    c = bands(field(h, w, 67, 18), ('#6d6455', '#8a7f6a', '#a39881')); G[bank, :3] = c[bank]
    for mk, sd in ((paved, 68), (river, 69)): stamp(G, inkedge(mk, sd), INK)
    O = Over(h, w)
    for _ in range(int(w * h / 3400)):
        x, y = r.randrange(4, w - 4), r.randrange(4, h - 4)
        if not paved[y, x] and not river[y, x] and not bank[y, x]: O.tuft(x, y, r, ('#79914c', '#5b7843', '#a4a35a'))
    for _ in range(80):
        x, y = r.randrange(w), r.randrange(h)
        if river[y, x]:
            L = r.uniform(14, 46); O.d.line([((x + t) * 2, (y + math.sin(t / 7) * 1.4) * 2) for t in np.linspace(0, L, 9)], fill=rgb(r.choice(('#b6d0c0', '#8cb8ad'))) + (255,), width=2)
    O.onto(G)
    S = np.zeros((h, w))
    for y in range(H):
        for x in range(W):
            if o[y][x] == N['solid']: S[y * TX:(y + 1) * TX + 18, x * TX + 6:(x + 1) * TX + 26] = 1
    flat_shadow(G, S, 70, .34)
    gouache(G, 94, .07); B.fade(G); save(G, f'{root}/assets/{name}.png')
    return river


def ground_meadow(root, g, o, W, H, name='meadow_ground'):
    h, w = H * TX, W * TX; r = random.Random(52)
    G = np.dstack([bands(field(h, w, 71, 110), MEADOW), np.full((h, w), 255, np.uint8)])
    # sunlit swells in the grass, a few soft lighter patches
    sun = np.clip((P.fbm(h, w, 160, 72, 3) - .55) / .3, 0, 1)[..., None] * .22
    G[..., :3] = np.clip(G[..., :3] * (1 - sun) + np.array(rgb('#a7b968')) * sun, 0, 255).astype(np.uint8)
    p = B.organic(B.cells(g, {N['dirt']}), 73, 7, .45); c = bands(field(h, w, 74, 40), C.DIRT); G[p, :3] = c[p]
    stamp(G, inkedge(p, 75), INK)
    O = Over(h, w); FL = ('#e8dfc0', '#e0b04a', '#c0607f', '#8a97c8', '#f0e6a0')
    for _ in range(int(w * h / 1500)):
        x, y = r.randrange(4, w - 4), r.randrange(4, h - 4)
        if not p[y, x]: O.tuft(x, y, r, ('#86a356', '#6a8a4a', '#b0b060', '#5f8045'))
    fl = _mask(g, [N['mflower']])
    for _ in range(int(w * h / 900)):
        x, y = r.randrange(4, w - 4), r.randrange(4, h - 4)
        if p[y, x]: continue
        dense = fl[y, x]
        if not dense and r.random() > .18: continue
        col = r.choice(FL); O.blade(x, y + 6, r.uniform(-2, 2), -7, '#2f4a33', 1.4)
        for t in range(5): O.dab(x + math.cos(t * 1.26) * 3.2, y + math.sin(t * 1.26) * 2.6, 2.4, 2.1, col, None, t)
        O.dab(x, y, 1.6, 1.4, '#5d3a24')
    for _ in range(200):
        x, y = r.randrange(w), r.randrange(h)
        if p[y, x]: O.dab(x, y, r.uniform(2, 5), r.uniform(1.5, 3.5), r.choice(('#6b5a48', '#a18c6c', '#b8a582')), INK, r.randrange(999))
    O.onto(G)
    S = np.zeros((h, w))
    for y in range(H):
        for x in range(W):
            if o[y][x] == N['solid']: B.cast(S, x * TX + TX / 2, y * TX + TX, 40, 14)
    flat_shadow(G, S, 76, .3)
    gouache(G, 95, .07); B.fade(G); save(G, f'{root}/assets/{name}.png')


def ground_cave(root, g, o, W, H, name='cave_ground'):
    h, w = H * TX, W * TX; r = random.Random(53)
    G = np.zeros((h, w, 4), np.uint8); G[..., :3] = rgb('#07070a'); G[..., 3] = 255
    fl = B.organic(B.cells(g, {N['cavefloor'], N['glow'], N['pool']}), 81, 9, .45)
    c = bands(field(h, w, 82, 70), CAVE); G[fl, :3] = c[fl]
    # cracks: thin ink veins wandering over the floor
    O = Over(h, w)
    for _ in range(int(w * h / 24000)):
        x, y = r.randrange(w), r.randrange(h)
        if not fl[y, x]: continue
        pts = [(x, y)]
        for _ in range(r.randint(3, 6)):
            x += r.uniform(-28, 28); y += r.uniform(-16, 16); pts.append((x, y))
        O.d.line([(a * 2, b * 2) for a, b in pts], fill=rgb('#0b0a0e') + (255,), width=3)
    for _ in range(int(w * h / 2600)):
        x, y = r.randrange(w), r.randrange(h)
        if fl[y, x]: O.dab(x, y, r.uniform(2, 5.5), r.uniform(1.5, 3.8), r.choice(('#3a3640', '#45404c', '#2c2a33', '#4d4656')), INK, r.randrange(999))
    O.onto(G)
    pool = B.organic(B.cells(g, {N['pool']}), 84, 8, .3)
    d = P.blur(pool.astype(float), 14); wv = np.clip(1 - np.clip((d - .42) / .55, 0, 1), 0, 1)
    cc = bands(wv, ('#0f2a28', '#174039', '#25594b', '#3c7a62')); G[pool, :3] = cc[pool]
    # the green dew glows where it gathers
    glow = P.blur(B.cells(g, {N['glow'], N['pool']}), 40)
    q = np.clip(glow * 1.6, 0, 1)[..., None] * .5 * fl[..., None]
    G[..., :3] = np.clip(G[..., :3] * (1 - q) + np.array(rgb('#3fa07a')) * q, 0, 255).astype(np.uint8)
    stamp(G, inkedge(fl, 85, 4, .06, .2), INK); stamp(G, inkedge(pool, 86), INK)
    S = np.zeros((h, w))
    for y in range(H):
        for x in range(W):
            if o[y][x] == N['solid']: B.cast(S, x * TX + TX / 2, y * TX + TX, 36, 12)
    flat_shadow(G, S, 87, .45, (4, 4, 8))
    gouache(G, 96, .08); save(G, f'{root}/assets/{name}.png')


if __name__ == '__main__':
    # a quick look at each on a small made-up map
    W, H = 20, 12
    g = [[N['cobble'] if 3 <= y <= 8 else 0 for x in range(W)] for y in range(H)]
    for x in range(6, 12): g[5][x] = N['plaza']
    for x in range(W): g[0][x] = g[1][x] = N['river']
    o = [[-1] * W for _ in range(H)]
    os.makedirs(sys.argv[1] + '/assets', exist_ok=True)
    ground_town(sys.argv[1], g, o, W, H, 'test_town')
    g = [[N['mflower'] if (x + y) % 7 == 0 else N['meadow'] for x in range(W)] for y in range(H)]
    for x in range(W): g[6][x] = N['dirt']
    ground_meadow(sys.argv[1], g, o, W, H, 'test_meadow')
    g = [[N['cavefloor'] if 2 <= y <= 9 and 2 <= x <= 17 else N['cavevoid'] for x in range(W)] for y in range(H)]
    g[5][8] = g[5][9] = N['pool']; g[7][14] = N['glow']
    ground_cave(sys.argv[1], g, o, W, H, 'test_cave')
