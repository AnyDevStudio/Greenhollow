# Writes scene.json and logic.json for Greenhollow 2: a short story, character making with three classes, the
# village with Mira's garden, Brookmere town, the meadow, the forest and the cave, five quests, packs of creatures,
# cats and dogs to adopt, and up to four players. Every item and block is what Studio itself would save.
import json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import art as A
import art4 as C
import art5 as U
import art6_grounds as G6
from blocks6 import *

I = A.INDEX; N6 = G6.N; TS = 64
GOLD = '#F0C84A'; PAPER = '#F6EFE0'; MINT = '#A4EFDB'; ROSE = '#E39A8C'
root = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
PLAYERS = (1, 2, 3, 4)
CLASSES = ('Warrior', 'Ranger', 'Mage')

# ---------- skills: the first branch belongs to the class, the other two everyone shares
CLASS_SKILLS = [
    [('Sharp Edge', 'Your sword hits 2 harder.'), ('Wide Swing', 'Your swing reaches farther.'), ('Whirlwind', 'Your swing hits all around you.')],
    [('Keen Eye', 'Your arrows fly much farther.'), ('Twin Arrows', 'Each arrow hits 1 harder.'), ('Quick Draw', 'Shoot twice as fast.')],
    [('Ember', 'Your fireball hits 2 harder.'), ('Blaze', 'Your fireball bursts wider.'), ('Mana Well', 'Mana comes back twice as fast.')],
]
SHARED_SKILLS = [('Tough', '4 more health.'), ('Second Wind', 'Heal quickly over time.'), ('Stout Heart', '6 more health.'),
                 ('Keen Hunter', 'Creatures give half again as much XP.'), ('Lucky', 'Creatures drop gold more often.'), ('Best Friend', 'Your pet bites 2 harder.')]
BRANCHES = ['Class', 'Heart', 'Hunter']

# ---------- every word the game shows, set once as pictures
L = {}
def lab_text(key, text, size=38, color=U.PAPER, width=None): L[key] = (text, size, color, width)
for k, t in dict(hint='[X] Talk   [SQ] Attack   [TRI] Bag   [OPT] Menu', next='[X] Next', talk='[X] Talk', sleep='[X] Sleep').items(): lab_text(k, t, 26 if k == 'hint' else 30, U.MINT if k == 'next' else U.GOLD if k in ('talk', 'sleep') else U.PAPER)
lab_text('banner', 'Level up!', 120, U.GOLD)
TOASTS = {1: 'Game saved', 2: 'A friend joined!', 3: 'Skill learned!', 4: 'Garden cleared!', 5: "Found Tobin's hammer!", 6: 'Your new friend is here!',
          7: 'Your pet grew!', 8: 'You fainted and lost a little gold.', 9: 'Quest accepted', 10: 'Quest complete!', 11: 'Not enough gold.',
          12: 'The Stone Warden falls!', 13: 'Bought!', 14: 'Your pet loved that treat.', 15: 'Wolves: one less in the pack.'}
for k, t in TOASTS.items(): lab_text(f'toast{k}', t, 34, U.GOLD if k in (2, 3, 4, 5, 6, 7, 10, 12) else U.MINT if k in (1, 9, 13, 14, 15) else U.ROSE)
for n, t in (('mira', 'Mira'), ('tobin', 'Tobin'), ('odo', 'Odo the merchant'), ('pell', 'Pell'), ('rhea', 'Captain Rhea'), ('dunn', 'Dunn the miner')): lab_text(f'who_{n}', t, 44, U.GOLD)
LINES = {
    'm1': 'Oh, thank goodness. Slimes crept up from the old well and got into my garden.',
    'm2': 'Three of them are chewing my cabbages right now. Could you clear them out?',
    'm3': 'Will you help?      [X] Of course      [O] Not now',
    'm4': 'The three slimes are still in the garden, by the cabbages. Mind their bite!',
    'm5': 'My garden is safe! Take 30 gold and this potion. Bless you.',
    'm6': 'You cleared my garden before I could even ask! Here, take this for your trouble.',
    'm7': 'The town of Brookmere is north of the meadow. They could use someone like you.',
    't1': 'Ah, a visitor. I lost my good hammer out in the meadow, near the old stone walls.',
    't2': 'Find it and I will make it worth your while.      [X] I will look      [O] Maybe later',
    't3': 'No luck yet? Look near the stone walls in the meadow, east of the haystacks.',
    't4': 'My hammer! You found it! Here, 40 gold for your trouble.',
    't5': 'Rest in my bed any time. It heals you and keeps your story safe.',
    'o1': 'Welcome to Brookmere market! I make warm cloaks, but I am out of hopper fur.',
    'o2': 'Bring me 4 soft furs from the meadow hoppers?      [X] Deal      [O] No thanks',
    'o3': 'Four soft furs, friend. Hoppers are quick, so be quicker!',
    'o4': 'Lovely fur! Here are 50 gold and two potions.',
    'o5': 'Potions, 15 gold each.      [X] Buy one      [O] Goodbye',
    'p1': 'Every critter here needs a home. A cat or a dog is 20 gold, and a friend for life.',
    'p2': 'Who will it be?      [X] A cat      [SQ] A dog      [O] Not yet',
    'p4': 'How is your friend? Treats help them grow. 3 treats for 10 gold.      [X] Buy      [O] Bye',
    'r1': 'Halt, traveler. Wolves have run wild in the east forest since the green dew came.',
    'r2': 'Thin the pack: defeat 5 wolves.      [X] I will do it      [O] Not now',
    'r3': 'Five wolves. Keep your guard up, they hunt in packs.',
    'r4': 'Well fought! Brookmere owes you. 60 gold, and my thanks.',
    'r5': 'Dunn the miner camps by the cave past the forest. Something big woke down there.',
    'd1': 'The green dew pours out of this cave. Something old guards it: a Stone Warden.',
    'd2': 'Bring it down and the dew may fade.      [X] Leave it to me      [O] Not yet',
    'd3': 'The Warden waits in the deepest hall. Bats and stone things guard the way.',
    'd4': 'You did it! The dew is fading already. Greenhollow is safe, thanks to you.',
    'd5': 'I will keep digging. Come by if you ever want crystals.',
}
for k, t in LINES.items(): lab_text(k, t, 38, U.PAPER, 1600)
for k, t in (('bag', 'Bag'), ('gold', 'Gold'), ('potion', 'Potion'), ('treat', 'Pet treat'), ('fur', 'Soft fur'), ('hammer', "Tobin's hammer"), ('baghelp', '[O] Drink a potion      [SQ] Feed your pet      [TRI] Close'),
             ('pet_none', 'No pet yet. Pell in Brookmere has cats and dogs.'), ('pet_cat', 'Your cat'), ('pet_dog', 'Your dog'), ('pet_lv', 'Level'), ('pet_full', 'Fed'), ('pet_hungry', 'Hungry!')):
    lab_text(f'b_{k}', t, 36 if k != 'baghelp' else 28, U.GOLD if k == 'bag' else U.PAPER, 440 if k == 'pet_none' else None)
L['b_bag'] = ('Bag', 72, U.GOLD, None)
lab_text('paused', 'Paused', 76, U.GOLD)
OPTIONS = ['Resume', 'Skills', 'Journal', 'Save game', 'Quit to title']
for n, t in enumerate(OPTIONS): lab_text(f'o{n}', t, 46)
lab_text('menuhelp', '[X] Choose      [O] Back', 26, U.MINT)
lab_text('skills', 'Skills', 76, U.GOLD); lab_text('points', 'Skill points', 34)
for b, t in enumerate(BRANCHES): lab_text(f'br{b}', t, 40, U.GOLD)
for c in range(3):
    lab_text(f'brc{c}', CLASSES[c], 40, U.GOLD)
    for k, (name, desc) in enumerate(CLASS_SKILLS[c]): lab_text(f'sn{c}_{k}', name, 46, U.GOLD); lab_text(f'sd{c}_{k}', desc, 32, U.PAPER, 420)
for k, (name, desc) in enumerate(SHARED_SKILLS): lab_text(f'sn{k + 3}', name, 46, U.GOLD); lab_text(f'sd{k + 3}', desc, 32, U.PAPER, 420)
for k, t in (('st_have', 'Learned'), ('st_can', '[X] Learn for 1 point'), ('st_above', 'Learn the skill above it first.'), ('st_none', 'No points left. Level up to earn one.')):
    lab_text(k, t, 32 if k in ('st_have', 'st_can') else 30, U.MINT if k == 'st_have' else U.GOLD if k == 'st_can' else U.ROSE)
lab_text('skillhelp', '[X] Learn      [O] Back', 26, U.MINT)
lab_text('journal', 'Journal', 76, U.GOLD)
QUESTS = [('Mira\'s garden', 'Clear the 3 slimes from Mira\'s garden.'), ('The lost hammer', 'Find Tobin\'s hammer in the meadow.'),
          ('Soft furs', 'Bring Odo 4 soft furs from the meadow hoppers.'), ('The wolf pack', 'Defeat 5 wolves in the east forest.'), ('The Stone Warden', 'Defeat the Stone Warden deep in the cave.')]
for q, (name, desc) in enumerate(QUESTS, 1):
    lab_text(f'qn{q}', name, 40, U.GOLD); lab_text(f'qd{q}', desc, 30, U.PAPER, 900)
lab_text('q_done', 'Done', 32, U.MINT); lab_text('q_ready', 'Go back and tell them!', 30, U.GOLD); lab_text('q_empty', 'No quests yet. Talk to the people you meet.', 32, U.DIM)
lab_text('journalhelp', '[O] Back', 26, U.MINT)
lab_text('new', 'New game', 54); lab_text('join', 'Join a friend', 54); lab_text('looking', "Looking for a friend's game on your network...      [O] Stop", 30, U.MINT)
lab_text('cont', 'Continue', 54); lab_text('cont_dim', 'Continue', 54, U.DIM); lab_text('titlehelp', '[X] Choose', 26, U.MINT)
lab_text('p2title', 'Playing with a friend? They press [X] on a second controller.', 26, U.MINT); lab_text('p2ready', 'Player 2 is ready!', 34, U.GOLD)
STORY = [
    ('Greenhollow was a quiet place: a few cottages, a garden, a well older than anyone could remember.', 'Evenings smelled of woodsmoke, and nothing much ever happened.'),
    ('Then one night the old well began to glow.', 'A green dew rose from it, cold and bright, and crept out over the grass.'),
    ('Wherever the dew went, creatures changed. Slimes grew bold, wolves grew wild,', 'and something deep in the hills woke up.'),
    ('Someone had to find where the dew was coming from.', 'That someone is you.'),
]
for k, (a, b) in enumerate(STORY): lab_text(f'st{k}a', a, 40, U.PAPER, 1600); lab_text(f'st{k}b', b, 40, U.MINT, 1600)
lab_text('storyhelp', '[X] Next      [OPT] Skip', 26, U.MINT)
lab_text('create', 'Who are you?', 70, U.GOLD)
for k, t in enumerate(('Class', 'Skin', 'Clothes', 'Hair', 'Hair color', 'Name', 'Ready')): lab_text(f'row{k}', t, 34, U.PAPER)
for c, t in enumerate(CLASSES): lab_text(f'cls{c}', t, 40, U.GOLD)
for k, t in enumerate(('Short', 'Long', 'Tied')): lab_text(f'style{k}', t, 34, U.GOLD)
CLASS_TEXT = ['Sword and shield arm. Tough, hits hard up close.', 'Bow and keen eyes. Strikes from far away.', 'Staff and fire. Bursts that hit many at once.']
for c, t in enumerate(CLASS_TEXT): lab_text(f'clsd{c}', t, 28, U.PAPER, 560)
lab_text('readyq', '[X] Start the adventure', 34, U.GOLD); lab_text('readyok', 'Ready!', 40, U.MINT)
lab_text('createhelp', 'Up and down: choose a line      Left and right: change it      [X] Type a name', 24, U.MINT)
lab_text('gridhelp', '[X] Add letter      [O] Done', 24, U.MINT)
lab_text('p2create', 'Player 2: press [X] to join', 30, U.MINT)
lab_text('waiting', 'Waiting for the others...', 30, U.DIM)
lab_text('peace', 'The green dew fades. Greenhollow is safe.', 54, U.GOLD)
lab_text('p2name', 'Player 2', 30, U.MINT)

os.makedirs(f'{root}/assets/ui', exist_ok=True)
U.build(root)
SIZE = U.write_labels(root, L)
def sized(src): return Image.open(f'{root}/assets/{src}.png').size


