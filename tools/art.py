# Original pixel art and sounds for the Greenhollow sample. Everything is drawn or synthesized here.
import math, os, random, struct, sys, wave
from PIL import Image, ImageDraw

T = 16
def hexc(s, a=255): return (int(s[1:3],16), int(s[3:5],16), int(s[5:7],16), a)

PAL = {
 'k':'#2b2137','h':'#6b4226','H':'#8a5a33','f':'#f1c9a5','F':'#d9a57f','e':'#2b2137',
 't':'#3f8f5b','T':'#2f6e47','b':'#7a4f2a','p':'#3d4a78','P':'#2f3a60','B':'#4f3421',
 'w':'#d7d7e3','W':'#a9a9c4','m':'#8a4fa8','M':'#6b3a86','g':'#bfbfd0','G':'#94949f','y':'#f0c84a','Y':'#c9962e',
 's':'#58c9b0','S':'#3a9e91','l':'#a4efdb','r':'#d94f5c','R':'#a93644','c':'#f6efe0','o':'#e58a3c',
}
def art(rows, swap=None):
    im = Image.new('RGBA',(len(rows[0]),len(rows)),(0,0,0,0))
    for y,row in enumerate(rows):
        for x,ch in enumerate(row):
            if ch=='.': continue
            c = PAL[(swap or {}).get(ch,ch)]
            im.putpixel((x,y),hexc(c))
    return im

HEAD_DOWN = [
"................",
".....kkkkkk.....",
"....khhhhhhk....",
"...khHHHHHHhk...",
"...khffffffhk...",
"...kfekffekfk...",
"...kffffffffk...",
"....kFffffFk....",
"....kttttttk....",
"...kftTttTtfk...",
"...kFtbbbbtFk...",
"....kttTTttk....",
]
HEAD_UP = [
"................",
".....kkkkkk.....",
"....khhhhhhk....",
"...khHHHHHHhk...",
"...khhHHHHhhk...",
"...khhhhhhhhk...",
"...khhhhhhhhk...",
"....khhhhhhk....",
"....kttttttk....",
"...kftTttTtfk...",
"...kFtTTTTtFk...",
"....kttTTttk....",
]
HEAD_SIDE = [
"................",
".....kkkkkk.....",
"....khhhhhhk....",
"...khHHHHHfk....",
"...khhfffffk....",
"...khhffefkk....",
"...khffffffk....",
"....kFffffk.....",
"....kttttk......",
"....ktTtftk.....",
"....ktbbFtk.....",
"....kttTtk......",
]
LEGS = {
 'stand':["....kppkkppk....",".....pp..pp.....",".....kB..Bk.....","................"],
 'a':    ["....kppkkppk....",".....pp..kk.....",".....kB.........","................"],
 'b':    ["....kppkkppk....",".....kk..pp.....",".........Bk.....","................"],
 'side_stand':[".....kppPk......",".....kppPk......",".....kBBk.......","................"],
 'side_a':[".....kpkPk......",".....pk..Pk.....","....kB...kB.....","................"],
 'side_b':[".....kPkpk......","......Pkk.......",".....kBB........","................"],
}
def person(swap=None):
    "12 frames: down, up and side, each stand, walk a, stand, walk b."
    sheet = Image.new('RGBA',(T*4,T*3),(0,0,0,0))
    rows = [(HEAD_DOWN,['stand','a','stand','b']),(HEAD_UP,['stand','b','stand','a']),(HEAD_SIDE,['side_stand','side_a','side_stand','side_b'])]
    for r,(head,legs) in enumerate(rows):
        for c,leg in enumerate(legs):
            sheet.paste(art(head+LEGS[leg],swap),(c*T,r*T))
    return sheet

def slime():
    a=[
    "................","................","................","................",
    ".....kkkkkk.....","....kllssssk....","...klssssssSk...","..klssssssssSk..",
    "..kssekssekssk..","..kssskssskSSk..","..kssssssssSSk..","..kSssssssSSSk..",
    "...kSSSSSSSSk...","....kkkkkkkk....","................","................"]
    b=[
    "................","................","................",".....kkkkkk.....",
    "....klsssssk....","...klsssssSSk...","...kssssssSSk...","...ksekssekSk...",
    "...ksskssskSk...","...kssssssSSk...","...kSssssSSSk...","...kSSSSSSSSk...",
    "....kkkkkkkk....","................","................","................"]
    c=[
    "................","................","................","................",
    "................","......kkkk......","...kkklsssskk...","..klssssssssSk..",
    ".klsseksseksSSk.",".ksssskssskSSSk.",".kSsssssssSSSSk.",".kSSSSSSSSSSSSk.",
    "..kkkkkkkkkkkk..","................","................","................"]
    sheet=Image.new('RGBA',(T*3,T),(0,0,0,0))
    for i,f in enumerate((a,b,c)): sheet.paste(art(f),(i*T,0))
    return sheet

