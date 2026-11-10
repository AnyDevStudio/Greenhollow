# Greenhollow's ink-and-gouache art: original, drawn by this code the way a hand would.
# Every shape is a wobbling curve, every outline a brush line that swells and thins, every color a flat coat of paint.
import math, os, random, sys, zlib
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art2 as P
import art3 as B

SS = 3
TX = B.TX
INK = '#1c1512'

def rgb(s): return (int(s[1:3],16),int(s[3:5],16),int(s[5:7],16))
def save(a,p): Image.fromarray(a,'RGBA').save(p)

# ---- pen and brush
def spline(pts, closed=True, step=3.0):
    "A Catmull-Rom curve through the points, sampled every few pixels."
    p=[np.array(q,float) for q in pts]; n=len(p); out=[]
    last=n if closed else n-1
    for i in range(last):
        a=p[(i-1)%n] if closed or i>0 else p[i]; b=p[i]; c=p[(i+1)%n]; d=p[(i+2)%n] if closed or i+2<n else c
        k=max(int(np.hypot(*(c-b))/step),2)
        for t in np.linspace(0,1,k,endpoint=False):
            out.append(.5*((2*b)+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(3*b-a-3*c+d)*t*t*t))
    if not closed: out.append(p[-1])
    return np.array(out)
def noise1(n,knots,seed,closed=False):
    r=np.random.RandomState(seed&0x7fffffff); k=max(knots,2); v=r.uniform(-1,1,k+1)
    if closed: v[-1]=v[0]
    x=np.linspace(0,k,n,endpoint=not closed); i=np.minimum(x.astype(int),k-1); f=x-i; f=f*f*(3-2*f)
    return v[i]*(1-f)+v[i+1]*f
def normals(p,closed):
    d=np.roll(p,-1,0)-np.roll(p,1,0) if closed else np.gradient(p,axis=0)
    l=np.maximum(np.hypot(d[:,0],d[:,1]),1e-6); return np.stack([-d[:,1]/l,d[:,0]/l],1)
def wobble(p,amp,seed,closed=True,every=34.0):
    "Shakes a curve a little, the way no ruler would."
    n=len(p); L=np.sum(np.hypot(*np.diff(p,axis=0).T))+1
    return p+normals(p,closed)*(noise1(n,int(L/every)+3,seed,closed)*amp+noise1(n,int(L/(every/3))+3,seed+1,closed)*amp*.3)[:,None]

