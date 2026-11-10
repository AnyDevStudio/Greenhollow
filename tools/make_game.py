# Writes scene.json and logic.json for Greenhollow, as Studio would save them.
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import art as A
import art4 as C
I=A.INDEX; TS=64
GOLD='#F0C84A'; PAPER='#F6EFE0'; MINT='#A4EFDB'
root=sys.argv[1]

# ---------- items
def base(i,name,kind,x,y,**k): return dict(id=i,type=kind,name=name,x=x,y=y,controllable=False,**k)
def img(i,name,x,y,w,h,src,pix=False,**k):
    d=base(i,name,'image',x,y,width=w,height=h,source=f'assets/{src}.png',**k)
    if pix: d['pixelated']=True
    return d
def up(i,name,x,y,w,h,src,dw,dh,**k): return img(i,name,x,y,w,h,src,upright=True,drawWidth=dw,drawHeight=dh,**k)
def hud(i,name,x,y,w,h,src,pix=False): return img(i,name,x,y,w,h,src,pix=pix,screenFixed=True)
def text(i,name,x,y,scale,t,color=PAPER,fixed=True):
    d=base(i,name,'text',x,y,scale=scale,text=t,color=color)
    if fixed: d['screenFixed']=True
    return d
def sheet(fw,fh,anims,start): return dict(frameWidth=fw,frameHeight=fh,animation=start,animations=[dict(name=n,frames=f,fps=s) for n,f,s in anims])
PERSON=[('idleDown',[0],1),('walkDown',[1,2,3,2],8),('idleUp',[4],1),('walkUp',[5,6,7,6],8),('idleSide',[8],1),('walkSide',[9,10,11,10],8)]
def hero(col,row):
    return up('hero','Hero',col*TS,row*TS,64,64,'hero',102,136,sheet=sheet(120,160,PERSON,'idleDown'),physics='body',gravityScale=0,platformer=False,topDown=True,moveSpeed=420,jumpHeight=260)
def npc(i,name,src,col,row):
    return up(i,name,col*TS,row*TS,64,64,src,102,136,sheet=sheet(120,160,[('idle',[0,1],2)],'idle'),physics='solid')
def trigger(i,name,x,y,w,h): return up(i,name,x,y,w,h,'clear',4,4)
def tree_item(n,c,r,src):
    return up(f'tree{n}',f'Tree {n}',c*TS,r*TS,TS,TS,src,236,320,sheet=sheet(340,460,[(f'v{k}',[k],1) for k in range(4)],f'v{(c*7+r*13)%4}'))
def flat(i,name,x,y,w,h,src): return img(i,name,x,y,w,h,src)
def outer(kind,W,H): return flat('outer','Land around the map',-1800,-900,W*TS+3600,H*TS+1500,f'outer_{kind}')
def art_layer(i,name,src,W,H): return img(i,name,0,0,W*TS,H*TS,src)
def light_layer(kind): return hud('light','Light',0,0,1920,1080,f'light_{kind}')
def tilemap(i,name,grid,solid=(),source='assets/tiles.png'):
    def row(r): return ','.join(str(v) for v in r)
    return base(i,name,'tilemap',0,0,source=source,tileWidth=16,tileHeight=16,tileScale=4,columns=len(grid[0]),rows=len(grid),tiles=[row(r) for r in grid],solidTiles=sorted(set(solid)))
def particles(i,name,preset,palette,amount,size,pixel,color=GOLD,gravity=100,speed=100):
    return base(i,name,'particles',0,-400,width=size,height=size,color=color,preset=preset,palette=palette,amount=amount,spread=70,speed=speed,gravity=gravity,pixelSize=pixel,looping=False)