ICONS={
'jelly':["................","................","......kkkk......","....kkllssk.....","...klssssssk....","..klssssssSSk...","..kssssssssSk...","..kssssssSSSk...","..kSsssssSSSk...","...kSSSSSSSk....","....kkkkkkk.....","................","................","................","................","................"],
'potion':["................","......kkkk......","......kBBk......","......kggk......",".....kgggk......","....kgrrrgk.....","...kgrrrrrgk....","...kgrcrrrgk....","...kgrrrrRgk....","...kgrrrRRgk....","....kgRRRgk.....",".....kkkkk......","................","................","................","................"],
'coin':["................","................",".....kkkkkk.....","....kyyyyyYk....","...kyyccyyyYk...","...kycyyyyyYk...","...kycyyYyyYk...","...kyyyYYyyYk...","...kyyyyyyyYk...","...kYyyyyyYYk...","....kYYYYYYk....",".....kkkkkk.....","................","................","................","................"],
'heart':["................","................","...kkk...kkk....","..krrrk.krrrk...",".krcrrrkrrrrRk..",".krcrrrrrrrrRk..",".krrrrrrrrrRRk..","..krrrrrrrRRk...","...krrrrrRRk....","....krrrRRk.....",".....krRRk......","......kRk.......",".......k........","................","................","................"],
}

def noise(rng,d,base,spots,n):
    for y in range(T):
        for x in range(T): d[x,y]=hexc(base)
    for _ in range(n):
        x,y=rng.randrange(T),rng.randrange(T); d[x,y]=hexc(rng.choice(spots))

def rect(d,x0,y0,x1,y1,c):
    for y in range(y0,y1):
        for x in range(x0,x1): d[x,y]=hexc(c)

TILES={}
ORDER=[]
def tile(name):
    def reg(fn):
        ORDER.append(name); TILES[name]=fn; return fn
    return reg

GR='#6aa84f';GS=['#7cbb5e','#5a9443']
@tile('grass')
def _(d,r): noise(r,d,GR,GS,22)
@tile('flowers')
def _(d,r):
    noise(r,d,GR,GS,18)
    for x,y,c in [(3,4,'#f6efe0'),(11,3,'#f0c84a'),(6,11,'#e58a9c'),(13,12,'#f6efe0')]:
        d[x,y]=hexc(c); d[x+1,y]=hexc('#f0c84a' if c!='#f0c84a' else '#e58a3c')
@tile('path')
def _(d,r): noise(r,d,'#c9a26b',['#d8b67f','#b58e5a'],30)
@tile('water')
def _(d,r):
    noise(r,d,'#3f7fbf',['#4f92d0','#356fa8'],16)
    for x in range(3,9): d[x,5]=hexc('#8fc4ec')
    for x in range(9,14): d[x,11]=hexc('#8fc4ec')
@tile('trunk')
def _(d,r):
    noise(r,d,GR,GS,14)
    rect(d,4,0,12,14,'#6b4226'); rect(d,6,0,8,14,'#8a5a33'); rect(d,10,2,11,12,'#4f3421')
    rect(d,2,13,14,15,'#3f6f33')
@tile('crown')
def _(d,r):
    for y in range(T):
        for x in range(T):
            dx,dy=x-7.5,y-7.5
            if dx*dx+dy*dy<=64: d[x,y]=hexc('#2f7a43')
    for _ in range(40):
        x,y=r.randrange(T),r.randrange(T)
        if d[x,y][3] and (x-7.5)**2+(y-7.5)**2<46: d[x,y]=hexc(r.choice(['#3f9a55','#256339','#4fae63']))
@tile('roof')
def _(d,r):
    rect(d,0,0,16,16,'#b5503f')
    for y in (3,7,11,15):
        rect(d,0,y,16,y+1,'#8a3a30')
    for y,o in ((0,0),(4,4),(8,0),(12,4)):
        for x in range(o,16,8): rect(d,x,y,x+1,y+3,'#8a3a30')
