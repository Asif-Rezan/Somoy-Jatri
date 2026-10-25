from PIL import Image, ImageDraw, ImageFont, features
from somoy_jatri.subtitles.captions import font


def create(root,text):
    if not features.check_feature('raqm'): raise ValueError('Pillow RAQM required for Bengali shaping')
    image=Image.open(sorted((root/'images').glob('*.png'))[0]).convert('RGB').resize((1280,720))
    draw=ImageDraw.Draw(image)
    from PIL import ImageEnhance
    image = ImageEnhance.Brightness(image).enhance(1.12)
    shade = Image.new('RGBA', image.size)
    sd = ImageDraw.Draw(shade)
    for x in range(760):
        sd.line((x,0,x,720),fill=(10,18,28,int(235*(1-x/760))))
    image = Image.alpha_composite(image.convert('RGBA'),shade).convert('RGB')
    draw = ImageDraw.Draw(image)
    words = text.split()
    split = max(1,len(words)//2)
    lines = [' '.join(words[:split]), ' '.join(words[split:])] if len(words)>2 else [text]
    size=76
    while True:
        face=ImageFont.truetype(font(),size)
        if max(draw.textbbox((0,0),line,font=face)[2] for line in lines)<650:break
        size-=2
        if size<20:raise ValueError('Thumbnail text too long')
    for i,line in enumerate(lines):
        draw.text((45,240+i*(size+24)),line,font=face,fill=(255,221,65),language='bn',
                  stroke_width=2,stroke_fill=(10,18,28))
    draw.text((30,20),'সময় যাত্রী',fill='white',font=ImageFont.truetype(font(),30))
    image.save(root/'thumbnail.jpg',quality=94)