def hud_items():
    return [
     hud('hud_panel','HUD panel',24,24,600,136,'panel_hud'),
     hud('quest_panel','Quest panel',1448,24,448,64,'panel_quest'),
     hud('hint_panel','Controls panel',1180,1000,716,56,'panel_hint'),
     hud('heart','Heart',48,92,56,56,'heart'),hud('coin','Coin',320,92,56,56,'coin'),hud('quest_icon','Quest jelly',1456,28,56,56,'jelly'),
     text('lv','Level text',48,44,5,'LV {level}',GOLD),text('xp','XP text',240,52,3,'XP {xp}/{xpNeed}',MINT),
     text('hp_text','HP text',112,104,4,'{hp}/{maxHp}'),text('gold_text','Gold text',384,104,4,'{gold}',GOLD),
     text('quest_text','Quest text',1520,44,4,'Jelly {jelly}/3'),
     text('hint','Controls',1204,1016,3,'X TALK   SQUARE HIT   TRIANGLE BAG',PAPER),
     text('banner','Level up banner',528,260,16,'LEVEL UP!',GOLD),
     text('faint','Fainted text',504,200,4,'You fainted and woke up in the village',PAPER),
    ]
def bag_items():
    x,y=440,180
    return [
     hud('bag','Bag panel',x,y,1040,720,'panel_bag'),
     hud('bag_s1','Slot 1',x+56,y+108,144,144,'slot'),hud('bag_s2','Slot 2',x+56,y+268,144,144,'slot'),hud('bag_s3','Slot 3',x+56,y+428,144,144,'slot'),
     hud('bag_i1','Jelly in bag',x+80,y+132,96,96,'jelly'),hud('bag_i2','Potion in bag',x+80,y+292,96,96,'potion'),hud('bag_i3','Gold in bag',x+80,y+452,96,96,'coin'),
     text('bag_t','Bag title',x+56,y+36,8,'BAG',GOLD),
     text('bag_n1','Jelly name',x+224,y+132,4,'Slime Jelly'),text('bag_c1','Jelly count',x+224,y+180,5,'x {jelly}',MINT),
     text('bag_n2','Potion name',x+224,y+292,4,'Potion'),text('bag_c2','Potion count',x+224,y+340,5,'x {potion}',MINT),
     text('bag_n3','Gold name',x+224,y+452,4,'Gold'),text('bag_c3','Gold count',x+224,y+500,5,'{gold}',GOLD),
     text('bag_a','Attack',x+560,y+132,4,'Attack {atk}'),text('bag_l','Level',x+560,y+180,4,'Level {level}'),
     text('bag_q0','Quest none',x+560,y+292,3,'No quest yet. Talk to Mira.',MINT),text('bag_q1','Quest active',x+560,y+292,3,'Bring 3 jelly to Mira.',MINT),text('bag_q2','Quest done',x+560,y+292,3,'Mira is happy. Quest done!',GOLD),
     text('bag_f','Bag help',x+56,y+640,3,'CIRCLE DRINK POTION      TRIANGLE CLOSE',PAPER),
    ]
BAG_ONLY=['bag','bag_s1','bag_s2','bag_s3','bag_i1','bag_i2','bag_i3','bag_t','bag_n1','bag_c1','bag_n2','bag_c2','bag_n3','bag_c3','bag_a','bag_l','bag_f']
def dialog_items(pages):
    x,y=80,800
    out=[hud('dlg_panel','Dialog panel',x,y,1760,248,'panel_dialog')]
    for k,(who,line) in pages.items():
        out.append(text(f'who{k}',f'Speaker {k}',x+48,y+28,5,who,GOLD)); out.append(text(f'line{k}',f'Line {k}',x+48,y+92,4,line))
    out.append(text('dlg_x','Dialog hint',x+1560,y+192,3,'X NEXT',MINT))
    return out

# ---------- maps
def trees_of(o,W,H,trunk,src):
    "Every tree that stands, thinned along the sides and left off the near edge so nothing hides the player. Walls stay."
    out=[]
    for y in range(H):
        for x in range(W):
            if o[y][x]!=trunk or y==H-1: continue
            if (x==0 or x==W-1) and y%2: continue
            out.append(tree_item(len(out),x,y,src))
    return out