class Sheet:
    "A sheet of paper at three times the size it will be shown."
    def __init__(s,w,h,seed=1):
        s.w,s.h=w,h; s.im=Image.new('RGBA',(w*SS,h*SS),(0,0,0,0)); s.n=seed*97; s.r=random.Random(seed)
    def next(s): s.n+=13; return s.n
    def curve(s,pts,closed=True,wob=.9):
        p=spline(pts,closed); return wobble(p,wob,s.next(),closed) if wob else p
    def rough(s,pts,wob=.8):
        "A polygon whose corners stay corners but whose edges are hand ruled."
        out=[]
        for a,b in zip(pts,pts[1:]+pts[:1]):
            a,b=np.array(a,float),np.array(b,float); k=max(int(np.hypot(*(b-a))/3),2); seg=a+(b-a)*np.linspace(0,1,k,endpoint=False)[:,None]
            if len(seg)>3:
                env=np.sin(np.linspace(0,math.pi,k))[:,None]
                d=b-a; nn=np.array([-d[1],d[0]])/max(np.hypot(*d),1e-6); seg=seg+nn[None,:]*noise1(k,int(k/10)+3,s.next())[:,None]*env*wob
            out.append(seg)
        return np.concatenate(out)
    def mask(s,p):
        m=Image.new('L',s.im.size,0); ImageDraw.Draw(m).polygon([(float(x)*SS,float(y)*SS) for x,y in p],fill=255); return m
    def paint(s,m,col,alpha=255,clip=None):
        if clip is not None: m=ImageChops.multiply(m,clip)
        if alpha<255: m=m.point(lambda v:v*alpha//255)
        s.im.paste(Image.new('RGBA',s.im.size,rgb(col)+(255,)),(0,0),m)
    def fill(s,p,col,alpha=255,clip=None):
        m=s.mask(p); s.paint(m,col,alpha,clip); return m
    def line(s,p,w=2.2,col=INK,closed=False,taper=True,clip=None,alpha=255,dry=0.0):
        "A brush line: it swells, thins and lifts off the paper at its ends."
        p=np.asarray(p,float)
        if closed: p=np.concatenate([p,p[:3]])
        n=len(p)
        if n<2: return
        v=.62+.38*noise1(n,int(n/22)+3,s.next()); env=np.ones(n)
        if taper:
            t=np.linspace(0,1,n); env=np.clip(np.minimum(t,1-t)/.16,0,1)**.7*.92+.08
        r=w*v*env*SS/2
        m=Image.new('L',s.im.size,0); d=ImageDraw.Draw(m); q=p*SS; skip=noise1(n,int(n/30)+3,s.next())
        for i in range(n-1):
            if dry and skip[i]>1-dry: continue
            a,b=q[i],q[i+1]; ra,rb=r[i],r[i+1]; dd=b-a; l=max(np.hypot(*dd),1e-6); nn=np.array([-dd[1],dd[0]])/l
            d.polygon([tuple(a+nn*ra),tuple(b+nn*rb),tuple(b-nn*rb),tuple(a-nn*ra)],fill=255)
            d.ellipse((b[0]-rb,b[1]-rb,b[0]+rb,b[1]+rb),fill=255)
        s.paint(m,col,alpha,clip)
    def shape(s,pts,col,lw=2.6,wob=.9,smooth=True,ink=INK):
        p=s.curve(pts,True,wob) if smooth else s.rough(pts,wob)
        m=s.fill(p,col)
        if lw: s.line(p,lw,ink,closed=True,taper=False)
        return p,m
    def stroke(s,pts,w=2.2,col=INK,wob=.6,clip=None,alpha=255):
        s.line(s.curve(pts,False,wob),w,col,clip=clip,alpha=alpha)
    def done(s,grain=.09):
        a=np.asarray(s.im.resize((s.w,s.h),Image.LANCZOS)).copy()
        return gouache(a,s.n&0xffff,grain)

def gouache(a,seed,grain=.09):
    "The tooth of the paper and the unevenness of the paint."
    h,w=a.shape[:2]; r=np.random.RandomState(seed)
    fine=np.asarray(Image.fromarray((r.rand(h//2+1,w//2+1)*255).astype(np.uint8)).resize((w,h),Image.BILINEAR),dtype=float)/255-.5
    big=P.fbm(h,w,max(18,min(h,w)//5),seed+3,3)-.5
    a[...,:3]=np.clip(a[...,:3]*(1+(fine*grain+big*grain*1.2))[...,None],0,255).astype(np.uint8)
    return a

# ---- leafy things
def scallop(cx,cy,rx,ry,lobes,seed,depth=.13,step=2.5):
    "An outline of leaf clumps: round bumps meeting in sharp little creases."
    r=random.Random(seed); w=[r.uniform(.7,1.3) for _ in range(lobes)]; t=np.cumsum([0]+w)/sum(w)
    n=int(2*math.pi*max(rx,ry)/step); th=np.linspace(0,1,n,endpoint=False); i=np.searchsorted(t,th,side='right')-1; u=(th-t[i])/(t[i+1]-t[i])
    bump=np.sin(np.pi*u)**.55; low=noise1(n,5,seed+9,True)*.09
    k=1+depth*(bump-.6)+low; a=th*2*np.pi-np.pi/2
    return np.stack([cx+np.cos(a)*rx*k,cy+np.sin(a)*ry*k],1)
def clump_arc(p,a0,a1):
    n=len(p); return p[int(a0*n):int(a1*n)]

def tree(seed,pal,gaunt=False):
    d,m,l,hi,tr,trd,trl=pal
    W,H=340,460; s=Sheet(W,H,seed); r=s.r; cx=W/2+r.randint(-8,8); base=H-12; lean=r.uniform(-16,16); hw=r.uniform(19,26)
    # trunk with its roots spread, drawn up into the leaves
    top=base-250
    left=[(cx-hw*2.5,base+2),(cx-hw*1.2,base-16),(cx-hw*.8,base-90),(cx-hw*.62+lean*.5,base-170),(cx-hw*.45+lean,top)]
    right=[(cx+hw*.45+lean,top),(cx+hw*.66+lean*.5,base-170),(cx+hw*.85,base-90),(cx+hw*1.3,base-14),(cx+hw*2.7,base+3)]
    roots=[(cx+hw*.9,base+7),(cx+hw*.2,base-3),(cx-hw*.5,base+8),(cx-hw*1.2,base+4)]
    pts=left+right+roots
    # limbs
    for sgn,ty,reach in ((-1,140,96),(1,175,104),(-1,205,60)):
        x0=cx+lean*.5; y0=base-ty; x1=x0+sgn*reach; y1=y0-reach*.95
        q=[(x0-7,y0+9),(x0+sgn*reach*.5-5,y0-reach*.42),(x1,y1),(x0+sgn*reach*.5+7,y0-reach*.35),(x0+7,y0+14)]
        s.shape(q,tr,lw=3.2,wob=1.1)
    p,mk=s.shape(pts,tr,lw=3.4,wob=1.6)
    # the shadow side of the trunk, one flat coat, and the lines of the bark
    sh=[(cx+hw*.1+lean,top),(cx+hw*.8+lean*.5,base-170),(cx+hw*.95,base-90),(cx+hw*2.7,base+6),(cx+hw*.5,base+10),(cx+hw*.25,base-60),(cx-hw*.1+lean*.6,base-170)]
    s.fill(s.curve(sh,True,1.6),trd,clip=mk)
    li=[(cx-hw*.74,base-120),(cx-hw*.42+lean*.5,base-200),(cx-hw*.28+lean*.5,base-190),(cx-hw*.5,base-90),(cx-hw*.9,base-30)]
    s.fill(s.curve(li,True,1.4),trl,clip=mk)
    for i in range(7):
        x=cx+r.uniform(-.62,.62)*hw; y0=base-r.uniform(20,120); ln=r.uniform(36,92)
        s.stroke([(x,y0),(x+r.uniform(-5,5)+lean*.1,y0-ln*.5),(x+r.uniform(-4,6)+lean*.3,y0-ln)],r.uniform(1.2,2.2),INK,wob=1.2,clip=mk)
    ccy=base-(292+r.randint(-14,12)); ccx=cx+lean*.8
    k=.78 if gaunt else 1.0
    masses=[(ccx+r.uniform(-14,14),ccy-34*k,r.uniform(88,108)*k,r.uniform(66,84)*k,11)]
    for t in range(6):
        a=-2.9+t*1.05+r.uniform(-.3,.3); q=r.uniform(.72,1.02); masses.append((ccx+math.cos(a)*92*k*q,ccy+6+math.sin(a)*60*k*q,r.uniform(44,74)*k,r.uniform(36,56)*k,r.randint(6,9)))
    masses.append((ccx+r.uniform(-20,20),ccy+48,r.uniform(70,92)*k,r.uniform(40,54)*k,9))
    if gaunt: masses=[(ccx+r.uniform(-16,16),ccy-44,92,62,10),(ccx-86,ccy+24,58,42,7),(ccx+84,ccy+10,62,44,7)]
    outlines=[scallop(a,b,c,dd,e,seed*7+i,.17) for i,(a,b,c,dd,e) in enumerate(masses)]
    for p in outlines: s.line(p,6.4,INK,closed=True,taper=False)
    union=Image.new('L',s.im.size,0)
    for p in outlines:
        m_=s.fill(p,d); union=ImageChops.lighter(union,m_)
    # middle and light coats, each a clump shifted toward the light
    for i,(a,b,c,dd,e) in enumerate(sorted(masses,key=lambda v:v[1])):
        p=scallop(a,b,c*.97,dd*.95,e,seed*11+i,.17); s.fill(p,l,clip=union)
        q=scallop(a+c*.17,b+dd*.26,c*.92,dd*.86,e,seed*12+i,.2); s.fill(q,m,clip=union)
        u=scallop(a+c*.3,b+dd*.56,c*.86,dd*.62,max(e-2,5),seed*13+i,.22); s.fill(u,d,clip=union)
        s.line(clump_arc(p,.72,1.0),2.8,INK,clip=union); s.line(clump_arc(p,.0,.2),2.8,INK,clip=union); s.line(clump_arc(q,.1,.36),1.8,d,clip=union)
    # single leaves caught along the lit edges, and a few loose ones in the air
    for _ in range(46 if not gaunt else 26):
        a,b,c,dd,e=r.choice(masses); t=r.uniform(0,2*math.pi); q=r.uniform(.25,.95); x=a-c*.1+math.cos(t)*c*q*.75; y=b-dd*.16+math.sin(t)*dd*q*.75; ang=r.uniform(-.9,.9); L=r.uniform(5,10)
        leaf=[(x-math.cos(ang)*L,y-math.sin(ang)*L),(x,y-L*.34),(x+math.cos(ang)*L,y+math.sin(ang)*L),(x,y+L*.34)]
        s.fill(s.curve(leaf,True,0),r.choice((hi,l,l,m)),clip=union)
    return s.done()
def tree_sheet(pal,seed,gaunt=False):
    out=np.zeros((460,340*4,4),dtype=np.uint8)
    for i in range(4): P.over(out,tree(seed+i,pal,gaunt),i*340,0)
    return out
VILLAGE_TREE=('#26382f','#3c5b3c','#6d8444','#b4ab5a','#4b362b','#2b1f1c','#755440')
FOREST_TREE=('#101b24','#1b3236','#2f544c','#6b9273','#2a2424','#161317','#463a35')

# ---- buildings and what stands around them
def cottage(w,seed,roof):
    W,H=w*64,400; s=Sheet(W,H,seed); r=s.r; wy=256; rd,rm,rl=roof
    # chimney first, then the roof over its foot
    cw=W-112; s.shape([(cw-1,76),(cw+1,6),(cw+40,3),(cw+42,78)],'#6d6470',lw=3,smooth=False,wob=1.4)
    s.shape([(cw-7,10),(cw+47,6),(cw+48,20),(cw-6,23)],'#544c58',lw=3,smooth=False,wob=1)
    for y in (32,48,63):
        for x in range(cw+r.randint(3,9),cw+34,14): s.stroke([(x,y),(x+9,y+r.uniform(-1,1))],1.6)
    sag=r.uniform(4,9)
    outline=[(-1,wy+13),(34,6),(W*.3,6+sag),(W*.7,4+sag*.6),(W-34,6),(W+1,wy+13),(W*.72,wy+17),(W*.3,wy+11)]
    rp=s.curve(outline,True,1.4); rm_=s.fill(rp,rm)
    # the eaves in shadow, one wavering coat
    s.fill(s.curve([(-8,wy-62),(W*.3,wy-48),(W*.65,wy-66),(W+8,wy-54),(W+8,wy+30),(-8,wy+30)],True,3),rd,clip=rm_)
    s.fill(s.curve([(44,14),(W*.32,12+sag),(W*.42,44),(W*.22,86),(30,92)],True,3),rl,clip=rm_)
    y=26; row=0
    while y<wy+2:
        off=r.randint(0,18); inset=int((1-y/wy)*30); x=-off+inset
        while x<W-inset:
            w0=r.randint(25,38)
            if r.random()<.82:
                s.stroke([(x+3,y+r.uniform(-1,1)),(x+w0/2,y+r.uniform(4,7)),(x+w0-2,y+r.uniform(-1,1))],r.uniform(1.3,2.3),clip=rm_,wob=.4)
            if r.random()<.6: s.stroke([(x+w0-2,y-1),(x+w0-1+r.uniform(-1,1),y-r.uniform(10,16))],1.3,clip=rm_,wob=.3)
            if r.random()<.05:
                s.fill(s.rough([(x+4,y-12),(x+w0-5,y-12),(x+w0-5,y+1),(x+4,y+1)],.8),r.choice((rm,rd)),clip=rm_)
            x+=w0
        y+=r.randint(18,23); row+=1
    s.line(rp,4,INK,closed=True,taper=False)
    # plaster walls
    wp=s.rough([(5,wy+12),(W-5,wy+12),(W-3,H-15),(3,H-15)],1.6); wm=s.fill(wp,'#c9b892')
    s.fill(s.curve([(0,wy+8),(W,wy+8),(W,wy+36),(W*.74,wy+44),(W*.5,wy+33),(W*.24,wy+46),(0,wy+35)],True,2.4),'#7d6f62',clip=wm)
    s.fill(s.curve([(W*.58,wy+50),(W,wy+42),(W,H),(W*.68,H),(W*.62,wy+100)],True,4),'#ab9a7c',clip=wm)
    for _ in range(9):
        x=r.randint(24,W-60); y=r.randint(wy+50,H-44)
        pat=s.curve([(x,y),(x+r.randint(26,46),y-r.randint(2,8)),(x+r.randint(34,54),y+r.randint(10,18)),(x+8,y+r.randint(16,24))],True,2)
        if r.random()<.5:
            s.fill(pat,'#ddcfae',clip=wm)
        else:
            for k in range(3):
                bx=x+k*14+r.randint(0,4); by=y+k%2*9+r.randint(0,4); s.stroke([(bx,by),(bx+11,by),(bx+11,by+6),(bx,by+6)],1.1,'#6a5545',wob=.3,clip=wm)
    s.line(wp,3,INK,closed=True,taper=False)
    def beam(a,b,wd):
        (x0,y0),(x1,y1)=a,b; dx,dy=x1-x0,y1-y0; l=max(math.hypot(dx,dy),1); nx,ny=-dy/l*wd/2,dx/l*wd/2
        p=[(x0+nx,y0+ny),(x1+nx,y1+ny),(x1-nx,y1-ny),(x0-nx,y0-ny)]; q,m=s.shape(p,'#4a3429',lw=2.4,smooth=False,wob=1.3)
        for _ in range(3):
            t=r.uniform(.05,.6); u=t+r.uniform(.15,.35); o=r.uniform(-.28,.28)
            s.stroke([(x0+dx*t+nx*o*2,y0+dy*t+ny*o*2),(x0+dx*u+nx*o*2,y0+dy*u+ny*o*2)],1.1,'#231a18',wob=.5,clip=m)
    for x in list(range(4,W-30,128))+[W-14]: beam((x+7+r.uniform(-2,2),wy+11),(x+7+r.uniform(-2,2),H-16),15)
    beam((0,wy+77+r.uniform(-3,3)),(W,wy+76+r.uniform(-3,3)),13)
    s.fill(s.curve([(-2,wy+10),(W+2,wy+10),(W+2,wy+22),(W*.5,wy+18),(-2,wy+23)],True,1.2),'#231a18')
    # the stones the house sits on
    x=-4
    while x<W:
        wd=r.randint(22,36); s.shape([(x,H-1),(x+1,H-17-r.randint(0,4)),(x+wd/2,H-20-r.randint(0,3)),(x+wd,H-16-r.randint(0,4)),(x+wd+1,H-1)],r.choice(('#6b6673','#7d7680','#57525f')),lw=2.2,wob=.7); x+=wd
    def window(x):
        y=wy+24; a,b=46,50
        s.shape([(x-8,y-7),(x+a+8,y-8),(x+a+9,y+b+7),(x-9,y+b+8)],'#3a2922',lw=2.6,smooth=False,wob=1.2)
        g,gm=s.shape([(x,y),(x+a,y-1),(x+a+1,y+b),(x-1,y+b+1)],'#f0bd5c',lw=2,smooth=False,wob=.7)
        s.fill(s.curve([(x+a+4,y+b*.1),(x+a*.55,y+b*.36),(x+a*.25,y+b+6),(x+a+6,y+b+6)],True,1.4),'#d38f39',clip=gm)
        s.fill(s.curve([(x+4,y+4),(x+18,y+4),(x+14,y+18),(x+4,y+22)],True,1),'#fbe3a4',clip=gm)
        s.stroke([(x+a/2+r.uniform(-1,1),y),(x+a/2+r.uniform(-1,1),y+b)],3); s.stroke([(x,y+b*.47),(x+a,y+b*.5)],3)
        # a window box of flowers
        by=y+b+7; s.shape([(x-11,by),(x+a+11,by-1),(x+a+8,by+13),(x-8,by+13)],'#5a3f30',lw=2.4,smooth=False,wob=.8)
        for k in range(7):
            fx=x-7+k*(a+14)/6+r.uniform(-2,2); fy=by-r.uniform(3,9); s.shape([(fx-6,fy+2),(fx,fy-5),(fx+6,fy+2),(fx,fy+6)],r.choice(('#a84f55','#d8a24a','#7f5a93','#3f5f3f','#3f5f3f')),lw=1.6,wob=.3)
    for x in (72,W-118): window(x)
    dx=(w//2)*64+6
    s.shape([(dx-10,H-16),(dx-9,H-110),(dx+26,H-126),(dx+61,H-110),(dx+62,H-16)],'#3a2922',lw=3,wob=1)
    dp,dm=s.shape([(dx-1,H-15),(dx,H-104),(dx+26,H-117),(dx+52,H-104),(dx+53,H-15)],'#6a4a35',lw=2.2,wob=.7)
    s.fill(s.curve([(dx+30,H-120),(dx+58,H-112),(dx+58,H-10),(dx+36,H-10)],True,1),'#4c3529',clip=dm)
    for k in (dx+14,dx+27,dx+40): s.stroke([(k+r.uniform(-1,1),H-112),(k+r.uniform(-1,1),H-16)],1.6,clip=dm)
    for y in (H-90,H-40): s.shape([(dx,y-4),(dx+50,y-5),(dx+50,y+3),(dx,y+4)],'#2f2a2b',lw=1.4,smooth=False,wob=.5)
    s.shape([(dx+40,H-66),(dx+47,H-68),(dx+49,H-60),(dx+42,H-57)],'#d7a941',lw=1.6,wob=.3)
    return s.done()

def fence_run(cells):
    W,H=cells*64,110; s=Sheet(W,H,cells+40); r=s.r; WD=('#6f523f','#46322a','#967356')
    for y in (42,72):
        a=r.uniform(-2,2); p,m=s.shape([(-4,y+a),(W*.5,y+r.uniform(-2,2)),(W+4,y+r.uniform(-2,2)),(W+4,y+11),(W*.5,y+11+r.uniform(-2,2)),(-4,y+11+a)],WD[0],lw=2.4,wob=.8,smooth=False)
        s.fill(s.rough([(-4,y+7),(W+4,y+7),(W+4,y+13),(-4,y+13)],1),WD[1],clip=m)
        for k in range(cells*3): x=r.randint(0,W); s.stroke([(x,y+4),(x+r.randint(8,24),y+r.uniform(3,7))],1.0,clip=m)
    for x in range(10,W,64):
        wd=r.randint(16,20); j=r.uniform(-3,3); top=r.randint(5,12)
        p,m=s.shape([(x+j,H-2),(x+j*.5,top+12),(x+wd*.5+j*.4,top),(x+wd+j*.5,top+10),(x+wd+j,H-2)],WD[0],lw=2.8,wob=.8,smooth=False)
        s.fill(s.rough([(x+wd*.6,top),(x+wd+6,top),(x+wd+6,H),(x+wd*.6,H)],1.2),WD[1],clip=m)
        s.fill(s.rough([(x+1,top+14),(x+5,top+14),(x+4,H-30),(x+1,H-30)],.8),WD[2],clip=m)
        for k in range(3): yy=r.randint(top+14,H-20); s.stroke([(x+r.randint(3,wd-3),yy),(x+r.randint(3,wd-3),yy+r.randint(12,30))],1.0,clip=m)
    return s.done()
def well_img():
    W,H=170,210; s=Sheet(W,H,8); r=s.r
    for x in (20,136): s.shape([(x,160),(x+1,34),(x+14,33),(x+15,160)],'#5a4133',lw=2.8,smooth=False,wob=1)
    s.stroke([(27,62),(85,58),(143,62)],4.5,'#2f2520',wob=.6); s.stroke([(85,60),(85,134)],1.6,'#2f2520',wob=.8)
    s.shape([(76,132),(94,132),(92,152),(78,152)],'#6f523f',lw=2,smooth=False,wob=.5)
    p,m=s.shape([(13,160),(30,126),(85,116),(140,126),(157,160),(140,196),(85,204),(30,196)],'#6f6a77',lw=3.4,wob=1)
    s.fill(s.curve([(85,190),(150,168),(160,210),(40,212)],True,2),'#514c5a',clip=m)
    s.shape([(30,152),(50,134),(85,128),(120,134),(140,152),(120,164),(85,170),(50,164)],'#1e3442',lw=2.6,wob=.8)
    for _ in range(17):
        a=r.uniform(.05,.95)*math.pi; rx,ry=66,36; x=85+math.cos(a)*rx; y=172+math.sin(a)*ry*.7; w=r.randint(13,22); s.stroke([(x-w/2,y),(x,y+3),(x+w/2,y-1),(x+w/2-2,y+9)],1.5,clip=m)
    p,m=s.shape([(4,48),(32,5),(138,4),(166,48),(120,54),(50,52)],'#3a4d6e',lw=3.2,wob=1)
    s.fill(s.curve([(0,36),(85,44),(170,32),(170,58),(0,58)],True,2),'#26334f',clip=m)
    y=14
    while y<46:
        x=20+r.randint(0,12)
        while x<150: s.stroke([(x,y),(x+8,y+4),(x+16,y)],1.3,clip=m,wob=.3); x+=r.randint(20,26)
        y+=10
    return s.done()
def sign_img():
    W,H=130,150; s=Sheet(W,H,9); r=s.r
    s.shape([(56,H-2),(58,50),(73,50),(75,H-2)],'#4f392d',lw=2.8,smooth=False,wob=1)
    p,m=s.shape([(8,16),(112,9),(124,36),(112,69),(8,62)],'#856447',lw=3,smooth=False,wob=1.3)
    s.fill(s.curve([(0,50),(70,46),(130,40),(130,80),(0,76)],True,2),'#5f4634',clip=m)
    s.stroke([(22,30),(58,27),(92,29)],3); s.stroke([(22,44),(50,43),(74,45)],3)
    for _ in range(5): y=r.randint(14,62); x=r.randint(14,80); s.stroke([(x,y),(x+r.randint(12,30),y+r.uniform(-1,1))],.9,clip=m)
    return s.done()
def table_img():
    W,H=196,144; s=Sheet(W,H,10); r=s.r
    for x in (30,154): s.shape([(x,60),(x+13,60),(x+12,106),(x+1,106)],'#2f221d',lw=2.6,smooth=False,wob=.7)
    for x in (12,166):
        p,m=s.shape([(x,84),(x+19,84),(x+16,141),(x+3,141)],'#4d372c',lw=3,smooth=False,wob=.9)
        s.fill(s.rough([(x+11,80),(x+24,80),(x+24,145),(x+11,145)],.8),'#35271f',clip=m)
    p,m=s.shape([(28,20),(168,20),(193,72),(3,72)],'#94714f',lw=3.4,smooth=False,wob=1.1)
    s.fill(s.curve([(120,14),(200,14),(200,80),(90,80),(124,48)],True,3),'#7b5c42',clip=m)
    for k,t in enumerate((.25,.5,.75)):
        s.stroke([(28+140*t,20),(3+190*t,72)],1.7,clip=m,wob=.7)
    for _ in range(9):
        y=r.randint(27,66); x=r.randint(20,130); s.stroke([(x,y),(x+r.randint(14,42),y+r.uniform(-1,1))],1,'#4f3a2c',clip=m)
    e,em=s.shape([(3,72),(193,72),(191,90),(5,90)],'#5a4334',lw=3,smooth=False,wob=.9)
    for x in (34,72,118,158): s.stroke([(x,74),(x+r.uniform(-1,1),88)],1.2,clip=em,wob=.2)
    # supper: a bowl, a loaf and a mug
    s.shape([(68,42),(98,34),(128,42),(120,62),(98,68),(76,62)],'#b9a77c',lw=2.8,wob=.7)
    s.shape([(74,42),(98,37),(122,42),(98,49)],'#a35a35',lw=1.8,wob=.5)
    s.stroke([(92,42),(98,44),(108,41)],2,'#d8a24a',wob=.3)
    s.shape([(136,46),(150,36),(168,44),(170,56),(150,62),(136,58)],'#b9823f',lw=2.6,wob=.8)
    for x in (146,154,162): s.stroke([(x,40),(x-3,50)],1.5,wob=.2)
    s.shape([(34,36),(54,36),(54,60),(34,60)],'#5d7a70',lw=2.6,smooth=False,wob=.6); s.shape([(34,36),(44,32),(54,36),(44,40)],'#2a241f',lw=1.6,wob=.2); s.stroke([(54,41),(63,45),(54,54)],2.6,wob=.2)
    return s.done()
def bed_img():
    W,H=176,190; s=Sheet(W,H,14); r=s.r
    for x in (12,152): s.shape([(x,16),(x+12,14),(x+13,100),(x,100)],'#3f2d25',lw=2.8,smooth=False,wob=.8)
    p,m=s.shape([(20,36),(42,16),(88,9),(134,16),(156,36),(156,96),(20,96)],'#6d4d38',lw=3.2,wob=1)
    s.fill(s.curve([(96,6),(160,14),(160,100),(108,100),(122,50)],True,3),'#4f382b',clip=m)
    for x in (52,88,124): s.stroke([(x,14),(x+r.uniform(-2,2),96)],1.7,clip=m,wob=.8)
    s.shape([(68,30),(88,24),(108,30),(100,44),(88,48),(76,44)],'#b9a77c',lw=2,wob=.5)
    p,m=s.shape([(24,78),(152,78),(168,160),(8,160)],'#d6cbaf',lw=3.2,smooth=False,wob=1.2)
    s.fill(s.curve([(100,70),(170,70),(176,170),(120,170),(126,116)],True,3),'#b3a78e',clip=m)
    q,qm=s.shape([(42,66),(88,60),(134,66),(142,92),(88,104),(34,92)],'#f0e7cf',lw=2.8,wob=1)
    s.fill(s.curve([(90,60),(146,62),(148,98),(92,108),(112,84)],True,1.6),'#c9bea3',clip=qm); s.stroke([(70,80),(88,88),(104,78)],1.6,'#8f846e')
    b,bm=s.shape([(17,112),(88,106),(159,112),(170,162),(88,166),(6,162)],'#3a5a8d',lw=3.2,wob=1.2)
    s.fill(s.curve([(104,100),(176,106),(178,170),(118,172),(130,136)],True,3),'#27406d',clip=bm)
    s.fill(s.curve([(26,126),(56,120),(62,130),(36,152),(18,156)],True,1.6),'#5779a8',clip=bm)
    for x,y in ((44,132),(78,148),(112,126),(136,150)): s.stroke([(x,y),(x+12,y-4),(x+22,y+1)],1.5,'#1c2f54',clip=bm,wob=.5)
    f,fm=s.shape([(13,106),(88,100),(163,106),(165,121),(88,116),(11,121)],'#ddd2b6',lw=2.6,wob=.8)
    d,dm=s.shape([(6,160),(88,164),(170,160),(168,178),(88,182),(8,178)],'#203866',lw=3,wob=.9)
    for x in range(20,160,23): s.stroke([(x,168),(x+11,170)],1.3,'#6d88a0',clip=dm,wob=.2)
    for x in (10,150): s.shape([(x,174),(x+16,174),(x+15,189),(x+1,189)],'#2f221d',lw=2.4,smooth=False,wob=.5)
    return s.done()
def rock_img():
    s=Sheet(120,120,11); p,m=s.shape([(10,112),(14,70),(38,40),(76,36),(106,64),(112,112)],'#67626f',lw=3.4,smooth=False,wob=2.2)
    s.fill(s.curve([(64,36),(112,70),(116,116),(58,116),(74,76)],True,2),'#48434f',clip=m)
    s.fill(s.curve([(24,62),(44,44),(62,46),(46,66),(26,84)],True,2),'#8f8995',clip=m)
    s.stroke([(58,44),(70,70),(58,92)],2); s.stroke([(30,92),(50,96),(62,108)],1.5)
    s.shape([(34,44),(58,32),(84,36),(70,46),(46,50)],'#4f6b48',lw=2,wob=1.2)
    return s.done()
def fire_sheet():
    out=np.zeros((110,330,4),dtype=np.uint8)
    for f in range(3):
        s=Sheet(110,110,60+f); r=s.r
        def flame(cx,hh,wd,col):
            lean=r.uniform(-7,7); q=[(cx-wd,106),(cx-wd*1.05,106-hh*.36),(cx-wd*.3+lean*.5,106-hh*.68),(cx+lean,106-hh),(cx+wd*.55+lean*.4,106-hh*.6),(cx+wd,106-hh*.3),(cx+wd,106)]
            return s.curve(q,True,1)
        for cx,hh,wd,c in ((30,50+[0,8,-6][f],19,'#a03a1e'),(58,84+[6,-4,8][f],26,'#a03a1e'),(84,44+[-4,8,0][f],17,'#a03a1e')):
            p=flame(cx,hh,wd,c); s.fill(p,c); s.line(p,2.4,INK,closed=True,taper=False)
        for cx,hh,wd in ((32,32+f*2,12),(58,58-f*3,18),(82,28+f*3,11)): s.fill(flame(cx,hh,wd,''),'#e88a2c')
        for cx,hh,wd in ((58,32+f*2,10),(40,14,5),(76,16,5)): s.fill(flame(cx,hh,wd,''),'#f7d67c')
        P.over(out,s.done(.04),f*110,0)
    return out

# ---- people
SK=('#d6ac8c','#a87a64','#f0d2b0'); HAIR=('#2d2230','#4b3a44'); SILVER=('#b4b2bd','#7f7d8e')
LOOK=dict(hero=dict(top=('#2f6b66','#1e4a4c','#6ba88d'),bot=('#34395a','#232642'),hair=HAIR,boot='#3e2c2a'),
          mira=dict(top=('#54488a','#362e60','#8678ba'),bot=('#54488a','#362e60'),hair=SILVER,boot='#2d2230'),
          tobin=dict(top=('#a15a31','#6e3a22','#d1904f'),bot=('#34303c','#23202c'),hair=SILVER,boot='#2d2230'))
def person(style,d,leg,breathe=0,seed=0):
    # the same few wobbles each time would freeze; a new seed per frame makes the line boil gently, as drawn animation does
    s=Sheet(120,160,zlib.crc32(repr((style,d,leg,breathe,seed)).encode())&0xffff); L=LOOK[style]; T,Td,Tl=L['top']; Bo,Bd=L['bot']; H0,H1=L['hair']; dy=breathe*2.5; cx=60
    robe=style=='mira'
    # legs
    if robe:
        p,m=s.shape([(cx-22,100+dy),(cx-30,132),(cx-37,155),(cx,159),(cx+37,155),(cx+30,132),(cx+22,100+dy)],T,lw=3.2)
        s.fill(s.curve([(cx+6,100),(cx+44,120),(cx+44,160),(cx+8,160),(cx+14,130)],True,1.4),Td,clip=m)
        for x in (-14,4,20): s.stroke([(cx+x,126),(cx+x*1.25,154)],1.6,clip=m)
    elif d=='side':
        for k,(sw,col) in enumerate(((-leg*12,Bd),(leg*12,Bo))):
            s.shape([(cx-9+sw*.25,122),(cx+9+sw*.25,122),(cx+9+sw,146),(cx-7+sw,146)],col,lw=2.8,smooth=False,wob=.7)
            s.shape([(cx-9+sw,145),(cx+6+sw,143),(cx+18+sw,150),(cx+17+sw,157),(cx-9+sw,157)],L['boot'],lw=2.8,wob=.6)
    else:
        l,rr=max(leg,0)*5,max(-leg,0)*5
        for x,lift in ((-13,rr),(13,l)):
            s.shape([(cx+x-9,122),(cx+x+9,122),(cx+x+8,146-lift),(cx+x-8,146-lift)],Bo if x<0 else Bd,lw=2.8,smooth=False,wob=.7)
            s.shape([(cx+x-11,146-lift),(cx+x,142-lift),(cx+x+11,146-lift),(cx+x+12,156-lift),(cx+x-12,156-lift)],L['boot'],lw=2.8,wob=.6)
    # body
    sw=leg*6
    def arm(x0,x1,ys,colr=T):
        p,m=s.shape([(x0-7,98+dy),(x0+7,97+dy),(x1+7,ys+dy),(x1-7,ys+dy)],colr,lw=2.8,wob=.7,smooth=False)
        s.shape([(x1-7,ys-2+dy),(x1+7,ys-2+dy),(x1+8,ys+9+dy),(x1,ys+14+dy),(x1-8,ys+9+dy)],SK[0],lw=2.4,wob=.4)
    if d=='side':
        arm(cx-3,cx-3-leg*12,122,Td)
        p,m=s.shape([(cx-19,100+dy),(cx,93+dy),(cx+19,101+dy),(cx+23,132),(cx,136),(cx-24,132)],T,lw=3.2)
        s.fill(s.curve([(cx-30,100),(cx-6,96),(cx-12,140),(cx-30,140)],True,1.4),Td,clip=m)
    elif not robe:
        arm(cx-31,cx-33,120-sw); arm(cx+31,cx+33,120+sw,Td)
        p,m=s.shape([(cx-24,102+dy),(cx,94+dy),(cx+24,102+dy),(cx+30,132),(cx,137),(cx-30,132)],T,lw=3.2)
        s.fill(s.curve([(cx+8,92),(cx+36,100),(cx+36,142),(cx+6,142),(cx+16,120)],True,1.4),Td,clip=m)
    else:
        arm(cx-27,cx-31,120-sw); arm(cx+27,cx+31,120+sw,Td); m=None
    if style=='hero':
        if d=='down':
            s.fill(s.curve([(cx-22,108),(cx-10,104),(cx-14,128),(cx-26,126)],True,1),Tl,clip=m)
            s.shape([(cx-30,124+dy),(cx,128+dy),(cx+30,124+dy),(cx+30,132+dy),(cx,136+dy),(cx-30,132+dy)],'#5c3f2b',lw=2.2,wob=.5)
            s.shape([(cx-6,124+dy),(cx+6,124+dy),(cx+7,136+dy),(cx-7,136+dy)],'#c79b42',lw=2,smooth=False,wob=.4)
            s.shape([(cx-22,92+dy),(cx,99+dy),(cx+22,92+dy),(cx+21,104+dy),(cx,110+dy),(cx-21,104+dy)],'#7d3250',lw=2.8,wob=.7)
            s.shape([(cx+10,104+dy),(cx+20,104+dy),(cx+22,126+dy),(cx+14,128+dy)],'#642541',lw=2.4,wob=.6)
        elif d=='up':
            c,cm=s.shape([(cx-22,94+dy),(cx,90+dy),(cx+22,94+dy),(cx+33,140),(cx,146),(cx-33,140)],'#7d3250',lw=3.2)
            s.fill(s.curve([(cx+4,88),(cx+40,96),(cx+40,150),(cx+8,150),(cx+16,120)],True,1.4),'#5a2140',clip=cm)
            for x in (-16,2,17): s.stroke([(cx+x*.6,102),(cx+x*1.2,140)],1.5,clip=cm)
        else:
            c,cm=s.shape([(cx-14,94+dy),(cx+14,94+dy),(cx+2,108+dy),(cx-32-leg*5,142),(cx-44-leg*5,126)],'#7d3250',lw=2.8)
            s.shape([(cx-18,92+dy),(cx+18,92+dy),(cx+18,104+dy),(cx-18,104+dy)],'#7d3250',lw=2.6,wob=.5)
            s.shape([(cx-23,124+dy),(cx+22,124+dy),(cx+22,132+dy),(cx-23,132+dy)],'#5c3f2b',lw=2.2,smooth=False,wob=.5)
    if style=='mira' and d=='down':
        s.shape([(cx-16,110+dy),(cx+16,110+dy),(cx+20,152),(cx,155),(cx-20,152)],'#ddd2b6',lw=2.6,wob=.7)
        s.shape([(cx-24,108+dy),(cx+24,108+dy),(cx+24,114+dy),(cx-24,114+dy)],'#c79b42',lw=2.2,smooth=False,wob=.4)
    if style=='tobin' and d=='down':
        s.shape([(cx-18,108+dy),(cx+18,108+dy),(cx+21,134),(cx,138),(cx-21,134)],'#ddd2b6',lw=2.6,wob=.7)
    # head
    hx=cx+(5 if d=='side' else 0); hy=70+dy; R=31
    hp,hm=s.shape([(hx-R,hy+1),(hx-R*.72,hy-R*.72),(hx,hy-R*.96),(hx+R*.72,hy-R*.72),(hx+R,hy+1),(hx+R*.76,hy+R*.72),(hx,hy+R*.98),(hx-R*.76,hy+R*.72)],SK[0],lw=3.2,wob=.5)
    s.fill(s.curve([(hx+R*.2,hy+R*1.1),(hx+R*.9,hy+R*.8),(hx+R*1.2,hy-R*.3),(hx+R*.76,hy+R*.1)],True,1),SK[1],clip=hm)
    bl=breathe==1 and leg==0 and style!='hero'
    if d=='down':
        for ex,sg in ((-13,-1),(13,1)):
            if bl: s.stroke([(hx+ex-5,hy+4),(hx+ex,hy+6),(hx+ex+5,hy+4)],2.6)
            else:
                s.fill(s.curve([(hx+ex-4,hy+1),(hx+ex,hy-5),(hx+ex+4,hy+1),(hx+ex,hy+9)],True,0),INK); s.fill(s.curve([(hx+ex-2.6,hy-1),(hx+ex-.6,hy-3),(hx+ex+.4,hy-1),(hx+ex-1.2,hy+1)],True,0),'#f2ead8')
            s.fill(s.curve([(hx+ex*1.35-5,hy+11),(hx+ex*1.35,hy+9),(hx+ex*1.35+5,hy+11),(hx+ex*1.35,hy+14)],True,.3),'#c98a72')
        s.stroke([(hx-4,hy+15),(hx,hy+17),(hx+4,hy+15)],1.8,'#5e3528')
        hair=[(hx-R-2,hy+10),(hx-R-3,hy-14),(hx-R*.6,hy-R-3),(hx,hy-R-6),(hx+R*.6,hy-R-3),(hx+R+3,hy-14),(hx+R+2,hy+10),(hx+R*.76,hy-7),(hx+R*.42,hy-3),(hx+R*.16,hy-12),(hx-R*.2,hy-5),(hx-R*.55,hy-10),(hx-R*.8,hy-3)]
    elif d=='up':
        hair=[(hx-R-2,hy+14),(hx-R-3,hy-14),(hx-R*.6,hy-R-3),(hx,hy-R-6),(hx+R*.6,hy-R-3),(hx+R+3,hy-14),(hx+R+2,hy+14),(hx+R*.5,hy+R*.96),(hx,hy+R*.8),(hx-R*.5,hy+R*.96)]
    else:
        if bl: s.stroke([(hx+13,hy+4),(hx+18,hy+6)],2.6)
        else:
            s.fill(s.curve([(hx+11,hy+1),(hx+15,hy-5),(hx+19,hy+1),(hx+15,hy+9)],True,0),INK); s.fill(s.curve([(hx+13,hy-1),(hx+15,hy-3),(hx+16,hy-1),(hx+14,hy+1)],True,0),'#f2ead8')
        s.fill(s.curve([(hx+4,hy+11),(hx+9,hy+9),(hx+14,hy+11),(hx+9,hy+14)],True,.3),'#c98a72')
        s.stroke([(hx+14,hy+16),(hx+20,hy+15)],1.8,'#5e3528')
        hair=[(hx-R-3,hy+18),(hx-R-4,hy-12),(hx-R*.55,hy-R-3),(hx+R*.1,hy-R-6),(hx+R*.72,hy-R*.72),(hx+R+2,hy-12),(hx+R*.55,hy-8),(hx+R*.1,hy-13),(hx-R*.12,hy+2),(hx-R*.4,hy+R*.8),(hx-R*.86,hy+R*.72)]
    if style=='tobin':
        if d!='up': s.shape([(hx-R*.86,hy+6),(hx-R*.5,hy+10),(hx,hy+8),(hx+R*.5,hy+10),(hx+R*.86,hy+6),(hx+R*.64,hy+R*1.05),(hx,hy+R*1.4),(hx-R*.64,hy+R*1.05)],H0,lw=2.8,wob=.8); s.stroke([(hx-5,hy+17),(hx,hy+19),(hx+5,hy+17)],1.8)
        hair=[(hx-R-2,hy+2),(hx-R-2,hy-16),(hx-R*.5,hy-R+2),(hx,hy-R-1),(hx+R*.5,hy-R+2),(hx+R+2,hy-16),(hx+R+2,hy+2),(hx+R*.8,hy-13),(hx,hy-20),(hx-R*.8,hy-13)]
    hp2,hmk=s.shape(hair,H0,lw=3.2,wob=.7)
    s.fill(s.curve([(hx-R*.7,hy-R*.56),(hx-R*.15,hy-R*.9),(hx+R*.26,hy-R*.84),(hx-R*.1,hy-R*.62),(hx-R*.6,hy-R*.3)],True,1),H1,clip=hmk)
    for k in range(3):
        a=-1+k; s.stroke([(hx+a*R*.3,hy-R*.9),(hx+a*R*.5,hy-R*.5)],1.3,'#191216',clip=hmk) if style=='hero' else None
    if style=='mira':
        by=hy-R-7; s.shape([(hx-14,by+6),(hx-10,by-9),(hx+10,by-9),(hx+14,by+6),(hx,by+11)],H0,lw=3,wob=.6)
        s.stroke([(hx-7,by-3),(hx+1,by+2),(hx+8,by-4)],1.5,'#6c6a7b')
    return s.done(.05)
def person_sheet(style):
    fw,fh=120,160; out=np.zeros((fh*3,fw*4,4),dtype=np.uint8)
    for r,(d,legs) in enumerate((('down',(0,1,0,-1)),('up',(0,-1,0,1)),('side',(0,1,0,-1)))):
        for c,l in enumerate(legs): P.over(out,person(style,d,l,1 if l else 0,c),c*fw,r*fh)
    return out
def npc_sheet(style):
    out=np.zeros((160,240,4),dtype=np.uint8)
    for i,b in enumerate((0,1)): P.over(out,person(style,'down',0,b,i),i*120,0)
    return out

def jelly_body(s,cx,cy,rx,ry,base):
    pts=[(cx-rx,base),(cx-rx*1.02,cy+ry*.1),(cx-rx*.66,cy-ry*.76),(cx,cy-ry),(cx+rx*.66,cy-ry*.76),(cx+rx*1.02,cy+ry*.1),(cx+rx,base),(cx+rx*.5,base+5),(cx,base+1),(cx-rx*.5,base+5)]
    p,m=s.shape(pts,'#3f9a8d',lw=3.6,wob=1.1)
    s.fill(s.curve([(cx+rx*.05,cy+ry),(cx+rx*.8,cy-ry*.4),(cx+rx*1.3,cy),(cx+rx*1.2,base+8),(cx-rx*.8,base+8),(cx-rx,base-rx*.12)],True,2),'#266f70',clip=m)
    s.fill(s.curve([(cx-rx*.74,cy-ry*.3),(cx-rx*.5,cy-ry*.74),(cx-rx*.08,cy-ry*.84),(cx-rx*.3,cy-ry*.5),(cx-rx*.6,cy-ry*.05)],True,1),'#8ed1b4',clip=m)
    return m
def slime_frame(rx,ry,cy,i):
    s=Sheet(120,120,70+i); k=3.75; rx,ry,cy=rx*k,ry*k,cy*k; base=27*k; m=jelly_body(s,60,cy,rx,ry,base); ey=cy-ry*.12
    for ex in (60-rx*.34,60+rx*.34):
        s.fill(s.curve([(ex-7,ey+1),(ex,ey-11),(ex+7,ey+1),(ex,ey+12)],True,.2),INK); s.fill(s.curve([(ex-4,ey-3),(ex-1,ey-7),(ex+1,ey-3),(ex-2,ey)],True,0),'#f2ead8')
    s.stroke([(60-8,ey+16),(60,ey+19+i),(60+8,ey+16)],2.4)
    return s.done(.05)
def slime_sheet():
    out=np.zeros((120,360,4),dtype=np.uint8)
    for i,a in enumerate(((12,10,18),(10,12,16),(14,7.5,20))): P.over(out,slime_frame(*a,i),i*120,0)
    return out

def icon(n):
    s=Sheet(120,120,{'jelly':21,'potion':22,'coin':23,'heart':24}[n]); r=s.r
    if n=='jelly':
        m=jelly_body(s,60,66,42,36,98); s.fill(s.curve([(72,76),(84,72),(90,80),(78,86)],True,.6),'#1c5d60',clip=m)
    elif n=='potion':
        s.shape([(46,8),(74,8),(76,22),(44,22)],'#5c3f2b',lw=3,smooth=False,wob=.7)
        p,m=s.shape([(47,20),(73,20),(74,44),(100,74),(96,104),(60,114),(24,104),(20,74),(46,44)],'#b6c4c4',lw=3.4,wob=.9)
        s.fill(s.curve([(16,70),(60,62),(104,70),(104,118),(16,118)],True,1.6),'#a33c4b',clip=m)
        s.fill(s.curve([(64,62),(104,70),(104,118),(74,118),(84,90)],True,1.6),'#772b3e',clip=m)
        s.stroke([(30,74),(34,92),(44,102)],4,'#f0dcc4',clip=m); s.stroke([(20,70),(60,63),(100,70)],2.4,clip=m)
    elif n=='coin':
        p,m=s.shape([(12,60),(26,26),(60,12),(94,26),(108,60),(94,94),(60,108),(26,94)],'#cfa144',lw=3.6,wob=.8)
        s.fill(s.curve([(66,10),(112,40),(112,110),(40,112),(88,76)],True,1.4),'#986f2c',clip=m)
        s.line(s.curve([(26,60),(36,36),(60,26),(84,36),(94,60),(84,84),(60,94),(36,84)],True,.9),2.2,closed=True,clip=m,taper=False)
        s.stroke([(60,40),(60,80)],7,'#6f4f20'); s.stroke([(47,41),(73,41)],5,'#6f4f20'); s.stroke([(47,79),(73,79)],5,'#6f4f20')
        s.stroke([(30,46),(40,32),(52,27)],3.4,'#f1dca0',clip=m)
    else:
        p,m=s.shape([(60,36),(46,14),(20,14),(6,40),(16,72),(60,114),(104,72),(114,40),(100,14),(74,14)],'#a33c4b',lw=4,wob=1)
        s.fill(s.curve([(64,110),(92,70),(104,34),(120,40),(116,120)],True,1.6),'#74293c',clip=m)
        s.fill(s.curve([(20,36),(30,22),(46,24),(34,34),(26,56)],True,1),'#e0a08c',clip=m)
    return s.done(.05)

def panel(w,h,k=2):
    "A dark ink wash with a torn edge and a hand-ruled line inside it."
    W,H=w*k,h*k; s=Sheet(W,H,w+h); r=s.r; m=8
    p=s.rough([(m,m),(W-m,m),(W-m,H-m),(m,H-m)],3.2); mk=s.fill(p,'#1f1a18',235)
    n=min(H//3,70)
    s.fill(s.curve([(0,H*.62),(W*.3,H*.55),(W*.7,H*.68),(W,H*.56),(W,H),(0,H)],True,6),'#191513',235,clip=mk)
    s.line(p,5,INK,closed=True,taper=False)
    q=s.rough([(m+9,m+9),(W-m-9,m+9),(W-m-9,H-m-9),(m+9,H-m-9)],1.6); s.line(q,2.2,'#a6936a',closed=True,taper=False,dry=.14)
    for cx,cy,sx,sy in ((m+9,m+9,1,1),(W-m-9,m+9,-1,1),(m+9,H-m-9,1,-1),(W-m-9,H-m-9,-1,-1)):
        s.stroke([(cx-sx*3,cy+sy*17),(cx+sx*5,cy+sy*5),(cx+sx*17,cy-sy*3)],3.4,'#c7b282',wob=.3)
        s.stroke([(cx+sx*10,cy+sy*14),(cx+sx*14,cy+sy*10)],2,'#c7b282',wob=.1)
    return s.done(.08)
def slot():
    s=Sheet(144,144,5); p=s.rough([(9,9),(135,9),(135,135),(9,135)],2.4); m=s.fill(p,'#2b2522',245); s.line(p,4.2,INK,closed=True,taper=False)
    q=s.rough([(17,17),(127,17),(127,127),(17,127)],1.2); s.line(q,2,'#a6936a',closed=True,taper=False,dry=.14)
    return s.done(.08)
def slash():
    out=np.zeros((192,576,4),dtype=np.uint8)
    for f in range(3):
        s=Sheet(192,192,30+f); head=(f+1)/3
        a0=-math.pi+head*2*math.pi-1.9; a1=a0+1.9; t=np.linspace(0,1,70); ang=a0+(a1-a0)*t
        outer=np.stack([96+np.cos(ang)*88,96+np.sin(ang)*88],1); inner=np.stack([96+np.cos(ang)*(88-34*np.sin(t*math.pi)**.8*(.45+.55*t)),96+np.sin(ang)*(88-34*np.sin(t*math.pi)**.8*(.45+.55*t))],1)
        p=np.concatenate([outer,inner[::-1]]); s.fill(p,'#efe6cc'); s.line(p,3,INK,closed=True,taper=False)
        ang2=a0+(a1-a0)*t; mid=np.stack([96+np.cos(ang2)*70,96+np.sin(ang2)*70],1); s.line(mid[20:],3,'#8ed1b4')
        P.over(out,s.done(.04),f*192,0)
    return out

# ---- painted grounds
def bands(v,cols,edge=.02):
    "Paints a field in a few flat coats, with soft antialiased borders between them."
    n=len(cols); t=np.clip(v,0,.9999)*n; i=t.astype(int); f=t-i
    c=np.array([rgb(x) for x in cols],float); up=np.minimum(i+1,n-1); w=np.clip((f-(1-edge*n))/(edge*n),0,1)[...,None]
    return (c[i]*(1-w)+c[up]*w).astype(np.uint8)
def field(h,w,seed,scale=90):
    "Broad patches of paint with dragged, dry-brush borders."
    big=P.fbm(h,w,scale,seed,3); r=np.random.RandomState(seed+1)
    st=np.asarray(Image.fromarray((r.rand(h//3+1,w//34+2)*255).astype(np.uint8)).resize((w,h),Image.BICUBIC),dtype=float)/255
    return np.clip((big-.5)*1.5+.5+(st-.5)*.2,0,1)
def inkedge(m,seed,blur=3.2,w0=.05,w1=.17):
    d=P.blur(m.astype(float),blur); h,ww=m.shape; n=P.fbm(h,ww,30,seed,2); wd=w0+(w1-w0)*np.clip((n-.35)/.3,0,1)
    return np.clip((wd-np.abs(d-.5))/.03,0,1)
def stamp(G,mask,col):
    a=mask[...,None]; G[...,:3]=(G[...,:3]*(1-a)+np.array(rgb(col))*a).astype(np.uint8)
class Over:
    "Marks made with a small brush on top of a painted ground."
    def __init__(s,h,w): s.k=2; s.im=Image.new('RGBA',(w*2,h*2),(0,0,0,0)); s.d=ImageDraw.Draw(s.im)
    def blade(s,x,y,dx,dy,c,wd=1.6):
        pts=[(x+dx*t+dy*.0,y+dy*t+ (t*t)*abs(dy)*.25) for t in (0,.25,.5,.75,1)]
        for i,(a,b) in enumerate(zip(pts,pts[1:])): s.d.line([(a[0]*2,a[1]*2),(b[0]*2,b[1]*2)],fill=rgb(c)+(255,),width=max(int(round(wd*2*(1-i/5))),1))
    def dab(s,x,y,rx,ry,c,ink=None,seed=0):
        r=random.Random(seed); q=[(x+math.cos(a)*rx*r.uniform(.78,1.14),y+math.sin(a)*ry*r.uniform(.78,1.14)) for a in np.linspace(0,2*math.pi,9,endpoint=False)]
        s.d.polygon([(a*2,b*2) for a,b in q],fill=rgb(c)+(255,),outline=(rgb(ink)+(255,)) if ink else None)
    def tuft(s,x,y,r,cols):
        n=r.randint(3,6); h_=r.uniform(7,14)
        for i in range(n):
            s.blade(x+r.uniform(-4,4),y+1,r.uniform(-7,7),-h_*r.uniform(.6,1.1),INK,2.2)
        for i in range(n):
            s.blade(x+r.uniform(-4,4),y,r.uniform(-7,7),-h_*r.uniform(.6,1),r.choice(cols),1.4)
    def onto(s,G):
        o=np.asarray(s.im.resize((G.shape[1],G.shape[0]),Image.LANCZOS),dtype=float); a=o[...,3:]/255; G[...,:3]=(G[...,:3]*(1-a)+o[...,:3]*a).astype(np.uint8)
def flat_shadow(G,S,seed,amt=.5,tint=(18,20,34)):
    d=P.blur(S,2.5)+(P.fbm(S.shape[0],S.shape[1],16,seed,2)-.5)*.3; q=np.clip((d-.4)/.05,0,1)[...,None]*amt
    G[...,:3]=(G[...,:3]*(1-q)+np.array(tint)*q).astype(np.uint8)

GRASS=('#2f4a37','#3b5a3b','#4d6d40','#688246'); DIRT=('#6e5b48','#7a664f','#867159','#937d62'); FGR=('#18252b','#1d2e31','#233936','#2a433c'); FDIRT=('#33343a','#3c3c3e','#464541','#4f4c45')
def ground_village(root,g,o,W,H,I,houses):
    h,w=H*TX,W*TX; r=random.Random(77)
    G=np.dstack([bands(field(h,w,1),GRASS),np.full((h,w),255,np.uint8)])
    p=B.organic(B.cells(g,{I['path'],I['mat']}),5); c=bands(field(h,w,6,40),DIRT); G[p,:3]=c[p]
    so=B.cells(g,{I['soil']})>0; c=bands(np.clip(.5+.42*np.sin(np.arange(h)/5.2)[:,None]+(P.fbm(h,w,12,8,2)-.5)*.5,0,1),('#2e2422','#42332c','#574436')); G[so,:3]=c[so]
    wm=B.cells(g,{I['water']}); wo=B.organic(wm,9,12,.3); sh=B.organic(np.clip(P.blur(wm,14)*2.2,0,1),10,4,.25)&~wo; c=bands(field(h,w,12,18),('#6d6455','#8a7f6a','#a39881')); G[sh,:3]=c[sh]
    d=P.blur(wo.astype(float),20); wv=np.clip(1-np.clip((d-.42)/.55,0,1)+(P.fbm(h,w,24,13,2)-.5)*.34,0,1); c=bands(wv,('#23465e','#2f5e72','#467f8a','#79a9a2')); G[wo,:3]=c[wo]
    for mk,sd in ((p,41),(wo,42),(sh,43)): stamp(G,inkedge(mk,sd),INK)
    S=np.zeros((h,w))
    for c0,r0,hw,_ in houses: S[(r0+4)*TX:(r0+5)*TX+22,c0*TX+6:(c0+hw)*TX+34]=1
    for y in range(H):
        for x in range(W):
            n=o[y][x]; a,b=x*TX,y*TX
            if n==I['trunk']: B.cast(S,a+TX/2,b+TX,64,22)
            elif n==I['fence']: S[b+36:b+44,a:a+TX]=np.maximum(S[b+36:b+44,a:a+TX],.8)
            elif n==I['well']: B.cast(S,a+TX/2,b+TX,34,16)
            elif n==I['sign']: B.cast(S,a+TX/2,b+TX,20,8)
    flat_shadow(G,S,3,.38)
    O=Over(h,w); FL=('#d9cfae','#d4a24c','#b0647f','#8a97c8')
    for _ in range(int(w*h/2600)):
        x,y=r.randrange(4,w-4),r.randrange(4,h-4); cx,cy=int(x/TX),int(y/TX)
        if g[cy][cx] in (I['grass'],I['flowers']) and not p[y,x] and not wo[y,x] and not sh[y,x]: O.tuft(x,y,r,('#79914c','#5b7843','#a4a35a'))
    for y in range(H):
        for x in range(W):
            if g[y][x]==I['soil']:
                cx,cy=x*TX+TX/2,y*TX+TX*.62
                O.dab(cx,cy,15,11,'#3a5c3c',INK,x+y*40); O.dab(cx-4,cy-3,8,6,'#6d8c4c',None,x+y*41); O.dab(cx+6,cy-1,5,4,'#a0ad5e',None,x+y*42)
            elif o[y][x]==-1 and g[y][x]==I['flowers']:
                for _ in range(4):
                    a,b=x*TX+r.randint(6,TX-7),y*TX+r.randint(6,TX-7); col=r.choice(FL); O.blade(a,b+6,r.uniform(-2,2),-7,'#26382f',1.4)
                    for t in range(5): O.dab(a+math.cos(t*1.26)*3.4,b+math.sin(t*1.26)*2.8,2.5,2.2,col,None,t)
                    O.dab(a,b,1.7,1.5,'#4d3324')
    for _ in range(260):
        x,y=r.randrange(w),r.randrange(h)
        if p[y,x]: O.dab(x,y,r.uniform(2,6),r.uniform(1.5,4),r.choice(('#6b5a48','#a18c6c','#b8a582')),INK,r.randrange(999))
    for _ in range(90):
        x,y=r.randrange(w),r.randrange(h)
        if wo[y,x]:
            L=r.uniform(14,46); O.d.line([((x+t)*2,(y+math.sin(t/7)*1.4)*2) for t in np.linspace(0,L,9)],fill=rgb(r.choice(('#b6d0c0','#8cb8ad')))+(255,),width=2)
    O.onto(G)
    mx,my=11*TX,8*TX; mat=G[my+8:my+40,mx+5:mx+43]; mat[...,:3]=rgb('#6d3448'); G[my+8:my+11,mx+5:mx+43,:3]=rgb(INK); G[my+37:my+40,mx+5:mx+43,:3]=rgb(INK); G[my+8:my+40,mx+5:mx+8,:3]=rgb(INK); G[my+8:my+40,mx+40:mx+43,:3]=rgb(INK)
    gouache(G,91,.08); B.fade(G); save(G,f'{root}/assets/village_ground.png')
    return wo
def shimmer(root,wo,pond):
    c0,r0,cw,ch=pond; fh,fw=ch*TX,cw*TX; m=wo[r0*TX:(r0+ch)*TX,c0*TX:(c0+cw)*TX]; sh=np.zeros((fh,fw*4,4),dtype=np.uint8)
    for f in range(4):
        r=random.Random(40+f); im=Image.new('L',(fw*2,fh*2),0); d=ImageDraw.Draw(im)
        for _ in range(46):
            x,y=r.randrange(fw),r.randrange(fh)
            if m[y,x]: L=r.uniform(8,30); d.line([((x+t)*2,(y+math.sin(t/6+f)*1.3)*2) for t in np.linspace(0,L,8)],fill=255,width=2)
        a=np.asarray(im.resize((fw,fh),Image.LANCZOS),dtype=float); fr=sh[0:fh,f*fw:(f+1)*fw]; fr[...,:3]=(222,236,214); fr[...,3]=(a*.62).astype(np.uint8)
    save(sh,f'{root}/assets/shimmer.png')
def ground_forest(root,g,o,W,H,I):
    h,w=H*TX,W*TX; r=random.Random(31); G=np.dstack([bands(field(h,w,21,70),FGR),np.full((h,w),255,np.uint8)])
    p=B.organic(B.cells(g,{I['forest_path']}),25,8,.55); c=bands(field(h,w,26,32),FDIRT); G[p,:3]=c[p]; stamp(G,inkedge(p,44),'#0e0c0e')
    S=np.zeros((h,w))
    for y in range(H):
        for x in range(W):
            n=o[y][x]; a,b=x*TX,y*TX
            if n==I['forest_trunk']: B.cast(S,a+TX/2,b+TX,70,26)
            elif n==I['rock']: B.cast(S,a+TX/2,b+TX,26,10)
    flat_shadow(G,S,5,.36,(6,10,18))
    O=Over(h,w)
    for _ in range(int(w*h/4200)):
        x,y=r.randrange(4,w-4),r.randrange(4,h-4)
        if not p[y,x]: O.tuft(x,y,r,('#2f4a3e','#3f6050','#577a5e'))
    for _ in range(int(w*h/1900)):
        x,y=r.randrange(w),r.randrange(h); O.dab(x,y,r.uniform(2,4.6),r.uniform(1.4,2.8),r.choice(('#6a5429','#4e4b2c','#3d4530','#7d5f2e','#7a3f30')),None,r.randrange(999))
    for y in range(H):
        for x in range(W):
            a,b=x*TX,y*TX
            if g[y][x]==I['mushroom'] and o[y][x]==-1:
                for k in range(r.randint(1,3)):
                    cx,cy=a+r.randint(10,TX-10),b+r.randint(12,TX-8); O.d.rectangle(((cx-2)*2,cy*2,(cx+2)*2,(cy+8)*2),fill=rgb('#d3c7ad')+(255,),outline=rgb(INK)+(255,)); O.d.pieslice(((cx-11)*2,(cy-10)*2,(cx+11)*2,(cy+10)*2),180,360,fill=rgb('#a03f4d')+(255,),outline=rgb(INK)+(255,),width=3); O.dab(cx-4,cy-5,2,1.5,'#e6cdb0'); O.dab(cx+3,cy-3,1.6,1.2,'#e6cdb0')
    O.onto(G); gouache(G,92,.08); B.fade(G); save(G,f'{root}/assets/forest_ground.png')
def ground_house(root,g,o,W,H,I):
    h,w=H*TX,W*TX; G=np.zeros((h,w,4),dtype=np.uint8); G[...,:3]=rgb('#0e0b0d'); G[...,3]=255; r=random.Random(5)
    fl=B.cells(g,{I['floor'],I['rug'],I['exit_mat']})>0; O=Over(h,w); PL=('#6a4a35','#74523a','#5f4331','#7f5c42'); C_=np.zeros((h,w,3),dtype=np.uint8)
    y=0
    while y<h:
        ph=r.randint(32,42); x=-r.randint(0,120)
        while x<w:
            pw=r.randint(150,300); C_[y:y+ph,max(x,0):max(x+pw,0)]=rgb(r.choice(PL))
            if r.random()<.9: O.d.line([((x+pw)*2,y*2),((x+pw+r.uniform(-1,1))*2,(y+ph)*2)],fill=rgb(INK)+(255,),width=3)
            for _ in range(2):
                gx=x+r.randint(10,max(pw-50,12)); gy=y+r.randint(6,ph-6); L=r.randint(20,90); O.d.line([((gx+t)*2,(gy+math.sin(t/14)*1.5)*2) for t in np.linspace(0,L,8)],fill=rgb('#3c2a22')+(255,),width=1)
            for dx in (6,pw-8): O.dab(x+dx,y+7,1.6,1.6,'#231a18'); O.dab(x+dx,y+ph-7,1.6,1.6,'#231a18')
            x+=pw
        O.d.line([(0,(y+ph)*2),(w*2,(y+ph+r.uniform(-1,1))*2)],fill=rgb(INK)+(255,),width=4); y+=ph
    G[fl,:3]=C_[fl]
    O2=np.array(O.im.resize((w,h),Image.LANCZOS)); O2[~fl,3]=0; O.im=Image.fromarray(O2,'RGBA').resize((w*2,h*2)); O.onto(G)
    x0,y0,x1,y1=13*TX,9*TX,18*TX,11*TX; s=Sheet(x1-x0,y1-y0,6)
    rw,rh=x1-x0,y1-y0; p,m=s.shape([(4,4),(rw-4,4),(rw-4,rh-4),(4,rh-4)],'#6d3448',lw=3.4,smooth=False,wob=2)
    q=s.rough([(16,14),(rw-16,14),(rw-16,rh-14),(16,rh-14)],1.2); s.line(q,3,'#c79b42',closed=True,taper=False)
    for i in range(1,5):
        cx=rw*i/5; cy=rh/2; s.shape([(cx-22,cy),(cx,cy-18),(cx+22,cy),(cx,cy+18)],'#a35a62' if i%2 else '#46294a',lw=2,smooth=False,wob=.8)
    P.over(G,s.done(.08),x0,y0)
    mw=2*TX; s=Sheet(mw,TX,12); s.shape([(4,5),(mw-4,4),(mw-3,TX-5),(3,TX-4)],'#6d3448',lw=3,smooth=False,wob=1.2)
    q=s.rough([(13,12),(mw-13,12),(mw-13,TX-12),(13,TX-12)],.8); s.line(q,2,'#c79b42',closed=True,taper=False,dry=.1)
    s.stroke([(mw/2-16,17),(mw/2,31),(mw/2+16,17)],4.4,'#ddd2b6',wob=.3); P.over(G,s.done(.05),15*TX,14*TX)
    gouache(G,93,.07)
    S=np.zeros((h,w)); S[:,8*TX:9*TX+12]=1; S[:,22*TX-12:23*TX]=1; S[3*TX:4*TX+24,:]=1; flat_shadow(G,S,8,.5,(10,6,14))
    save(G,f'{root}/assets/house_ground.png')

def wall_img(cols):
    W,H=cols*64,300; s=Sheet(W,H,13); r=s.r
    p=s.rough([(0,0),(W,0),(W,H),(0,H)],0); mk=s.fill(p,'#5c5262')
    s.fill(s.curve([(-8,-8),(W+8,-8),(W+8,86),(W*.7,110),(W*.4,84),(0,112)],True,5),'#3e3748',clip=mk)
    s.fill(s.curve([(W*.1,160),(W*.32,136),(W*.5,170),(W*.34,214),(W*.12,212)],True,5),'#6c6172',clip=mk)
    y=112
    while y<H-36:
        x=r.randint(-30,0)
        while x<W:
            wd=r.randint(46,86)
            if r.random()<.42: s.stroke([(x,y+18),(x+wd,y+18+r.uniform(-1,1)),(x+wd,y)],1.4,'#2d2734',wob=.8)
            x+=wd
        y+=r.randint(26,36)
    def bm(x0,y0,x1,y1): s.shape([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],'#3b2a24',lw=2.8,smooth=False,wob=1.2)
    for x in range(0,W,96): bm(x,0,x+11,H)
    bm(0,68,W,80); bm(-2,H-36,W+2,H)
    for c0 in (4,5):
        sx=c0*64; bm(sx-5,84,sx+65,H-34); s.shape([(sx+2,92),(sx+60,92),(sx+60,262),(sx+2,262)],'#191316',lw=2,smooth=False,wob=.7)
        for row in (96,180):
            bm(sx+1,row+72,sx+61,row+78); x=sx+4
            while x<sx+55:
                wd=r.randint(7,12); hh=r.randint(44,66); cl=r.choice(['#7a3f4c','#3d6a5e','#a58340','#3f5a7e','#60467e','#9a5f33']); s.shape([(x,row+72),(x+.5,row+72-hh),(x+wd,row+72-hh+r.randint(-2,2)),(x+wd,row+72)],cl,lw=1.6,smooth=False,wob=.5)
                if r.random()<.5: s.stroke([(x+2,row+72-hh*.7),(x+wd-2,row+72-hh*.7)],1.2,'#e6cdb0',wob=.1)
                x+=wd+1
    hx=10*64; s.shape([(hx-26,H),(hx-22,60),(hx+86,58),(hx+90,H)],'#5c5662',lw=3.4,smooth=False,wob=1.8)
    for yy in range(70,H-4,24):
        x=hx-22+r.randint(0,14)
        while x<hx+80: s.stroke([(x,yy),(x+r.randint(16,28),yy+r.uniform(-1,1)),],1.4,'#2d2734'); x+=r.randint(30,40)
    s.shape([(hx-2,H-2),(hx-1,178),(hx+32,148),(hx+66,178),(hx+67,H-2)],'#110c0e',lw=3,wob=1)
    s.shape([(hx-30,146),(hx+94,144),(hx+96,160),(hx-32,162)],'#4a3429',lw=3,smooth=False,wob=1)
    wx=7*64; bm(wx-9,90,wx+97,218); g,gm=s.shape([(wx,100),(wx+88,100),(wx+88,208),(wx,208)],'#2f4b78',lw=2,smooth=False,wob=.7)
    s.fill(s.curve([(wx-4,150),(wx+50,136),(wx+92,158),(wx+92,212),(wx-4,212)],True,3),'#1e3158',clip=gm); s.fill(s.curve([(wx+56,114),(wx+66,108),(wx+76,116),(wx+66,126)],True,.6),'#dfdcbe',clip=gm)
    s.stroke([(wx+44,100),(wx+44,208)],4); s.stroke([(wx,154),(wx+88,154)],4)
    return s.done(.08)

# ---- what lies behind the world and hangs in front of it
def ridge(w,base,amp,seed,knots=9):
    return base+noise1(w,knots,seed)*amp+noise1(w,knots*4,seed+1)*amp*.3
def treeline(s,w,base,seed,col,hs=(70,130)):
    r=random.Random(seed); x=-20
    while x<w+20:
        wd=r.randint(46,96); ht=r.randint(*hs); p=scallop(x,base-ht*.55,wd*.75,ht*.75,r.randint(5,8),r.randrange(9999),.2,2.5); s.fill(p,col)
        s.fill(s.rough([(x-3,base-ht*.3),(x+3,base-ht*.3),(x+5,base+140),(x-5,base+140)],1),col); x+=int(wd*r.uniform(.8,1.2))
def backdrop(kind):
    h,w=540,960
    if kind=='house':
        s=np.zeros((h,w,4),dtype=np.uint8); s[...,:3]=rgb('#0e0b0d'); s[...,3]=255; return s
    if kind=='village': sky=('#2a2b48','#403c5a','#675266','#96705f','#c3936b'); L=(('#544c68',250,'#5c5168'),('#3f3d57',300,'#4a4560'),('#2d2f47',350,None))
    else: sky=('#0c151e','#111f29','#172b33','#1f3a3c','#2b4a45'); L=(('#1a2f36',220,'#26423f'),('#14252c',280,'#1d3536'),('#0e1a21',340,None))
    v=np.clip(np.linspace(0,1,h)[:,None]*np.ones((h,w))*1.25+(P.fbm(h,w,70,4,3)-.5)*.34,0,1); a=np.dstack([bands(v,sky),np.full((h,w),255,np.uint8)])
    s=Sheet(w,h,17 if kind=='village' else 18); s.im=Image.new('RGBA',(w*SS,h*SS),(0,0,0,0))
    for i,(col,base,mist) in enumerate(L):
        treeline(s,w,base,31+i*7+(kind=='forest'),col,(60+i*26,120+i*34)) if not (kind=='village' and i==0) else s.fill(np.concatenate([np.stack([np.arange(-4,w+4,4.0),ridge(len(np.arange(-4,w+4,4.0)),base-30,34,5)],1),[(w+4,h+4),(-4,h+4)]]),col)
        s.fill(s.rough([(-4,base+40),(w+4,base+40),(w+4,h+4),(-4,h+4)],6),col)
    b=np.asarray(s.im.resize((w,h),Image.LANCZOS)); P.over(a,b,0,0)
    # mist laid over each ridge in thin horizontal veils
    Y=np.arange(h)[:,None]; n=P.fbm(h,w,120,9,3); mistc=np.array(rgb('#b8a998' if kind=='village' else '#5d8078'),float)
    for base,amt in ((270,.32),(330,.3)):
        q=np.clip(1-np.abs(Y-base)/46,0,1)*np.clip((n-.28)/.34,0,1)*amt; a[...,:3]=(a[...,:3]*(1-q[...,None])+mistc*q[...,None]).astype(np.uint8)
    return gouache(a,17,.08)
def light(kind):
    h,w=540,960; Y,X=np.mgrid[0:h,0:w]; a=np.zeros((h,w,4),dtype=float); vig=np.clip(np.hypot((X-480)/640,(Y-270)/390)-.62,0,1)*1.8; fog=np.clip(1-Y/230,0,1)**1.6
    if kind=='village':
        warm=np.clip(1-np.hypot((X+80)/900,(Y+120)/700),0,1)*.2; cool=vig*.42+fog*.32; wc,cc=[244,190,130],[58,50,84]
    elif kind=='forest':
        sh=np.clip(np.sin((X+Y*.62)/58+1.2*np.sin(Y/140))-.5,0,1)*2*np.clip(1-Y/300,0,1); warm=sh*.15; cool=(.12+vig*.5+fog*.5)*(1-sh*.4); wc,cc=[206,226,170],[18,42,48]
    else:
        fire=np.clip(1-np.hypot((X-640)/430,(Y-210)/340),0,1); warm=fire*.26; cool=(.12+vig*.55)*np.clip(1.25-fire*1.5,0,1); wc,cc=[246,160,84],[22,14,34]
    al=1-(1-warm)*(1-cool); mix=(warm/np.maximum(warm+cool,1e-4))[...,None]; a[...,:3]=np.array(wc)*mix+np.array(cc)*(1-mix); a[...,3]=np.clip(al,0,1)*255
    return a.astype(np.uint8)

def build(root):
    A=f'{root}/assets'; os.makedirs(A,exist_ok=True)
    save(person_sheet('hero'),f'{A}/hero.png'); save(npc_sheet('mira'),f'{A}/mira.png'); save(npc_sheet('tobin'),f'{A}/tobin.png'); save(slime_sheet(),f'{A}/slime.png')
    for n in ('jelly','potion','coin','heart'): save(icon(n),f'{A}/{n}.png')
    save(tree_sheet(VILLAGE_TREE,301),f'{A}/trees.png'); save(tree_sheet(FOREST_TREE,401,True),f'{A}/dark_trees.png')
    save(cottage(7,50,('#5b2c2a','#8f4a3a','#a05c44')),f'{A}/house_a.png'); save(cottage(6,79,('#25334f','#3f5777','#4c6684')),f'{A}/house_b.png')
    save(fence_run(9),f'{A}/fence_long.png'); save(fence_run(1),f'{A}/fence_short.png'); save(well_img(),f'{A}/well.png'); save(sign_img(),f'{A}/sign.png'); save(table_img(),f'{A}/table.png'); save(bed_img(),f'{A}/bed.png'); save(wall_img(15),f'{A}/back_wall.png'); save(fire_sheet(),f'{A}/fire.png'); save(rock_img(),f'{A}/rock.png')
    for k in ('village','forest','house'): save(backdrop(k),f'{A}/backdrop_{k}.png'); save(light(k),f'{A}/light_{k}.png')
    save(slash(),f'{A}/slash.png'); save(slot(),f'{A}/slot.png')
    for n,(w,h) in dict(panel_hud=(300,68),panel_quest=(224,32),panel_hint=(358,28),panel_dialog=(880,124),panel_bag=(520,360)).items(): save(panel(w,h),f'{A}/{n}.png')
    for name,cols,seed in (('outer_village',GRASS,5),('outer_forest',FGR,6)):
        save(np.dstack([bands(field(128,256,seed,50)*.6,cols),np.full((128,256),255,np.uint8)]),f'{A}/{name}.png')
    save(np.zeros((4,4,4),dtype=np.uint8),f'{A}/clear.png'); save(np.zeros((16,16,4),dtype=np.uint8),f'{A}/collision.png')