@tile('roof_edge')
def _(d,r):
    rect(d,0,0,16,16,'#b5503f'); rect(d,0,3,16,4,'#8a3a30'); rect(d,0,7,16,8,'#8a3a30')
    rect(d,0,10,16,14,'#6d2c24'); rect(d,0,14,16,16,'#3a2230')
@tile('wall')
def _(d,r):
    rect(d,0,0,16,16,'#e6d4ae')
    for x in (0,15): rect(d,x,0,x+1,16,'#7a5a3a')
    rect(d,0,0,16,1,'#7a5a3a'); rect(d,0,15,16,16,'#7a5a3a'); rect(d,5,6,6,10,'#d2bc92'); rect(d,10,2,12,3,'#d2bc92')
@tile('window')
def _(d,r):
    TILES['wall'](d,r)
    rect(d,3,3,13,12,'#4f3421'); rect(d,4,4,12,11,'#8fd0ee'); rect(d,7,4,9,11,'#4f3421'); rect(d,4,7,12,8,'#4f3421'); rect(d,4,4,6,6,'#d6f0fa')
@tile('door')
def _(d,r):
    TILES['wall'](d,r)
    rect(d,3,1,13,16,'#4f3421'); rect(d,4,2,12,16,'#8a5a33'); rect(d,7,2,9,16,'#6b4226'); rect(d,10,8,11,10,'#f0c84a')
@tile('mat')
def _(d,r):
    noise(r,d,'#c9a26b',['#d8b67f','#b58e5a'],20)
    rect(d,2,4,14,13,'#8a3a4f'); rect(d,3,5,13,12,'#b5506a'); rect(d,4,8,12,9,'#e6c07a')
@tile('fence')
def _(d,r):
    noise(r,d,GR,GS,14)
    rect(d,0,5,16,7,'#a9794a'); rect(d,0,10,16,12,'#a9794a'); rect(d,0,7,16,8,'#6b4226'); rect(d,0,12,16,13,'#6b4226')
    rect(d,2,2,5,15,'#c49463'); rect(d,11,2,14,15,'#c49463'); rect(d,4,2,5,15,'#8a5a33'); rect(d,13,2,14,15,'#8a5a33')
@tile('soil')
def _(d,r):
    noise(r,d,'#6b4a2f',['#7c5a3a','#573a25'],24)
    for x,y in [(3,4),(11,4),(3,12),(11,12)]:
        rect(d,x,y-3,x+2,y+1,'#7cbb5e'); d[x-1,y-2]=hexc('#5a9443'); d[x+2,y-2]=hexc('#5a9443')
@tile('well')
def _(d,r):
    noise(r,d,GR,GS,12)
    rect(d,2,6,14,15,'#8d8d99'); rect(d,2,6,14,7,'#b9b9c6'); rect(d,4,8,12,12,'#3f7fbf'); rect(d,3,1,5,8,'#6b4226'); rect(d,11,1,13,8,'#6b4226'); rect(d,1,0,15,3,'#b5503f')
@tile('sign')
def _(d,r):
    noise(r,d,GR,GS,12)
    rect(d,7,9,9,15,'#6b4226'); rect(d,2,2,14,10,'#a9794a'); rect(d,3,3,13,9,'#c49463'); rect(d,4,5,12,6,'#6b4226'); rect(d,4,7,10,8,'#6b4226')
@tile('forest')
def _(d,r): noise(r,d,'#3f7a48',['#4c8c55','#32663c'],26)
@tile('forest_trunk')
def _(d,r):
    noise(r,d,'#3f7a48',['#4c8c55','#32663c'],14)
    rect(d,4,0,12,14,'#4f3421'); rect(d,6,0,8,14,'#6b4226'); rect(d,10,2,11,12,'#3a2618'); rect(d,2,13,14,15,'#27522f')
@tile('forest_crown')
def _(d,r):
    for y in range(T):
        for x in range(T):
            if (x-7.5)**2+(y-7.5)**2<=64: d[x,y]=hexc('#1f5a3a')
    for _ in range(40):
        x,y=r.randrange(T),r.randrange(T)
        if d[x,y][3] and (x-7.5)**2+(y-7.5)**2<46: d[x,y]=hexc(r.choice(['#2a6f49','#17482f','#347f55']))