def walls(g,o,W,H,solid,ground_solid):
    # The art is painted as whole pictures, so what blocks the hero is this invisible layer, one tile per cell.
    grid_=[[0 if (o[y][x] in solid or g[y][x] in ground_solid) else -1 for x in range(W)] for y in range(H)]
    return tilemap('walls','Walls (invisible)',grid_,[0],source='assets/collision.png')
def grid(w,h,v): return [[v]*w for _ in range(h)]
def tree(obj,over,x,y,trunk='trunk',crown='crown'):
    obj[y][x]=I[trunk]
    if y>0: over[y-1][x]=I[crown]
def house(obj,c0,r0,w,door=True):
    for c in range(c0,c0+w):
        obj[r0][c]=obj[r0+1][c]=I['roof']; obj[r0+2][c]=I['roof_edge']; obj[r0+3][c]=obj[r0+4][c]=I['wall']
    obj[r0+3][c0+1]=obj[r0+3][c0+w-2]=I['window']
    if door: obj[r0+4][c0+w//2]=I['door']

def village():
    W,H=40,24; r=random.Random(11)
    g=[[I['flowers'] if r.random()<.07 else I['grass'] for _ in range(W)] for _ in range(H)]
    o=grid(W,H,-1); v=grid(W,H,-1)
    for c in range(W):
        tree(o,v,c,1); tree(o,v,c,H-1)
    for y in range(2,H-1):
        tree(o,v,0,y)
        if not 10<=y<=14: tree(o,v,W-1,y)
    for y in range(9,13): g[y][11]=I['path']
    for c in range(6,W): g[12][c]=g[11][c]=I['path']
    for y in range(9,12): g[y][21]=I['path']
    g[8][11]=I['mat']
    house(o,8,3,7); house(o,29,3,6)
    for c in range(17,26):
        o[3][c]=I['fence']; 
        if c not in (21,): o[7][c]=I['fence']
    for y in range(3,8): o[y][17]=o[y][25]=I['fence']
    o[7][21]=I['fence']
    for y in range(4,7):
        for c in range(18,25): g[y][c]=I['soil']
    for y in range(16,21):
        for c in range(3,10): g[y][c]=I['water']
    o[15][15]=I['well']; o[9][36]=I['sign']
    for c,y in ((24,19),(30,16),(35,18),(27,14),(33,9),(5,6),(4,12),(37,5),(3,4),(16,20)):
        tree(o,v,c,y)
    solid={I[n] for n in ('trunk','roof','roof_edge','wall','window','door','fence','well','sign')}
    wo=C.ground_village(root,g,o,W,H,I,[(8,3,7,0),(29,3,6,0)]); C.shimmer(root,wo,(3,16,7,5))
    items=[hud('backdrop','Sky',0,0,1920,1080,'backdrop_village'),outer('village',W,H),art_layer('ground','Ground art','village_ground',W,H),walls(g,o,W,H,solid,{I['water']}),
     img('shimmer','Water shimmer',3*TS,16*TS,7*TS,5*TS,'shimmer',sheet=sheet(7*C.TX,5*C.TX,[('shine',[0,1,2,3],3)],'shine')),
     trigger('door_trigger','House door',11*TS,8*TS+20,TS,44),trigger('gate','East gate',W*TS-40,10*TS,40,5*TS),
     up('house_a','Your house',8*TS,7*TS,7*TS,TS,'house_a',7*TS,400),up('house_b','Blue house',29*TS,7*TS,6*TS,TS,'house_b',6*TS,400),
     up('fence1','Fence back',17*TS,3*TS,9*TS,TS,'fence_long',9*TS,110),up('fence2','Fence front',17*TS,7*TS,9*TS,TS,'fence_long',9*TS,110),
     *[up(f'post{i}','Fence side',c*TS,y*TS,TS,TS,'fence_short',TS,110) for i,(c,y) in enumerate((c,y) for c in (17,25) for y in (4,5,6))],
     up('well','Well',15*TS,15*TS,TS,TS,'well',136,168),up('sign','Sign',36*TS,9*TS,TS,TS,'sign',104,120),
     npc('mira','Mira','mira',21,8),hero(11,11),*trees_of(o,W,H,I['trunk'],'trees'),
     text('talk','Talk prompt',21*TS-22,6*TS,3,'X TALK',GOLD,fixed=False),
     particles('levelfx','Level up sparks','fireworks','festival',110,520,5),light_layer('village')]
    pages={'1':('Mira','Slimes crawled out of the east woods and ate my garden.'),
           '2':('Mira','Bring me 3 slime jellies and I will make it worth your while.'),
           '3':('Mira','Will you help me?   X  Yes, I will     CIRCLE  Not now'),
           '4':('Mira','Thank you! The woods are past the gate to the east.'),
           '5':('Mira','Still hunting? I need 3 jellies. You have {jelly}.'),
           '6':('Mira','You did it! Take 50 gold, a potion and my thanks.'),
           '7':('Mira','The garden is safe thanks to you, hero.')}
    items+=hud_items()+dialog_items(pages)+bag_items()
    return dict(id='village',name='Village',background='#1F2A58',world=dict(width=W*TS,height=H*TS),tilt=55,items=items),pages

def forest():
    W,H=48,26; r=random.Random(23)
    g=[[I['mushroom'] if r.random()<.04 else I['forest'] for _ in range(W)] for _ in range(H)]
    o=grid(W,H,-1); v=grid(W,H,-1)
    t=dict(trunk='forest_trunk',crown='forest_crown')
    for c in range(W):
        tree(o,v,c,1,**t); tree(o,v,c,H-1,**t)
    for y in range(2,H-1):
        tree(o,v,W-1,y,**t)
        if not 11<=y<=15: tree(o,v,0,y,**t)
    for c in range(0,W-3):
        g[13][c]=g[14][c]=I['forest_path']
    spots=[(12,9),(20,18),(30,8),(38,17)]
    for _ in range(90):
        c,y=r.randrange(2,W-2),r.randrange(3,H-2)
        if 11<=y<=16: continue
        if any(abs(c-a)<=4 and abs(y-b)<=4 for a,b in spots): continue
        if o[y][c]==-1: tree(o,v,c,y,**t) if r.random()<.8 else o[y].__setitem__(c,I['rock'])
    C.ground_forest(root,g,o,W,H,I)
    items=[hud('backdrop','Sky',0,0,1920,1080,'backdrop_forest'),outer('forest',W,H),art_layer('ground','Ground art','forest_ground',W,H),walls(g,o,W,H,{I['forest_trunk'],I['rock']},set()),trigger('exit','West exit',0,11*TS,40,5*TS)]
    items+=[up(f'rock{n}','Rock',c*TS,y*TS,TS,TS,'rock',96,96) for n,(c,y) in enumerate((c,y) for y in range(H) for c in range(W) if o[y][c]==I['rock'])]
    for n in range(1,5): items.append(up(f'drop{n}',f'Jelly drop {n}',0,-200,48,48,'jelly',60,60))
    for n,(c,y) in enumerate(spots,1):
        items.append(up(f'slime{n}',f'Slime {n}',c*TS,y*TS,64,64,'slime',96,96,sheet=sheet(120,120,[('hop',[0,1,0,2],6)],'hop'),physics='body',gravityScale=0,platformer=False,moveSpeed=150,jumpHeight=260))
    items+=[hero(3,13),*trees_of(o,W,H,I['forest_trunk'],'dark_trees'),
      up('slash','Sword sweep',0,-400,192,192,'slash',192,192,sheet=sheet(192,192,[('sweep',[0,1,2],18)],'sweep')),
      particles('hitfx','Hit sparks','sparks','ice',24,120,4,MINT),particles('hurtfx','Hurt sparks','sparks','fire',22,120,4,'#D94F5C'),
      particles('levelfx','Level up sparks','fireworks','festival',110,520,5),light_layer('forest')]
    items+=hud_items()+bag_items()
    return dict(id='forest',name='Forest',background='#0A1A2A',world=dict(width=W*TS,height=H*TS),tilt=55,items=items),spots

def inside():
    W,H=30,17
    g=grid(W,H,I['void']); o=grid(W,H,I['void']); v=grid(W,H,-1)
    for y in range(4,14):
        for c in range(9,22): g[y][c]=I['floor']; o[y][c]=-1
    for c in range(8,23): o[3][c]=I['inner_wall']; o[14][c]=I['inner_wall']
    for y in range(3,15): o[y][8]=o[y][22]=I['inner_wall']
    for c in (15,16): g[14][c]=I['exit_mat']; o[14][c]=-1
    o[3][12]=o[3][13]=I['shelf']; o[3][18]=I['hearth']
    o[4][9]=o[4][10]=I['bed_top']; o[5][9]=o[5][10]=I['bed_bottom']; o[9][18]=o[9][19]=I['table']
    for y in (9,10):
        for c in range(13,18): g[y][c]=I['rug']
    C.ground_house(root,g,o,W,H,I)
    items=[hud('backdrop','Dark',0,0,1920,1080,'backdrop_house'),art_layer('ground','Room art','house_ground',W,H),walls(g,o,W,H,{I[n] for n in ('void','inner_wall','shelf','hearth','bed_top','bed_bottom','table')},set()),
      up('back_wall','Back wall',8*TS,3*TS,15*TS,TS,'back_wall',15*TS,300),up('fire','Fire',18*TS,3*TS+4,TS,TS,'fire',104,104,sheet=sheet(110,110,[('burn',[0,1,2],7)],'burn')),up('table','Table',18*TS,9*TS,2*TS,TS,'table',196,144),up('bed','Bed',9*TS,5*TS,2*TS,TS,'bed',144,155),
      trigger('exit','Door out',15*TS,14*TS+24,2*TS,40),trigger('bedspot','Bed',9*TS,4*TS,2*TS,2*TS),npc('tobin','Tobin','tobin',19,6),hero(15,12),
      text('talk','Talk prompt',19*TS-22,4*TS+20,3,'X TALK',GOLD,fixed=False),text('sleep','Bed prompt',9*TS+2,3*TS+44,3,'X SLEEP',GOLD,fixed=False),
      particles('levelfx','Level up sparks','fireworks','festival',110,520,5),light_layer('house')]
    pages={'1':('Tobin','Hurt? Lie down on my bed. It fixes nearly everything.')}
    items+=hud_items()+[text('rest','Rested text',720,200,5,'You feel rested',MINT)]+dialog_items(pages)+bag_items()
    return dict(id='house',name='House',background='#0A080E',world=dict(width=W*TS,height=H*TS),tilt=45,items=items),pages

# ---------- blocks
class Ids:
    n=0
def _id():
    Ids.n+=1; return f'b{Ids.n}'
def ev(t,*actions,**f): return dict(id=_id(),type=t,actions=list(actions),**f)
def act(t,**f): return dict(id=_id(),type=t,**f)
def iff(v,c,n,*a): return dict(id=_id(),type='ifVariable',variable=v,comparison=c,value=n,actions=list(a))
def near(a,b,c,n,*k): return dict(id=_id(),type='ifItemDistance',item=a,otherItem=b,comparison=c,value=n,actions=list(k))
def setv(v,n): return act('setVariable',variable=v,value=n)
def chg(v,n): return act('changeVariable',variable=v,value=n)
def show(i): return act('show',item=i)
def hide(i): return act('hide',item=i)
def snd(s): return act('playSound',sound=s)
def put(i,t,x=0,y=0): return act('putAtItem',item=i,otherItem=t,x=x,y=y)
def burst(i): return act('burstParticles',item=i)
def go(s): return act('goToScene',scene=s)
def anim(i,a): return act('playAnimation',item=i,animation=a)
def pos(i,c,r): return act('setPosition',item=i,x=c*TS,y=r*TS)
def vel(i,x,y): return act('setVelocity',item=i,x=x,y=y)
EQ='equal';NE='notEqual';LT='less';LE='lessOrEqual';GT='greater';GE='greaterOrEqual'
def only_when(items,v,c,n): return [*[hide(i) for i in items],iff(v,c,n,*[show(i) for i in items])]
MAXLV=10
def need(l): return 100*l
def maxhp(l): return 8+2*l
def atk(l): return min(l,3)
def restore_hp(): return [iff('level',EQ,l,setv('hp',maxhp(l))) for l in range(1,MAXLV+1)]
def cap_hp(): return [iff('level',EQ,l,iff('hp',GT,maxhp(l),setv('hp',maxhp(l)))) for l in range(1,MAXLV+1)]

def common_start():
    return ev('whenGameStarts',act('cameraFollow',item='hero'),act('setVolume',value=70),act('playMusic',sound='theme'),setv('atkCd',0),setv('hurtCd',0),setv('bag',0),setv('dlg',0))

def common_frame(quest_items=True):
    e=[]
    e.append(ev('everyFrame',setv('moving',0)))
    e.append(ev('whileButtonHeld',setv('facing',1),setv('moving',1),button='moveUp'))
    e.append(ev('whileButtonHeld',setv('facing',0),setv('moving',1),button='moveDown'))
    e.append(ev('whileButtonHeld',setv('facing',2),setv('moving',1),act('flipItem',item='hero',flipped=True),button='moveLeft'))
    e.append(ev('whileButtonHeld',setv('facing',2),setv('moving',1),act('flipItem',item='hero',flipped=False),button='moveRight'))
    names={0:'Down',1:'Up',2:'Side'}
    e.append(ev('everyFrame',*[iff('facing',EQ,f,iff('moving',EQ,1,anim('hero','walk'+names[f])),iff('moving',EQ,0,anim('hero','idle'+names[f]))) for f in names]))
    e.append(ev('whenButtonPressed',iff('bag',EQ,1,setv('bag',2)),iff('bag',EQ,0,setv('bag',1)),iff('bag',EQ,2,setv('bag',0)),button='triangle'))
    e.append(ev('whenButtonPressed',iff('bag',EQ,1,iff('potion',GT,0,chg('potion',-1),chg('hp',5),snd('pickup'),*cap_hp())),button='circle'))
    levels=[iff('level',EQ,l,iff('xp',GE,need(l),chg('xp',-need(l)),setv('level',l+1),setv('xpNeed',need(l+1)),setv('maxHp',maxhp(l+1)),setv('hp',maxhp(l+1)),setv('atk',atk(l+1)),setv('bannerT',150),snd('levelup'),put('levelfx','hero',-228,-228),burst('levelfx'))) for l in range(1,MAXLV)]
    e.append(ev('everyFrame',*levels))
    e.append(ev('everyFrame',iff('bannerT',GT,0,chg('bannerT',-1)),iff('faintT',GT,0,chg('faintT',-1)),iff('restT',GT,0,chg('restT',-1)),
        *only_when(['banner'],'bannerT',GT,0),*only_when(['faint'],'faintT',GT,0),*only_when(BAG_ONLY,'bag',EQ,1),
        *only_when(['quest_panel','quest_icon','quest_text'],'quest',EQ,1),
        *only_when(['bag_q0'],'qshow',EQ,0),*only_when(['bag_q1'],'qshow',EQ,1),*only_when(['bag_q2'],'qshow',EQ,2),
        iff('bag',NE,1,setv('qshow',9)),iff('bag',EQ,1,*[iff('quest',EQ,q,setv('qshow',q)) for q in (0,1,2)])))
    return e

def dialog_frame(pages,npc_id):
    a=[]
    a+=only_when(['dlg_panel','dlg_x'],'dlg',NE,0)
    a+=only_when(['hint_panel','hint'],'dlg',EQ,0) # the controls bar sits where the dialog box opens
    for k in pages: a+=only_when([f'who{k}',f'line{k}'],'dlg',EQ,int(k))
    a+=[hide('talk'),iff('dlg',EQ,0,near('hero',npc_id,LE,170,show('talk'))),iff('dlg',NE,0,near('hero',npc_id,GT,260,setv('dlg',0)))]
    return ev('everyFrame',*a)

def village_logic(pages):
    start=common_start()
    start['actions']+=[iff('from',EQ,1,pos('hero',11,10)),iff('from',EQ,2,pos('hero',36,12)),iff('from',EQ,3,pos('hero',21,10)),hide('banner')]
    e=[start]
    e+=common_frame()
    e.append(dialog_frame(pages,'mira'))
    opener=near('hero','mira',LE,170,
        snd('talk'),
        iff('quest',EQ,2,setv('dlg',7)),
        iff('quest',EQ,1,iff('jelly',LT,3,setv('dlg',5)),iff('jelly',GE,3,setv('dlg',6),setv('quest',2),chg('jelly',-3),chg('xp',100),chg('gold',50),chg('potion',1),snd('levelup'))),
        iff('quest',EQ,0,setv('dlg',1)))
    # Quest 1 to 2 happens inside the opener, so quest 2's line is checked first and cannot answer in the same press.
    advance=[iff('dlg',GE,4,setv('dlg',0)),iff('dlg',EQ,3,setv('quest',1),setv('dlg',4),snd('pickup')),iff('dlg',EQ,2,setv('dlg',3),snd('talk')),iff('dlg',EQ,1,setv('dlg',2),snd('talk'))]
    e.append(ev('whenButtonPressed',setv('consumed',0),iff('dlg',EQ,0,setv('consumed',1),opener),iff('consumed',EQ,0,*advance),button='cross'))
    e.append(ev('whenButtonPressed',iff('dlg',EQ,3,setv('dlg',0)),button='circle'))
    e.append(ev('whenItemsTouch',setv('from',0),snd('door'),go('house'),item='hero',otherItem='door_trigger'))
    e.append(ev('whenItemsTouch',setv('from',0),snd('door'),go('forest'),item='hero',otherItem='gate'))
    return e

def house_logic(pages):
    start=common_start(); start['actions']+=[hide('banner'),hide('rest')]
    e=[start]+common_frame()
    e.append(dialog_frame(pages,'tobin'))
    e.append(ev('everyFrame',hide('sleep'),near('hero','bedspot',LE,140,show('sleep')),*only_when(['rest'],'restT',GT,0)))
    e.append(ev('whenButtonPressed',setv('consumed',0),iff('dlg',NE,0,setv('dlg',0),setv('consumed',1)),
        iff('consumed',EQ,0,near('hero','tobin',LE,170,setv('dlg',1),setv('consumed',1),snd('talk'))),
        iff('consumed',EQ,0,near('hero','bedspot',LE,140,*restore_hp(),setv('restT',150),snd('levelup'))),button='cross'))
    e.append(ev('whenItemsTouch',setv('from',1),snd('door'),go('village'),item='hero',otherItem='exit'))
    return e

def forest_logic(n):
    start=common_start()
    start['actions']+=[hide('banner'),hide('slash'),setv('tick',0)]
    for i in range(1,n+1): start['actions']+=[setv(f's{i}',3),setv(f'r{i}',0),setv(f'd{i}',0),hide(f'drop{i}')]
    e=[start]+common_frame()
    def die(i): return iff(f's{i}',LE,0,hide(f'slime{i}'),vel(f'slime{i}',0,0),put(f'drop{i}',f'slime{i}',8,8),show(f'drop{i}'),setv(f'd{i}',40),chg('xp',30),setv(f'r{i}',420),snd('kill'))
    hits=[]
    for i in range(1,n+1):
        hits.append(iff(f's{i}',GT,0,near(f'slime{i}','hero',LE,150,
            iff('atk',EQ,1,chg(f's{i}',-1)),iff('atk',EQ,2,chg(f's{i}',-2)),iff('atk',GE,3,chg(f's{i}',-3)),
            put('hitfx',f'slime{i}',-28,-28),burst('hitfx'),die(i))))
    e.append(ev('whenButtonPressed',iff('atkCd',EQ,0,setv('atkCd',22),put('slash','hero',-64,-64),show('slash'),snd('hit'),*hits),button='square'))
    e.append(ev('everyFrame',iff('atkCd',GT,0,chg('atkCd',-1),put('slash','hero',-64,-64)),iff('atkCd',EQ,10,hide('slash')),iff('hurtCd',GT,0,chg('hurtCd',-1)),chg('tick',1),iff('tick',GE,240,setv('tick',0))))
    for i in range(1,n+1):
        s=f'slime{i}'; sign=1 if i%2 else -1
        e.append(ev('everyFrame',
            iff(f's{i}',GT,0,
              near(s,'hero',LE,520,act('chaseItem',item=s,otherItem='hero',value=150)),
              near(s,'hero',GT,520,iff('tick',LT,120,vel(s,70*sign,0)),iff('tick',GE,120,vel(s,-70*sign,0))),
              near(s,'hero',LE,72,iff('hurtCd',EQ,0,chg('hp',-1),setv('hurtCd',50),snd('hurt'),put('hurtfx','hero',-28,-28),burst('hurtfx')))),
            iff(f'r{i}',GT,0,chg(f'r{i}',-1),iff(f'r{i}',EQ,1,show(s),setv(f's{i}',3)))))
        # A drop stays on the ground for a moment first, so it is seen even when the slime died right beside the hero.
        e.append(ev('everyFrame',iff(f'd{i}',EQ,1,near('hero',f'drop{i}',LE,64,hide(f'drop{i}'),setv(f'd{i}',0),chg('jelly',1),snd('pickup'))),iff(f'd{i}',GT,1,chg(f'd{i}',-1))))
    e.append(ev('everyFrame',iff('hp',LE,0,*restore_hp(),setv('from',3),setv('faintT',240),go('village'))))
    e.append(ev('whenItemsTouch',setv('from',2),snd('door'),go('village'),item='hero',otherItem='exit'))
    return e

vil,vp=village(); fo,spots=forest(); ho,hp=inside()
scenes=[vil,ho,fo]
variables=[('hp',10),('maxHp',10),('level',1),('xp',0),('xpNeed',100),('atk',1),('gold',0),('potion',0),('jelly',0),('quest',0),('from',0),('facing',0),('moving',0),('bag',0),('qshow',9),('dlg',0),('consumed',0),('atkCd',0),('hurtCd',0),('bannerT',0),('faintT',0),('restT',0),('tick',0)]
for i in range(1,5): variables+=[(f's{i}',3),(f'r{i}',0),(f'd{i}',0)]
sounds=['hit','hurt','pickup','talk','levelup','door','kill','theme']
logic=dict(schemaVersion=4,variables=[dict(name=n,initial=v) for n,v in variables],sounds=[dict(name=s,source=f'assets/sounds/{s}.wav') for s in sounds],
  scenes=[dict(scene='village',events=village_logic(vp)),dict(scene='house',events=house_logic(hp)),dict(scene='forest',events=forest_logic(4))])
scene=dict(schemaVersion=6,startScene='village',scenes=scenes)
json.dump(scene,open(f'{root}/scene.json','w'),indent=1); json.dump(logic,open(f'{root}/logic.json','w'),indent=1)
total=0; items={}
for s in scenes:
    for k,it in enumerate(s['items']): items[f"{s['id']}.{it['id']}"]=total+k
    total+=len(s['items'])
json.dump(dict(vars={n:i for i,(n,_) in enumerate(variables)},items=items,scenes={s['id']:i for i,s in enumerate(scenes)},spots=spots),open(f'{os.path.dirname(os.path.abspath(__file__))}/ids.json','w'))
print('items per scene',[len(s['items']) for s in scenes],'variables',len(variables),'blocks',Ids.n)
