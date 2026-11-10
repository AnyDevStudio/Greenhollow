# Greenhollow's hi-bit art: original, made entirely by this code. Shapes are lit like small 3D volumes, then
# quantized to hand-picked color ramps with ordered dithering, so it stays pixel art with real light and shadow.
import math, os, random, sys
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art as Old

TX = 32  # texels per map cell; a texel is drawn 2x2 world units
LIGHT = np.array([-0.52, -0.62, 0.59])

def rgb(s): return (int(s[1:3],16), int(s[3:5],16), int(s[5:7],16))
def R(*cols): return np.array([rgb(c) for c in cols], dtype=np.uint8)
_B = np.array([[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],
               [3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]])/64.0-0.5
def bayer(h,w,ox=0,oy=0): return np.tile(np.roll(np.roll(_B,oy,0),ox,1),(h//8+1,w//8+1))[:h,:w]
def shade(v,ramp,d=0.8):
    n=len(ramp); idx=np.clip(np.floor(v*(n-1)+0.5+bayer(*v.shape)*d),0,n-1).astype(int); return ramp[idx]
def noise(h,w,cell,seed):
    r=np.random.RandomState(seed); gh,gw=h//cell+3,w//cell+3; g=r.rand(gh,gw)
    y=np.arange(h)/cell; x=np.arange(w)/cell; yi=y.astype(int); xi=x.astype(int); fy=y-yi; fx=x-xi
    fy=fy*fy*(3-2*fy); fx=fx*fx*(3-2*fx)
    a=g[np.ix_(yi,xi)]; b=g[np.ix_(yi,xi+1)]; c=g[np.ix_(yi+1,xi)]; d=g[np.ix_(yi+1,xi+1)]
    fx=fx[None,:]; fy=fy[:,None]
    return (a*(1-fx)+b*fx)*(1-fy)+(c*(1-fx)+d*fx)*fy
def fbm(h,w,cell,seed,octs=4):
    t=np.zeros((h,w)); amp=1.0; tot=0
    for i in range(octs):
        t+=noise(h,w,max(cell>>i,1),seed+i*17)*amp; tot+=amp; amp*=.5
    return t/tot
def blur(m,r): return np.asarray(Image.fromarray((np.clip(m,0,1)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)),dtype=float)/255
def canvas(h,w): return np.zeros((h,w,4),dtype=np.uint8)
def over(dst,src,x,y):
    x=int(round(x)); y=int(round(y)); h,w=src.shape[:2]; H,W=dst.shape[:2]
    x0,y0=max(x,0),max(y,0); x1,y1=min(x+w,W),min(y+h,H)
    if x0>=x1 or y0>=y1: return
    s=src[y0-y:y1-y,x0-x:x1-x].astype(float); d=dst[y0:y1,x0:x1].astype(float)
    sa=s[...,3:]/255; da=d[...,3:]/255; oa=sa+da*(1-sa); safe=np.where(oa==0,1,oa)
    c=(s[...,:3]*sa+d[...,:3]*da*(1-sa))/safe
    dst[y0:y1,x0:x1,:3]=c.astype(np.uint8); dst[y0:y1,x0:x1,3]=(oa[...,0]*255).astype(np.uint8)
def grid_xy(s): h,w=s.shape[:2]; return np.mgrid[0:h,0:w]

def blob(s,cx,cy,rx,ry,ramp,bias=0.0,d=0.7,alpha=255,keep=None,L=LIGHT):
    yy,xx=grid_xy(s); nx=(xx+.5-cx)/rx; ny=(yy+.5-cy)/ry; q=nx*nx+ny*ny; inside=q<=1
    if keep is not None: inside&=keep(xx+.5,yy+.5)
    nz=np.sqrt(np.clip(1-q,0,1)); l=np.clip(nx*L[0]+ny*L[1]+nz*L[2],0,1)
    c=shade(np.clip(.08+.92*l+bias,0,1),ramp,d); s[inside,:3]=c[inside]; s[inside,3]=alpha
def bar(s,x0,y0,x1,y1,ramp,vertical=True,bias=0.0,d=0.6,alpha=255):
    x0,y0,x1,y1=[int(v) for v in (x0,y0,x1,y1)]; h,w=y1-y0,x1-x0
    if h<=0 or w<=0: return
    t=(np.arange(w)+.5)/w*2-1 if vertical else (np.arange(h)+.5)/h*2-1
    nz=np.sqrt(np.clip(1-t*t,0,1)); l=np.clip(t*(LIGHT[0] if vertical else LIGHT[1])+nz*LIGHT[2],0,1)
    v=np.tile(l[None,:],(h,1)) if vertical else np.tile(l[:,None],(1,w))
    c=shade(np.clip(.1+.9*v+bias,0,1),ramp,d); H,W=s.shape[:2]
    ax0,ay0,ax1,ay1=max(x0,0),max(y0,0),min(x1,W),min(y1,H)
    if ax0>=ax1 or ay0>=ay1: return
    s[ay0:ay1,ax0:ax1,:3]=c[ay0-y0:ay1-y0,ax0-x0:ax1-x0]; s[ay0:ay1,ax0:ax1,3]=alpha
def fill(s,x0,y0,x1,y1,c,alpha=255):
    H,W=s.shape[:2]; a,b,e,f=max(int(x0),0),max(int(y0),0),min(int(x1),W),min(int(y1),H)
    if a<e and b<f: s[b:f,a:e,:3]=rgb(c); s[b:f,a:e,3]=alpha
def px(s,x,y,c,alpha=255):
    if 0<=y<s.shape[0] and 0<=x<s.shape[1]: s[y,x,:3]=rgb(c); s[y,x,3]=alpha
def outline(s,c='#22182c'):
    a=s[...,3]>60; n=np.zeros_like(a)
    n[1:]|=a[:-1]; n[:-1]|=a[1:]; n[:,1:]|=a[:,:-1]; n[:,:-1]|=a[:,1:]
    e=n&~a; s[e,:3]=rgb(c); s[e,3]=255
def ground_shadow(s,cx,cy,rx,ry,alpha=95):
    yy,xx=grid_xy(s); q=((xx+.5-cx)/rx)**2+((yy+.5-cy)/ry)**2; m=(q<=1)&(s[...,3]==0)
    s[m,:3]=(24,18,40); s[m,3]=alpha

# ---- ramps
SKIN=R('#8a4f3c','#b8744f','#dc9c74','#f3c49c','#ffe0c0'); HAIR=R('#2e1a18','#4c2a1e','#6e4128','#935c34','#b98046')
TUNIC=R('#123d33','#1c5c44','#2a7d55','#43a065','#73c47e'); PANTS=R('#1c2038','#2b3254','#3d4874','#57689a'); BOOT=R('#27160f','#472a18','#6c4325','#94633a')
BELT=R('#3a2112','#5e3a1e','#83562e'); METAL=R('#6d4a1c','#a97a26','#e0b23e','#fff0a0'); CAPE=R('#4a1626','#71223a','#9c3350','#c8506c')
ROBE=R('#2e1648','#4a2470','#6a389a','#8e55c0','#b681df'); SILVER=R('#5c5a70','#8a8aa0','#b8b8c8','#e4e4ee','#ffffff'); APRON=R('#a89a88','#d0c4b0','#efe6d4','#fff9ec')
ORANGE=R('#5a2410','#8f3f16','#c2641f','#e8903a','#f8bc68'); DARK=R('#1a1420','#2c2436','#433a50')

def person(style,direction,leg,breathe=0):
    s=canvas(32,32); up=breathe
    if style=='hero': top,bot,hair=TUNIC,PANTS,HAIR
    elif style=='mira': top,bot,hair=ROBE,ROBE,SILVER
    else: top,bot,hair=ORANGE,DARK,SILVER
    robe=style=='mira'
    swing=leg*2
    if direction=='up' and style=='hero': pass
    if robe:
        for y in range(19,30):
            t=(y-19)/10; hw=6.5+3*t
            bar(s,16-hw,y,16+hw,y+1,bot,True,bias=-.05*t)
        fill(s,8,29,24,30,'#2e1648')
    elif direction=='side':
        f,b=(leg*3,-leg*3)
        bar(s,13+b,24,17+b,29,bot,True,bias=-.18); bar(s,12+b,28,17+b+1,31,BOOT,False,bias=-.15)
        bar(s,13+f,24,17+f,29,bot,True); bar(s,13+f,28,18+f,31,BOOT,False)
    else:
        l=max(leg,0)*1; r=max(-leg,0)*1
        bar(s,11,24,15,29-r,bot,True); bar(s,17,24,21,29-l,bot,True)
        bar(s,10,28-r,15,31-r,BOOT,False); bar(s,17,28-l,22,31-l,BOOT,False)
    if not robe and style=='hero' and direction=='up':
        pass
    dy=up
    if direction=='side':
        blob(s,16,20+dy,7,7.5,top,keep=lambda x,y:y<26+dy)
        if style=='hero': fill(s,10,23+dy,23,25+dy,'#5e3a1e'); px(s,18,23+dy,'#e0b23e'); px(s,18,24+dy,'#a97a26')
        blob(s,16-leg*2.5,20+dy,2.6,5.5,top,bias=.05); blob(s,16-leg*2.5,25+dy,2.3,2.3,SKIN)
    else:
        blob(s,16,20+dy,8,7.5,top,keep=lambda x,y:y<26+dy)
        if style=='hero' and direction=='down':
            fill(s,9,23+dy,24,25+dy,'#5e3a1e'); bar(s,14,23+dy,18,25+dy,METAL,False)
            blob(s,12,17+dy,3,2.4,top,bias=.2)
            blob(s,20,17+dy,3,2.4,top,bias=.1)
        if style=='tobin' and direction=='down': blob(s,16,22+dy,4.4,3.4,APRON)
        if style=='mira' and direction=='down': blob(s,16,23+dy,4.5,5,APRON,keep=lambda x,y:y>20+dy); fill(s,11,20+dy,21,21+dy,'#e0b23e')
        blob(s,8,20+dy-swing*.4,2.7,5.4,top,bias=-.02); blob(s,24,20+dy+swing*.4,2.7,5.4,top,bias=-.12)
        blob(s,8,25+dy-swing*.4,2.4,2.3,SKIN); blob(s,24,25+dy+swing*.4,2.4,2.3,SKIN,bias=-.1)
    if style=='hero' and direction=='up':
        for y in range(16+dy,27+dy):
            hw=6+ (y-16-dy)*.25; bar(s,16-hw,y,16+hw,y+1,CAPE,True)
        fill(s,10,16+dy,22,17+dy,'#c8506c')
    hx=16+(1.5 if direction=='side' else 0); hy=10+dy
    blob(s,hx,hy,7.2,7,SKIN,bias=.05)
    if direction=='down':
        blob(s,16,8+dy,8,6.8,hair,keep=lambda x,y:y<9.5+dy+1.7*np.sin(x*1.1)**2)
        blob(s,9.2,11+dy,1.7,3.6,hair,bias=-.1); blob(s,22.8,11+dy,1.7,3.6,hair,bias=-.15)
        for ex in (12,19):
            fill(s,ex,11+dy,ex+2,14+dy,'#fff8f0'); fill(s,ex+(1 if ex==12 else 0),12+dy,ex+1+(1 if ex==12 else 0),14+dy,'#2a1e38'); px(s,ex+(1 if ex==12 else 0),12+dy,'#7fb8f0')
        px(s,11,14+dy,'#e88a78'); px(s,21,14+dy,'#e88a78'); fill(s,15,15+dy,17,16+dy,'#a45a44')
    elif direction=='up':
        blob(s,16,9.5+dy,8,7.8,hair,bias=.02)
    else:
        blob(s,hx-.4,8+dy,7.9,6.2,hair,keep=lambda x,y:y<8.6+dy+.9*np.sin(x*1.3))
        blob(s,12.4,10+dy,5.6,6.6,hair,bias=-.04,keep=lambda x,y:x<15.2)
        blob(s,9.5,12+dy,2.2,3.2,hair,bias=-.1)
        fill(s,19,11+dy,21,14+dy,'#fff8f0'); fill(s,20,12+dy,21,14+dy,'#2a1e38'); px(s,20,12+dy,'#7fb8f0'); px(s,18,14+dy,'#e88a78'); px(s,23,12+dy,'#dc9c74')
    if style=='tobin' and direction=='down': blob(s,16,16.5+dy,6,4.4,SILVER,keep=lambda x,y:y>13.5+dy); fill(s,15,14+dy,17,15+dy,'#a45a44')
    if style=='mira' and direction!='down': blob(s,16,4+dy,3.6,3,SILVER)
    if style=='mira' and direction=='down': blob(s,16,2.6+dy,3.4,2.4,SILVER)
    outline(s); ground_shadow(s,16,30,11,2.6)
    return s

def person_sheet(style):
    out=canvas(32*3,32*4)
    for r,(d,legs) in enumerate((('down',(0,1,0,-1)),('up',(0,-1,0,1)),('side',(0,1,0,-1)))):
        for c,l in enumerate(legs):
            over(out,person(style,d,l,1 if l else 0),c*32,r*32)
    return out
def npc_sheet(style):
    out=canvas(32,64)
    over(out,person(style,'down',0,0),0,0); over(out,person(style,'down',0,1),32,0)
    return out

SLIME=R('#17585a','#1f8080','#34aca0','#5cd4bc','#a2f2d8','#e4fff2')
def slime_frame(rx,ry,cy):
    s=canvas(32,32); base=27
    keep=lambda x,y:y<=base
    blob(s,16,cy,rx,ry,SLIME,bias=.05,alpha=225,keep=keep)
    ey=int(cy-ry*.12)
    for ex in (int(16-rx*.46),int(16+rx*.2)):
        fill(s,ex,ey,ex+4,ey+5,'#0e2a34'); fill(s,ex,ey,ex+2,ey+2,'#ffffff')
    fill(s,14,ey+6,19,ey+7,'#14505a')
    blob(s,16-rx*.42,cy-ry*.62,rx*.22,ry*.16,R('#ffffff'),d=0)
    outline(s,'#0e3440'); ground_shadow(s,16,28,rx+1,2.6)
    return s
def slime_sheet():
    out=canvas(32,96)
    for i,a in enumerate(((12,10,18),(10,12,16),(14,7.5,20))): over(out,slime_frame(*a),i*32,0)
    return out

def icon(name):
    s=canvas(32,32)
    if name=='jelly':
        blob(s,16,18,11,9.5,SLIME,bias=.05,alpha=230,keep=lambda x,y:y<26); blob(s,12,14,2.5,1.8,R('#ffffff'),d=0); blob(s,20,21,2,1.4,SLIME,bias=-.5)
    elif name=='potion':
        RED=R('#5a0f22','#961c34','#d0344a','#f06a6a','#ffb0a0'); GLASS=R('#6a7a90','#9cb0c4','#d8e8f4')
        blob(s,16,20,10,9.5,GLASS,bias=.1); blob(s,16,21.5,8.4,7.6,RED,keep=lambda x,y:y>15.5); bar(s,12,5,20,12,GLASS,True); bar(s,12,3,20,7,BOOT,True,bias=.1)
        fill(s,11,11,21,12,'#6a7a90'); blob(s,11.5,17,1.5,3,R('#ffffff'),d=0)
    elif name=='coin':
        G=METAL; blob(s,16,16,11.5,11.5,G,bias=.05); blob(s,16,16,8.5,8.5,G,bias=-.35); bar(s,14,10,18,22,G,True,bias=.25); fill(s,12,10,20,12,'#fff0a0'); fill(s,12,20,20,22,'#a97a26')
    elif name=='heart':
        RED=R('#5a0f22','#961c34','#d0344a','#f06a6a','#ffc0b4')
        blob(s,11,12,7,7,RED); blob(s,21,12,7,7,RED,bias=-.05)
        yy,xx=grid_xy(s); tri=(yy+.5>=12)&(np.abs(xx+.5-16)<=(27.5-(yy+.5))*.9)
        c=shade(np.clip(.62-(xx-16)/34-(yy-12)/42,0,1),RED); s[tri,:3]=c[tri]; s[tri,3]=255
        blob(s,10,9,2.6,1.9,R('#ffffff'),d=0)
    outline(s)
    return s

def panel(w,h,inner='#1c1430',a=238):
    s=canvas(h,w); yy,xx=grid_xy(s)
    grad=R('#150f26','#1c1430','#251a3e','#2e2150'); v=.75-(yy/h)*.6+(fbm(h,w,48,3)-.5)*.3
    c=shade(np.clip(v,0,1),grad,.9); s[...,:3]=c; s[...,3]=a
    G=METAL
    for t,(cc) in enumerate(('#3c2610','#e0b23e','#a97a26','#3c2610')):
        s[t,t:w-t,:3]=rgb(cc); s[h-1-t,t:w-t,:3]=rgb('#6d4a1c' if cc=='#e0b23e' else cc); s[t:h-t,t,:3]=rgb(cc); s[t:h-t,w-1-t,:3]=rgb('#6d4a1c' if cc=='#e0b23e' else cc)
    s[0:4,:,3]=255; s[h-4:h,:,3]=255; s[:,0:4,3]=255; s[:,w-4:w,3]=255
    for cx,cy in ((0,0),(w-12,0),(0,h-12),(w-12,h-12)):
        fill(s,cx,cy,cx+12,cy+12,'#3c2610'); bar(s,cx+2,cy+2,cx+10,cy+10,G,False,bias=.15); fill(s,cx+5,cy+5,cx+7,cy+7,'#fff0a0')
    return s
def slot():
    s=panel(72,72); yy,xx=grid_xy(s); m=(xx>8)&(xx<63)&(yy>8)&(yy<63); s[m,:3]=(40,30,64); return s

def slash():
    out=canvas(64,192); yy,xx=np.mgrid[0:64,0:64]; dx=xx+.5-32; dy=yy+.5-32; r=np.hypot(dx,dy); a=(np.arctan2(dy,dx)+math.pi)/(2*math.pi)
    C=R('#2a8a90','#5cd4bc','#c8fff0','#ffffff')
    for f in range(3):
        head=(f+1)/3.0; tr=(head-a)%1.0
        band=(r>=22)&(r<=31)&(tr<.55)
        v=np.clip((1-tr/.55)*(1-np.abs(r-27)/6),0,1)
        cols=shade(v,C,.6); fr=out[0:64,f*64:(f+1)*64]; fr[band,:3]=cols[band]; fr[band,3]=(np.clip(v*1.3+.15,0,1)[band]*255).astype(np.uint8)
    return out

# ---- world parts
LEAF=R('#123a2c','#1b5238','#2a6e41','#44904a','#70b252','#a8d060')
DLEAF=R('#0c2a28','#123c30','#1b5238','#2a6e41','#468a4c','#7cab58')
BARK=R('#2c1a14','#47291c','#684027','#8c5a36','#ad7a4c')
def tree_sprite(seed,leaf=LEAF):
    r=random.Random(seed); W,H=128,120; c=canvas(H,W); cx,cy=64,60; rx=r.randint(46,54); ry=r.randint(42,50)
    clusters=[]
    for _ in range(95):
        a=r.uniform(0,2*math.pi); d=math.sqrt(r.random()); clusters.append((cx+math.cos(a)*d*rx,cy+math.sin(a)*d*ry,r.uniform(9,16)))
    clusters.sort(key=lambda p:(p[1]-p[0]*.3))
    for x,y,rad in clusters:
        lit=-(y-cy)/ry*.28-(x-cx)/rx*.16
        blob(c,x,y,rad,rad*.92,leaf,bias=lit-.02,d=.95)
    a=c[...,3]>0; n=noise(H,W,3,seed+5)
    yy,xx=grid_xy(c); edge=blur(a.astype(float),2)
    c[(edge<.72)&(n<.55),3]=0
    outline(c,'#0d2a24')
    t=canvas(64,48)
    bar(t,17,0,31,58,BARK,True); 
    for i,x in enumerate((13,31)): bar(t,x,50,x+5,60,BARK,True,bias=-.1)
    blob(t,24,60,14,4.5,BARK,bias=.05); 
    bk=fbm(64,48,4,seed+9,2)<.42; m=(t[...,3]>0)&bk; t[m,:3]=(t[m,:3]*.74).astype(np.uint8)
    outline(t,'#22130e')
    return t,c

def flower(s,x,y,c1,c2,rng):
    for dx,dy in ((0,-2),(0,2),(-2,0),(2,0)):
        px(s,x+dx,y+dy,c1); px(s,x+dx+(1 if dx==0 else 0),y+dy+(1 if dy==0 else 0),c1)
    px(s,x,y,c2); px(s,x+1,y,c2)

def apply_shadow(g,S,strength=.46,tint=(26,30,70)):
    b=bayer(*S.shape); q=np.floor(np.clip(S,0,1)*4+.5+b*.7)/4; q=np.clip(q,0,1)[...,None]*strength
    g[...,:3]=(g[...,:3]*(1-q)+np.array(tint)*q*.55).astype(np.uint8)
def ell(S,cx,cy,rx,ry,v=1.0):
    H,W=S.shape; x0,x1=max(int(cx-rx),0),min(int(cx+rx)+1,W); y0,y1=max(int(cy-ry),0),min(int(cy+ry)+1,H)
    if x0>=x1 or y0>=y1: return
    yy,xx=np.mgrid[y0:y1,x0:x1]; m=((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1; S[y0:y1,x0:x1][m]=v

ROOF=R('#4a1c1c','#742a24','#a03e2c','#c85a38','#e58a56'); ROOF2=R('#1f2f50','#2f4874','#44689a','#6690bc','#9cc0d8')
PLASTER=R('#8c7a5c','#b8a47e','#dcc9a0','#f2e4c0','#fff6dc'); TIMBER=R('#2c1a14','#4a2c1c','#6e4428','#925f38')
STONE=R('#3c3a48','#5e5c6c','#858494','#b0afbc','#d8d8e0')
def house_img(w,seed,roof=ROOF):
    Wp,Hp=w*TX,5*TX; s=canvas(Hp,Wp); r=random.Random(seed)
    rh=TX*3-8; n=fbm(rh,Wp,12,seed)
    V=np.zeros((rh,Wp))
    for row in range(0,rh,8):
        off=0 if (row//8)%2 else 7
        for x in range(-off,Wp,14):
            q=r.uniform(-.1,.12); a,b=max(x,0),min(x+14,Wp); V[row:row+8,a:b]=.62+q-.25*(row/rh)+.12*(1-(a/Wp))
            V[row:row+8,max(x,0):max(x,0)+1]=.12
        V[row+7:row+8,:]=.14
    V+= (n-.5)*.2
    c=shade(np.clip(V,0,1),roof,.55); s[:rh,:,:3]=c; s[:rh,:,3]=255
    fill(s,0,0,Wp,3,'#2c1414'); bar(s,0,rh-6,Wp,rh,roof,False,bias=-.15); fill(s,0,rh-1,Wp,rh,'#241018')
    # chimney
    bar(s,Wp-52,2,Wp-34,34,STONE,True); fill(s,Wp-54,2,Wp-32,6,'#3c3a48'); fill(s,Wp-52,6,Wp-34,7,'#d8d8e0')
    wy=rh; wh=Hp-rh; n2=fbm(wh,Wp,8,seed+4)
    c=shade(np.clip(.62+(n2-.5)*.5-np.linspace(0,.28,wh)[:,None],0,1),PLASTER,.8); s[wy:Hp,:,:3]=c; s[wy:Hp,:,3]=255
    fill(s,0,wy,Wp,wy+7,'#3a2a26',255); s[wy:wy+12,:,:3]=(s[wy:wy+12,:,:3]*.78).astype(np.uint8)
    for x in list(range(0,Wp,TX*2))+[Wp-8]: bar(s,x,wy+2,x+8,Hp-8,TIMBER,True)
    bar(s,0,wy+30,Wp,wy+36,TIMBER,False)
    bar(s,0,Hp-8,Wp,Hp,STONE,False,bias=-.05)
    for x in range(0,Wp,12): fill(s,x,Hp-8,x+1,Hp,'#3c3a48')
    return s
def window(s,x,y):
    bar(s,x-3,y-3,x+25,y+27,TIMBER,False,bias=.1); GL=R('#2f5a84','#4f90b8','#8fd0e0','#e0fbff')
    yy,xx=grid_xy(s); m=(xx>=x)&(xx<x+22)&(yy>=y)&(yy<y+24); v=np.clip(((x+22-xx)/22*.5+(y+24-yy)/24*.5),0,1); c=shade(v,GL,.8); s[m,:3]=c[m]
    fill(s,x+10,y,x+12,y+24,'#4a2c1c'); fill(s,x,y+11,x+22,y+13,'#4a2c1c')
    bar(s,x-4,y+26,x+26,y+31,TIMBER,False)
    for i in range(6):
        blob(s,x+i*4+1,y+25,3,2.6,LEAF,bias=.15); px(s,x+i*4+1,y+24,'#f09ac0' if i%2 else '#ffe07a')
def door(s,x,y):
    bar(s,x-3,y-2,x+27,y+32,TIMBER,False,bias=.1); W=R('#472a18','#6c4325','#94633a','#b98046')
    bar(s,x,y,x+24,y+32,W,True)
    for t in (x+8,x+16): fill(s,t,y,t+1,y+32,'#3a2112')
    fill(s,x,y+6,x+24,y+8,'#3a2112'); fill(s,x,y+22,x+24,y+24,'#3a2112'); bar(s,x+18,y+13,x+22,y+18,METAL,False)
def fence_cell(s,x,y,h,v):
    W=R('#4a2c1c','#7a5230','#a97a4a','#d2a56e')
    if h:
        bar(s,x,y+11,x+TX,y+15,W,False); bar(s,x,y+19,x+TX,y+23,W,False)
    if v: bar(s,x+13,y,x+18,y+TX,W,True,bias=-.05)
    bar(s,x+12,y+6,x+20,y+29,W,True,bias=.1); fill(s,x+12,y+6,x+20,y+8,'#d2a56e'); fill(s,x+12,y+28,x+20,y+29,'#2c1a14')
def well(s,x,y):
    blob(s,x+16,y+24,15,8,STONE); blob(s,x+16,y+21,11,5,R('#163c64','#245f9c','#3f8fc0'),bias=-.1); bar(s,x+2,y-6,x+6,y+22,TIMBER,True); bar(s,x+26,y-6,x+30,y+22,TIMBER,True)
    bar(s,x-3,y-14,x+35,y-5,ROOF,False)
    bar(s,x+13,y-5,x+19,y+12,BELT,True)
def sign(s,x,y):
    bar(s,x+13,y+14,x+19,y+31,TIMBER,True); W=R('#6e4428','#a97a4a','#d2a56e'); bar(s,x+2,y+1,x+30,y+18,W,False)
    fill(s,x+6,y+6,x+26,y+7,'#4a2c1c'); fill(s,x+6,y+10,x+20,y+11,'#4a2c1c'); fill(s,x+2,y+1,x+30,y+2,'#f0d4a0')
def cabbage(s,x,y,rng):
    G=R('#1b5238','#2a7a44','#4ea451','#88c860')
    blob(s,x+16,y+17,8,6.5,G,bias=.1); blob(s,x+12,y+15,4,3.4,G,bias=.2); blob(s,x+20,y+15,4,3.4,G,bias=.05)
def tuft(s,x,y,ramp_c):
    for dx,h in ((-2,3),(0,5),(2,3)):
        for k in range(h): px(s,x+dx+(k>2)*(1 if dx>0 else -1 if dx<0 else 0),y-k,ramp_c)
GRASS=R('#28583a','#347242','#478c49','#62a44f','#84bc58','#b0d468')
DIRT=R('#5e432e','#7c5a3c','#9a7650','#b89364','#d4b382','#ecd2a4')
FOREST=R('#132f2a','#1a4031','#245238','#33683f','#4a8148','#6c9c52')
FDIRT=R('#2e281f','#433829','#5c4c35','#766445','#938058')
WATER=R('#123a72','#1a5392','#2570ae','#3a95c6','#62bfd6','#a2e4e0')
SAND=R('#a98d62','#c8ac7c','#e2c898','#f4e2b8')

def blade_field(h,w,seed,n):
    r=np.random.RandomState(seed); F=np.zeros((h,w))
    xs=r.randint(0,w,n); ys=r.randint(4,h,n); hs=r.randint(2,6,n); val=r.choice([-.14,-.08,.1,.16],n)
    for x,y,hh,v in zip(xs,ys,hs,val):
        F[max(y-hh,0):y,x]+=v
    return F
def cells(grid,want):
    return np.kron(np.array([[1.0 if v in want else 0.0 for v in row] for row in grid]),np.ones((TX,TX)))
def organic(m,seed,r=5,amp=.42):
    b=blur(m,r); return b+(fbm(m.shape[0],m.shape[1],18,seed)-.5)*amp>.5

def save(a,path): Image.fromarray(a,'RGBA').save(path)

def bake_village(root,g,o,v,W,H,I,houses,pond):
    h,w=H*TX,W*TX; A=f'{root}/assets'
    base=.5+(fbm(h,w,64,1)-.5)*.75+blade_field(h,w,2,26000)+(noise(h,w,3,3)-.5)*.16
    col=shade(np.clip(base,0,1),GRASS,.95); G=np.dstack([col,np.full((h,w),255,np.uint8)])
    p=organic(cells(g,{I['path'],I['mat']}),5)
    pv=.56+(fbm(h,w,8,6)-.5)*.42+(noise(h,w,2,16)-.5)*.2; ed=blur(p.astype(float),4); pv-=np.clip(.75-ed,0,1)*.6
    c=shade(np.clip(pv,0,1),DIRT,.9); G[p,:3]=c[p]
    so=cells(g,{I['soil']})>0
    sv=.4+.25*np.sin(np.arange(h)/2.5)[:,None]+(fbm(h,w,6,8)-.5)*.4; c=shade(np.clip(sv,0,1),R('#2c1c14','#4a2f1f','#6a472e','#8a6240'),.7); G[so,:3]=c[so]
    wm=cells(g,{I['water']}); wo=organic(wm,9,8,.3); sand=organic(np.clip(blur(wm,10)*2.2,0,1),10,3,.25)
    ss=sand&~wo; c=shade(np.clip(.55+(fbm(h,w,5,11)-.5)*.8,0,1),SAND,.8); G[ss,:3]=c[ss]
    depth=blur(wo.astype(float),14); wv=1-np.clip((depth-.45)/.5,0,1)
    streak=noise(h,w*1,2,12)[:,:]; stretch=np.asarray(Image.fromarray((noise(h//4+1,w//24+2,1,13)*255).astype(np.uint8)).resize((w,h),Image.BILINEAR),dtype=float)/255
    wv=wv*.8+(stretch-.5)*.4; c=shade(np.clip(wv,0,1),WATER,.9); G[wo,:3]=c[wo]
    foam=wo&(blur(wo.astype(float),1.2)<.82); G[foam,:3]=(214,244,240)
    # flowers, tufts and small stones on the grass
    r=random.Random(77); open_cell=lambda c,y:0<=c<W and 0<=y<H and g[y][c] in (I['grass'],I['flowers']) and o[y][c]==-1
    F=[('#f6efe0','#f0c84a'),('#f09ac0','#ffe07a'),('#ffd24a','#e8903a'),('#a8b8ff','#ffffff')]
    for y in range(H):
        for c0 in range(W):
            if not open_cell(c0,y): continue
            for _ in range(5 if g[y][c0]==I['flowers'] else 0):
                a,b=r.choice(F); flower(G,c0*TX+r.randint(3,28),y*TX+r.randint(3,28),a,b,r)
            if r.random()<.5: tuft(G,c0*TX+r.randint(3,28),y*TX+r.randint(6,30),'#b0d468')
    # garden rows
    for y in range(H):
        for c0 in range(W):
            if g[y][c0]==I['soil']: cabbage(G,c0*TX,y*TX,r)
    # doormat
    fill(G,11*TX+3,8*TX+6,11*TX+29,8*TX+27,'#5a2436'); bar(G,11*TX+5,8*TX+8,11*TX+27,8*TX+25,R('#8a3a4f','#b5506a','#d67a88'),False)
    O=canvas(h,w); S=np.zeros((h,w))
    trees=[tree_sprite(s) for s in (101,102,103,104,105,106)]
    housecells=set()
    for c0,r0,hw,col_ in houses:
        for y in range(r0,r0+5):
            for x in range(c0,c0+hw): housecells.add((x,y))
        S[(r0+5)*TX-6:(r0+5)*TX+18,c0*TX+8:(c0+hw)*TX+22]=1
        S[r0*TX+40:(r0+5)*TX,(c0+hw)*TX:(c0+hw)*TX+22]=1
    is_f=lambda c,y:0<=c<W and 0<=y<H and o[y][c]==I['fence']
    order=[]
    for y in range(H):
        for c0 in range(W):
            n=o[y][c0]
            if n==-1 or (c0,y) in housecells: continue
            order.append((y,c0,n))
    pending=[]
    for y,c0,n in order:
        x0,y0=c0*TX,y*TX
        if n==I['trunk']: ell(S,x0+26,y0+28,40,14)
        elif n==I['fence']: S[y0+26:y0+32,x0:x0+TX]=np.maximum(S[y0+26:y0+32,x0:x0+TX],.8)
        elif n==I['well']: ell(S,x0+24,y0+30,20,8)
        elif n==I['sign']: ell(S,x0+22,y0+30,14,5)
    apply_shadow(G,blur(S,3))
    for y,c0,n in order:
        x0,y0=c0*TX,y*TX
        if n==I['trunk']:
            t,cr=trees[(c0*7+y*13)%6]; over(G,t,x0+16-24,y0+TX-60); over(O,cr,x0+16-64,y0+TX-122)
        elif n==I['fence']: fence_cell(G,x0,y0,is_f(c0-1,y) or is_f(c0+1,y),is_f(c0,y-1) or is_f(c0,y+1))
        elif n==I['well']: well(G,x0,y0)
        elif n==I['sign']: sign(G,x0,y0)
    for c0,r0,hw,roof in houses:
        im=house_img(hw,c0+50,roof); wy=3*TX-8
        for x in (TX+4,(hw-2)*TX+4): window(im,x,wy+8+24)
        if hw==7 or True: door(im,(hw//2)*TX+4,5*TX-34)
        over(G,im,c0*TX,r0*TX)
    save(G,f'{A}/village_ground.png'); save(O,f'{A}/village_over.png')
    c0,r0,cw,ch=pond; fh,fw=ch*TX,cw*TX; m=wo[r0*TX:(r0+ch)*TX,c0*TX:(c0+cw)*TX]; sh=canvas(fh,fw*4); C=R('#a2e4e0','#ffffff')
    for f in range(4):
        n=np.asarray(Image.fromarray((noise(fh//2+1,fw//7+2,1,40+f)*255).astype(np.uint8)).resize((fw,fh),Image.NEAREST),dtype=float)/255
        n2=noise(fh,fw,16,60+f); sp=(n>.8)&(n2>.42)&m; fr=sh[0:fh,f*fw:(f+1)*fw]; fr[sp,:3]=C[(n>.9)[sp].astype(int)]; fr[sp,3]=120
    save(sh,f'{A}/shimmer.png')
    return G,O

def bake_forest(root,g,o,v,W,H,I):
    h,w=H*TX,W*TX; A=f'{root}/assets'
    base=.5+(fbm(h,w,48,21)-.5)*.8+blade_field(h,w,22,24000)*.9+(noise(h,w,3,23)-.5)*.2
    c=shade(np.clip(base,0,1),FOREST,.95); G=np.dstack([c,np.full((h,w),255,np.uint8)])
    p=organic(cells(g,{I['forest_path']}),25,6,.55); pv=.55+(fbm(h,w,10,26)-.5)*.8-np.clip(.75-blur(p.astype(float),4),0,1)*.6
    c=shade(np.clip(pv,0,1),FDIRT,.9); G[p,:3]=c[p]
    r=random.Random(31)
    # fallen leaves and mushrooms
    for _ in range(1400):
        x,y=r.randrange(w),r.randrange(h); a=r.choice(['#a8772e','#7a5a24','#c28a34','#5c6e2a']); px(G,x,y,a); px(G,x+1,y,a)
    Cap=R('#6a1a24','#a82c34','#d9504c','#f08a70')
    for y in range(H):
        for c0 in range(W):
            if g[y][c0]==I['mushroom'] and o[y][c0]==-1:
                x0,y0=c0*TX+r.randint(2,14),y*TX+r.randint(2,12)
                for k in range(r.randint(1,3)):
                    dx,dy=k*7,(k%2)*5; bar(G,x0+dx+6,y0+dy+8,x0+dx+11,y0+dy+15,R('#b8a890','#e8dcc4','#fff8e8'),True); blob(G,x0+dx+8.5,y0+dy+7,7,5,Cap,keep=lambda a,b:b<y0+dy+9.5); px(G,x0+dx+6,y0+dy+5,'#fff0e0'); px(G,x0+dx+10,y0+dy+4,'#fff0e0')
            elif o[y][c0]==-1 and g[y][c0]==I['forest'] and r.random()<.4:
                x0,y0=c0*TX+r.randint(4,26),y*TX+r.randint(8,28)
                for a in (-3,-1,1,3):
                    for k in range(5): px(G,x0+a*(1+k//2),y0-k,'#5e9a52' if k>1 else '#33683f')
    O=canvas(h,w); S=np.zeros((h,w))
    trees=[tree_sprite(s,DLEAF) for s in (201,202,203,204,205,206)]
    rock=canvas(32,32); blob(rock,16,20,13,10,STONE); blob(rock,12,14,7,5,STONE,bias=.2); blob(rock,24,24,5,3,R('#245238','#33683f','#5e9a52')); outline(rock,'#1a1a24')
    for y in range(H):
        for c0 in range(W):
            n=o[y][c0]; x0,y0=c0*TX,y*TX
            if n==I['forest_trunk']: ell(S,x0+24,y0+28,44,16)
            elif n==I['rock']: ell(S,x0+20,y0+30,16,6)
    apply_shadow(G,blur(S,4),.55,(10,24,40))
    for y in range(H):
        for c0 in range(W):
            n=o[y][c0]; x0,y0=c0*TX,y*TX
            if n==I['forest_trunk']:
                t,cr=trees[(c0*5+y*11)%6]; over(G,t,x0+16-24,y0+TX-60); over(O,cr,x0+16-64,y0+TX-122)
            elif n==I['rock']: over(G,rock,x0,y0)
    save(G,f'{A}/forest_ground.png'); save(O,f'{A}/forest_over.png')
    return G,O

def bake_house(root,g,o,W,H,I):
    h,w=H*TX,W*TX; A=f'{root}/assets'; G=canvas(h,w); G[...,:3]=(14,10,20); G[...,3]=255
    fl=cells(g,{I['floor'],I['rug']})>0
    V=np.full((h,w),.55); r=np.random.RandomState(5)
    for y in range(0,h,10):
        off=r.randint(0,60); V[y:y+10]+=r.uniform(-.1,.1)
        V[y+9:y+10]=.08
        for x in range(off%64,w,64): V[y:y+9,x:x+1]=.12
    grain=np.asarray(Image.fromarray((noise(h//2+1,w//40+2,1,7)*255).astype(np.uint8)).resize((w,h),Image.BILINEAR),dtype=float)/255
    V+=(grain-.5)*.34; WOOD=R('#3a2214','#5c3820','#7f5230','#a37042','#c4905a')
    c=shade(np.clip(V,0,1),WOOD,.7); G[fl,:3]=c[fl]
    x0,y0,x1,y1=13*TX,9*TX,18*TX,11*TX
    RUG=R('#4a1626','#71223a','#9c3350','#c8506c'); yy,xx=grid_xy(G); m=(xx>=x0)&(xx<x1)&(yy>=y0)&(yy<y1)
    q=((xx-x0)%16<8)^((yy-y0)%16<8); v2=.45+q*.3+(noise(h,w,2,9)-.5)*.2; c=shade(np.clip(v2,0,1),RUG,.8); G[m,:3]=c[m]
    b=m&~((xx>=x0+8)&(xx<x1-8)&(yy>=y0+8)&(yy<y1-8)); G[b,:3]=(224,178,62); bb=m&~((xx>=x0+3)&(xx<x1-3)&(yy>=y0+3)&(yy<y1-3)); G[bb,:3]=(90,28,44)
    WALL=R('#3a2a4a','#57406a','#75598c','#9476ac','#b698c8')
    wc=[(cx,cy) for cy in range(H) for cx in range(W) if o[cy][cx]==I['inner_wall']]
    for cx,cy in wc:
        s=G[cy*TX:(cy+1)*TX,cx*TX:(cx+1)*TX]; v3=.55+(noise(TX,TX,6,cx*3+cy)-.5)*.3-np.linspace(0,.3,TX)[:,None]; s[...,:3]=shade(np.clip(v3,0,1),WALL,.8)
        s[-6:,:,:3]=(46,28,20); s[:4,:,:3]=(36,24,50)
        if o[cy+1][cx]==-1 and cy+1<H: bar(G,cx*TX,(cy+1)*TX-6,(cx+1)*TX,(cy+1)*TX,TIMBER,False)
    S=np.zeros((h,w)); S[4*TX:4*TX+14,9*TX:22*TX]=1; S[4*TX:14*TX,9*TX:9*TX+10]=1
    S[4*TX:6*TX+6,10*TX-2:11*TX+8]=1; S[9*TX+16:10*TX+6,18*TX:20*TX+6]=1
    apply_shadow(G,blur(S,2.5),.5,(20,10,30))
    for c0 in (15,16):
        fill(G,c0*TX+2,14*TX+4,c0*TX+30,14*TX+30,'#27452f'); bar(G,c0*TX+4,14*TX+6,c0*TX+28,14*TX+28,R('#2a7d55','#43a065','#73c47e'),False)
    for x in (15*TX+16,16*TX+16):
        y=14*TX+10
        fill(G,x-1,y,x+1,y+12,'#f6efe0'); 
        for k in range(5): fill(G,x-4+k,y+8+k,x+4-k,y+9+k,'#f6efe0')
    # bed
    bx,by=10*TX,4*TX; bar(G,bx+1,by+2,bx+TX-1,by+TX*2-2,TIMBER,True,bias=.1); bar(G,bx+4,by+22,bx+TX-4,by+TX*2-6,R('#1c3a78','#2a56a0','#3f76c4','#6ea0dc'),True); blob(G,bx+16,by+13,11,7,R('#b8b4a8','#e4e0d4','#fff8ec')); fill(G,bx+4,by+30,bx+TX-4,by+32,'#6ea0dc')
    # shelves
    for c0 in (12,13):
        sx,sy=c0*TX,3*TX; bar(G,sx,sy,sx+TX,sy+TX,TIMBER,False); cc=['#b5383c','#3f8f5b','#d9a43a','#3a68a8','#8a4fa8','#d97a34']; rr=random.Random(c0)
        for row in (3,18):
            fill(G,sx+2,sy+row,sx+TX-2,sy+row+12,'#1c1218'); x=sx+3
            while x<sx+TX-4:
                wd=rr.randint(2,4); bar(G,x,sy+row+rr.randint(0,3),x+wd,sy+row+12,R(rr.choice(cc),rr.choice(cc)),True); x+=wd+1
    # hearth
    hx,hy=18*TX,3*TX; bar(G,hx-3,hy,hx+TX+3,hy+TX,STONE,False); fill(G,hx+6,hy+10,hx+TX-6,hy+TX,'#120a10')
    # tables
    for c0 in (18,19):
        tx,ty=c0*TX,9*TX; bar(G,tx,ty+4,tx+TX,ty+20,R('#5c3820','#8a5e36','#b58350'),False); fill(G,tx,ty+20,tx+TX,ty+23,'#3a2214'); bar(G,tx+2,ty+22,tx+6,ty+30,TIMBER,True); bar(G,tx+TX-6,ty+22,tx+TX-2,ty+30,TIMBER,True)
    bar(G,18*TX+8,9*TX-3,18*TX+18,9*TX+10,R('#3f8f5b','#73c47e'),True); blob(G,19*TX+15,9*TX+8,7,4,R('#b8b4a8','#fff8ec')); blob(G,19*TX+15,9*TX+6,4,2.4,ORANGE)
    save(G,f'{A}/house_ground.png')
    fl_=canvas(TX,TX*3); F=R('#a0301c','#e8701f','#ffb02e','#fff0a0')
    for f in range(3):
        fr=canvas(TX,TX); 
        for k,(dx,sz) in enumerate(((-6,6),(0,9),(6,5))):
            sz=sz+[0,2,-1][(f+k)%3]; blob(fr,16+dx,27-sz*.6,4.2,sz,F,bias=.1)
        over(fl_,fr,f*TX,0)
    save(fl_,f'{A}/fire.png')
    return G

def light(kind):
    h,w=270,480; yy,xx=np.mgrid[0:h,0:w]; a=np.zeros((h,w,4),dtype=float); b=bayer(h,w)
    vig=np.clip(np.hypot((xx-240)/300,(yy-135)/190)-.55,0,1)*1.5
    if kind=='village':
        sun=np.clip(1-np.hypot((xx+40)/380,(yy+60)/280),0,1)
        col=np.array([255,214,140]); dark=np.array([24,22,70])
        warm=sun*.28; cool=vig*.32
    elif kind=='forest':
        sh=np.clip(np.sin((xx+yy*.62)/26+1.2*np.sin(yy/70))-.45,0,1)*1.6*np.clip(1-yy/300,0.1,1)
        col=np.array([232,244,170]); dark=np.array([8,28,42]); shade_=.16+vig*.5
        warm=sh*.22; cool=shade_*(1-sh*.6)
    else:
        fire=np.clip(1-np.hypot((xx-296)/250,(yy-60)/190),0,1)
        col=np.array([255,158,70]); dark=np.array([16,10,40]); shade_=.14+vig*.55
        warm=fire*.3; cool=shade_*np.clip(1.25-fire*1.5,0,1)
    alpha=1-(1-warm)*(1-cool)
    mix=(warm/np.maximum(warm+cool,1e-4))[...,None]
    alpha=np.floor(np.clip(alpha,0,1)*14+.5+b*.9)/14
    a[...,:3]=col*mix+dark*(1-mix); a[...,3]=np.clip(alpha,0,1)*255
    return a.astype(np.uint8)

def build(root):
    A=f'{root}/assets'; os.makedirs(A,exist_ok=True)
    save(person_sheet('hero'),f'{A}/hero.png'); save(npc_sheet('mira'),f'{A}/mira.png'); save(npc_sheet('tobin'),f'{A}/tobin.png')
    save(slime_sheet(),f'{A}/slime.png'); save(slash(),f'{A}/slash.png')
    for n in ('jelly','potion','coin','heart'): save(icon(n),f'{A}/{n}.png')
    save(canvas(4,4),f'{A}/clear.png'); save(canvas(16,16),f'{A}/collision.png')
    for n,(w,h) in dict(panel_hud=(300,68),panel_quest=(224,32),panel_hint=(358,28),panel_dialog=(880,124),panel_bag=(520,360)).items(): save(panel(w,h),f'{A}/{n}.png')
    save(slot(),f'{A}/slot.png')
    for k in ('village','forest','house'): save(light(k),f'{A}/light_{k}.png')

def store_art(root):
    A=f'{root}/assets'; S=f'{root}/app0/sce_sys'
    g=Image.open(f'{A}/village_ground.png').convert('RGBA'); o=Image.open(f'{A}/village_over.png').convert('RGBA')
    x,y=200,110; sc=g.crop((x,y,x+480,y+270))
    hero=Image.open(f'{A}/hero.png').convert('RGBA').crop((0,0,32,32)); mira=Image.open(f'{A}/mira.png').convert('RGBA').crop((0,0,32,32)); sl=Image.open(f'{A}/slime.png').convert('RGBA').crop((0,0,32,32))
    for im,px_,py_ in ((hero,352-x,352-y),(mira,672-x,256-y),(sl,500-x,300-y),(sl,600-x,340-y)):
        big=im.resize((64,64),Image.NEAREST) if im is hero else im; sc.alpha_composite(big,(px_,py_))
    sc.alpha_composite(o.crop((x,y,x+480,y+270))); sc.alpha_composite(Image.open(f'{A}/light_village.png').convert('RGBA'))
    full=sc.resize((3840,2160),Image.NEAREST).convert('RGB'); full.save(f'{S}/pic0.png'); full.save(f'{S}/pic1.png')
    sc.crop((130,40,130+230,40+230)).resize((512,512),Image.NEAREST).convert('RGB').save(f'{S}/icon0.png')