@tile('mushroom')
def _(d,r):
    noise(r,d,'#3f7a48',['#4c8c55','#32663c'],18)
    rect(d,5,5,11,8,'#d94f5c'); rect(d,4,6,12,8,'#d94f5c'); rect(d,7,8,9,12,'#f6efe0'); d[6,6]=hexc('#f6efe0'); d[9,5]=hexc('#f6efe0')
@tile('rock')
def _(d,r):
    noise(r,d,'#3f7a48',['#4c8c55','#32663c'],12)
    rect(d,3,6,13,14,'#8d8d99'); rect(d,4,4,12,6,'#a4a4b1'); rect(d,5,5,8,8,'#c2c2cd'); rect(d,3,13,13,14,'#62626e')
@tile('forest_path')
def _(d,r): noise(r,d,'#8f7a4f',['#a08b5c','#7a6741'],30)
@tile('floor')
def _(d,r):
    rect(d,0,0,16,16,'#b98a55')
    for y in (3,7,11,15): rect(d,0,y,16,y+1,'#8f6638')
    for y,x in ((0,5),(4,11),(8,3),(12,9)): rect(d,x,y,x+1,y+3,'#8f6638')
@tile('inner_wall')
def _(d,r):
    rect(d,0,0,16,16,'#9b7bb0'); rect(d,0,0,16,2,'#6d5284'); rect(d,0,12,16,14,'#6d5284'); rect(d,0,14,16,16,'#4f3421')
    for x in (3,11): rect(d,x,3,x+1,12,'#876a9c')
@tile('void')
def _(d,r): rect(d,0,0,16,16,'#191322')
@tile('rug')
def _(d,r):
    rect(d,0,0,16,16,'#b5506a'); rect(d,1,1,15,15,'#8a3a4f'); rect(d,3,3,13,13,'#d68a5a'); rect(d,5,5,11,11,'#8a3a4f')
@tile('bed_top')
def _(d,r):
    TILES['floor'](d,r)
    rect(d,1,1,15,16,'#4f3421'); rect(d,2,2,14,16,'#3f6fb5'); rect(d,3,3,13,9,'#f6efe0'); rect(d,3,8,13,9,'#c9c0ad')
@tile('bed_bottom')
def _(d,r):
    TILES['floor'](d,r)
    rect(d,1,0,15,14,'#4f3421'); rect(d,2,0,14,12,'#3f6fb5'); rect(d,2,3,14,4,'#5a88cc'); rect(d,2,8,14,9,'#2f5a96')
@tile('table')
def _(d,r):
    TILES['floor'](d,r)
    rect(d,1,3,15,12,'#6b4226'); rect(d,1,3,15,9,'#a9794a'); rect(d,2,12,4,15,'#4f3421'); rect(d,12,12,14,15,'#4f3421'); rect(d,6,4,10,8,'#d7d7e3'); rect(d,7,5,9,7,'#e58a3c')
@tile('shelf')
def _(d,r):
    rect(d,0,0,16,16,'#4f3421'); rect(d,1,1,15,7,'#2f2030'); rect(d,1,9,15,15,'#2f2030')
    for i,c in enumerate(['#d94f5c','#3f8f5b','#f0c84a','#3f6fb5','#8a4fa8','#e58a3c']):
        rect(d,2+i*2,2,4+i*2,7,c); rect(d,2+i*2,10,4+i*2,15,['#3f6fb5','#f0c84a','#d94f5c','#8a4fa8','#3f8f5b','#d7d7e3'][i])
@tile('hearth')
def _(d,r):
    rect(d,0,0,16,16,'#62626e'); rect(d,1,1,15,4,'#8d8d99'); rect(d,3,5,13,16,'#191322'); rect(d,5,10,11,16,'#e58a3c'); rect(d,6,12,10,16,'#f0c84a'); rect(d,7,8,9,11,'#d94f5c')
@tile('exit_mat')
def _(d,r):
    TILES['floor'](d,r); rect(d,2,3,14,14,'#3f8f5b'); rect(d,3,4,13,13,'#58c98a'); rect(d,7,5,9,12,'#f6efe0'); rect(d,5,9,11,10,'#f6efe0'); rect(d,6,10,10,11,'#f6efe0')

INDEX={n:i for i,n in enumerate(ORDER)}
COLS=8

