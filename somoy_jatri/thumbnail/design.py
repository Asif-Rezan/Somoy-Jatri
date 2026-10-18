from PIL import Image, ImageDraw, ImageFont, features
from somoy_jatri.subtitles.captions import font


def create(root,text):
    if not features.check_feature('raqm'): raise ValueError('Pillow RAQM required for Bengali shaping')
    image=Image.open(sorted((root/'images').glob('*.png'))[0]).convert('RGB').resize((1280,720))
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,520,1280,720),fill=(16,24,34))
    size=76
    while True:
        face=ImageFont.truetype(font(),size)
        if draw.textbbox((0,0),text,font=face)[2]<1190:break
        size-=2
        if size<20:raise ValueError('Thumbnail text too long')
    draw.text((45,555),text,font=face,fill=(255,221,65),language='bn')
    draw.text((30,20),'SOMOY JATRI',fill='white',font=ImageFont.truetype(font(),30))
    image.save(root/'thumbnail.jpg',quality=94)
