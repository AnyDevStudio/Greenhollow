# Greenhollow's painted 2.5D art: original, all made by this code. Ink outlines, muted dusk colors, fog and warm light.
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art2 as P

SS = 2          # sprites are drawn at twice their size and scaled down for clean edges
K = 3.75 * SS   # the person and icon drawings were laid out on a 32 cell grid
INK = '#14121f'
TX = 48         # ground texels per map cell

def rgb(s): return (int(s[1:3],16),int(s[3:5],16),int(s[5:7],16))
def smooth(v, ramp, d=0):
    n=len(ramp); t=np.clip(v,0,1)*(n-1); i=np.minimum(t.astype(int),n-2) if n>1 else np.zeros_like(t,dtype=int); f=(t-i)[...,None]
    return (ramp[i]*(1-f)+ramp[np.minimum(i+1,n-1)]*f).astype(np.uint8)

class Hi:
    "Runs art2's character and item drawings at high resolution with smooth shading instead of dithered pixels."
    names=('canvas','blob','bar','fill','px','outline','ground_shadow','shade')
    def __enter__(self):
        self.saved={n:getattr(P,n) for n in self.names}
        base_blob,base_bar,base_fill=self.saved['blob'],self.saved['bar'],self.saved['fill']
        P.canvas=lambda h,w: np.zeros((int(h*K),int(w*K),4),dtype=np.uint8)
        P.shade=smooth
        def blob(s,cx,cy,rx,ry,ramp,bias=0.0,d=0.7,alpha=255,keep=None,L=P.LIGHT):
            k=(lambda x,y: keep(x/K,y/K)) if keep else None
            base_blob(s,cx*K,cy*K,rx*K,ry*K,ramp,bias,0,alpha,k,L)
        def bar(s,x0,y0,x1,y1,ramp,vertical=True,bias=0.0,d=0.6,alpha=255): base_bar(s,x0*K,y0*K,x1*K,y1*K,ramp,vertical,bias,0,alpha)
        def fill(s,x0,y0,x1,y1,c,alpha=255): base_fill(s,x0*K,y0*K,x1*K,y1*K,c,alpha)
        def px(s,x,y,c,alpha=255): base_fill(s,x*K,y*K,(x+1)*K,(y+1)*K,c,alpha)
        def outline(s,c=INK): ink(s,int(K*.62),INK)
        def ground_shadow(s,cx,cy,rx,ry,alpha=95): pass
        P.blob,P.bar,P.fill,P.px,P.outline,P.ground_shadow=blob,bar,fill,px,outline,ground_shadow
        P.grid_xy_saved=P.grid_xy
        return self
    def __exit__(self,*a):
        for n,f in self.saved.items(): setattr(P,n,f)

def ink(s,r,c=INK):
    a=Image.fromarray((s[...,3]>70).astype(np.uint8)*255).filter(ImageFilter.MaxFilter(2*r+1)); e=(np.asarray(a)>0)&(s[...,3]<=70)
    s[e,:3]=rgb(c); s[e,3]=255