def tileset():
    rows=math.ceil(len(ORDER)/COLS)
    sheet=Image.new('RGBA',(COLS*T,rows*T),(0,0,0,0))
    for i,n in enumerate(ORDER):
        im=Image.new('RGBA',(T,T),(0,0,0,0)); r=random.Random(1000+i)
        TILES[n](im.load(),r)
        sheet.paste(im,((i%COLS)*T,(i//COLS)*T))
    return sheet

def panel(w,h,fill='#241a33',edge='#f0c84a',inner='#3a2a52'):
    "w,h in art pixels; drawn pixelated at 4x."
    im=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rectangle((2,0,w-3,h-1),fill=hexc(edge)); d.rectangle((0,2,w-1,h-3),fill=hexc(edge)); d.rectangle((1,1,w-2,h-2),fill=hexc(edge))
    d.rectangle((2,2,w-3,h-3),fill=hexc(inner)); d.rectangle((3,3,w-4,h-4),fill=hexc(fill))
    for x in (1,w-2):
        for y in (1,h-2): im.putpixel((x,y),hexc('#c9962e'))
    return im

def slash():
    "Three frames of a sword sweep around the hero, 32x32 each."
    sheet=Image.new('RGBA',(96,32),(0,0,0,0))
    for f in range(3):
        for y in range(32):
            for x in range(32):
                dx,dy=x-15.5,y-15.5; r=math.hypot(dx,dy); a=(math.atan2(dy,dx)+math.pi)/(2*math.pi)
                head=(f+1)/3.0
                trail=(head-a)
                if 12<=r<=15.5 and 0<=trail<0.45:
                    sheet.putpixel((96-96+x+f*32,y),hexc('#f6efe0' if trail<0.15 else '#a4efdb' if trail<0.3 else '#58c9b0'))
    return sheet

def scaled(im,w,h): return im.resize((w,h),Image.NEAREST)

# ---- sound
RATE=48000
def wav(path,samples,stereo=True):
    with wave.open(path,'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(RATE)
        data=bytearray()
        for s in samples:
            v=int(max(-1,min(1,s))*29000); data+=struct.pack('<hh',v,v)
        f.writeframes(bytes(data))
def square(ph,duty=.5): return 1.0 if (ph%1.0)<duty else -1.0
def tri(ph): p=ph%1.0; return 4*abs(p-.5)-1
def sweep(f0,f1,dur,wave_=square,vol=.3):
    n=int(RATE*dur); ph=0; out=[]
    for i in range(n):
        t=i/n; ph+=(f0+(f1-f0)*t)/RATE; out.append(wave_(ph)*vol*(1-t)**1.2)
    return out
def noise_burst(dur,vol=.3):
    r=random.Random(7); n=int(RATE*dur); out=[];hold=0
    for i in range(n):
        if i%12==0: hold=r.uniform(-1,1)
        out.append(hold*vol*(1-i/n)**2)
    return out
def notes(seq,dur,vol=.25,duty=.5):
    out=[]
    for f in seq:
        n=int(RATE*dur); ph=0
        for i in range(n):
            ph+=f/RATE; out.append(square(ph,duty)*vol*(1-i/n)**.7)
    return out
N={'C3':130.81,'E3':164.81,'F3':174.61,'G3':196.0,'A3':220.0,'B3':246.94,'C4':261.63,'D4':293.66,'E4':329.63,'F4':349.23,'G4':392.0,'A4':440.0,'B4':493.88,'C5':523.25,'D5':587.33,'E5':659.25,'G5':783.99,'R':0}
def music():
    # An original 8 bar loop in C major, 112 bpm eighth notes.
    mel="E4 G4 C5 G4 A4 G4 E4 D4 C4 E4 G4 E4 F4 E4 D4 R E4 G4 C5 D5 E5 D5 C5 A4 G4 A4 G4 E4 D4 E4 C4 R".split()
    mel2="C5 E5 D5 C5 A4 C5 G4 E4 F4 A4 G4 F4 E4 G4 C4 R D4 F4 A4 F4 G4 B4 D5 B4 C5 G4 E4 G4 C5 R C4 R".split()
    bass="C3 C3 G3 G3 A3 A3 E3 E3 F3 F3 C3 C3 F3 F3 G3 G3".split()
    step=60/112/2; n=int(RATE*step); seq=mel+mel2
    out=[0.0]*(n*len(seq))
    for s,name in enumerate(seq):
        f=N[name]; ph=0
        if not f: continue
        for i in range(n):
            ph+=f/RATE; out[s*n+i]+=square(ph,.25)*.13*(1-i/n)**.6
    for s,name in enumerate(bass*2):
        f=N[name]; ph=0
        for i in range(n*2):
            ph+=f/RATE; idx=s*2*n+i
            if idx<len(out): out[idx]+=tri(ph)*.22*(1-.5*i/(2*n))
    return out

def build(root):
    A=os.path.join(root,'assets'); os.makedirs(A,exist_ok=True); snd=os.path.join(A,'sounds'); os.makedirs(snd,exist_ok=True)
    tileset().save(f'{A}/tiles.png')
    person().save(f'{A}/hero.png')
    person({'t':'m','T':'M','h':'g','H':'w','p':'M','b':'y'}).save(f'{A}/mira.png')
    person({'t':'o','T':'R','h':'G','H':'g','p':'k','b':'B'}).save(f'{A}/tobin.png')
    slime().save(f'{A}/slime.png'); slash().save(f'{A}/slash.png')
    for k,v in ICONS.items(): art(v).save(f'{A}/{k}.png')
    Image.new('RGBA',(4,4),(0,0,0,0)).save(f'{A}/clear.png')
    panel(150,34).save(f'{A}/panel_hud.png'); panel(112,16).save(f'{A}/panel_quest.png')
    panel(440,62).save(f'{A}/panel_dialog.png'); panel(260,180).save(f'{A}/panel_bag.png')
    panel(179,14).save(f'{A}/panel_hint.png'); panel(24,24,fill='#3a2a52',edge='#6d5284',inner='#241a33').save(f'{A}/slot.png')
    wav(f'{snd}/hit.wav',[a+b for a,b in zip(sweep(520,160,.14),noise_burst(.14,.2))])
    wav(f'{snd}/hurt.wav',sweep(300,70,.22,vol=.35))
    wav(f'{snd}/pickup.wav',notes([N['E5'],N['G5']],.07))
    wav(f'{snd}/talk.wav',notes([N['A4']],.05,.16,.25))
    wav(f'{snd}/levelup.wav',notes([N['C4'],N['E4'],N['G4'],N['C5'],N['E5'],N['G5']],.09,.28))
    wav(f'{snd}/door.wav',sweep(180,320,.16,tri,.4))
    wav(f'{snd}/kill.wav',[a+b for a,b in zip(sweep(700,90,.28,vol=.28),noise_burst(.28,.16))])
    wav(f'{snd}/theme.wav',music())

def store_art(root):
    "icon0, pic0, pic1 for the console home screen, from the game's own art."
    sys_=os.path.join(root,'app0/sce_sys')
    ts=Image.open(os.path.join(root,'assets/tiles.png')); g=lambda n: ts.crop(((INDEX[n]%COLS)*T,(INDEX[n]//COLS)*T,(INDEX[n]%COLS+1)*T,(INDEX[n]//COLS+1)*T))
    W,H=240,135
    sc=Image.new('RGBA',(W,H),hexc('#6aa84f'))
    rng=random.Random(5)
    for y in range(0,H,T):
        for x in range(0,W,T): sc.paste(g('flowers' if rng.random()<.12 else 'grass'),(x,y))
    for x in range(0,W,T): sc.paste(g('path'),(x,96))
    for x in range(0,W,T):
        for y,n in ((0,'crown'),(T,'trunk')):
            c=g(n)
            if n=='crown': sc.paste(g('grass'),(x,y))
            sc.paste(c,(x,y),c)
    for cx in range(144,208,T):
        for r,n in ((3,'roof'),(4,'roof_edge'),(5,'wall')): sc.paste(g(n),(cx,r*T))
    sc.paste(g('door'),(176,5*T)); sc.paste(g('window'),(144,5*T))
    hero=Image.open(os.path.join(root,'assets/hero.png')).crop((0,0,T,T)); sl=Image.open(os.path.join(root,'assets/slime.png')).crop((0,0,T,T))
    b=scaled(hero,32,32); sc.paste(b,(54,76),b)
    for x,y in ((104,88),(128,104),(20,108)):
        s=scaled(sl,24,24); sc.paste(s,(x,y),s)
    full=scaled(sc,3840,2160).convert('RGB')
    full.save(f'{sys_}/pic0.png'); full.save(f'{sys_}/pic1.png')
    ic=sc.crop((24,48,24+96,48+96)).resize((512,512),Image.NEAREST).convert('RGB'); ic.save(f'{sys_}/icon0.png')

if __name__=='__main__':
    build(sys.argv[1])
