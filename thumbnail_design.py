"""Thumbnail hook validation and export of complete generated artwork."""
from colorsys import hls_to_rgb, rgb_to_hls
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from itertools import combinations


def _font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 '/System/Library/Fonts/Supplemental/Arial Bold.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hook_layout(text):
    """Find a readable one to three line layout before artwork is generated."""
    words = text.upper().split()
    if not 2 <= len(words) <= 5 or len(text) > 30 or not text.endswith('?'):
        raise ValueError('Thumbnail hook must be a short documentary question')
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for size in range(112, 63, -4):
        font = _font(size)
        for count in (1, 2, 3):
            for breaks in combinations(range(1, len(words)), count - 1):
                cuts = (0,) + breaks + (len(words),)
                lines = [' '.join(words[cuts[i]:cuts[i + 1]]) for i in range(count)]
                if all(measure.textbbox((0, 0), line, font=font, stroke_width=3)[2] <= 500
                       for line in lines):
                    return lines, size
    raise ValueError('Thumbnail hook cannot fit at readable size')


def render_thumbnail(source, text, target, category='Islamic'):
    # Typography and composition are already part of the generated image.
    # Only resize/encode for YouTube; never paint text over the artwork.
    with Image.open(source) as original:
        image = original.convert('RGB').resize((1280, 720), Image.Resampling.LANCZOS)
    return _save_jpeg(image, target)


def luminance(color):
    rgb = [channel/255 for channel in color]
    linear = [value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4 for value in rgb]
    return sum(channel*weight for channel,weight in zip(linear,(.2126,.7152,.0722)))


def contrast(a,b):
    dark,light = sorted((a,b))
    return (light+.05)/(dark+.05)


def lettering_colors(image,box):
    """Use the opposite hue and pick readable tones against the actual letter area."""
    patch = image.crop(box).resize((12,6),Image.Resampling.BOX)
    samples = [patch.getpixel((x,y)) for y in range(patch.height) for x in range(patch.width)]
    average = [sum(channel)/len(samples)/255 for channel in zip(*samples)]
    hue,_,saturation = rgb_to_hls(*average)
    hue = (hue+.5)%1 if saturation>=.10 else .08

    def tone(lightness,saturation):
        return tuple(round(255*value) for value in hls_to_rgb(hue,lightness,saturation))

    shadows,highlights = tone(.09,.45),tone(.96,.64)
    backgrounds = [luminance(color) for color in samples]
    bright_background = sum(backgrounds)/len(backgrounds) >= .30
    lightness_order = (.23,.15,.83,.91) if bright_background else (.83,.91,.23,.15)
    fills = [tone(lightness,.75) for lightness in lightness_order]
    for fill in fills:
        visible = sum(contrast(luminance(fill),background)>=4.5 for background in backgrounds)
        if visible>=len(backgrounds)*.80:
            break
    else:
        fill = max(fills,key=lambda value: sum(contrast(luminance(value),bg) for bg in backgrounds))
    outline = max((shadows,highlights),key=lambda value:contrast(luminance(value),luminance(fill)))
    return fill,outline



def render_history_thumbnail(source, subject, period, target, *, cast_islamic=None, hook=None):
    with Image.open(source) as original:
        image = ImageOps.fit(original.convert('RGB'), (1280, 720), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    if cast_islamic is not None:
        from history_animation import thumbnail_cast
        thumbnail_cast(image, islamic=cast_islamic)
    fonts = ('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
             '/System/Library/Fonts/Supplemental/Georgia Bold.ttf')
    font_path = next((path for path in fonts if Path(path).is_file()), 'DejaVuSerif-Bold.ttf')
    title = subject.upper()
    for size in range(156, 43, -2):
        font = ImageFont.truetype(font_path, size)
        if draw.textlength(title, font=font) <= 590:
            break
    else:
        raise ValueError('History thumbnail subject is too long')
    period_font = ImageFont.truetype(font_path, 52)
    for label, y, face in ((title, 112, font), (period, 112 + size + 13, period_font)):
        area = draw.textbbox((949,y),label,anchor='mt',font=face)
        fill,outline = lettering_colors(image,area)
        draw.text((949,y),label,anchor='mt',font=face,fill=fill,
                  stroke_width=4 if label==title else 3,stroke_fill=outline)
    if hook:
        hook = hook.upper()
        for hook_size in range(60,25,-2):
            face = _font(hook_size)
            if draw.textlength(hook,font=face) <= 520:
                break
        badge = (660,365,1238,460)
        pill,letter = lettering_colors(image,badge)
        draw.rounded_rectangle(badge,radius=19,fill=pill,outline=letter,width=3)
        draw.text((949,411),hook,anchor='mm',font=face,fill=letter)
        image = image.resize((1920,1080), Image.Resampling.LANCZOS)
    return _save_jpeg(image, target)


def _save_jpeg(image, target):
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert('RGB').save(output, quality=89, optimize=True)
    if output.stat().st_size >= 2*1024*1024:
        image.convert('RGB').save(output, quality=78, optimize=True)
    if output.stat().st_size >= 2*1024*1024:
        raise RuntimeError('Thumbnail exceeds YouTube size limit')
    return output