def down(s): return np.asarray(Image.fromarray(s,'RGBA').resize((s.shape[1]//SS,s.shape[0]//SS),Image.LANCZOS)).copy()
def save(a,p): Image.fromarray(a,'RGBA').save(p)

# Clothes and skin in a muted, inked palette
def retone():
    P.SKIN=P.R('#6e4a44','#a87a68','#d8ac90','#f0d0b4'); P.HAIR=P.R('#17121e','#2a1f2c','#46323a','#6d5048')
    P.TUNIC=P.R('#0f2a33','#17444a','#266a68','#4a9a8a','#8fcfb0'); P.PANTS=P.R('#14162a','#232742','#3a4066'); P.BOOT=P.R('#17101a','#31212a','#55393a')
    P.CAPE=P.R('#2c1230','#4c1c44','#7a2c58','#b04a70'); P.ROBE=P.R('#1c1838','#322a5c','#51458a','#7f6fb8','#b0a4dc'); P.SILVER=P.R('#44465e','#7c7f98','#b8bccb','#eef0f5')
    P.APRON=P.R('#8a8578','#c0b8a4','#eae2cc'); P.ORANGE=P.R('#3f1c1a','#7a3620','#b85f2c','#e09a50'); P.DARK=P.R('#12101c','#23202f','#3a3648')
    P.SLIME=P.R('#113a4a','#1a6a78','#2fa49c','#74dcc0','#c8fff0','#ffffff'); P.METAL=P.R('#54381a','#94682a','#d8ac48','#fff0b0')

def person_sheet(style):
    fw,fh=120,160
    out=np.zeros((fh*3,fw*4,4),dtype=np.uint8)
    for r,(d,legs) in enumerate((('down',(0,1,0,-1)),('up',(0,-1,0,1)),('side',(0,1,0,-1)))):
        for c,l in enumerate(legs):
            with Hi(): f=P.person(style,d,l,1 if l else 0)
            f=down(f); P.over(out,f,c*fw,r*fh+40)
    return out
def npc_sheet(style):
    out=np.zeros((160,240,4),dtype=np.uint8)
    for i,b in enumerate((0,1)):
        with Hi(): f=P.person(style,'down',0,b)
        P.over(out,down(f),i*120,40)
    return out
def slime_sheet():
    out=np.zeros((120,360,4),dtype=np.uint8)
    for i,a in enumerate(((12,10,18),(10,12,16),(14,7.5,20))):
        with Hi(): f=P.slime_frame(*a)
        P.over(out,down(f),i*120,0)
    return out
def heart():
    S=240; s=np.zeros((S,S,4),dtype=np.uint8); Y,X=np.mgrid[0:S,0:S]; x=(X-S/2)/(S*.42); y=(S*.48-Y)/(S*.42)
    q=(x*x+y*y-1)**3-x*x*y*y*y<=0; v=np.clip(.72-x*.3+y*.32,0,1); c=smooth(v,P.R('#3a0f24','#8a2238','#c8404e','#ee7a70')); s[q,:3]=c[q]; s[q,3]=255
    h=((X-S*.33)/(S*.08))**2+((Y-S*.3)/(S*.055))**2<=1; s[h&q,:3]=(255,232,226); ink(s,8)
    return np.asarray(Image.fromarray(s,'RGBA').resize((120,120),Image.LANCZOS)).copy()
def icon(n):
    if n=='heart': return heart()
    with Hi(): f=P.icon(n)
    return down(f)

# ---- trees, houses and the rest of what stands in the world
def fbm(h,w,c,s,o=4): return P.fbm(h,w,c,s,o)
LEAF=P.R('#0d2430','#143a3e','#1f5a4a','#3a7f58','#6aa864','#a8cf7e'); DARKLEAF=P.R('#081a26','#0e2a34','#163f42','#245c50','#3f8060','#74a86e')
BARK=P.R('#120e18','#2a1e26','#4a3433','#6f5244')
def tree(seed,leaf):
    r=random.Random(seed); W,H=340*SS,460*SS; c=np.zeros((H,W,4),dtype=np.uint8)
    # trunk, tapering, with two limbs
    t=Image.new('L',(W,H),0); d=ImageDraw.Draw(t); cx=W/2; base=H-14*SS; hw=(22+r.randint(-3,5))*SS
    d.polygon([(cx-hw*1.5,base),(cx-hw*.55,base-200*SS),(cx+hw*.55,base-200*SS),(cx+hw*1.5,base)],fill=255)
    for sgn,ty in ((-1,150),(1,190)):
        d.line([(cx,base-ty*SS),(cx+sgn*90*SS,base-(ty+110)*SS)],fill=255,width=16*SS)
    m=np.asarray(t)>0; yy,xx=np.mgrid[0:H,0:W]; v=.5-(xx-cx)/(hw*3.4)+(fbm(H,W,14*SS,seed+3,3)-.5)*.5
    col=smooth(v,BARK); c[m,:3]=col[m]; c[m,3]=255
    ccy=base-(285+r.randint(-14,14))*SS; rx=(116+r.randint(-10,10))*SS; ry=(104+r.randint(-10,10))*SS
    clusters=[]
    for _ in range(190):
        a=r.uniform(0,2*math.pi); q=math.sqrt(r.random()); clusters.append((cx+math.cos(a)*q*rx,ccy+math.sin(a)*q*ry,r.uniform(26,48)*SS))
    clusters.sort(key=lambda p:p[1]-p[0]*.35)
    L=np.array([-.5,-.68,.53])
    for x,y,rad in clusters:
        x0,x1=max(int(x-rad),0),min(int(x+rad)+1,W); y0,y1=max(int(y-rad),0),min(int(y+rad)+1,H)
        Y,X=np.mgrid[y0:y1,x0:x1]; nx=(X-x)/rad; ny=(Y-y)/(rad*.9); q=nx*nx+ny*ny; ins=q<=1
        nz=np.sqrt(np.clip(1-q,0,1)); l=np.clip(nx*L[0]+ny*L[1]+nz*L[2],0,1)
        lit=-(y-ccy)/ry*.26-(x-cx)/rx*.14
        v=np.clip(.1+.74*l+lit,0,1); col=smooth(v,leaf); s=c[y0:y1,x0:x1]; s[ins,:3]=col[ins]; s[ins,3]=255
    n=fbm(H,W,5*SS,seed+7,2); leafy=(c[...,3]>0)&(yy<base-180*SS); c[leafy,:3]=np.clip(c[leafy,:3]*(0.86+.3*n[leafy,None]),0,255).astype(np.uint8)
    ink(c,3*SS)
    return down(c)
def tree_sheet(leaf,seed):
    out=np.zeros((460,340*4,4),dtype=np.uint8)
    for i in range(4): P.over(out,tree(seed+i,leaf),i*340,0)
    return out

def poly(s,pts,fn):
    m=Image.new('L',(s.shape[1],s.shape[0]),0); ImageDraw.Draw(m).polygon(pts,fill=255); m=np.asarray(m)>0
    col=fn(); s[m,:3]=col[m]; s[m,3]=255; return m
def rect(s,x0,y0,x1,y1,col,a=255):
    s[int(y0):int(y1),int(x0):int(x1),:3]=rgb(col); s[int(y0):int(y1),int(x0):int(x1),3]=a
def glow(s,cx,cy,r,col=(255,190,110),amt=.8):
    Y,X=np.mgrid[0:s.shape[0],0:s.shape[1]]; d=np.clip(1-np.hypot(X-cx,Y-cy)/r,0,1)**2*amt
    a=s[...,3]/255; na=np.maximum(a,d)
    s[...,:3]=np.clip(s[...,:3]*(1-d[...,None]*.55)+np.array(col)*d[...,None]*.55+ (s[...,:3]==0)*np.array(col)*d[...,None],0,255).astype(np.uint8); s[...,3]=(na*255).astype(np.uint8)
def house(w,seed,roof):
    "A front view with its roof sloping up and back. w is in map cells; one cell is 64 pixels."
    W,H=w*64,400; s=np.zeros((H,W,4),dtype=np.uint8); r=random.Random(seed); n=fbm(H,W,10,seed); wy=256; Y,X=np.mgrid[0:H,0:W]
    def tiles():
        V=np.zeros((H,W))
        for row in range(10,wy,17):
            off=0 if ((row-10)//17)%2 else 15
            for x in range(-off,W,30):
                V[row:row+17,max(x,0):max(x+29,0)]=.52+r.uniform(-.12,.13)+.2*(1-row/wy)*.5
            V[row+15:row+17,:]=.08
        V+=(n-.5)*.22-(X/W)*.12
        return smooth(V,roof)
    poly(s,[(0,wy+12),(36,0),(W-36,0),(W,wy+12)],tiles)
    rect(s,0,wy+2,W,wy+12,'#14121f')
    wn=fbm(H,W,16,seed+4); plaster=P.R('#5a5b6a','#8d8a86','#c2b89e','#ece0c2')
    v=.68+(wn-.5)*.32-(Y-wy)/190*.34-(X/W)*.12; c=smooth(v,plaster); b=(Y>=wy+12)&(Y<H-18); s[b,:3]=c[b]; s[b,3]=255
    s[(Y>=wy+12)&(Y<wy+34),:3]=(s[(Y>=wy+12)&(Y<wy+34),:3]*.58).astype(np.uint8)
    T=P.R('#120e18','#2a1e26','#4a3433','#6f5244')
    for x in list(range(0,W-1,128))+[W-14]:
        c=smooth(np.tile((1-np.abs(np.linspace(-1,1,14)))[None,:]*.75+.1,(H-18-wy-12,1)),T); s[wy+12:H-18,x:x+14,:3]=c; s[wy+12:H-18,x:x+14,3]=255
    c=smooth(np.tile((1-np.abs(np.linspace(-1,1,12)))[:,None]*.75+.1,(1,W)),T); s[wy+70:wy+82,:,:3]=c; s[wy+70:wy+82,:,3]=255
    st=P.R('#2a2a3c','#50506a','#8a8aa0'); v=.55+(fbm(H,W,6,seed+8)-.5)*.8; c=smooth(v,st); b=Y>=H-18; s[b,:3]=c[b]; s[b,3]=255
    for x in range(0,W,26): rect(s,x,H-18,x+2,H,INK)
    def win(x):
        wy2=wy+26; rect(s,x-7,wy2-7,x+51,wy2+51,'#14121f'); g=P.R('#7a4a22','#d8902e','#ffd27a','#fff4c8'); Yy,Xx=np.mgrid[0:44,0:44]
        s[wy2:wy2+44,x:x+44,:3]=smooth(np.clip(.95-np.hypot(Xx-22,Yy-36)/62,0,1),g); s[wy2:wy2+44,x:x+44,3]=255; rect(s,x+20,wy2,x+24,wy2+44,'#14121f'); rect(s,x,wy2+20,x+44,wy2+24,'#14121f')
    wx=[64+10, W-64*2+10]
    for x in wx: win(x)
    dx=(w//2)*64+6; rect(s,dx-7,H-112,dx+59,H,INK); D=P.R('#20161c','#3f2a2a','#65443a'); 
    s[H-105:H,dx:dx+52,:3]=smooth(np.tile(np.linspace(.75,.25,52)[None,:],(105,1)),D); s[H-105:H,dx:dx+52,3]=255
    for x in (dx+17,dx+34): rect(s,x,H-105,x+2,H,INK)
    rect(s,dx+42,H-58,dx+48,H-50,'#e8b040')
    cw=W-112; rect(s,cw-3,0,cw+37,74,INK); st2=P.R('#2a2a3c','#50506a','#9090a8'); s[3:74,cw:cw+34,:3]=smooth(np.tile(np.linspace(.8,.25,34)[None,:],(71,1))+(fbm(71,34,5,seed+9)-.5)*.3,st2); s[3:74,cw:cw+34,3]=255
    for x in wx: glow(s,x+22,wy+50,120,amt=.34)
    ink(s,2)
    return s
def fence_run(cells_):
    W,H=cells_*64,110; s=np.zeros((H,W,4),dtype=np.uint8); F=P.R('#17121e','#3a2a30','#6a4e42','#a08060')
    for y in (42,72):
        s[y:y+11,:,:3]=smooth(np.tile((1-np.abs(np.linspace(-1,1,11)))[:,None]*.8+.1,(1,W)),F); s[y:y+11,:,3]=255
    for x in range(10,W,64):
        s[6:H-2,x:x+18,:3]=smooth(np.tile((1-np.abs(np.linspace(-1,1,18)))[None,:]*.85+.1,(H-8,1)),F); s[6:H-2,x:x+18,3]=255
    ink(s,2); return s
def well_img():
    W,H=170,210; s=np.zeros((H,W,4),dtype=np.uint8); St=P.R('#1f2030','#4a4a62','#8c8ca4')
    Y,X=np.mgrid[0:H,0:W]; q=((X-85)/72)**2+((Y-160)/42)**2<=1; v=.65-(X-85)/190-(Y-150)/130+(fbm(H,W,8,3)-.5)*.5; c=smooth(v,St); s[q,:3]=c[q]; s[q,3]=255
    w=((X-85)/54)**2+((Y-150)/20)**2<=1; s[w,:3]=(18,40,70); F=P.R('#17121e','#4a3433','#7a5a48')
    for x in (20,136):
        s[34:158,x:x+14,:3]=smooth(np.tile((1-np.abs(np.linspace(-1,1,14)))[None,:]*.85+.1,(124,1)),F); s[34:158,x:x+14,3]=255
    poly(s,[(4,46),(30,4),(140,4),(166,46)],lambda:smooth(.62-X/360-(Y)/200+(fbm(H,W,7,6)-.5)*.4,P.R('#1c2240','#30406c','#5a70a0')))
    ink(s,2); return s
def sign_img():
    W,H=130,150; s=np.zeros((H,W,4),dtype=np.uint8); F=P.R('#17121e','#4a3433','#7a5a48','#b0946e'); Y,X=np.mgrid[0:H,0:W]
    s[58:H-2,56:74,:3]=smooth(np.tile((1-np.abs(np.linspace(-1,1,18)))[None,:]*.85+.1,(H-60,1)),F); s[58:H-2,56:74,3]=255
    poly(s,[(8,14),(112,8),(122,36),(112,68),(8,62)],lambda:smooth(.75-(X/230)-(Y/300)+(fbm(H,W,7,9)-.5)*.3,F)); rect(s,24,28,92,32,'#17121e'); rect(s,24,42,74,46,'#17121e'); ink(s,2); return s
def table_img():
    W,H=138,90; s=np.zeros((H,W,4),dtype=np.uint8); F=P.R('#17121e','#4a3433','#7f5e48','#b49470'); Y,X=np.mgrid[0:H,0:W]
    poly(s,[(0,44),(18,18),(120,18),(138,44),(138,54),(0,54)],lambda:smooth(.9-Y/70+(fbm(H,W,8,4)-.5)*.3,F))
    for x in (8,118): s[54:H-2,x:x+12,:3]=smooth(np.tile(np.linspace(.8,.2,12)[None,:],(H-56,1)),F); s[54:H-2,x:x+12,3]=255
    ink(s,2); return s
def wall_img(cols):
    W,H=cols*64,300; s=np.zeros((H,W,4),dtype=np.uint8); Y,X=np.mgrid[0:H,0:W]; W_=P.R('#17182c','#2a2c4a','#4a4a6e','#7070a0')
    c=smooth(.62-(Y/H)*.42+(fbm(H,W,18,3)-.5)*.35,W_); s[...,:3]=c; s[...,3]=255
    for x in range(0,W,96): rect(s,x,0,x+10,H,'#17121e')
    rect(s,0,H-34,W,H,'#2a1e26'); rect(s,0,H-36,W,H-32,'#14121f'); rect(s,0,70,W,80,'#17121e')
    r=random.Random(7)
    for c0 in (4,5):
        sx=c0*64; rect(s,sx-4,84,sx+64,H-34,'#17121e')
        for row in (94,178):
            rect(s,sx+2,row,sx+60,row+72,'#0c0a12'); x=sx+4
            while x<sx+56:
                wd=r.randint(6,11); hh=r.randint(48,68); cl=r.choice(['#7a3048','#2f6a5c','#b08a34','#34507e','#5e3a84','#a35a2c']); rect(s,x,row+72-hh,x+wd,row+72,cl); x+=wd+2
    hx=10*64; St=P.R('#17121e','#44445a','#8a8aa0'); s[60:H,hx-22:hx+86,:3]=smooth(.6-(X[60:H,hx-22:hx+86]-hx)/220+(fbm(H-60,108,8,5)-.5)*.5,St); s[60:H,hx-22:hx+86,3]=255; rect(s,hx-2,150,hx+66,H-2,'#0a0810')
    # window with a moonlit night
    wx=7*64; rect(s,wx-8,92,wx+96,216,'#17121e'); g=P.R('#1a2a56','#2f4e8e','#6f94cc'); s[100:208,wx:wx+88,:3]=smooth(np.tile(np.linspace(.9,.2,108)[:,None],(1,88)),g); s[100:208,wx:wx+88,3]=255; rect(s,wx+42,100,wx+46,208,'#17121e'); rect(s,wx,152,wx+88,156,'#17121e')
    glow(s,hx+32,230,300,amt=.5)
    return s
def fire_sheet():
    out=np.zeros((110,330,4),dtype=np.uint8); F=P.R('#8f2a14','#e0641e','#ffb030','#fff0b0')
    for f in range(3):
        c=np.zeros((110*SS,110*SS,4),dtype=np.uint8); Y,X=np.mgrid[0:110*SS,0:110*SS]
        for i,(dx,hh,wd) in enumerate(((-22,44,17),(0,70,23),(22,38,15))):
            hh2=(hh+[0,9,-6][(f+i)%3])*SS; cx=(55+dx)*SS; base=108*SS; t=np.clip((base-Y)/hh2,0,1); w=wd*SS*(1-t)**.6*(1+.2*np.sin(t*7+f*2))+.01
            m=(np.abs(X-cx)<w)&(Y<base)&(Y>base-hh2); v=(1-np.abs(X-cx)/np.maximum(w,1))*.8+(1-t)*.3; col=smooth(v,F); c[m,:3]=col[m]; c[m,3]=255
        P.over(out,down(c),f*110,0)
    return out

# ---- the ground each scene is painted on, seen from straight above; the camera leans it
GR=P.R('#16343a','#1f4c46','#2f6a4c','#4c8a54','#7fae62'); DIRT2=P.R('#2c2830','#544640','#83705a','#b39c7a','#d8c49a'); WT=P.R('#0c2448','#143a68','#205c8c','#3e8cb0','#8ccacc')
FO=P.R('#0a1f2a','#102e36','#18423f','#27594a','#3f7458'); FD=P.R('#141820','#262a30','#3f3f40','#5a5850')
def brush(h,w,seed,n,minr=4,maxr=11):
    r=np.random.RandomState(seed); F=Image.new('L',(w,h),128); d=ImageDraw.Draw(F)
    for x,y,rad,v in zip(r.randint(0,w,n),r.randint(0,h,n),r.randint(minr,maxr,n),r.randint(70,186,n)):
        d.ellipse((x-rad,y-rad*.6,x+rad,y+rad*.6),fill=int(v))
    return np.asarray(F.filter(ImageFilter.GaussianBlur(1.2)),dtype=float)/255-.5
def cells(g,want): return np.kron(np.array([[1.0 if v in want else 0.0 for v in row] for row in g]),np.ones((TX,TX)))
def organic(m,seed,r=8,amp=.4):
    b=P.blur(m,r); return b+(fbm(m.shape[0],m.shape[1],26,seed)-.5)*amp>.5
def cast(S,cx,cy,rx,ry):
    P.ell(S,cx+rx*.5,cy+ry*.2,rx,ry)
def darken(g,S,amt=.6,tint=(10,14,40)):
    q=np.clip(S,0,1)[...,None]*amt; g[...,:3]=(g[...,:3]*(1-q)+np.array(tint)*q*.7).astype(np.uint8)
def fade(G):
    "Melts the edges of the painted ground into the dim land around the map."
    h,w=G.shape[:2]; a=np.minimum.reduce([np.arange(w)[None,:]/TX*np.ones((h,w)),(w-1-np.arange(w))[None,:]/TX*np.ones((h,w)),np.arange(h)[:,None]/TX*np.ones((h,w))])
    G[...,3]=(np.clip(a,0,1)*255).astype(np.uint8)
def ground_village(root,g,o,W,H,I,houses):
    h,w=H*TX,W*TX
    v=.5+(fbm(h,w,70,1)-.5)*.75+brush(h,w,2,20000)*.5; c=smooth(v,GR); G=np.dstack([c,np.full((h,w),255,np.uint8)])
    p=organic(cells(g,{I['path'],I['mat']}),5); e=P.blur(p.astype(float),6)
    pv=.56+(fbm(h,w,12,6)-.5)*.5+brush(h,w,16,9000,2,6)*.32-np.clip(.72-e,0,1)*.7; c=smooth(pv,DIRT2); G[p,:3]=c[p]
    so=cells(g,{I['soil']})>0; c=smooth(.42+.28*np.sin(np.arange(h)/4.5)[:,None]+(fbm(h,w,9,8)-.5)*.4,P.R('#1a1418','#3a2a2a','#5a4238')); G[so,:3]=c[so]
    wm=cells(g,{I['water']}); wo=organic(wm,9,12,.3); sh=organic(np.clip(P.blur(wm,14)*2.2,0,1),10,4,.25)&~wo; c=smooth(.5+(fbm(h,w,8,11)-.5)*.7,P.R('#3a3a40','#7a705e','#b0a080')); G[sh,:3]=c[sh]
    d=P.blur(wo.astype(float),20); wv=1-np.clip((d-.42)/.55,0,1)+(fbm(h,w,20,13)-.5)*.2; c=smooth(wv,WT); G[wo,:3]=c[wo]
    r=random.Random(77); S=np.zeros((h,w)); FL=['#d8d0e0','#e6c070','#d090b0','#9cb0e8']
    for y in range(H):
        for x in range(W):
            if g[y][x]==I['soil']:
                cx,cy=x*TX+TX/2,y*TX+TX*.6; Y,X=np.mgrid[int(cy-14):int(cy+14),int(cx-16):int(cx+16)]; q=((X-cx)/15)**2+((Y-cy)/12)**2<=1; G[int(cy-14):int(cy+14),int(cx-16):int(cx+16)][q,:3]=smooth(np.clip(.8-(Y-cy+14)/40-(X-cx+16)/90+(fbm(28,32,5,x+y,2)-.5)*.5,0,1),P.R('#123a30','#2a6a44','#62a05a','#a4d07a'))[q]
            elif o[y][x]==-1 and g[y][x] in (I['grass'],I['flowers']):
                for _ in range(6 if g[y][x]==I['flowers'] else 0):
                    a,b=x*TX+r.randint(4,TX-5),y*TX+r.randint(4,TX-5); P.ell_c=None; col=rgb(r.choice(FL)); G[b-2:b+2,a-2:a+2,:3]=col
    P.fill(G,11*TX+6,8*TX+9,11*TX+42,8*TX+40,'#2a1826'); G[8*TX+13:8*TX+36,11*TX+10:11*TX+38,:3]=rgb('#7a3a54')
    for c0,r0,hw,_ in houses: S[(r0+4)*TX:(r0+5)*TX+22,c0*TX+6:(c0+hw)*TX+34]=1
    for y in range(H):
        for x in range(W):
            n=o[y][x]; a,b=x*TX,y*TX
            if n==I['trunk']: cast(S,a+TX/2,b+TX,70,26)
            elif n==I['fence']: S[b+36:b+44,a:a+TX]=np.maximum(S[b+36:b+44,a:a+TX],.8)
            elif n==I['well']: cast(S,a+TX/2,b+TX,34,16)
            elif n==I['sign']: cast(S,a+TX/2,b+TX,20,8)
    darken(G,P.blur(S,5))
    fade(G); A=f'{root}/assets'; save(G,f'{A}/village_ground.png')
    return wo
def shimmer(root,wo,pond):
    c0,r0,cw,ch=pond; fh,fw=ch*TX,cw*TX; m=wo[r0*TX:(r0+ch)*TX,c0*TX:(c0+cw)*TX]; sh=np.zeros((fh,fw*4,4),dtype=np.uint8)
    for f in range(4):
        n=np.asarray(Image.fromarray((P.noise(fh//3+1,fw//12+2,1,40+f)*255).astype(np.uint8)).resize((fw,fh),Image.BILINEAR),dtype=float)/255
        a=np.clip((n-.72)/.14,0,1)*(P.noise(fh,fw,26,60+f)>.42)*m; fr=sh[0:fh,f*fw:(f+1)*fw]; fr[...,:3]=(214,240,240); fr[...,3]=(a*120).astype(np.uint8)
    save(sh,f'{root}/assets/shimmer.png')
def ground_forest(root,g,o,W,H,I):
    h,w=H*TX,W*TX; v=.5+(fbm(h,w,60,21)-.5)*.85+brush(h,w,22,22000)*.5; c=smooth(v,FO); G=np.dstack([c,np.full((h,w),255,np.uint8)])
    p=organic(cells(g,{I['forest_path']}),25,8,.55); pv=.55+(fbm(h,w,14,26)-.5)*.7+brush(h,w,27,8000,2,6)*.3-np.clip(.72-P.blur(p.astype(float),6),0,1)*.75; c=smooth(pv,FD); G[p,:3]=c[p]
    r=random.Random(31); S=np.zeros((h,w))
    for _ in range(2200):
        x,y=r.randrange(w-3),r.randrange(h-3); G[y:y+3,x:x+3,:3]=rgb(r.choice(['#6e5a2c','#4e5a2c','#3f4a30','#8a6a30']))
    Cap=P.R('#4a1c2e','#8a2c3e','#c8505c','#ecc0a8')
    for y in range(H):
        for x in range(W):
            a,b=x*TX,y*TX
            if g[y][x]==I['mushroom'] and o[y][x]==-1:
                for k in range(r.randint(1,3)):
                    cx,cy=a+r.randint(8,TX-8),b+r.randint(10,TX-6); Y,X=np.mgrid[cy-10:cy+3,cx-11:cx+11]; q=((X-cx)/10.5)**2+((Y-cy)/9)**2<=1; c=smooth(np.clip(.9-(Y-cy+10)/20-(X-cx+11)/50,0,1),Cap); G[cy-10:cy+3,cx-11:cx+11][q,:3]=c[q]; G[cy+3:cy+8,cx-2:cx+3,:3]=(216,208,190)
            n=o[y][x]
            if n==I['forest_trunk']: cast(S,a+TX/2,b+TX,76,28)
            elif n==I['rock']: cast(S,a+TX/2,b+TX,26,10)
    darken(G,P.blur(S,6),.7,(4,12,26))
    fade(G); save(G,f'{root}/assets/forest_ground.png')
def ground_house(root,g,o,W,H,I):
    h,w=H*TX,W*TX; G=np.zeros((h,w,4),dtype=np.uint8); G[...,:3]=(10,8,14); G[...,3]=255; fl=cells(g,{I['floor'],I['rug'],I['exit_mat']})>0; r=np.random.RandomState(5); V=np.full((h,w),.5)
    for y in range(0,h,18):
        V[y:y+18]+=r.uniform(-.09,.09); V[y+16:y+18]=.1
        for x in range(r.randint(0,90),w,120): V[y:y+16,x:x+2]=.12
    grain=np.asarray(Image.fromarray((P.noise(h//3+1,w//50+2,1,7)*255).astype(np.uint8)).resize((w,h),Image.BILINEAR),dtype=float)/255; V+=(grain-.5)*.3
    c=smooth(V,P.R('#1f1820','#4a3430','#7a5a44','#a88462')); G[fl,:3]=c[fl]
    Y,X=np.mgrid[0:h,0:w]; x0,y0,x1,y1=13*TX,9*TX,18*TX,11*TX; m=(X>=x0)&(X<x1)&(Y>=y0)&(Y<y1); v=.45+(((X-x0)%28<14)^((Y-y0)%28<14))*.3+(P.noise(h,w,4,9)-.5)*.2; c=smooth(v,P.R('#2c1230','#5a1c3e','#8a3050','#b85a70')); G[m,:3]=c[m]
    b=m&~((X>=x0+12)&(X<x1-12)&(Y>=y0+12)&(Y<y1-12)); G[b,:3]=rgb('#c8a050'); bb=m&~((X>=x0+5)&(X<x1-5)&(Y>=y0+5)&(Y<y1-5)); G[bb,:3]=rgb('#2c1230')
    # the bed lies flat, so it is painted on the floor
    bx,by=10*TX,4*TX; G[by+3:by+2*TX-3,bx+2:bx+TX-2,:3]=rgb('#14121f'); G[by+6:by+2*TX-6,bx+5:bx+TX-5,:3]=smooth(np.tile(np.linspace(.85,.25,TX-10)[None,:],(2*TX-12,1)),P.R('#14224a','#26468a','#5a80c8')); G[by+8:by+30,bx+8:bx+TX-8,:3]=rgb('#dcd8cc')
    for c0 in (15,16):
        G[14*TX+6:14*TX+42,c0*TX+4:c0*TX+44,:3]=rgb('#1f4a44'); G[14*TX+10:14*TX+38,c0*TX+8:c0*TX+40,:3]=rgb('#3f8a72')
        x=c0*TX+24; G[14*TX+14:14*TX+30,x-2:x+2,:3]=rgb('#eae2cc')
        for k in range(7): G[14*TX+26+k:14*TX+27+k,x-8+k:x+8-k,:3]=rgb('#eae2cc')
    side=np.zeros((h,w)); side[:,8*TX:9*TX+6]=1; side[:,22*TX-6:23*TX]=1; side[3*TX:4*TX+16,:]=1; darken(G,P.blur(side,10),.55,(6,4,18))
    save(G,f'{root}/assets/house_ground.png')

def backdrop(kind):
    h,w=540,960; Y,X=np.mgrid[0:h,0:w]; s=np.zeros((h,w,4),dtype=np.uint8); s[...,3]=255
    if kind=='house': s[...,:3]=(10,8,14); return s
    sky=P.R('#0d1636','#1f2a58','#46467a','#8a6c8a','#d89a78') if kind=='village' else P.R('#050c18','#0a1a2a','#10303a','#1f5048')
    s[...,:3]=smooth(np.clip(Y/360,0,1),sky)
    r=random.Random(3)
    for layer,(base,amp,col,seed) in enumerate(((250,40,'#24305a',1),(292,30,'#18244a',2),(330,18,'#101a38',3)) if kind=='village' else ((210,30,'#0c2630',4),(270,24,'#0a1e28',5),(320,16,'#07161e',6))):
        n=fbm(1,w,110,seed,3)[0]; top=(base+(n-.5)*amp*3).astype(int); m=Y>=top[X]; s[m,:3]=rgb(col)
    if kind=='forest':
        for _ in range(26):
            x=r.randrange(w); wd=r.randint(10,34); s[0:h,x:x+wd,:3]=(s[0:h,x:x+wd,:3]*.55+np.array(rgb('#07141c'))*.45).astype(np.uint8)
    return s
def light(kind):
    h,w=540,960; Y,X=np.mgrid[0:h,0:w]; a=np.zeros((h,w,4),dtype=float); vig=np.clip(np.hypot((X-480)/620,(Y-270)/380)-.5,0,1)*1.6
    fog=np.clip(1-Y/250,0,1)**1.4
    if kind=='village':
        warm=np.clip(1-np.hypot((X+80)/800,(Y+120)/620),0,1)*.3; cool=vig*.5+fog*.55; wc,cc=[255,204,150],[60,62,120]
    elif kind=='forest':
        sh=np.clip(np.sin((X+Y*.62)/52+1.2*np.sin(Y/140))-.42,0,1)*1.7*np.clip(1-Y/600,.12,1); warm=sh*.26; cool=(.2+vig*.55+fog*.72)*(1-sh*.5); wc,cc=[206,240,190],[12,44,58]
    else:
        fire=np.clip(1-np.hypot((X-640)/430,(Y-210)/340),0,1); warm=fire*.34; cool=(.16+vig*.6)*np.clip(1.25-fire*1.5,0,1); wc,cc=[255,158,74],[14,10,38]
    alpha=1-(1-warm)*(1-cool); mix=(warm/np.maximum(warm+cool,1e-4))[...,None]
    a[...,:3]=np.array(wc)*mix+np.array(cc)*(1-mix); a[...,3]=np.clip(alpha,0,1)*255
    return a.astype(np.uint8)

def build(root):
    retone(); A=f'{root}/assets'; os.makedirs(A,exist_ok=True)
    save(person_sheet('hero'),f'{A}/hero.png'); save(npc_sheet('mira'),f'{A}/mira.png'); save(npc_sheet('tobin'),f'{A}/tobin.png'); save(slime_sheet(),f'{A}/slime.png')
    for n in ('jelly','potion','coin','heart'): save(icon(n),f'{A}/{n}.png')
    save(tree_sheet(LEAF,301),f'{A}/trees.png'); save(tree_sheet(DARKLEAF,401),f'{A}/dark_trees.png')
    save(house(7,50,P.R('#2c1626','#6e2c30','#a84a3c','#d8805a')),f'{A}/house_a.png'); save(house(6,79,P.R('#101a3a','#24386a','#3f6496','#7ca0c8')),f'{A}/house_b.png')
    save(fence_run(9),f'{A}/fence_long.png'); save(fence_run(1),f'{A}/fence_short.png'); save(well_img(),f'{A}/well.png'); save(sign_img(),f'{A}/sign.png'); save(table_img(),f'{A}/table.png'); save(wall_img(15),f'{A}/back_wall.png'); save(fire_sheet(),f'{A}/fire.png')
    rock=np.zeros((96*SS,120*SS,4),dtype=np.uint8); P.blob(rock,60*SS,58*SS,54*SS,36*SS,P.R('#1a1a28','#44445a','#7c7c90','#b0b0bc'),d=0) if False else None
    with Hi(): P.blob(rockc:=P.canvas(32,32),16,20,13,10,P.R('#1a1a28','#44445a','#7c7c90','#b0b0bc')); P.blob(rockc,12,15,6.5,4.8,P.R('#1a1a28','#44445a','#7c7c90','#c4c4d0'),bias=.2); P.outline(rockc)
    save(down(rockc),f'{A}/rock.png')
    for k in ('village','forest','house'): save(backdrop(k),f'{A}/backdrop_{k}.png'); save(light(k),f'{A}/light_{k}.png')
    from PIL import Image as _I
    save(P.slash(),f'{A}/slash.png'); save(P.slot(),f'{A}/slot.png')
    for n,(w,h) in dict(panel_hud=(300,68),panel_quest=(224,32),panel_hint=(358,28),panel_dialog=(880,124),panel_bag=(520,360)).items(): save(P.panel(w,h),f'{A}/{n}.png')
    for name,ramp,seed in (('outer_village',GR,5),('outer_forest',FO,6)):
        v=.3+(P.fbm(128,256,40,seed,3)-.5)*.5; save(np.dstack([smooth(v,ramp),np.full((128,256),255,np.uint8)]),f'{A}/{name}.png')
    save(np.zeros((4,4,4),dtype=np.uint8),f'{A}/clear.png'); save(np.zeros((16,16,4),dtype=np.uint8),f'{A}/collision.png')
