# Draws saved game states the way the game's tilted camera does, for screenshots without opening a window.
import glob,json,os,re,sys,math
from PIL import Image
root,src,out=sys.argv[1:4]; nohud=len(sys.argv)>4 and sys.argv[4]=='nohud'
glyphs={}
for m in re.finditer(r"case '(\\?.)': return \{([^}]*)\}",open(src).read()):
    ch=m.group(1); ch=ch[-1] if len(ch)>1 else ch; glyphs[ch]=[int(v) for v in m.group(2).split(',')]
S=json.load(open(root+'/scene.json')); cache={}
def load(p):
    if p not in cache: cache[p]=Image.open(root+'/'+p).convert('RGBA')
    return cache[p]
def hexc(c): return tuple(int(c[i:i+2],16) for i in (1,3,5))+(255,)
SW,SH,A=1920.0,1080.0,640.0
class V:
    def __init__(s,t,cx,cy): k=t/100; s.D=SH/k; s.q=1-k*.4; s.cx=cx+SW/2; s.cy=cy+SH/2
    def off(s,y): return min(y-s.cy,s.D*.85)
    def sc(s,y): return s.D/(s.D-s.off(y))
    def pr(s,x,y): c=s.sc(y); return (SW/2+(x-s.cx)*c,A+s.off(y)*c*s.q)
    def wy(s,sy): o=(sy-A)/s.q; return s.cy+o*s.D/(s.D+o)
def over(im,p,x,y):
    x,y=int(round(x)),int(round(y))
    if x>=SW or y>=SH or x+p.width<=0 or y+p.height<=0: return
    bx0,by0=max(x,0),max(y,0); bx1,by1=min(x+p.width,int(SW)),min(y+p.height,int(SH))
    im.alpha_composite(p.crop((bx0-x,by0-y,bx1-x,by1-y)),(bx0,by0))
for f in sorted(glob.glob(sys.argv[5] if len(sys.argv)>5 else 'shots/*.txt')):
    L=open(f).read().split('\n'); a=L[0].split(); sc=dict(S['scenes'][int(a[0])])
    # a template stands for its copies, numbered one after another as the game numbers them
    ex=[]
    for it in sc['items']:
        for k in range(max(1,it.get('copies',0))): ex.append(it)
    sc['items']=ex; cx,cy=float(a[1]),float(a[2]); view=V(sc.get('tilt',0) or 1,cx,cy); tilted=sc.get('tilt',0)>0
    im=Image.new('RGBA',(1920,1080),hexc(sc['background'])); state={}; quads={}; cur=None
    for l in L[1:]:
        if l.startswith('i '):
            a=l.split(); cur=int(a[1]); state[cur]=dict(x=float(a[2]),y=float(a[3]),vis=a[4]=='1',frame=int(a[5]),flip=a[6]=='1',text='')
        elif l.startswith('t '): state[cur]['text']=l[2:]
        elif l.startswith('q '):
            a=l.split(); quads.setdefault(int(a[1]),[]).append([float(v) for v in a[2:]])
    def pic(it,st):
        p=load(it['source'])
        if 'sheet' in it:
            fw,fh=it['sheet']['frameWidth'],it['sheet']['frameHeight']; cols=p.width//fw; n=st['frame']; p=p.crop(((n%cols)*fw,(n//cols)*fh,(n%cols+1)*fw,(n//cols+1)*fh))
        return p.transpose(Image.FLIP_LEFT_RIGHT) if st['flip'] else p
    def flatdraw(it,st):
        p=pic(it,st); iw,ih=p.size; x,y,w,h=st['x'],st['y'],it['width'],it['height']
        strip=4.0; sy=0.0
        while sy<SH:
            t=max(view.wy(sy),y); b=min(view.wy(sy+strip),y+h)
            if b>t:
                c=view.sc((t+b)/2); y0=view.pr(x,t)[1]; y1=view.pr(x,b)[1]; X=SW/2+(x-view.cx)*c; W=w*c; v0=(t-y)/h; v1=(b-y)/h
                r0=max(int(v0*ih),0); r1=max(min(int(math.ceil(v1*ih)),ih),r0+1)
                if W>=1 and y1>y0:
                    x0=max(X,0); x1=min(X+W,SW)
                    if x1>x0:
                        u0=(x0-X)/W*iw; u1=(x1-X)/W*iw; c_=p.crop((int(u0),r0,max(int(math.ceil(u1)),int(u0)+1),r1)).resize((max(int(math.ceil(x1-x0)),1),max(int(round(y1-y0))+1,1)),Image.BILINEAR); over(im,c_,x0,y0)
            sy+=strip
    stand=[]
    uid=[i for i,it in enumerate(sc['items']) if it.get('upright')]
    first=uid[0] if uid else -1
    for i,it in enumerate(sc['items']):
        st=state[i]; fixed=it.get('screenFixed')
        if nohud and fixed and it['id'] not in ('backdrop','light'): continue
        if it['type']=='particles':
            for q in quads.get(i,[]):
                x,y,w,h,r,g,b=q
                if tilted and not fixed:
                    c=view.sc(y); fx,fy=view.pr(x,y); W,H=w*c,h*c; x0,y0=int(fx-W/2),int(fy-H)
                else: x0,y0,W,H=int(x-cx),int(y-cy),w,h
                if W>0 and H>0: im.paste((int(r*255),int(g*255),int(b*255),255),(x0,y0,x0+int(W)+1,y0+int(H)+1))
            continue
        if it['type']=='tilemap': continue
        if it.get('upright'):
            if i==first:
                ups=sorted([j for j in uid if state[j]['vis']],key=lambda j:state[j]['y']+sc['items'][j]['height'])
                for j in ups:
                    t=sc['items'][j]; s=state[j]; fy=s['y']+t['height']; c=view.sc(fy); fx,py=view.pr(s['x']+t['width']/2,fy); dw=(t.get('drawWidth') or t['width'])*c; dh=(t.get('drawHeight') or t['height'])*c
                    if dw>=1 and dh>=1 and fx+dw/2>0 and fx-dw/2<SW and py>0 and py-dh<SH: over(im,pic(t,s).resize((int(dw),int(dh)),Image.BILINEAR),fx-dw/2,py-dh)
            continue
        if not st['vis']: continue
        if it['type']=='image':
            if tilted and not fixed: flatdraw(it,st)
            else: over(im,pic(it,st).resize((int(it['width']),int(it['height'])),Image.NEAREST if it.get('pixelated') else Image.BILINEAR),st['x'],st['y'])
        elif it['type']=='text':
            s0=it['scale']; col=hexc(it['color'])
            if tilted and not fixed: (x,y)=view.pr(st['x'],st['y']); s=s0*view.sc(st['y'])
            else: x,y,s=st['x'],st['y'],s0
            for k,ch in enumerate(st['text']):
                for r,bits in enumerate(glyphs.get(ch,glyphs.get(ch.upper(),[0]*7))):
                    for b in range(5):
                        if bits&(16>>b):
                            X=x+(k*6+b)*s; Y=y+r*s; im.paste(col,(int(X),int(Y),int(X+s)+1,int(Y+s)+1))
    im.convert('RGB').save(f'{out}/{os.path.basename(f)[:-4]}.png'); print(os.path.basename(f))
