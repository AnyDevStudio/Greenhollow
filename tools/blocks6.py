# Small helpers that write Studio blocks (logic.json schema 5) the way Studio saves them.
import itertools

_ids = itertools.count(1)


def _id(): return f'b{next(_ids)}'


def ev(t, *actions, **f): return dict(id=_id(), type=t, actions=[a for a in actions if a], **f)
def act(t, **f): return dict(id=_id(), type=t, **f)


# variables and formulas
def setv(v, n): return act('setVariable', variable=v, value=int(n))
def chg(v, n): return act('changeVariable', variable=v, value=int(n))
def f(v, formula): return act('setFormula', variable=v, formula=str(formula))
def when(formula, *a): return dict(id=_id(), type='ifFormula', formula=str(formula), actions=[x for x in a if x])
def other(*a): return dict(id=_id(), type='otherwise', actions=[x for x in a if x])
def branch(formula, yes, no):
    "If the formula holds, the first list, otherwise the second."
    return [when(formula, *yes), other(*no)]


# items
def show(i): return act('show', item=i)
def hide(i): return act('hide', item=i)
def put(i, t, x=0, y=0): return act('putAtItem', item=i, otherItem=t, x=x, y=y)
def at(i, x, y): return act('setPosition', item=i, x=x, y=y)
def move(i, x, y): return act('moveBy', item=i, x=x, y=y)
def vel(i, x, y): return act('setVelocity', item=i, x=x, y=y)
def anim(i, a): return act('playAnimation', item=i, animation=a)
def flip(i, left): return act('flipItem', item=i, flipped=bool(left))
def look(i, formula): return act('setLook', item=i, formula=str(formula))
def burst(i): return act('burstParticles', item=i)
def chase(i, t, speed): return act('chaseItem', item=i, otherItem=t, value=int(speed))
def near(a, b, c, n, *k): return dict(id=_id(), type='ifItemDistance', item=a, otherItem=b, comparison=c, value=int(n), actions=list(k))


# sound, scenes, saving, camera
def snd(s): return act('playSound', sound=s)
def music(s): return act('playMusic', sound=s)
def go(s): return act('goToScene', scene=s)
def save(): return act('saveVariables')
def load(): return act('loadVariables')
def follow(i): return act('cameraFollow', item=i)
def follow_both(a, b): return act('cameraFollowBoth', item=a, otherItem=b)


# events
def start(*a): return ev('whenGameStarts', *a)
def frame(*a): return ev('everyFrame', *a)
def press(button, *a): return ev('whenButtonPressed', *a, button=button)
def ppress(button, *a): return ev('whenPlayerPresses', *a, button=button)
def phold(button, *a): return ev('whilePlayerHolds', *a, button=button)
def joins(*a): return ev('whenPlayerJoins', *a)
def touch(a, b, *k): return ev('whenItemsTouch', *k, item=a, otherItem=b)


# players and copies
def each_player(*a): return dict(id=_id(), type='forEachPlayer', actions=[x for x in a if x])
def as_player(n, *a):
    "Blocks for one player only, inside a block that goes through the players."
    return when(f'player = {n}', *a)
def copies(t, *a): return ev('everyFrameForEachCopy', *a, item=t)
def copy_touch(t, other_item, *a): return ev('whenCopyTouches', *a, item=t, otherItem=other_item)
def for_copies(t, *a): return dict(id=_id(), type='forEachCopy', item=t, actions=[x for x in a if x])
def spawn(t, where, x=0, y=0, *a): return dict(id=_id(), type='spawnCopy', item=t, otherItem=where, x=x, y=y, actions=[x_ for x_ in a if x_])
def remove(): return act('removeCopy', item='@self')
def wander(i, speed, radius): return act('wander', item=i, value=int(speed), radius=int(radius))
def flee(i, other_item, speed): return act('flee', item=i, otherItem=other_item, value=int(speed))
def alert(t, var, value, radius): return act('alertNearby', item=t, variable=var, value=int(value), radius=int(radius))


def renumber(logic):
    "Every block its own id, in file order, as Studio would number a freshly made program."
    count = [0]
    def walk(blocks):
        for b in blocks:
            count[0] += 1
            b['id'] = f'b{count[0]}'
            walk(b.get('actions', []))
    for s in logic['scenes']: walk(s['events'])
    return count[0]
