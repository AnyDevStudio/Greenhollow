# Puts the host's and the friend's screens side by side, each with its label: the pictures of playing online.
# python3 pairs6.py <folder of render6 pictures> <output folder>
import os, sys
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1:3]
HERE = os.path.dirname(os.path.abspath(__file__))
font = ImageFont.truetype(f'{HERE}/fonts/IBMPlexSans-SemiBold.ttf', 26)
W, H, GAP, BAR = 960, 540, 16, 48
INK, PAPER, GOLD = (21, 26, 44), (246, 239, 224), (240, 200, 74)
names = sorted({f[:-len('-host.png')] for f in os.listdir(src) if f.endswith('-host.png')})
for name in names:
    page = Image.new('RGB', (W * 2 + GAP, H + BAR), INK)
    draw = ImageDraw.Draw(page)
    for k, (who, label) in enumerate((('host', 'Host console'), ('friend', "Friend's console"))):
        shot = Image.open(f'{src}/{name}-{who}.png').convert('RGB').resize((W, H), Image.LANCZOS)
        x = k * (W + GAP)
        page.paste(shot, (x, BAR))
        draw.ellipse((x + 14, 17, x + 28, 31), fill=GOLD if who == 'host' else (164, 239, 219))
        draw.text((x + 40, 8), label, font=font, fill=PAPER)
    page.save(f'{out}/online-{name.split("-", 1)[1]}.jpg', quality=88, subsampling=0, optimize=True)
    print(f'online-{name.split("-", 1)[1]}.jpg')