# ---------- items
def base(i, name, kind, x, y, **k): return dict(id=i, type=kind, name=name, x=x, y=y, controllable=False, **k)
def img(i, name, x, y, w, h, src, **k): return base(i, name, 'image', x, y, width=w, height=h, source=f'assets/{src}.png', **k)
def up(i, name, x, y, w, h, src, dw, dh, **k): return img(i, name, x, y, w, h, src, upright=True, drawWidth=dw, drawHeight=dh, **k)
def hud(i, name, x, y, w, h, src): return img(i, name, x, y, w, h, src, screenFixed=True)
def lab(i, name, x, y, key, center=False):
    w, h = SIZE[key]
    return hud(i, name, x - w // 2 if center else x, y, w, h, f'ui/t_{key}')
def text(i, name, x, y, scale, t, color=PAPER, fixed=True, **k):
    d = base(i, name, 'text', x, y, scale=scale, text=t, color=color, **k)
    if fixed: d['screenFixed'] = True
    return d
def sheet(fw, fh, anims, start, looks=1):
    d = dict(frameWidth=fw, frameHeight=fh, animation=start, animations=[dict(name=n, frames=fr, fps=s) for n, fr, s in anims])
    if looks > 1: d['looks'] = looks
    return d
PERSON = [('idleDown', [0], 1), ('walkDown', [1, 2, 3, 2], 8), ('idleUp', [4], 1), ('walkUp', [5, 6, 7, 6], 8), ('idleSide', [8], 1), ('walkSide', [9, 10, 11, 10], 8)]
def body(**k): return dict(physics='body', gravityScale=0, platformer=False, jumpHeight=260, **k)

def heroes(x, y):
    "Each player's character in three layers: body, hair and what they carry, all playing the same frames."
    out = []
    for p in PLAYERS:
        hx = x + (p - 1) * 56
        out.append(up(f'hero{p}', f'Player {p}', hx, y, 64, 64, 'hero_body', 102, 136, sheet=sheet(120, 160, PERSON, 'idleDown', 12), topDown=True, moveSpeed=420, player=p, **body()))
        out.append(up(f'hair{p}', f'Player {p} hair', hx, y + 1, 64, 64, 'hero_hair', 102, 136, sheet=sheet(120, 160, PERSON, 'idleDown', 12), follows=f'hero{p}', followX=0, followY=1))
        out.append(up(f'gear{p}', f'Player {p} weapon', hx, y + 2, 64, 64, 'hero_gear', 102, 136, sheet=sheet(120, 160, PERSON, 'idleDown', 3), follows=f'hero{p}', followX=0, followY=2))
    return out

def npc(i, name, src, col, row):
    return up(i, name, col * TS, row * TS, 64, 64, src, 102, 136, sheet=sheet(120, 160, [('idle', [0, 1], 2)], 'idle'), physics='solid')
def prompt(i, name, key, cx, foot):
    "Words standing in the world above someone's head: an upright picture, padded below so it floats over them."
    w, h = SIZE[key]
    im = Image.open(f'{root}/assets/ui/t_{key}.png'); pad = Image.new('RGBA', (w, h + 170), (0, 0, 0, 0)); pad.alpha_composite(im, (0, 0))
    pad.save(f'{root}/assets/ui/p_{key}.png')
    return up(i, name, cx - w // 2, foot - 4, w, 4, f'ui/p_{key}', w, h + 170)
def marker(i, name, c, r, w=1, h=1): return up(i, name, c * TS, r * TS, w * TS, h * TS, 'clear', 4, 4)
def tree_item(n, c, r, src):
    return up(f'tree{n}', f'Tree {n}', c * TS, r * TS, TS, TS, src, 236, 320, sheet=sheet(340, 460, [(f'v{k}', [k], 1) for k in range(4)], f'v{(c * 7 + r * 13) % 4}'))
def outer(kind, W, H): return img('outer', 'Land around the map', -1800, -900, W * TS + 3600, H * TS + 1500, f'outer_{kind}')
def art_layer(src, W, H): return img('ground', 'Ground art', 0, 0, W * TS, H * TS, src)
def light_layer(kind): return hud('light', 'Light', 0, 0, 1920, 1080, f'light_{kind}')
def tilemap(i, name, grid, solid=(), source='assets/tiles.png'):
    def row(r): return ','.join(str(v) for v in r)
    return base(i, name, 'tilemap', 0, 0, source=source, tileWidth=16, tileHeight=16, tileScale=4, columns=len(grid[0]), rows=len(grid), tiles=[row(r) for r in grid], solidTiles=sorted(set(solid)))
def particles(i, name, preset, palette, amount, size, pixel, color=GOLD, gravity=100, speed=100):
    return base(i, name, 'particles', 0, -400, width=size, height=size, color=color, preset=preset, palette=palette, amount=amount, spread=70, speed=speed, gravity=gravity, pixelSize=pixel, looping=False)
def walls(solid_cells, W, H):
    grid_ = [[0 if (x, y) in solid_cells else -1 for x in range(W)] for y in range(H)]
    return tilemap('walls', 'Walls (invisible)', grid_, [0], source='assets/collision.png')
def grid(w, h, v): return [[v] * w for _ in range(h)]

# creatures, from art6_creatures (frames counted within one look)
CRE = json.load(open(f'{HERE}/../out6_creatures/creatures.json')) if os.path.exists(f'{HERE}/../out6_creatures/creatures.json') else {}
def cre_anims(name, fallback):
    spec = CRE.get(name) or CRE.get(name + '.png') or {}
    anims = spec.get('animations') or {}
    if anims: return [(n, (a['frames'] if isinstance(a, dict) else a), (a.get('fps', 8) if isinstance(a, dict) else 8)) for n, a in anims.items()]
    return fallback
MOBS = {
    # name: sheet, frame, draw size, body size, looks, anims (idle, run), fallback anims
    'slime': dict(src='slime', fw=120, fh=120, dw=96, dh=96, bw=60, bh=40, looks=3, idle='hop', run='hop', fb=[('hop', [0, 1, 0, 2], 6)]),
    'hopper': dict(src='hopper', fw=120, fh=120, dw=88, dh=88, bw=52, bh=40, looks=1, idle='idle', run='hop', fb=[('idle', [0, 1], 3), ('hop', [2, 3, 4, 5], 10)]),
    'wolf': dict(src='wolf', fw=160, fh=120, dw=150, dh=112, bw=96, bh=48, looks=1, idle='idle', run='run', fb=[('idle', [0, 1], 3), ('run', [2, 3, 4, 5], 12), ('bite', [6, 7], 10)]),
    'boar': dict(src='boar', fw=160, fh=120, dw=150, dh=112, bw=96, bh=50, looks=1, idle='idle', run='walk', fb=[('idle', [0, 1], 3), ('walk', [2, 3, 4, 5], 9), ('charge', [6, 7], 12)]),
    'bat': dict(src='bat', fw=120, fh=100, dw=96, dh=80, bw=56, bh=40, looks=1, idle='flap', run='flap', fb=[('flap', [0, 1, 2, 3], 12)]),
    'golem': dict(src='golem', fw=160, fh=180, dw=150, dh=170, bw=96, bh=56, looks=1, idle='idle', run='walk', fb=[('idle', [0, 1], 2), ('walk', [2, 3, 4, 5], 7), ('slam', [6, 7], 8)]),
    'warden': dict(src='warden', fw=240, fh=260, dw=260, dh=280, bw=150, bh=80, looks=1, idle='idle', run='walk', fb=[('idle', [0, 1], 2), ('walk', [2, 3, 4, 5], 6), ('slam', [6, 7], 8)]),
}
def mob_template(t, kind, copies, speed):
    m = MOBS[kind]
    anims = cre_anims(kind, m['fb'])
    names = [a[0] for a in anims]
    m['idle'] = m['idle'] if m['idle'] in names else names[0]; m['run'] = m['run'] if m['run'] in names else names[-1]
    item = up(t, f'{kind.title()} (template)', -4000, -4000, m['bw'], m['bh'], m['src'], m['dw'], m['dh'], sheet=sheet(m['fw'], m['fh'], anims, m['idle'], m['looks']), copies=copies, moveSpeed=max(60, speed), **body())
    tag = text(f'{t}_lv', f'{kind.title()} level', -4000, -4000, 3, 'Lv{mlv}', GOLD, fixed=False, follows=t, followX=m['bw'] // 2 - 30, followY=m['bh'] + 6, copies=copies)
    return [item, tag]
PET = dict(fw=112, fh=96, dw=96, dh=82, looks=6, fb=[('idle', [0, 1], 3), ('walk', [2, 3, 4, 5], 10), ('sit', [6], 1), ('happy', [7], 1)])
def pet_template():
    anims = cre_anims('pets', PET['fb'])
    return [up('pet', 'Pet (template)', -4000, -4000, 44, 32, 'pets', PET['dw'], PET['dh'], sheet=sheet(PET['fw'], PET['fh'], anims, 'idle', PET['looks']), copies=4, moveSpeed=420, **body())]
def effect_templates():
    out = []
    out.append(up('arrowh', 'Arrow (template)', -4000, -4000, 48, 16, 'arrow', 72, 24, sheet=sheet(96, 32, [('fly', [0, 1], 12)], 'fly'), copies=8))
    out.append(up('arrowup', 'Arrow up (template)', -4000, -4000, 16, 48, 'arrow_up', 24, 72, sheet=sheet(32, 96, [('fly', [0, 1], 12)], 'fly'), copies=4))
    out.append(up('arrowdn', 'Arrow down (template)', -4000, -4000, 16, 48, 'arrow_down', 24, 72, sheet=sheet(32, 96, [('fly', [0, 1], 12)], 'fly'), copies=4))
    out.append(up('fireball', 'Fireball (template)', -4000, -4000, 48, 48, 'fireball', 80, 80, sheet=sheet(96, 96, [('burn', [0, 1, 2], 12)], 'burn'), copies=6))
    out.append(up('coin_drop', 'Coin (template)', -4000, -4000, 40, 40, 'coin', 44, 44, copies=10))
    out.append(up('fur_drop', 'Fur (template)', -4000, -4000, 44, 44, 'fur', 52, 52, copies=6))
    for p in PLAYERS:
        out.append(up(f'slash{p}', f'Sword sweep {p}', 0, -4000, 192, 192, 'slash', 192, 192, sheet=sheet(192, 192, [('sweep', [0, 1, 2], 18)], 'sweep')))
    out += [particles('hitfx', 'Hit sparks', 'sparks', 'ice', 24, 120, 4, MINT), particles('hurtfx', 'Hurt sparks', 'sparks', 'fire', 22, 120, 4, '#D94F5C'),
            particles('boomfx', 'Fire burst', 'fireworks', 'fire', 90, 320, 6, '#F08A3C'), particles('levelfx', 'Level up sparks', 'fireworks', 'festival', 110, 520, 5),
            particles('petfx', 'Pet sparks', 'sparks', 'festival', 20, 100, 4, GOLD)]
    return out


# ---------- what stays on the screen: each player's card, the bag, menus, notes
def name_text(p): return ''.join(f'{{n{k}@{p}:letter}}' for k in range(8))
def hud_items():
    out = [hud('hud_panel', 'Player 1 card', 24, 24, 640, 150, 'panel_hud'),
           text('p1_name', 'Player 1 name', 48, 40, 4, name_text(1), GOLD), text('p1_lv', 'Player 1 level', 300, 44, 3, 'LV {level@1}', MINT),
           hud('heart', 'Heart', 48, 92, 56, 56, 'heart'), text('p1_hp', 'Player 1 health', 112, 104, 4, '{hp@1}/{maxHp@1}'),
           hud('mana', 'Mana', 300, 92, 56, 56, 'ui/mana'), text('p1_mp', 'Player 1 mana', 364, 104, 4, '{mp@1}/{maxMp@1}', '#9EC8FF'),
           hud('coin', 'Coin', 480, 92, 56, 56, 'coin'), text('gold_text', 'Gold', 544, 104, 4, '{gold}', GOLD),
           hud('p2_panel', 'Player 2 card', 1436, 24, 460, 110, 'ui/panel_p2'), text('p2_name', 'Player 2 name', 1460, 40, 4, name_text(2), GOLD),
           text('p2_lv', 'Player 2 level', 1720, 44, 3, 'LV {level@2}', MINT), hud('heart2', 'Heart 2', 1460, 76, 44, 44, 'heart'), text('p2_hp', 'Player 2 health', 1516, 86, 4, '{hp@2}/{maxHp@2}'),
           hud('hint_panel', 'Controls panel', 1110, 1000, 786, 56, 'panel_hint'), lab('hint', 'Controls', 1503, 1004, 'hint', center=True),
           lab('banner', 'Level up banner', 960, 230, 'banner', center=True), lab('peace', 'Ending', 960, 300, 'peace', center=True)]
    tw, th = sized('ui/panel_toast')
    out.append(hud('toast', 'Note panel', 960 - tw // 2, 196, tw, th, 'ui/panel_toast'))
    for k in TOASTS: out.append(lab(f'toast{k}', TOASTS[k], 960, 206, f'toast{k}', center=True))
    return out
TOAST_IDS = ['toast'] + [f'toast{k}' for k in TOASTS]

BAGX, BAGY = 400, 170
BAG_IDS = []
def bag_items():
    x, y = BAGX, BAGY
    rows = [('gold', 'coin', '{gold}'), ('potion', 'potion', 'x {potion}'), ('treat', 'treat', 'x {treat}'), ('fur', 'fur', 'x {fur}')]
    out = [hud('bag', 'Bag panel', x, y, 1120, 740, 'panel_bag'), lab('bag_t', 'Bag title', x + 52, y + 22, 'b_bag')]
    for n, (key, icon, t) in enumerate(rows):
        yy = y + 120 + n * 132
        out += [hud(f'bag_s{n}', f'Slot {n}', x + 56, yy, 112, 112, 'slot'), hud(f'bag_i{n}', key, x + 72, yy + 16, 80, 80, icon),
                lab(f'bag_n{n}', f'{key} name', x + 190, yy + 10, f'b_{key}'), text(f'bag_c{n}', f'{key} count', x + 196, yy + 64, 4, t, MINT)]
    out += [hud('bag_hs', 'Hammer slot', x + 600, y + 120, 112, 112, 'slot'), hud('bag_hi', 'Hammer', x + 616, y + 136, 80, 80, 'hammer'), lab('bag_hn', 'Hammer name', x + 730, y + 150, 'b_hammer'),
            lab('bag_pn', 'No pet', x + 600, y + 300, 'pet_none' if False else 'b_pet_none'),
            lab('bag_pc', 'Your cat', x + 600, y + 290, 'b_pet_cat'), lab('bag_pd', 'Your dog', x + 600, y + 290, 'b_pet_dog'),
            text('bag_pl', 'Pet level', x + 604, y + 350, 4, 'LV {petLevel@1}', GOLD), lab('bag_pf', 'Fed', x + 800, y + 340, 'b_pet_full'), lab('bag_ph', 'Hungry', x + 800, y + 340, 'b_pet_hungry'),
            lab('bag_f', 'Bag help', x + 56, y + 660, 'b_baghelp')]
    BAG_IDS[:] = [i['id'] for i in out]
    return out
PET_BAG = ['bag_pn', 'bag_pc', 'bag_pd', 'bag_pl', 'bag_pf', 'bag_ph']

PX, PY = 600, 160
OPT_Y = [350, 440, 530, 620, 710]
PAUSE = ['pause_panel', 'pause_t', *[f'opt{n}' for n in range(5)], 'pointer', 'pause_help']
def node_xy(k): c, r = divmod(k, 3); return 330 + c * 300, 330 + r * 200
SKILL_BASE = ['skill_panel', 'skill_t', 'skill_pts', 'skill_help', 'skill_b1', 'skill_b2', 'skill_ring'] + [f'icon{k}' for k in range(3, 9)]
SKILL_CLASS = [f'brc{c}' for c in range(3)] + [f'cicon{c}_{k}' for c in range(3) for k in range(3)] + [f'sn{c}_{k}' for c in range(3) for k in range(3)] + [f'sd{c}_{k}' for c in range(3) for k in range(3)]
SKILL_ALL = SKILL_BASE + SKILL_CLASS + [f'spn{p}' for p in PLAYERS] + [f'lock{k}' for k in range(9)] + [f'own{k}' for k in range(9)] + [f'sn{k}' for k in range(3, 9)] + [f'sd{k}' for k in range(3, 9)] + ['st_have', 'st_can', 'st_above', 'st_none']
JOURNAL = ['jr_panel', 'jr_t', 'jr_help', 'jr_empty'] + [f'jq{q}' for q in range(1, 6)] + [f'jd{q}' for q in range(1, 6)] + [f'jok{q}' for q in range(1, 6)] + [f'jready{q}' for q in range(1, 6)] + ['jc1', 'jc3', 'jc4']
def menu_items():
    out = [hud('dim', 'Menu shade', 0, 0, 1920, 1080, 'ui/dim'),
           hud('pause_panel', 'Pause panel', PX, PY, 720, 720, 'ui/panel_pause'), lab('pause_t', 'Paused title', 960, PY + 34, 'paused', center=True)]
    for n, y in enumerate(OPT_Y): out.append(lab(f'opt{n}', OPTIONS[n], 790, y, f'o{n}'))
    pw, ph = sized('ui/pointer')
    out += [hud('pointer', 'Menu pointer', 720, OPT_Y[0] + 20, pw, ph, 'ui/pointer'), lab('pause_help', 'Pause help', 960, PY + 640, 'menuhelp', center=True)]
    out += [hud('skill_panel', 'Skills panel', 170, 90, 1580, 900, 'ui/panel_skills'), lab('skill_t', 'Skills title', 240, 110, 'skills'),
            lab('skill_pts', 'Points label', 1300, 136, 'points'), lab('skill_help', 'Skills help', 960, 920, 'skillhelp', center=True)]
    for p in PLAYERS: out.append(text(f'spn{p}', f'Skill points {p}', 1530, 146, 6, f'{{sp@{p}}}', GOLD))
    for c in range(3): out.append(lab(f'brc{c}', CLASSES[c], 386, 246, f'brc{c}', center=True))
    for b in (1, 2): out.append(lab(f'skill_b{b}', BRANCHES[b], 386 + b * 300, 246, f'br{b}', center=True))
    rw, rh = sized('ui/ring')
    out.append(hud('skill_ring', 'Skill cursor', node_xy(0)[0] - 18, node_xy(0)[1] - 18, rw, rh, 'ui/ring'))
    for c in range(3):
        for k in range(3):
            x, y = node_xy(k); out.append(hud(f'cicon{c}_{k}', CLASS_SKILLS[c][k][0], x, y, 112, 112, f'ui/cskill{c}_{k}'))
    for k in range(3, 9):
        x, y = node_xy(k); out.append(hud(f'icon{k}', SHARED_SKILLS[k - 3][0], x, y, 112, 112, f'ui/skill{k}'))
    for k in range(9):
        x, y = node_xy(k); out.append(hud(f'lock{k}', f'Skill {k} locked', x, y, 112, 112, 'ui/lock'))
    for k in range(9):
        x, y = node_xy(k); out.append(hud(f'own{k}', f'Skill {k} learned', x - 6, y - 6, 124, 124, 'ui/ring'))
    for c in range(3):
        for k in range(3): out += [lab(f'sn{c}_{k}', CLASS_SKILLS[c][k][0], 1260, 330, f'sn{c}_{k}'), lab(f'sd{c}_{k}', 'Skill text', 1260, 400, f'sd{c}_{k}')]
    for k in range(3, 9): out += [lab(f'sn{k}', SHARED_SKILLS[k - 3][0], 1260, 330, f'sn{k}'), lab(f'sd{k}', 'Skill text', 1260, 400, f'sd{k}')]
    for key in ('st_have', 'st_can', 'st_above', 'st_none'): out.append(lab(key, key, 1260, 620, key))
    # the journal: each quest's name, then what to do, Done, or go back and tell them
    out += [hud('jr_panel', 'Journal panel', 270, 90, 1380, 900, 'ui/panel_journal'), lab('jr_t', 'Journal title', 340, 110, 'journal'), lab('jr_help', 'Journal help', 960, 920, 'journalhelp', center=True),
            lab('jr_empty', 'No quests', 340, 260, 'q_empty')]
    for q in range(1, 6):
        y = 220 + (q - 1) * 136
        out += [lab(f'jq{q}', QUESTS[q - 1][0], 340, y, f'qn{q}'), lab(f'jd{q}', 'Quest text', 340, y + 52, f'qd{q}'),
                lab(f'jok{q}', 'Done', 1400, y + 6, 'q_done'), lab(f'jready{q}', 'Ready', 1200, y + 6, 'q_ready')]
    out += [text('jc1', 'Garden count', 1320, 272, 4, '{gKills}/3', MINT), text('jc3', 'Fur count', 1320, 544, 4, '{fur}/4', MINT), text('jc4', 'Wolf count', 1320, 680, 4, '{wolfKills}/5', MINT)]
    return out

def dialog_items(speakers, keys):
    x, y = 80, 800
    out = [hud('dlg_panel', 'Dialog panel', x, y, 1760, 248, 'panel_dialog')]
    for s in speakers: out.append(lab(f'who_{s}', s.title(), x + 44, y + 18, f'who_{s}'))
    for key in keys: out.append(lab(f'line_{key}', f'Line {key}', x + 44, y + 84, key))
    out.append(lab('dlg_x', 'Dialog hint', x + 1700 - SIZE['next'][0], y + 186, 'next'))
    return out

HIDDEN_AT_START = ['dim', 'banner', 'peace', 'dlg_panel', 'dlg_x', 'p2_panel', 'p2_name', 'p2_lv', 'heart2', 'p2_hp', 'mana', 'p1_mp'] + PAUSE + SKILL_ALL + JOURNAL + TOAST_IDS + [f'slash{p}' for p in PLAYERS]


# ---------- blocks used in every place you can walk
def gameplay(): return 'mode = 0 and bag = 0 and dlg = 0'
def each_screen(*a):
    "Blocks for what stays on the screen: once for each screen in the place, as its first player. Online every friend has a screen."
    return each_player(when('seat = 1', *a))
def toast(k, t=150): return [setv('toastK', k), setv('toastT', t)]

def world_start(where, music_name):
    "When a place starts: the menus closed, the players' looks and cameras, their pets, and where they arrive."
    a = [act('setVolume', value=70), music(music_name), setv('mode', 0), setv('bag', 0), setv('dlg', 0), setv('where', where), setv('atkWait', 0),
         *[hide(i) for i in HIDDEN_AT_START + BAG_IDS], follow('hero1'), act('hostOnline')]
    for p in PLAYERS: a.append(hide(f'hero{p}'))
    a.append(each_player(show('@player'), setv('atkNow', 0), setv('boomNow', 0), setv('slashT', 0),
                         *[as_player(p, look(f'hero{p}', 'skin * 4 + outfit'), look(f'hair{p}', 'hstyle * 4 + hcolor'), look(f'gear{p}', 'cls - 1')) for p in PLAYERS],
                         when('petKind > 0', spawn('pet', '@player', 60, 8, f('owner', 'player')))))
    a.append(each_player(as_player(2, follow_both('hero1', 'hero2'))))
    return a

def arrive(entries):
    "Puts the players at the way in they came by, side by side."
    out = []
    for k, m in entries.items():
        out.append(when(f'from = {k}', each_player(put('@player', m, 0, 0), *[as_player(p, move('@player', (p - 1) * 56, 0)) for p in PLAYERS[1:]])))
    return out

def walking():
    "Each player's facing and walking, and the same frames on their body, hair and weapon."
    e = [frame(each_player(setv('moving', 0)))]
    for button, face in (('moveDown', 0), ('moveUp', 1), ('moveLeft', 2), ('moveRight', 3)):
        e.append(phold(button, when('mode = 0', setv('face', face), setv('moving', 1))))
    names = {0: 'Down', 1: 'Up', 2: 'Side', 3: 'Side'}
    per = []
    for p in PLAYERS:
        parts = [f'hero{p}', f'hair{p}', f'gear{p}']
        blocks = []
        for face, nm in names.items():
            blocks.append(when(f'face = {face} and moving = 1', *[anim(i, 'walk' + nm) for i in parts]))
            blocks.append(when(f'face = {face} and moving = 0', *[anim(i, 'idle' + nm) for i in parts]))
        blocks += [when('face = 2', *[flip(i, True) for i in parts]), when('face != 2', *[flip(i, False) for i in parts])]
        per.append(as_player(p, *blocks))
    e.append(frame(each_player(*per)))
    e.append(frame(each_player(when('moving = 1 and mode = 0', chg('stepT', 1), when('stepT >= 22', setv('stepT', 0), snd('step'))), when('moving = 0', setv('stepT', 16)))))
    return e

def player_stats():
    "Health, mana, attack and timers from each player's level, class and skills; levels; fainting; pets growing."
    return frame(each_player(
        when('xp >= level * 100 and level < 20', f('xp', 'xp - level * 100'), chg('level', 1), chg('sp', 1), setv('hp', 999), f('mp', '99'),
             setv('bannerT', 150), snd('levelup'), put('levelfx', '@player', -228, -228), burst('levelfx')),
        f('maxHp', '10 + 2 * level + 4 * (cls = 1) + 4 * sk3 + 6 * sk5'),
        f('maxMp', '(cls = 3) * (6 + 2 * level)'),
        f('atk', '1 + level / 2 + (cls = 1) + 2 * sk0 * (cls != 2)'),
        when('hp > maxHp', f('hp', 'maxHp')), when('mp > maxMp', f('mp', 'maxMp')),
        when('atkCd > 0', chg('atkCd', -1)), when('hurtCd > 0', chg('hurtCd', -1)), when('petCd > 0', chg('petCd', -1)), when('slashT > 0', chg('slashT', -1)),
        when('mode = 0', chg('regenT', 1), chg('mpT', 1), when('petKind > 0', chg('petT', 1))),
        when('regenT >= 420 - 300 * sk4', setv('regenT', 0), when('hp < maxHp', chg('hp', 1))),
        when('mpT >= 80 - 40 * sk2 * (cls = 3)', setv('mpT', 0), when('mp < maxMp', chg('mp', 1))),
        when('petT >= 600', setv('petT', 0), when('petHunger > 0', chg('petHunger', -5))),
        when('petKind > 0 and petXp >= petLevel * 10 and petLevel < 10', f('petXp', 'petXp - petLevel * 10'), chg('petLevel', 1), *toast(7), snd('levelup')),
        when('hp <= 0', f('hp', 'maxHp'), f('gold', 'gold - gold / 10'), put('@player', 'respawn', 0, 0), *toast(8), snd('hurt')),
    ))

def arrow_blocks():
    "An arrow leaves the way its player faces."
    return [when('face = 3', spawn('arrowh', '@player', 40, 8, setv('dir', 3), setv('life', 26), flip('@self', False))),
            when('face = 2', spawn('arrowh', '@player', -40, 8, setv('dir', 2), setv('life', 26), flip('@self', True))),
            when('face = 1', spawn('arrowup', '@player', 24, -50, setv('dir', 1), setv('life', 26))),
            when('face = 0', spawn('arrowdn', '@player', 24, 40, setv('dir', 0), setv('life', 26)))]

def attacks():
    "Square attacks the way the player's class does: a sword sweep, an arrow, or a fireball that costs mana."
    sweep = [put(f'slash{p}', f'hero{p}', -64, -64) for p in PLAYERS]
    fire = [spawn('fireball', '@player', 8, -10, f('dir', 'face'), setv('life', 14), f('owner', 'player'))]
    swing = when(f'atkCd = 0 and {gameplay()}',
                 when('cls = 1', setv('atkNow', 1), setv('atkCd', 22), setv('slashT', 10), *[as_player(p, show(f'slash{p}'), sweep[p - 1]) for p in PLAYERS], snd('hit')),
                 when('cls = 2', setv('atkNow', 1), f('atkCd', '24 - 12 * sk2'), setv('shoot', 1), snd('bow')),   # the arrow leaves at the end of the frame, once the ranger has turned to their mark
                 when('cls = 3 and mp >= 2', chg('mp', -2), setv('atkCd', 30), *fire, snd('magic')))
    e = [ppress('square', swing)]
    # the sweep follows its player while it shows, and hides when it is done
    e.append(frame(each_player(*[as_player(p, when('slashT > 0', sweep[p - 1]), when('slashT = 0', hide(f'slash{p}'))) for p in PLAYERS])))
    e.append(copies('arrowh', when('dir = 3', move('@self', 24, 0)), other(move('@self', -24, 0)), chg('life', -1), when('life <= 0', remove())))
    e.append(copies('arrowup', move('@self', 0, -24), chg('life', -1), when('life <= 0', remove())))
    e.append(copies('arrowdn', move('@self', 0, 24), chg('life', -1), when('life <= 0', remove())))
    e.append(copies('fireball', when('dir = 0', move('@self', 0, 22)), when('dir = 1', move('@self', 0, -22)), when('dir = 2', move('@self', -22, 0)), when('dir = 3', move('@self', 22, 0)),
                    chg('life', -1),
                    when('life <= 0', each_player(when('player = owner', setv('boomNow', 1), f('boomX', 'selfX'), f('boomY', 'selfY'))),
                         put('boomfx', '@self', -136, -136), burst('boomfx'), snd('boom'), remove())))
    return e

def end_of_frame():
    "Attacks last one frame: every creature has had its chance to be hit by them."
    return frame(each_player(when('shoot = 1', setv('shoot', 0), *arrow_blocks()), setv('atkNow', 0), setv('boomNow', 0), f('aimPrev', 'aimD'), setv('aimD', 9999)))

def pets():
    "Each pet follows its owner, sits when it is hungry, and grows with its owner's pet level."
    return [copies('pet', setv('cnt', 0), each_player(when('player = owner', chg('cnt', 1))), when('cnt = 0', remove()), each_player(when('player = owner',
        f('petX', 'selfX'), f('petY', 'selfY'),
        look('@self', '(petKind - 1) * 3 + (petLevel >= 4) + (petLevel >= 8)'),
        when('dist > 900', put('@self', '@player', 60, 8)),
        when('dist > 140', chase('@self', '@player', 400)), other(vel('@self', 0, 0)),
        when('selfVX < -20', flip('@self', True)), when('selfVX > 20', flip('@self', False)),
        when('abs(selfVX) + abs(selfVY) > 30', anim('@self', 'walk')), other(when('petHunger > 30', anim('@self', 'idle')), other(anim('@self', 'sit'))),
        when('petKind = 0', remove()))))]

def bag_and_pause():
    "The bag and the pause menu, which belong to the screen: whoever opens one drives it."
    e = []
    e.append(ppress('triangle', when('mode = 0 and dlg = 0', f('pick', 'bag'), when('pick = 1', setv('bag', 0)), when('pick = 0', setv('bag', 1), f('bagP', 'seat'), snd('menu_select')))))
    e.append(ppress('circle', when('bag = 1 and potion > 0 and hp < maxHp', chg('potion', -1), chg('hp', 8), snd('heal'))))
    e.append(ppress('square', when('bag = 1 and treat > 0 and petKind > 0', chg('treat', -1), setv('petHunger', 100), chg('petXp', 5), snd('eat'), *toast(14))))
    open_pause = [setv('mode', 1), setv('sel', 0), setv('bag', 0), f('menuP', 'seat'), act('pauseGame'), snd('pause')]
    resume = [setv('mode', 0), act('resumeGame'), snd('menu_select')]
    e.append(ppress('options', f('pick', 'mode'), when('pick = 0 and dlg = 0', *open_pause), when('pick != 0 and seat = menuP', *resume)))
    e.append(ppress('circle', when('seat = menuP', f('pick', 'mode'), when('pick = 1', *resume), when('pick >= 2', setv('mode', 1), snd('menu_move')))))
    me = 'seat = menuP and '
    e.append(ppress('moveUp', when(me + 'mode = 1', f('sel', '(sel + 4) % 5'), snd('menu_move')), when(me + 'mode = 2 and ssel % 3 != 0', chg('ssel', -1), snd('menu_move'))))
    e.append(ppress('moveDown', when(me + 'mode = 1', f('sel', '(sel + 1) % 5'), snd('menu_move')), when(me + 'mode = 2 and ssel % 3 != 2', chg('ssel', 1), snd('menu_move'))))
    e.append(ppress('moveLeft', when(me + 'mode = 2 and ssel >= 3', chg('ssel', -3), snd('menu_move'))))
    e.append(ppress('moveRight', when(me + 'mode = 2 and ssel <= 5', chg('ssel', 3), snd('menu_move'))))
    def learn(k):
        need = 'sp > 0' + (f' and sk{k - 1} = 1' if k % 3 else '')
        return when(f'ssel = {k} and sk{k} = 0 and {need}', setv(f'sk{k}', 1), chg('sp', -1), snd('skill'), *toast(3, 120))
    save_now = [setv('hasSave', 1), setv('p2ready', 0), save(), *toast(1), snd('save')]
    e.append(ppress('cross', when('seat = menuP', f('pick', 'mode'), f('pick2', 'sel'),
        when('pick = 1 and pick2 = 0', *resume), when('pick = 1 and pick2 = 1', setv('mode', 2), setv('ssel', 0), snd('menu_select')),
        when('pick = 1 and pick2 = 2', setv('mode', 3), snd('menu_select')), when('pick = 1 and pick2 = 3', *save_now),
        when('pick = 1 and pick2 = 4', setv('mode', 0), act('resumeGame'), snd('menu_select'), when('guest = 1', act('stopOnline')), other(act('stopOnline'), go('title'))),
        when('pick = 2', *[learn(k) for k in range(9)]))))
    # what the menus show
    shown = [*[hide(i) for i in ['dim'] + PAUSE + SKILL_ALL + JOURNAL], when('mode >= 1', show('dim')),
             when('mode = 1', *[show(i) for i in PAUSE], *[when(f'sel = {n}', at('pointer', 720, y + 18)) for n, y in enumerate(OPT_Y)])]
    skill = [*[show(i) for i in SKILL_BASE], *[when(f'menuP = {p}', show(f'spn{p}')) for p in (1, 2)]]
    for k in range(9):
        x, y = node_xy(k)
        skill.append(when(f'ssel = {k}', at('skill_ring', x - 18, y - 18)))
    skill.append(each_player(when('seat = menuP and mode = 2',
        *[when(f'cls = {c + 1}', show(f'brc{c}'), *[show(f'cicon{c}_{k}') for k in range(3)], *[when(f'ssel = {k}', show(f'sn{c}_{k}'), show(f'sd{c}_{k}')) for k in range(3)]) for c in range(3)],
        *[when(f'ssel = {k}', show(f'sn{k}'), show(f'sd{k}')) for k in range(3, 9)],
        *[when(f'sk{k} = 1', show(f'own{k}')) for k in range(9)],
        *[when(f'sk{k} = 0 and sk{k - 1} = 0', show(f'lock{k}')) for k in range(9) if k % 3],
        when('ssel % 3 = 0', f('pick', '0')), other(f('pick', '1')),
        *[when(f'ssel = {k}', when(f'sk{k} = 1', show('st_have')),
                when(f'sk{k} = 0', *([when(f'sk{k - 1} = 0', show('st_above')), when(f'sk{k - 1} = 1 and sp > 0', show('st_can')), when(f'sk{k - 1} = 1 and sp <= 0', show('st_none'))]
                                     if k % 3 else [when('sp > 0', show('st_can')), other(show('st_none'))]))) for k in range(9)])))
    shown.append(when('mode = 2', *skill))
    jr = [show('jr_panel'), show('jr_t'), show('jr_help'), when('q1 + q2 + q3 + q4 + q5 = 0', show('jr_empty'))]
    counters = {1: 'jc1', 3: 'jc3', 4: 'jc4'}
    ready = {1: 'gardenClean = 1', 2: 'hammer = 1', 3: 'fur >= 4', 4: 'wolfKills >= 5', 5: 'wardenDead = 1'}
    for q in range(1, 6):
        jr.append(when(f'q{q} = 1', show(f'jq{q}'), show(f'jd{q}'), *([show(counters[q])] if q in counters else []), when(ready[q], show(f'jready{q}'))))
        jr.append(when(f'q{q} = 2', show(f'jq{q}'), show(f'jok{q}')))
    shown.append(when('mode = 3', *jr))
    e.append(frame(each_screen(*shown)))
    return e

def screen_frame():
    "The players' cards, the bag, the level banner and the notes."
    a = [hide('mana'), hide('p1_mp'), each_player(when('seat = 1 and cls = 3', show('mana'), show('p1_mp'))),
         *[hide(i) for i in ['p2_panel', 'p2_name', 'p2_lv', 'heart2', 'p2_hp']], each_player(when('seat = 2', *[show(i) for i in ['p2_panel', 'p2_name', 'p2_lv', 'heart2', 'p2_hp']])),
         *[hide(i) for i in BAG_IDS], when('bag = 1', *[show(i) for i in BAG_IDS if i not in PET_BAG + ['bag_hs', 'bag_hi', 'bag_hn']], when('hammer = 1', show('bag_hs'), show('bag_hi'), show('bag_hn')),
              each_player(when('seat = bagP and bag = 1', when('petKind = 0', show('bag_pn')), when('petKind = 1', show('bag_pc')), when('petKind = 2', show('bag_pd')),
                          when('petKind > 0', show('bag_pl'), when('petHunger > 30', show('bag_pf')), other(show('bag_ph')))))),
         when('bannerT > 0', chg('bannerT', -1)), hide('banner'), when('bannerT > 0 and bag = 0 and mode = 0', show('banner')),
         hide('peace'), when('endT > 0', chg('endT', -1), show('peace')),
         *[hide(i) for i in TOAST_IDS], when('toastT > 0', chg('toastT', -1), when('mode = 0', show('toast'), *[when(f'toastK = {k}', show(f'toast{k}')) for k in TOASTS])),
         hide('hint_panel'), hide('hint'), when('dlg = 0 and mode = 0 and bag = 0', show('hint_panel'), show('hint'))]
    return frame(each_screen(*a))

def joining(where, music_name, entries):
    """A player arrives in a place that is already going: a second controller in the middle of the game, a friend
    joining online, or a screen walking in where another screen already is. The first player of a screen sets that
    screen up, as the start of a place does."""
    screen = [act('setVolume', value=70), music(music_name), setv('mode', 0), setv('bag', 0), setv('dlg', 0), setv('where', where),
              *[hide(i) for i in HIDDEN_AT_START + BAG_IDS if not i.startswith('slash')], follow('@player'),
              when('guest = 1', put('@player', 'hero1', 56, 0)), *[when(f'from = {k}', put('@player', m, 0, 0)) for k, m in entries.items()]]
    return [joins(when('made = 0 and guest = 1', go('create')),   # a friend with no character yet makes one first
                  other(when('made = 0', setv('made', 1), setv('cls', 2), setv('skin', 1), setv('outfit', 1), setv('hstyle', 2), setv('hcolor', 2), setv('level', 1), setv('hp', 20),
                             *[setv(f'n{k}', v) for k, v in enumerate((23, 18, 5, 14))]),
                        show('@player'), setv('atkNow', 0), setv('boomNow', 0), setv('slashT', 0),
                        *[as_player(p, look(f'hero{p}', 'skin * 4 + outfit'), look(f'hair{p}', 'hstyle * 4 + hcolor'), look(f'gear{p}', 'cls - 1')) for p in PLAYERS],
                        when('seat = 1', *screen),
                        when('seat = 2', put('@player', 'hero1', 56, 0), follow_both('hero1', 'hero2'), when('greeted = 0', setv('greeted', 1), *toast(2), snd('menu_select'))),
                        when('petKind > 0', spawn('pet', '@player', 60, 8, f('owner', 'player')))))]

def exits(gates):
    "Walking into a way out takes everyone to the next place."
    return [touch('@player', gate, when(gameplay(), setv('from', frm), snd('door'), go(scene))) for gate, frm, scene in gates]


# ---------- talking: each person has a few conversations, picked by how their quest stands
class Talk:
    "conv: (npc, condition, lines, on_open, choices) where choices maps cross/circle/square to blocks on the last line."
    def __init__(s, convs):
        s.convs = convs; s.npcs = []
        for c in convs:
            if c[0] not in s.npcs: s.npcs.append(c[0])
        s.ids = {}; n = 0
        for ci, c in enumerate(convs):
            for li, key in enumerate(c[2]):
                n += 1; s.ids[(ci, li)] = n
    def keys(s): return sorted({k for c in s.convs for k in c[2]})
    def items(s, positions):
        out = dialog_items(s.npcs, s.keys())
        for npc in s.npcs:
            cx, foot = positions[npc]
            out.append(prompt(f'talk_{npc}', f'Talk to {npc}', 'talk', cx, foot))
        return out
    def events(s):
        e = []
        opens = []
        for npc in s.npcs:
            branch_ = [f('opened', '0')]
            for ci, c in enumerate(s.convs):
                if c[0] != npc: continue
                branch_.append(when(f'opened = 0 and ({c[1]})', setv('opened', 1), setv('dlg', s.ids[(ci, 0)]), f('talker', 'seat'), setv('who', s.npcs.index(npc) + 1), snd('talk'), *c[3]))
            opens.append(near('@player', npc, 'lessOrEqual', 170, *branch_))
        advance = []
        for ci, c in enumerate(s.convs):
            last = len(c[2]) - 1
            for li in range(len(c[2])):
                i = s.ids[(ci, li)]
                if li < last: advance.append(when(f'pick = {i}', setv('dlg', s.ids[(ci, li + 1)]), snd('talk')))
                elif 'cross' in c[4]: advance.append(when(f'pick = {i}', setv('dlg', 0), *c[4]['cross']))
                else: advance.append(when(f'pick = {i}', setv('dlg', 0)))
        e.append(ppress('cross', f('pick', 'dlg'), when('pick = 0 and mode = 0 and bag = 0', *opens), when('pick > 0 and seat = talker', *advance)))
        for button in ('circle', 'square'):
            acts = []
            for ci, c in enumerate(s.convs):
                i = s.ids[(ci, len(c[2]) - 1)]
                if button in c[4] or (button == 'circle' and c[4]): acts.append(when(f'pick = {i}', setv('dlg', 0), *c[4].get(button, [])))
            if acts: e.append(ppress(button, f('pick', 'dlg'), when('pick > 0 and seat = talker', *acts)))
        shown = [hide('dlg_panel'), hide('dlg_x'), *[hide(f'who_{n}') for n in s.npcs], *[hide(f'line_{k}') for k in s.keys()],
                 when('dlg > 0', show('dlg_panel'), show('dlg_x'), *[when(f'who = {k + 1}', show(f'who_{n}')) for k, n in enumerate(s.npcs)],
                      *[when(f'dlg = {s.ids[(ci, li)]}', show(f'line_{key}')) for ci, c in enumerate(s.convs) for li, key in enumerate(c[2])]),
                 when('dlg > 0', each_player(when('seat = talker and dlg > 0', *[when(f'who = {k + 1}', near('@player', n, 'greater', 300, setv('dlg', 0))) for k, n in enumerate(s.npcs)])))]
        e.append(frame(each_screen(*shown)))
        # the words over someone's head stand in the world, for whoever is near and free to talk
        e.append(frame(*[hide(f'talk_{n}') for n in s.npcs], each_player(when('dlg = 0 and mode = 0', *[near('@player', n, 'lessOrEqual', 170, show(f'talk_{n}')) for n in s.npcs]))))
        return e

def reward(gold=0, xp=0, potion=0, extra=()):
    return [*( [chg('gold', gold)] if gold else []), *( [chg('xp', xp)] if xp else []), *( [chg('potion', potion)] if potion else []), *extra, *toast(10), snd('complete')]
def accept(q, *extra): return [setv(f'q{q}', 1), *extra, *toast(9), snd('quest')]
def buy(cost, *got): return [when(f'gold >= {cost}', chg('gold', -cost), *got, *toast(13), snd('coin')), other(*toast(11))]
def adopt(kind): return [when('gold >= 20', chg('gold', -20), setv('petKind', kind), setv('petLevel', 1), setv('petXp', 0), setv('petHunger', 100),
                              spawn('pet', '@player', 60, 8, f('owner', 'player')), *toast(6), snd('meow' if kind == 1 else 'bark')), other(*toast(11))]

MIRA = [('mira', 'q1 = 0 and gardenClean = 0', ['m1', 'm2', 'm3'], [], dict(cross=accept(1))),
        ('mira', 'q1 = 0 and gardenClean = 1', ['m6'], [setv('q1', 2), *reward(30, 60, 1)], {}),
        ('mira', 'q1 = 1 and gardenClean = 0', ['m4'], [], {}),
        ('mira', 'q1 = 1 and gardenClean = 1', ['m5'], [setv('q1', 2), *reward(30, 60, 1)], {}),
        ('mira', 'q1 = 2', ['m7'], [], {})]
TOBIN = [('tobin', 'q2 = 0 and hammer = 0', ['t1', 't2'], [], dict(cross=accept(2))),
         ('tobin', 'q2 != 2 and hammer = 1', ['t4'], [setv('q2', 2), setv('hammer', 2), *reward(40, 80)], {}),
         ('tobin', 'q2 = 1 and hammer = 0', ['t3'], [], {}),
         ('tobin', 'q2 = 2', ['t5'], [], {})]
ODO = [('odo', 'q3 = 0', ['o1', 'o2'], [], dict(cross=accept(3))),
       ('odo', 'q3 = 1 and fur >= 4', ['o4', 'o5'], [setv('q3', 2), chg('fur', -4), *reward(50, 80, 2)], dict(cross=buy(15, chg('potion', 1)))),
       ('odo', 'q3 = 1 and fur < 4', ['o3', 'o5'], [], dict(cross=buy(15, chg('potion', 1)))),
       ('odo', 'q3 = 2', ['o5'], [], dict(cross=buy(15, chg('potion', 1))))]
PELL = [('pell', 'petKind = 0', ['p1', 'p2'], [], dict(cross=adopt(1), square=adopt(2))),
        ('pell', 'petKind > 0', ['p4'], [], dict(cross=buy(10, chg('treat', 3))))]
RHEA = [('rhea', 'q4 = 0', ['r1', 'r2'], [], dict(cross=accept(4, setv('wolfKills', 0)))),
        ('rhea', 'q4 = 1 and wolfKills < 5', ['r3'], [], {}),
        ('rhea', 'q4 = 1 and wolfKills >= 5', ['r4'], [setv('q4', 2), *reward(60, 150)], {}),
        ('rhea', 'q4 = 2', ['r5'], [], {})]
DUNN = [('dunn', 'q5 = 0', ['d1', 'd2'], [], dict(cross=accept(5))),
        ('dunn', 'q5 = 1 and wardenDead = 0', ['d3'], [], {}),
        ('dunn', 'q5 != 2 and wardenDead = 1', ['d4'], [setv('q5', 2), setv('endT', 420), *reward(100, 300)], {}),
        ('dunn', 'q5 = 2', ['d5'], [], {})]


# ---------- creatures: how each kind behaves, fights and is rewarded
HIT_W = 'atkNow = 1 and cls = 1 and dist < 150 + 60 * sk1 and (sk2 = 1 or (face = 3 and hx > -40) or (face = 2 and hx < 40) or (face = 0 and hy > -40) or (face = 1 and hy < 40))'
# A ranger aims by themselves: the arrow goes to the creature nearest to them, if it is within reach. Every creature tells
# each player how far it is (aimD); the nearest of the frame before (aimPrev) is the mark.
HIT_R = 'atkNow = 1 and cls = 2 and dist <= aimPrev + 16 and dist < 520 + 250 * sk0'
TURN_TO_MARK = [when('abs(hx) >= abs(hy)', when('hx > 0', setv('face', 3)), other(setv('face', 2))), other(when('hy > 0', setv('face', 0)), other(setv('face', 1)))]
HIT_M = 'boomNow = 1 and (selfX - boomX) * (selfX - boomX) + (selfY - boomY) * (selfY - boomY) < (170 + 80 * sk1) * (170 + 80 * sk1)'
PET_BITE = 'petKind > 0 and petCd = 0 and petHunger > 0 and (selfX - petX) * (selfX - petX) + (selfY - petY) * (selfY - petY) < 40000'

def mob(t, kind, *, levels, hp, temper, speed, calm=70, roam=220, aggro=420, pack=0, reach=80, dmg='1 + mlv / 3', coin=40, fur=0, on_kill=(),
        cry=None, look_=None, onhit=1):
    "The blocks of one kind of creature: its wandering, its temper, being hit by players and pets, hurting them, and dying."
    hit = [f('mhp', 'mhp - atk - (cls = 2) * sk1'), setv('mstate', onhit), *([alert(t, 'mstate', 1, pack)] if pack else []), put('hitfx', '@self', -28, -28), burst('hitfx'), snd('hit')]
    die = [f('xp', 'xp + mlv * 10 * (2 + sk6) / 2'), *on_kill,
           when(f'rand(1, 100) <= {coin} + 25 * sk7', spawn('coin_drop', '@self', 20, 0, setv('life', 1200))),
           *([when(f'rand(1, 100) <= {fur}', spawn('fur_drop', '@self', -10, 0, setv('life', 1500)))] if fur else []),
           snd('kill'), remove()]
    kill = when('mhp <= 0', *die)
    temper_ = []
    if temper == 'aggro': temper_.append(when(f'mstate = 0 and nearestDist < {aggro}', setv('mstate', 1), *([alert(t, 'mstate', 1, pack)] if pack else []), *([snd(cry)] if cry else [])))
    if temper == 'flee': temper_.append(when('mstate = 0 and nearestDist < 300', setv('mstate', 2)))
    m = MOBS[kind]
    loop = copies(t,
        when('mcd > 0', chg('mcd', -1)),
        *temper_,
        when('mstate = 0', wander('@self', calm, roam)),
        when('mstate = 1', chase('@self', '@nearestPlayer', speed), when('nearestDist > 1100', setv('mstate', 0))),
        when('mstate = 2', flee('@self', '@nearestPlayer', speed), when('nearestDist > 600', setv('mstate', 0))),
        when('selfVX < -20', flip('@self', True)), when('selfVX > 20', flip('@self', False)),
        when('abs(selfVX) + abs(selfVY) > 30', anim('@self', m['run'])), other(anim('@self', m['idle'])),
        *([look('@self', look_)] if look_ else []),
        each_player(
            f('hx', 'selfX - playerX'), f('hy', 'selfY - playerY'),
            when('mhp > 0 and dist < aimD', f('aimD', 'dist')),
            when(f'mhp > 0 and {HIT_W}', *hit, kill), when(f'mhp > 0 and {HIT_R}', *TURN_TO_MARK, *hit, kill), when(f'mhp > 0 and {HIT_M}', *hit, kill),
            when(f'mhp > 0 and {PET_BITE}', f('mhp', 'mhp - petLevel - 2 * sk8'), setv('petCd', 70), chg('petXp', 1), setv('mstate', onhit),
                 put('hitfx', '@self', -28, -28), burst('hitfx'), when('petKind = 1', snd('meow')), other(snd('bark')), kill),
            when(f'mhp > 0 and mstate = 1 and dist < {reach} and hurtCd = 0 and mcd = 0', f('hp', f'hp - ({dmg})'), setv('hurtCd', 45), setv('mcd', 50),
                 put('hurtfx', '@player', -28, -28), burst('hurtfx'), snd('hurt'))))
    return loop

def born(lo, hi, hp_formula, look_=None):
    "What a creature starts as when it is spawned: a level from the range, and health from its level."
    return [f('mlv', f'rand({lo}, {hi})'), f('mmax', hp_formula), f('mmax', 'mmax'), f('mhp', 'mmax'), setv('mstate', 0), setv('mcd', 0), *([look('@self', look_)] if look_ else [])]

def spawner(t, var, count, markers, lo, hi, hp_formula, every=420, look_=None):
    "Keeps `count` of a creature about: when there are fewer, one more comes back at one of the markers after a while."
    picks = [when(f'pick = {k + 1}', spawn(t, m, 0, 0, *born(lo, hi, hp_formula, look_))) for k, m in enumerate(markers)]
    return frame(setv('cnt', 0), for_copies(t, chg('cnt', 1)), when(f'{var} > 0', chg(var, -1)),
                 when(f'cnt < {count} and {var} = 0', setv(var, every), f('pick', f'rand(1, {len(markers)})'), *picks))

def drops():
    return [copies('coin_drop', chg('life', -1), when('life <= 0', remove())), copies('fur_drop', chg('life', -1), when('life <= 0', remove())),
            copy_touch('coin_drop', '@player', chg('gold', 3), snd('coin'), remove()), copy_touch('fur_drop', '@player', chg('fur', 1), snd('pickup'), remove())]

def folk_logic():
    return copies('folk', wander('@self', 80, 280),
                  when('abs(selfVX) + abs(selfVY) < 30', anim('@self', 'idleDown')),
                  other(when('abs(selfVX) >= abs(selfVY)', anim('@self', 'walkSide')), other(when('selfVY < 0', anim('@self', 'walkUp')), other(anim('@self', 'walkDown')))),
                  when('selfVX < -20', flip('@self', True)), when('selfVX > 20', flip('@self', False)))
def folk_template(n):
    return up('folk', 'Townsfolk (template)', -4000, -4000, 56, 44, 'folk', 102, 136, sheet=sheet(120, 160, PERSON, 'idleDown', 6), copies=n, moveSpeed=200, **body())
def folk_spawns(markers): return [spawn('folk', m, 0, 0, look('@self', 'rand(0, 5)')) for m in markers]


# ---------- props drawn by art6_world, at the sizes it suggests
WORLD = json.load(open(f'{HERE}/../out6_world/world.json')) if os.path.exists(f'{HERE}/../out6_world/world.json') else {}
def prop(i, name, src, c, r, wc, dw, dh, hc=1):
    spec = WORLD.get(src) or WORLD.get(src + '.png') or {}
    dw = spec.get('drawWidth', dw); dh = spec.get('drawHeight', dh)
    return up(i, name, c * TS, r * TS, wc * TS, hc * TS, src, dw, dh)
def common_items():
    return effect_templates() + pet_template()

def trees_of(cells, src, start=0):
    return [tree_item(start + n, c, r, src) for n, (c, r) in enumerate(cells)]


# ---------- the village: home, Mira's garden with its three slimes, and the road east
def village():
    W, H = 40, 24; r = random.Random(11)
    g = [[I['flowers'] if r.random() < .07 else I['grass'] for _ in range(W)] for _ in range(H)]
    o = grid(W, H, -1); trees = []
    def tree(c, y): o[y][c] = I['trunk']; trees.append((c, y))
    for c in range(W): tree(c, 1); tree(c, H - 1)
    for y in range(2, H - 1):
        tree(0, y)
        if not 10 <= y <= 14: tree(W - 1, y)
    for y in range(9, 13): g[y][11] = I['path']
    for c in range(6, W): g[12][c] = g[11][c] = I['path']
    for y in range(8, 12): g[y][21] = I['path']
    g[8][11] = I['mat']
    def house(c0, r0, w):
        for c in range(c0, c0 + w):
            o[r0][c] = o[r0 + 1][c] = I['roof']; o[r0 + 2][c] = I['roof_edge']; o[r0 + 3][c] = o[r0 + 4][c] = I['wall']
        o[r0 + 3][c0 + 1] = o[r0 + 3][c0 + w - 2] = I['window']; o[r0 + 4][c0 + w // 2] = I['door']
    house(8, 3, 7); house(29, 3, 6)
    for c in range(17, 26):
        o[3][c] = I['fence']
        if c != 21: o[7][c] = I['fence']
    for y in range(3, 8): o[y][17] = o[y][25] = I['fence']
    for y in range(4, 7):
        for c in range(18, 25): g[y][c] = I['soil']
    for y in range(16, 21):
        for c in range(3, 10): g[y][c] = I['water']
    o[15][15] = I['well']; o[9][36] = I['sign']
    for c, y in ((24, 19), (30, 16), (35, 18), (27, 14), (33, 9), (5, 6), (4, 12), (37, 5), (3, 4), (16, 20)): tree(c, y)
    solid = {(x, y) for y in range(H) for x in range(W) if o[y][x] in {I[n] for n in ('trunk', 'roof', 'roof_edge', 'wall', 'window', 'door', 'fence', 'well', 'sign')} or g[y][x] == I['water']}
    solid.discard((11, 7))
    wo = C.ground_village(root, g, o, W, H, I, [(8, 3, 7, 0), (29, 3, 6, 0)]); C.shimmer(root, wo, (3, 16, 7, 5))
    talk = Talk(MIRA)
    items = [hud('backdrop', 'Sky', 0, 0, 1920, 1080, 'backdrop_village'), outer('village', W, H), art_layer('village_ground', W, H), walls(solid, W, H),
             img('shimmer', 'Water shimmer', 3 * TS, 16 * TS, 7 * TS, 5 * TS, 'shimmer', sheet=sheet(7 * C.TX, 5 * C.TX, [('shine', [0, 1, 2, 3], 3)], 'shine')),
             marker('door_trigger', 'House door', 11, 8), marker('gate', 'East road', W - 1, 10, 1, 5),
             marker('from0', 'Start', 14, 12), marker('from1', 'Out of the house', 11, 10), marker('from2', 'Back from the meadow', 37, 12), marker('respawn', 'Wake up spot', 12, 12),
             *[marker(f'gs{k}', f'Garden slime spot {k}', c, y) for k, (c, y) in enumerate(((19, 5), (21, 4), (23, 6)), 1)],
             *[marker(f'fk{k}', f'Folk spot {k}', c, y) for k, (c, y) in enumerate(((14, 15), (28, 14), (33, 12)), 1)],
             up('house_a', 'Your house', 8 * TS, 7 * TS, 7 * TS, TS, 'house_a', 7 * TS, 400), up('house_b', 'Blue house', 29 * TS, 7 * TS, 6 * TS, TS, 'house_b', 6 * TS, 400),
             up('fence1', 'Fence back', 17 * TS, 3 * TS, 9 * TS, TS, 'fence_long', 9 * TS, 110),
             *[up(f'fencef{c}', 'Fence front', c * TS, 7 * TS, TS, TS, 'fence_short', TS, 110) for c in range(17, 26) if c != 21],
             *[up(f'post{i}', 'Fence side', c * TS, y * TS, TS, TS, 'fence_short', TS, 110) for i, (c, y) in enumerate((c, y) for c in (17, 25) for y in (4, 5, 6))],
             up('well', 'Well', 15 * TS, 15 * TS, TS, TS, 'well', 136, 168), up('sign', 'Sign', 36 * TS, 9 * TS, TS, TS, 'sign', 104, 120),
             npc('mira', 'Mira', 'mira', 24, 8), *heroes(14 * TS, 12 * TS), *trees_of(trees, 'trees'),
             *mob_template('gslime', 'slime', 3, 170), folk_template(3), *common_items(), light_layer('village')]
    items += talk.items({'mira': (24 * TS + 32, 9 * TS + 2)})
    items += hud_items() + bag_items() + menu_items()
    hp = '6 + mlv * 2'
    logic = [start(*world_start(1, 'theme'), *arrive({0: 'from0', 1: 'from1', 2: 'from2'}),
                   when('gKills < 1', spawn('gslime', 'gs1', 0, 0, *born(1, 1, hp, '2'))), when('gKills < 2', spawn('gslime', 'gs2', 0, 0, *born(1, 2, hp, '2'))),
                   when('gKills < 3', spawn('gslime', 'gs3', 0, 0, *born(2, 2, hp, '2'))), *folk_spawns(['fk1', 'fk2', 'fk3']))]
    logic += joining(1, 'theme', {0: 'from0', 1: 'from1', 2: 'from2'}) + walking() + attacks() + talk.events() + bag_and_pause()
    logic += [mob('gslime', 'slime', levels=(1, 2), hp=hp, temper='aggro', speed=150, calm=50, roam=90, aggro=260, look_='2',
                  on_kill=[chg('gKills', 1), when('gKills >= 3 and gardenClean = 0', setv('gardenClean', 1), *toast(4), snd('complete'))]),
              folk_logic(), *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('door_trigger', 1, 'house'), ('gate', 1, 'meadow')])
    logic.append(end_of_frame())
    return dict(id='village', name='Village', background='#1F2A58', world=dict(width=W * TS, height=H * TS), tilt=55, items=items), logic


def house():
    W, H = 30, 17
    g = grid(W, H, I['void']); o = grid(W, H, I['void'])
    for y in range(4, 14):
        for c in range(9, 22): g[y][c] = I['floor']; o[y][c] = -1
    for c in range(8, 23): o[3][c] = I['inner_wall']; o[14][c] = I['inner_wall']
    for y in range(3, 15): o[y][8] = o[y][22] = I['inner_wall']
    for c in (15, 16): g[14][c] = I['exit_mat']; o[14][c] = -1
    o[3][12] = o[3][13] = I['shelf']; o[3][18] = I['hearth']
    o[4][9] = o[4][10] = I['bed_top']; o[5][9] = o[5][10] = I['bed_bottom']; o[9][18] = o[9][19] = I['table']
    for y in (9, 10):
        for c in range(13, 18): g[y][c] = I['rug']
    C.ground_house(root, g, o, W, H, I)
    solid = {(x, y) for y in range(H) for x in range(W) if o[y][x] in {I[n] for n in ('void', 'inner_wall', 'shelf', 'hearth', 'bed_top', 'bed_bottom', 'table')}}
    talk = Talk(TOBIN)
    lab_rest = lab('rest', 'Rested', 960, 300, 'toast1', center=True)
    items = [hud('backdrop', 'Dark', 0, 0, 1920, 1080, 'backdrop_house'), art_layer('house_ground', W, H), walls(solid, W, H),
             up('back_wall', 'Back wall', 8 * TS, 3 * TS, 15 * TS, TS, 'back_wall', 15 * TS, 300), up('fire', 'Fire', 18 * TS, 3 * TS + 4, TS, TS, 'fire', 104, 104, sheet=sheet(110, 110, [('burn', [0, 1, 2], 7)], 'burn')),
             up('table', 'Table', 18 * TS, 9 * TS, 2 * TS, TS, 'table', 196, 144), up('bed', 'Bed', 9 * TS, 5 * TS, 2 * TS, TS, 'bed', 144, 155),
             marker('exit', 'Door out', 15, 14, 2, 1), marker('bedspot', 'Bed', 9, 4, 2, 2), marker('from1', 'In from the village', 15, 12), marker('from0', 'Start', 15, 12), marker('respawn', 'By the bed', 11, 7),
             npc('tobin', 'Tobin', 'tobin', 19, 6), *heroes(15 * TS, 12 * TS), prompt('sleep', 'Bed prompt', 'sleep', 10 * TS, 6 * TS + 2), *common_items(), light_layer('house')]
    items += talk.items({'tobin': (19 * TS + 32, 7 * TS + 2)})
    items += hud_items() + bag_items() + menu_items()
    sleep = ppress('cross', when(f'dlg = 0 and mode = 0 and bag = 0', near('@player', 'bedspot', 'lessOrEqual', 140,
                   each_player(f('hp', 'maxHp'), f('mp', 'maxMp')), setv('hasSave', 1), save(), *toast(1), snd('save'))))
    logic = [start(*world_start(2, 'theme'), *arrive({0: 'from0', 1: 'from1'}))]
    logic += joining(2, 'theme', {0: 'from0', 1: 'from1'}) + walking() + attacks() + talk.events() + [sleep] + bag_and_pause()
    logic += [frame(hide('sleep'), each_player(when('dlg = 0 and mode = 0', near('@player', 'bedspot', 'lessOrEqual', 140, show('sleep'))))), *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('exit', 1, 'village')])
    logic.append(end_of_frame())
    return dict(id='house', name='House', background='#0A080E', world=dict(width=W * TS, height=H * TS), tilt=45, items=items), logic


# ---------- the meadow: open grass between the village, Brookmere and the forest
def meadow():
    W, H = 48, 28; r = random.Random(41)
    g = [[N6['mflower'] if r.random() < .12 else N6['meadow'] for _ in range(W)] for _ in range(H)]
    o = grid(W, H, -1); trees = []; solid = set()
    def tree(c, y): o[y][c] = N6['solid']; trees.append((c, y)); solid.add((c, y))
    for c in range(W):
        if not 21 <= c <= 26: tree(c, 1)
        tree(c, H - 1)
    for y in range(2, H - 1):
        if not 12 <= y <= 16: tree(0, y); tree(W - 1, y)
    for c in range(0, W): g[14][c] = g[15][c] = N6['dirt']
    for y in range(0, 15): g[y][23] = g[y][24] = N6['dirt']
    for c, y in ((6, 5), (12, 22), (19, 8), (30, 4), (41, 9), (44, 21), (9, 18), (36, 24), (16, 3)): tree(c, y)
    walls_ = [(33, 7), (36, 20)]; hay = [(10, 9), (14, 10), (28, 20)]
    for c, y in walls_:
        for k in range(3): o[y][c + k] = N6['solid']; solid.add((c + k, y))
    for c, y in hay: o[y][c] = N6['solid']; solid.add((c, y))
    G6.ground_meadow(root, g, o, W, H)
    items = [hud('backdrop', 'Sky', 0, 0, 1920, 1080, 'backdrop_meadow'), outer('village', W, H), art_layer('meadow_ground', W, H), walls(solid, W, H),
             marker('gate_w', 'West road', 0, 12, 1, 5), marker('gate_n', 'North road', 21, 0, 6, 1), marker('gate_e', 'East road', W - 1, 12, 1, 5),
             marker('from1', 'From the village', 2, 14), marker('from2', 'From Brookmere', 23, 3), marker('from3', 'From the forest', 44, 14), marker('respawn', 'Roadside', 4, 14),
             *[prop(f'wall{k}', 'Stone wall', 'stone_wall', c, y, 3, 3 * TS, 110) for k, (c, y) in enumerate(walls_)],
             *[prop(f'hay{k}', 'Haystack', 'haystack', c, y, 1, 150, 140) for k, (c, y) in enumerate(hay)],
             *[prop(f'flw{k}', 'Wildflowers', 'flowers_patch', c, y, 1, 120, 100) for k, (c, y) in enumerate(((5, 20), (17, 18), (26, 9), (38, 13), (42, 25), (8, 4)))],
             prop('msign', 'Signpost', 'meadow_sign', 25, 13, 1, 110, 130),
             up('hammer_item', "Tobin's hammer", 37 * TS, 21 * TS + 20, 48, 40, 'hammer', 64, 64),
             *[marker(f'sl{k}', f'Slime spot {k}', c, y) for k, (c, y) in enumerate(((8, 7), (16, 20), (30, 10), (40, 18), (20, 24)), 1)],
             *[marker(f'hp{k}', f'Hopper spot {k}', c, y) for k, (c, y) in enumerate(((12, 5), (27, 22), (35, 5), (42, 11), (6, 24)), 1)],
             *heroes(2 * TS, 14 * TS), *trees_of(trees, 'trees'),
             *mob_template('slime', 'slime', 5, 140), *mob_template('hopper', 'hopper', 5, 330), *common_items(), light_layer('meadow')]
    items += hud_items() + bag_items() + menu_items()
    sl = ['sl1', 'sl2', 'sl3', 'sl4', 'sl5']; hpm = ['hp1', 'hp2', 'hp3', 'hp4', 'hp5']
    logic = [start(*world_start(3, 'meadow'), *arrive({1: 'from1', 2: 'from2', 3: 'from3'}),
                   *[spawn('slime', m, 0, 0, *born(1, 3, '5 + mlv * 2', '0')) for m in sl], *[spawn('hopper', m, 0, 0, *born(1, 2, '3 + mlv')) for m in hpm],
                   when('hammer != 0', hide('hammer_item')))]
    logic += joining(3, 'meadow', {1: 'from1', 2: 'from2', 3: 'from3'}) + walking() + attacks() + bag_and_pause()
    logic += [spawner('slime', 'spawnA', 5, sl, 1, 3, '5 + mlv * 2', look_='0'), spawner('hopper', 'spawnB', 5, hpm, 1, 2, '3 + mlv'),
              mob('slime', 'slime', levels=(1, 3), hp='', temper='calm', speed=150, calm=40, roam=180, look_='0'),
              mob('hopper', 'hopper', levels=(1, 2), hp='', temper='flee', speed=330, calm=90, roam=260, coin=20, fur=75, onhit=2),
              touch('@player', 'hammer_item', when('hammer = 0', setv('hammer', 1), hide('hammer_item'), *toast(5), snd('pickup'))),
              *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('gate_w', 2, 'village'), ('gate_n', 1, 'town'), ('gate_e', 1, 'forest')])
    logic.append(end_of_frame())
    return dict(id='meadow', name='Meadow', background='#2A4A3A', world=dict(width=W * TS, height=H * TS), tilt=55, items=items), logic


# ---------- Brookmere: the market town by the river
def town():
    W, H = 44, 28
    g = grid(W, H, N6['meadow'])
    o = grid(W, H, -1); solid = set(); trees = []
    for y in range(0, 3):
        for c in range(W): g[y][c] = N6['river']; solid.add((c, y))
    for y in range(3, H):
        for c in range(19, 26): g[y][c] = N6['cobble']
    for y in range(11, 19):
        for c in range(3, W - 3): g[y][c] = N6['cobble']
    for y in range(12, 18):
        for c in range(16, 29): g[y][c] = N6['plaza']
    for c in range(W):
        if not 19 <= c <= 25: trees.append((c, H - 1)); solid.add((c, H - 1))
    for y in range(3, H - 1):
        trees.append((0, y)); solid.add((0, y)); trees.append((W - 1, y)); solid.add((W - 1, y))
    def block(c0, r0, w, h=3):
        for y in range(r0, r0 + h):
            for c in range(c0, c0 + w): solid.add((c, y))
    houses = [('town_house_a', 3, 5), ('town_house_b', 10, 5), ('town_house_c', 31, 5)]
    for _, c, rr in houses: block(c, rr, 6)
    block(31, 20, 6)                 # the shelter
    block(26, 6, 3, 2)               # the guard post
    stalls = [('stall_food', 14, 9), ('stall_goods', 28, 9)]
    for _, c, rr in stalls: block(c, rr, 3, 1)
    block(21, 14, 3, 2)              # the fountain
    for c, rr in ((5, 21), (12, 21)): block(c, rr, 6)
    G6.ground_town(root, g, o, W, H)
    talk = Talk(ODO + PELL + RHEA)
    items = [hud('backdrop', 'Sky', 0, 0, 1920, 1080, 'backdrop_town'), outer('village', W, H), art_layer('town_ground', W, H), walls(solid, W, H),
             marker('gate_s', 'South road', 19, H - 1, 7, 1), marker('from1', 'From the meadow', 22, 25), marker('respawn', 'By the fountain', 22, 19),
             *[prop(n, n.replace('_', ' ').title(), n, c, rr + 2, 6, 6 * TS, 420) for n, c, rr in houses],
             prop('house_d', 'Weaver house', 'town_house_b', 5, 23, 6, 6 * TS, 420), prop('house_e', 'Baker house', 'town_house_a', 12, 23, 6, 6 * TS, 420),
             prop('shelter', 'Animal shelter', 'shelter', 31, 22, 6, 6 * TS, 400), prop('guardpost', 'Guard post', 'guardpost', 26, 7, 3, 3 * TS, 330),
             *[prop(n, n.replace('_', ' ').title(), n, c, rr, 3, 3 * TS, 230) for n, c, rr in stalls],
             prop('fountain', 'Fountain', 'fountain', 21, 15, 3, 3 * TS, 220), prop('board', 'Notice board', 'board', 23, 9, 1, 140, 170),
             *[prop(f'lamp{k}', 'Lamp', 'lamp', c, rr, 1, 70, 230) for k, (c, rr) in enumerate(((18, 11), (26, 11), (18, 18), (26, 18), (8, 11), (36, 18)))],
             *[prop(f'bench{k}', 'Bench', 'bench', c, rr, 2, 150, 90) for k, (c, rr) in enumerate(((16, 17), (27, 12)))],
             *[prop(f'crates{k}', 'Crates', 'crates', c, rr, 2, 150, 140) for k, (c, rr) in enumerate(((13, 10), (32, 10), (38, 18)))],
             npc('odo', 'Odo', 'odo', 29, 11), npc('pell', 'Pell', 'pell', 33, 24), npc('rhea', 'Rhea', 'rhea', 24, 10),
             *[marker(f'fk{k}', f'Folk spot {k}', c, y) for k, (c, y) in enumerate(((10, 14), (34, 15), (22, 20), (6, 17), (38, 13), (15, 25)), 1)],
             *heroes(22 * TS, 25 * TS), *trees_of(trees, 'trees'), folk_template(6), *common_items(), light_layer('town')]
    items += talk.items({'odo': (29 * TS + 32, 12 * TS + 2), 'pell': (33 * TS + 32, 25 * TS + 2), 'rhea': (24 * TS + 32, 11 * TS + 2)})
    items += hud_items() + bag_items() + menu_items()
    logic = [start(*world_start(4, 'town'), *arrive({1: 'from1'}), *folk_spawns([f'fk{k}' for k in range(1, 7)]))]
    logic += joining(4, 'town', {1: 'from1'}) + walking() + attacks() + talk.events() + bag_and_pause()
    logic += [folk_logic(), *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('gate_s', 2, 'meadow')])
    logic.append(end_of_frame())
    return dict(id='town', name='Brookmere', background='#3A3040', world=dict(width=W * TS, height=H * TS), tilt=55, items=items), logic


# ---------- the forest: wolf packs, boars, blue slimes, and Dunn by the cave
def forest():
    W, H = 48, 26; r = random.Random(23)
    g = [[I['mushroom'] if r.random() < .04 else I['forest'] for _ in range(W)] for _ in range(H)]
    o = grid(W, H, -1); trees = []; solid = set()
    def tree(c, y): o[y][c] = I['forest_trunk']; trees.append((c, y)); solid.add((c, y))
    for c in range(W): tree(c, 1); tree(c, H - 1)
    for y in range(2, H - 1):
        if not 10 <= y <= 15: tree(W - 1, y)
        if not 11 <= y <= 15: tree(0, y)
    for c in range(0, W - 2): g[13][c] = g[14][c] = I['forest_path']
    spots = [(12, 9), (20, 18), (30, 8), (38, 18), (14, 20), (26, 6)]
    for _ in range(90):
        c, y = r.randrange(2, W - 6), r.randrange(3, H - 2)
        if 11 <= y <= 16: continue
        if any(abs(c - a) <= 3 and abs(y - b) <= 3 for a, b in spots): continue
        if o[y][c] == -1:
            if r.random() < .8: tree(c, y)
            else: o[y][c] = I['rock']; solid.add((c, y))
    for y in range(9, 17):
        for c in range(W - 5, W): solid.add((c, y))
    for y in (12, 13, 14):
        for c in range(W - 5, W): solid.discard((c, y))
    C.ground_forest(root, g, o, W, H, I)
    rocks = [(c, y) for y in range(H) for c in range(W) if o[y][c] == I['rock']]
    talk = Talk(DUNN)
    items = [hud('backdrop', 'Sky', 0, 0, 1920, 1080, 'backdrop_forest'), outer('forest', W, H), art_layer('forest_ground', W, H), walls(solid, W, H),
             marker('gate_w', 'West path', 0, 11, 1, 5), marker('cave_gate', 'Cave mouth', W - 2, 12, 1, 3),
             marker('from1', 'From the meadow', 3, 13), marker('from2', 'Out of the cave', W - 8, 13), marker('respawn', 'Path start', 4, 13),
             prop('cave_mouth', 'Cave mouth', 'cave_mouth', W - 5, 15, 5, 5 * TS, 380, 1),
             *[up(f'rock{n}', 'Rock', c * TS, y * TS, TS, TS, 'rock', 96, 96) for n, (c, y) in enumerate(rocks)],
             npc('dunn', 'Dunn', 'dunn', W - 8, 10),
             *[marker(f'pk{k}', f'Wolf den {k}', c, y) for k, (c, y) in enumerate(((14, 8), (30, 18), (36, 6)), 1)],
             *[marker(f'bo{k}', f'Boar spot {k}', c, y) for k, (c, y) in enumerate(((20, 19), (26, 7), (10, 21)), 1)],
             *[marker(f'bs{k}', f'Slime spot {k}', c, y) for k, (c, y) in enumerate(((12, 18), (34, 9), (22, 5)), 1)],
             *heroes(3 * TS, 13 * TS), *trees_of(trees, 'dark_trees'),
             *mob_template('wolf', 'wolf', 6, 360), *mob_template('boar', 'boar', 3, 300), *mob_template('bslime', 'slime', 3, 150), *common_items(), light_layer('forest')]
    items += talk.items({'dunn': ((W - 8) * TS + 32, 11 * TS + 2)})
    items += hud_items() + bag_items() + menu_items()
    wolf_hp, boar_hp, sl_hp = '8 + mlv * 3', '14 + mlv * 3', '6 + mlv * 2'
    wolves = [spawn('wolf', m, dx, dy, *born(4, 6, wolf_hp)) for m in ('pk1', 'pk2') for dx, dy in ((0, 0), (90, 40), (-70, 60))]
    logic = [start(*world_start(5, 'forest'), *arrive({1: 'from1', 2: 'from2'}), *wolves,
                   *[spawn('boar', m, 0, 0, *born(5, 7, boar_hp)) for m in ('bo1', 'bo2', 'bo3')], *[spawn('bslime', m, 0, 0, *born(3, 4, sl_hp, '1')) for m in ('bs1', 'bs2', 'bs3')])]
    logic += joining(5, 'forest', {1: 'from1', 2: 'from2'}) + walking() + attacks() + talk.events() + bag_and_pause()
    logic += [spawner('wolf', 'spawnA', 6, ['pk1', 'pk2', 'pk3'], 4, 6, wolf_hp, 300), spawner('boar', 'spawnB', 3, ['bo1', 'bo2', 'bo3'], 5, 7, boar_hp, 600),
              spawner('bslime', 'spawnC', 3, ['bs1', 'bs2', 'bs3'], 3, 4, sl_hp, 420, '1'),
              mob('wolf', 'wolf', levels=(4, 6), hp=wolf_hp, temper='aggro', speed=340, calm=80, roam=200, aggro=460, pack=520, reach=90, cry='wolf',
                  on_kill=[when('q4 = 1', chg('wolfKills', 1))]),
              mob('boar', 'boar', levels=(5, 7), hp=boar_hp, temper='calm', speed=380, calm=50, roam=160, reach=100, dmg='2 + mlv / 3', coin=60),
              mob('bslime', 'slime', levels=(3, 4), hp=sl_hp, temper='calm', speed=150, calm=40, roam=180, look_='1'),
              *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('gate_w', 3, 'meadow'), ('cave_gate', 1, 'cave')])
    logic.append(end_of_frame())
    return dict(id='forest', name='Forest', background='#0A1A2A', world=dict(width=W * TS, height=H * TS), tilt=55, items=items), logic


# ---------- the cave: bats, stone golems, and the Stone Warden in the deepest hall
def cave():
    W, H = 40, 24; r = random.Random(61)
    g = grid(W, H, N6['cavevoid']); o = grid(W, H, -1); solid = set()
    def open_(c0, r0, c1, r1):
        for y in range(r0, r1):
            for c in range(c0, c1): g[y][c] = N6['cavefloor']
    open_(1, 5, 29, 20); open_(28, 8, 39, 17); open_(0, 11, 2, 14)
    for (c, y) in ((10, 8), (11, 8), (18, 15), (24, 7), (33, 12), (34, 12)): g[y][c] = N6['pool']
    for (c, y) in ((6, 16), (22, 11), (36, 9), (36, 15)): g[y][c] = N6['glow']
    for y in range(H):
        for c in range(W):
            if g[y][c] == N6['cavevoid']: solid.add((c, y))
    stal = [(7, 7), (15, 18), (20, 6), (26, 17), (12, 13), (30, 9)]
    crys = [(4, 6), (17, 9), (25, 13), (35, 9), (37, 15), (9, 18)]
    for c, y in stal + crys: o[y][c] = N6['solid']; solid.add((c, y))
    o[16][22] = N6['solid']; solid.add((22, 16)); solid.add((23, 16))
    G6.ground_cave(root, g, o, W, H)
    items = [hud('backdrop', 'Dark', 0, 0, 1920, 1080, 'backdrop_cave'), art_layer('cave_ground', W, H), walls(solid, W, H),
             prop('cave_wall', 'Back wall', 'cave_wall', 1, 5, 15, 15 * TS, 300), prop('cave_wall2', 'Back wall', 'cave_wall', 16, 5, 13, 13 * TS, 300),
             marker('gate_w', 'Way out', 0, 11, 1, 3), marker('from1', 'From the forest', 3, 12), marker('respawn', 'By the entrance', 4, 12),
             *[prop(f'stal{k}', 'Stalagmite', 'stalagmite', c, y, 1, 110, 170) for k, (c, y) in enumerate(stal)],
             *[prop(f'crys{k}', 'Crystals', 'crystal_cluster', c, y, 1, 130, 140) for k, (c, y) in enumerate(crys)],
             prop('cart', 'Minecart', 'minecart', 22, 16, 2, 150, 120),
             *[marker(f'bt{k}', f'Bat roost {k}', c, y) for k, (c, y) in enumerate(((10, 10), (20, 15), (24, 9)), 1)],
             *[marker(f'gm{k}', f'Golem spot {k}', c, y) for k, (c, y) in enumerate(((14, 7), (22, 18), (27, 12)), 1)],
             marker('lair', 'Deepest hall', 35, 12),
             *heroes(3 * TS, 12 * TS),
             *mob_template('bat', 'bat', 8, 380), *mob_template('golem', 'golem', 3, 200), *mob_template('warden', 'warden', 1, 220), *common_items(), light_layer('cave')]
    items += hud_items() + bag_items() + menu_items()
    bat_hp, golem_hp, warden_hp = '5 + mlv * 2', '20 + mlv * 4', '160'
    logic = [start(*world_start(6, 'cave'), *arrive({1: 'from1'}),
                   *[spawn('bat', m, dx, dy, *born(7, 9, bat_hp)) for m in ('bt1', 'bt2') for dx, dy in ((0, 0), (70, -30), (-60, 40), (40, 60))],
                   *[spawn('golem', m, 0, 0, *born(9, 10, golem_hp)) for m in ('gm1', 'gm2', 'gm3')],
                   when('wardenDead = 0', spawn('warden', 'lair', 0, 0, *born(12, 12, warden_hp))))]
    logic += joining(6, 'cave', {1: 'from1'}) + walking() + attacks() + bag_and_pause()
    logic += [spawner('bat', 'spawnA', 8, ['bt1', 'bt2', 'bt3'], 7, 9, bat_hp, 240), spawner('golem', 'spawnB', 3, ['gm1', 'gm2', 'gm3'], 9, 10, golem_hp, 900),
              mob('bat', 'bat', levels=(7, 9), hp=bat_hp, temper='aggro', speed=420, calm=120, roam=160, aggro=420, pack=360, reach=70, cry='bat'),
              mob('golem', 'golem', levels=(9, 10), hp=golem_hp, temper='aggro', speed=170, calm=30, roam=100, aggro=320, reach=110, dmg='2 + mlv / 3', coin=80, cry='golem'),
              mob('warden', 'warden', levels=(12, 12), hp=warden_hp, temper='aggro', speed=200, calm=20, roam=120, aggro=520, reach=150, dmg='5', coin=100, cry='golem',
                  on_kill=[setv('wardenDead', 1), *toast(12, 240), snd('complete')]),
              *pets(), *drops(), player_stats(), screen_frame()]
    logic += exits([('gate_w', 2, 'forest')])
    logic.append(end_of_frame())
    return dict(id='cave', name='Cave', background='#050508', world=dict(width=W * TS, height=H * TS), tilt=50, items=items), logic


# ---------- variables: the game's, each player's, and each creature's
GAME_VARS = dict(gold=10, potion=1, treat=0, fur=0, hammer=0, q1=0, q2=0, q3=0, q4=0, q5=0, gKills=0, gardenClean=0, wolfKills=0, wardenDead=0,
                 where=1, **{'from': 0}, mode=0, sel=0, ssel=0, menuP=1, bagP=1, pick=0, pick2=0, opened=0, dlg=0, talker=1, who=0, bag=0, toastT=0, toastK=0,
                 bannerT=0, endT=0, hasSave=0, page=0, p2ready=0, cnt=0, cnt2=0, spawnA=0, spawnB=0, spawnC=0, hx=0, hy=0, code=0, atkWait=0)
PLAYER_VARS = dict(cls=1, skin=0, outfit=0, hstyle=0, hcolor=0, **{f'n{k}': 0 for k in range(8)}, nlen=0, made=0, hp=14, maxHp=14, mp=0, maxMp=0, level=1, xp=0, atk=1, sp=1,
                   **{f'sk{k}': 0 for k in range(9)}, face=0, moving=0, stepT=0, atkCd=0, atkNow=0, hurtCd=0, regenT=0, mpT=0, slashT=0,
                   petKind=0, petLevel=1, petXp=0, petHunger=100, petCd=0, petT=0, petX=0, petY=0, boomNow=0, boomX=0, boomY=0, crow=0, cgrid=0, cgx=0, cgy=0, cdone=0, greeted=0, aimD=9999, aimPrev=9999, shoot=0)
COPY_VARS = dict(mhp=0, mmax=1, mlv=1, mstate=0, mcd=0, life=0, dir=0, owner=0)
# What belongs to a screen: where it is, its menus, its talk and its notes. Online each friend's screen has its own.
SCREEN_VARS = ['where', 'from', 'mode', 'sel', 'ssel', 'menuP', 'bagP', 'opened', 'dlg', 'talker', 'who', 'bag', 'toastT', 'toastK', 'bannerT', 'endT', 'page']
GAME_TRANSIENT = ['mode', 'sel', 'ssel', 'bag', 'dlg', 'opened', 'toastT', 'bannerT', 'endT', 'pick', 'pick2', 'cnt', 'cnt2']
NAMES = {1: (18, 15, 23, 1, 14), 2: (23, 18, 5, 14), 3: (13, 1, 18, 5), 4: (10, 15, 19)}   # ROWAN, WREN, MARE, JOS


# ---------- the title, the story and making characters
def title():
    lw, lh = sized('ui/logo'); pw, ph = sized('ui/pointer')
    items = [hud('title_bg', 'Title painting', 0, 0, 1920, 1080, 'ui/title'), hud('logo', 'Logo', 960 - lw // 2, 120, lw, lh, 'ui/logo'),
             lab('t_new', 'New game', 960, 560, 'new', center=True), lab('t_cont', 'Continue', 960, 650, 'cont', center=True),
             lab('t_cont_dim', 'Continue, no save', 960, 650, 'cont_dim', center=True), lab('t_join', 'Join a friend', 960, 740, 'join', center=True),
             lab('t_look', 'Looking for a game', 960, 900, 'looking', center=True),
             hud('t_pointer', 'Title pointer', 960 - SIZE['new'][0] // 2 - pw - 16, 578, pw, ph, 'ui/pointer'),
             lab('t_help', 'Title help', 960, 850, 'titlehelp', center=True),
             lab('t_p2', 'Two players note', 960, 990, 'p2title', center=True), lab('t_p2ready', 'Player 2 ready', 960, 984, 'p2ready', center=True)]
    def reset_player():
        a = [setv(n, v) for n, v in PLAYER_VARS.items()]
        for p, letters in NAMES.items():
            a.append(as_player(p, *[setv(f'n{k}', v) for k, v in enumerate(letters)], setv('nlen', len(letters)), setv('outfit', p - 1), setv('hcolor', (p * 3) % 4)))
        return a
    newgame = [*[setv(n, v) for n, v in GAME_VARS.items() if n not in ('hasSave', 'p2ready')], each_player(*reset_player()), snd('menu_select'), go('story')]
    resume_save = [*[setv(n, 0) for n in GAME_TRANSIENT], each_player(setv('atkCd', 0), setv('atkNow', 0), setv('hurtCd', 0), setv('slashT', 0), setv('cgrid', 0)), snd('menu_select'),
                   *[when(f'where = {k}', go(s)) for k, s in enumerate(['village', 'village', 'house', 'meadow', 'town', 'forest', 'cave'])]]
    logic = [start(act('setVolume', value=70), music('title'), setv('hasSave', 0), setv('sel', 0), setv('p2ready', 0), setv('mode', 9), load(), hide('t_cont'), hide('t_p2ready'), hide('t_look'))]
    # up and down step over Continue while there is no save
    logic.append(ppress('moveDown', when('player = 1 and online = 0', f('sel', '(sel + 1 + (sel = 0 and hasSave = 0)) % 3'), snd('menu_move'))))
    logic.append(ppress('moveUp', when('player = 1 and online = 0', f('sel', '(sel + 2 - (sel = 2 and hasSave = 0)) % 3'), snd('menu_move'))))
    logic.append(ppress('circle', when('online = 2', act('stopOnline'), snd('menu_move'))))
    logic.append(ppress('cross', when('player = 1 and online = 0', f('pick', 'sel'), when('pick = 0', *newgame), when('pick = 1 and hasSave = 1', *resume_save), when('pick = 2', act('joinOnline'), snd('menu_select'))),
                        when('player = 2 and p2ready = 0', setv('p2ready', 1), snd('menu_select'))))
    logic.append(frame(when('mode != 9', setv('mode', 9), setv('sel', 0), setv('p2ready', 0)), when('hasSave != 1 and sel = 1', setv('sel', 0)),
                       hide('t_cont'), hide('t_cont_dim'), when('hasSave = 1', show('t_cont')), other(show('t_cont_dim')),
                       hide('t_p2ready'), hide('t_p2'), when('p2ready = 1', show('t_p2ready')), other(show('t_p2')),
                       hide('t_look'), when('online = 2', show('t_look')),
                       when('sel = 0', at('t_pointer', 960 - SIZE['new'][0] // 2 - pw - 16, 578)), when('sel = 1', at('t_pointer', 960 - SIZE['cont'][0] // 2 - pw - 16, 668)),
                       when('sel = 2', at('t_pointer', 960 - SIZE['join'][0] // 2 - pw - 16, 758))))
    return dict(id='title', name='Title', background='#151A2C', items=items), logic


def story():
    items = [hud(f'story{k}', f'Story picture {k + 1}', 0, 0, 1920, 1080, f'story{k + 1}') for k in range(4)]
    items += [hud('story_shade', 'Caption shade', 0, 760, 1920, 320, 'ui/dim')]
    # the second line sits under however many lines the first one wrapped to
    for k in range(4): items += [lab(f'st{k}a', f'Story {k + 1} line 1', 960, 790, f'st{k}a', center=True), lab(f'st{k}b', f'Story {k + 1} line 2', 960, 790 + SIZE[f'st{k}a'][1] + 6, f'st{k}b', center=True)]
    items.append(lab('story_help', 'Story help', 1880 - SIZE['storyhelp'][0], 1020, 'storyhelp'))
    ids = [f'story{k}' for k in range(4)] + [f'st{k}{s}' for k in range(4) for s in 'ab']
    logic = [start(act('setVolume', value=70), music('story'), setv('page', 0)),
             ppress('cross', chg('page', 1), snd('page'), when('page >= 4', go('create'))),
             ppress('options', go('create')),
             frame(each_screen(*[hide(i) for i in ids], *[when(f'page = {k}', show(f'story{k}'), show(f'st{k}a'), show(f'st{k}b')) for k in range(4)]))]
    return dict(id='story', name='Story', background='#0A0A12', items=items), logic


def create():
    import art6_ui as UI6
    items = [hud('create_bg', 'Background', 0, 0, 1920, 1080, 'create_bg'), lab('create_t', 'Title', 960, 34, 'create', center=True)]
    rows_y = lambda y0, k: y0 + 110 + k * 82
    for p in (1, 2):
        x0, y0 = (60, 150) if p == 1 else (990, 150)
        items += [hud(f'cpanel{p}', f'Panel {p}', x0, y0, 870, 880, 'ui/panel_create')]
        for part, src, lk in (('cbody', 'hero_body', 12), ('chair', 'hero_hair', 12), ('cgear', 'hero_gear', 3)):
            items.append(img(f'{part}{p}', f'Preview {part} {p}', x0 + 30, y0 + 110, 264, 352, src, screenFixed=True, sheet=sheet(120, 160, PERSON, 'walkDown', lk)))
        for c in range(3): items += [lab(f'ccls{c}_{p}', CLASSES[c], x0 + 520, rows_y(y0, 0) + 4, f'cls{c}'), lab(f'cclsd{c}_{p}', 'Class text', x0 + 30, y0 + 490, f'clsd{c}')]
        for k in range(7): items.append(lab(f'crow{k}_{p}', f'Row {k}', x0 + 330, rows_y(y0, k) + 8, f'row{k}'))
        pw, ph = sized('ui/pointer')
        items.append(hud(f'cptr{p}', f'Row pointer {p}', x0 + 300 - pw // 2, rows_y(y0, 0) + 14, pw // 2 + 8, ph // 2 + 6, 'ui/pointer'))
        for k in range(3): items.append(hud(f'csk{k}_{p}', 'Skin', x0 + 520 + k * 70, rows_y(y0, 1), 56, 56, f'ui/sw_skin{k}'))
        for k in range(4): items.append(hud(f'cot{k}_{p}', 'Clothes', x0 + 520 + k * 70, rows_y(y0, 2), 56, 56, f'ui/sw_outfit{k}'))
        for k in range(3): items.append(lab(f'cst{k}_{p}', 'Hair style', x0 + 520, rows_y(y0, 3) + 6, f'style{k}'))
        for k in range(4): items.append(hud(f'chc{k}_{p}', 'Hair color', x0 + 520 + k * 70, rows_y(y0, 4), 56, 56, f'ui/sw_hair{k}'))
        for row in ('skin', 'outfit', 'hcolor'): items.append(hud(f'cring_{row}{p}', 'Chosen', x0 + 512, rows_y(y0, 1) - 8, 72, 72, 'ui/ring'))
        items += [text(f'cname{p}', f'Name {p}', x0 + 524, rows_y(y0, 5) + 12, 5, name_text(p), GOLD),
                  lab(f'cready{p}', 'Ready?', x0 + 520, rows_y(y0, 6) + 6, 'readyq'), lab(f'cok{p}', 'Ready!', x0 + 520, rows_y(y0, 6) + 2, 'readyok'),
                  lab(f'cwait{p}', 'Waiting', x0 + 430, y0 + 820, 'waiting'),
                  hud(f'cgridp{p}', 'Letter panel', x0 + 50, y0 + 110, 780, 330, 'ui/panel_grid'),
                  hud(f'cletters{p}', 'Letters', x0 + 80, y0 + 140, UI6.GRID_COLS * UI6.CELL_W, UI6.GRID_ROWS * UI6.CELL_H, 'ui/letters'),
                  hud(f'ccell{p}', 'Letter cursor', x0 + 80, y0 + 140, UI6.CELL_W, UI6.CELL_H, 'ui/cell'),
                  hud(f'ccell2_{p}', 'Wide cursor', x0 + 80, y0 + 140, UI6.CELL_W * 2, UI6.CELL_H, 'ui/cell2'),
                  lab(f'cgridh{p}', 'Grid help', x0 + 80, y0 + 452, 'gridhelp')]
    items += [lab('p2create', 'Player 2 can join', 1425, 560, 'p2create', center=True), lab('createhelp', 'Help', 960, 1044, 'createhelp', center=True)]

    def row_change(sign):
        "Left or right on a line changes what it chooses, going round."
        d = 1 if sign > 0 else -1
        return when('cgrid = 0 and cdone = 0',
                    when('crow = 0', f('cls', f'(cls - 1 + {3 + d}) % 3 + 1')), when('crow = 1', f('skin', f'(skin + {3 + d}) % 3')),
                    when('crow = 2', f('outfit', f'(outfit + {4 + d}) % 4')), when('crow = 3', f('hstyle', f'(hstyle + {3 + d}) % 3')),
                    when('crow = 4', f('hcolor', f'(hcolor + {4 + d}) % 4')), when('crow <= 4', snd('menu_move')))
    typing = [f('code', 'cgy * 10 + cgx + 1'),
              when('code <= 36 and nlen < 8', *[when(f'nlen = {k}', f(f'n{k}', 'code')) for k in range(8)], chg('nlen', 1), snd('type')),
              when('code >= 37 and code <= 38 and nlen > 0', chg('nlen', -1), *[when(f'nlen = {k}', setv(f'n{k}', 0)) for k in range(8)], snd('type')),
              when('code >= 39', setv('cgrid', 0), snd('menu_select'))]
    defaults = [setv('crow', 0), setv('cgrid', 0), setv('cdone', 0)]
    logic = [start(act('setVolume', value=70), music('theme'), each_player(*defaults, when('made = 0 and nlen = 0', *[as_player(p, *[setv(f'n{k}', v) for k, v in enumerate(NAMES[p])], setv('nlen', len(NAMES[p])), setv('outfit', p - 1)) for p in PLAYERS]))),
             joins(when('made = 0', *[setv(n, v) for n, v in PLAYER_VARS.items() if n not in [f'n{k}' for k in range(8)] + ['nlen']],
                        *[as_player(p, *[setv(f'n{k}', v) for k, v in enumerate(NAMES[p])], setv('nlen', len(NAMES[p])), setv('outfit', p - 1)) for p in PLAYERS]), *defaults, when('seat = 1', act('setVolume', value=70), music('theme')), snd('menu_select')),
             ppress('moveUp', when('cgrid = 0 and cdone = 0', f('crow', '(crow + 6) % 7'), snd('menu_move')), when('cgrid = 1', f('cgy', '(cgy + 3) % 4'), snd('menu_move'))),
             ppress('moveDown', when('cgrid = 0 and cdone = 0', f('crow', '(crow + 1) % 7'), snd('menu_move')), when('cgrid = 1', f('cgy', '(cgy + 1) % 4'), snd('menu_move'))),
             ppress('moveLeft', row_change(-1), when('cgrid = 1', f('cgx', '(cgx + 9) % 10'), snd('menu_move'))),
             ppress('moveRight', row_change(1), when('cgrid = 1', f('cgx', '(cgx + 1) % 10'), snd('menu_move'))),
             ppress('cross', f('pick', 'cgrid'), when('cdone = 0 and pick = 1', *typing),
                    when('cdone = 0 and pick = 0', when('crow = 5', setv('cgrid', 1), setv('cgx', 0), setv('cgy', 0), snd('menu_select')),
                         when('crow = 6 and nlen > 0', setv('cdone', 1), setv('made', 1), snd('menu_select')))),
             ppress('circle', when('cgrid = 1', setv('cgrid', 0), snd('menu_move')), other(when('cdone = 1', setv('cdone', 0), snd('menu_move'))))]
    # everyone ready: off to the village, healthy
    logic.append(frame(setv('cnt', 0), setv('cnt2', 0), each_player(chg('cnt2', 1), when('cdone = 1', chg('cnt', 1))),
                       when('cnt = cnt2 and cnt > 0', each_player(f('maxHp', '10 + 2 * level + 4 * (cls = 1)'), f('hp', 'maxHp'), f('maxMp', '(cls = 3) * (6 + 2 * level)'), f('mp', 'maxMp')),
                            each_screen(setv('from', 0), snd('door'), go('village')))))
    UI6_ = UI6
    shown = []
    for p in (1, 2):
        x0, y0 = (60, 150) if p == 1 else (990, 150)
        ids = [f'cpanel{p}', f'cbody{p}', f'chair{p}', f'cgear{p}', *[f'ccls{c}_{p}' for c in range(3)], *[f'cclsd{c}_{p}' for c in range(3)], *[f'crow{k}_{p}' for k in range(7)], f'cptr{p}',
               *[f'csk{k}_{p}' for k in range(3)], *[f'cot{k}_{p}' for k in range(4)], *[f'cst{k}_{p}' for k in range(3)], *[f'chc{k}_{p}' for k in range(4)],
               f'cring_skin{p}', f'cring_outfit{p}', f'cring_hcolor{p}', f'cname{p}', f'cready{p}', f'cok{p}', f'cwait{p}', f'cgridp{p}', f'cletters{p}', f'ccell{p}', f'ccell2_{p}', f'cgridh{p}']
        always = [i for i in ids if not re.match(r'(ccls|cclsd|cst)\d|cready|cok|cwait|cgridp|cletters|ccell|cgridh', i)]
        # while the letter grid is open it takes the top of the panel; only the name line stays beside it
        keep = [f'cpanel{p}', f'crow5_{p}', f'cname{p}', f'cptr{p}']
        body_ = [*[show(i) for i in keep], when('cgrid = 0', *[show(i) for i in always if i not in keep]),
                 look(f'cbody{p}', 'skin * 4 + outfit'), look(f'chair{p}', 'hstyle * 4 + hcolor'), look(f'cgear{p}', 'cls - 1'),
                 *[when(f'cls = {c + 1} and cgrid = 0', show(f'ccls{c}_{p}'), show(f'cclsd{c}_{p}')) for c in range(3)],
                 *[when(f'hstyle = {k} and cgrid = 0', show(f'cst{k}_{p}')) for k in range(3)],
                 *[when(f'crow = {k}', at(f'cptr{p}', x0 + 300 - sized('ui/pointer')[0] // 2, rows_y(y0, k) + 14)) for k in range(7)],
                 *[when(f'skin = {k}', at(f'cring_skin{p}', x0 + 512 + k * 70, rows_y(y0, 1) - 8)) for k in range(3)],
                 *[when(f'outfit = {k}', at(f'cring_outfit{p}', x0 + 512 + k * 70, rows_y(y0, 2) - 8)) for k in range(4)],
                 *[when(f'hcolor = {k}', at(f'cring_hcolor{p}', x0 + 512 + k * 70, rows_y(y0, 4) - 8)) for k in range(4)],
                 when('cdone = 1', show(f'cok{p}'), when('cnt < cnt2', show(f'cwait{p}'))), other(when('cgrid = 0', show(f'cready{p}'))),
                 when('cgrid = 1', show(f'cgridp{p}'), show(f'cletters{p}'), show(f'cgridh{p}'),
                      when('cgy = 3 and cgx >= 6', show(f'ccell2_{p}'), when('cgx <= 7', at(f'ccell2_{p}', x0 + 80 + 6 * UI6_.CELL_W, y0 + 140 + 3 * UI6_.CELL_H)),
                           other(at(f'ccell2_{p}', x0 + 80 + 8 * UI6_.CELL_W, y0 + 140 + 3 * UI6_.CELL_H))),
                      other(show(f'ccell{p}'), *[when(f'cgx = {cx} and cgy = {cy}', at(f'ccell{p}', x0 + 80 + cx * UI6_.CELL_W, y0 + 140 + cy * UI6_.CELL_H)) for cy in range(4) for cx in range(10) if not (cy == 3 and cx >= 6)]))]
        shown.append(frame(each_screen(*[hide(i) for i in ids], each_player(when(f'seat = {p}', *body_)))))
    shown.append(frame(each_screen(hide('p2create'), when('guest = 0', setv('cnt2', 0), each_player(when('guest = 0', chg('cnt2', 1))), when('cnt2 < 2', show('p2create'))))))
    logic += shown
    # Items that share a picture sit next to each other, so the screen binds each picture once; panels stay under
    # what is on them, and the letter grid over everything.
    def layer(it):
        i = it['id']
        if i == 'create_bg': return 0
        if i.startswith('cpanel'): return 1
        if i.startswith('cgridp'): return 3
        if i.startswith('cletters'): return 4
        if i.startswith('ccell'): return 5
        return 2
    order = {it['id']: n for n, it in enumerate(items)}
    items.sort(key=lambda it: (layer(it), it.get('source', it['id']), order[it['id']]))
    return dict(id='create', name='Make your character', background='#141018', items=items), logic


# ---------- everything together
scenes, logics = [], []
for build in (title, story, create, village, house, meadow, town, forest, cave):
    sc, lg = build()
    scenes.append(sc); logics.append(dict(scene=sc['id'], events=lg))
sounds = ['hit', 'hurt', 'pickup', 'talk', 'levelup', 'door', 'kill', 'theme', 'forest', 'title', 'menu_move', 'menu_select', 'pause', 'save', 'skill', 'step',
          'bow', 'magic', 'boom', 'wolf', 'howl', 'boar', 'bat', 'golem', 'meow', 'bark', 'eat', 'quest', 'complete', 'coin', 'heal', 'type', 'page', 'town', 'meadow', 'cave', 'story']
variables = [dict(name=n, initial=v, scope='screen') if n in SCREEN_VARS else dict(name=n, initial=v) for n, v in GAME_VARS.items()] + [dict(name=n, initial=v, scope='player') for n, v in PLAYER_VARS.items()] + [dict(name=n, initial=v, scope='copy') for n, v in COPY_VARS.items()]
logic = dict(schemaVersion=6, variables=variables, sounds=[dict(name=s, source=f'assets/sounds/{s}.wav') for s in sounds], scenes=logics)
logic = json.loads(json.dumps(logic))
# The shared screen blocks show and hide the dialog panel and the like; a place with no one to talk to has none, so
# those blocks are left out there. Anything else naming a missing item is a mistake and stays for Studio to report.
SHARED_OPTIONAL = {'dlg_panel', 'dlg_x'}
for sc, lg in zip(scenes, logic['scenes']):
    present = {it['id'] for it in sc['items']}
    def prune(blocks):
        out = []
        for b in blocks:
            if b['type'] in ('show', 'hide') and b.get('item') in SHARED_OPTIONAL and b['item'] not in present: continue
            if 'actions' in b: b['actions'] = prune(b['actions'])
            out.append(b)
        return out
    lg['events'] = prune(lg['events'])
blocks = renumber(logic)
scene = dict(schemaVersion=6, startScene='title', scenes=scenes)
OVERLAY = r'dlg_.*|who_.*|line_.*|bag(_.*)?|banner|peace|talk_.*|sleep|dim|pause_.*|opt\d|pointer|skill_.*|icon\d|cicon.*|lock\d|own\d|sn.*|sd.*|spn\d|brc\d|st_.*|toast\d*|jr_.*|jq\d|jd\d|jok\d|jready\d|jc\d|p2_.*|heart2|mana|p1_mp|slash\d|t_cont_dim|t_p2ready|story[1-3]|st[1-3][ab]|cgridp\d|cletters\d|ccell.*|cgridh\d|cok\d|cwait\d|cready2|c.*_2|cpanel2|cbody2|chair2|cgear2|cname2|cring_.*2|p2create|rest'
for s in scenes:
    for it in s['items']:
        if re.fullmatch(OVERLAY, it['id']): it['hiddenWhileEditing'] = True
json.dump(scene, open(f'{root}/scene.json', 'w'), indent=1); json.dump(logic, open(f'{root}/logic.json', 'w'), indent=1)
ids = {}; total = 0
for s in scenes:
    count = 0
    for it in s['items']:
        n = max(1, it.get('copies', 0))
        ids[f"{s['id']}.{it['id']}"] = total + count; count += n
    total += count
json.dump(dict(game={n: i for i, n in enumerate(GAME_VARS)}, player={n: i for i, n in enumerate(PLAYER_VARS)}, copy={n: i for i, n in enumerate(COPY_VARS)},
               items=ids, scenes={s['id']: i for i, s in enumerate(scenes)}), open(f'{HERE}/ids6.json', 'w'))
print('items per scene', [sum(max(1, it.get('copies', 0)) for it in s['items']) for s in scenes], 'variables', len(variables), 'blocks', blocks)
