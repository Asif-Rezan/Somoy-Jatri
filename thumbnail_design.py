"""Thumbnail hook validation and export of complete generated artwork."""
from colorsys import hls_to_rgb, rgb_to_hls
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageStat
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



def calm_lettering_background(image,box,fill,outline):
    """Place a solid panel when a title would cross busy or low-contrast artwork."""
    patch = image.crop(box).resize((24,12),Image.Resampling.BOX)
    levels = sorted(luminance(color) for color in patch.getdata())
    span = levels[len(levels)*9//10]-levels[len(levels)//10]
    visible = sum(contrast(luminance(fill),level)>=4.5 for level in levels)
    if span<.20 and visible>=len(levels)*.90:
        return False
    panel = (box[0]-15,box[1]-12,box[2]+15,box[3]+12)
    ImageDraw.Draw(image).rounded_rectangle(panel,radius=15,fill=outline)
    return True


def quiet_lettering_position(image,width,height):
    """Prefer the least detailed upper region large enough for the complete headline."""
    gray = image.convert('L')
    horizontal = ImageChops.difference(gray,ImageChops.offset(gray,3,0))
    vertical = ImageChops.difference(gray,ImageChops.offset(gray,0,3))
    edges = ImageChops.lighter(horizontal,vertical)
    half = width//2
    last_top = min(225,image.height-height-48)
    candidates = []
    for center in range(half+34,image.width-half-24,56):
        for top in range(39,last_top+1,32):
            area = (center-half,top,center+half,top+height)
            detail = ImageStat.Stat(edges.crop(area)).mean[0]
            # Keep a slight preference for the upper-right when two areas are equally quiet.
            preference = abs(center-image.width*.74)/950 + top/950
            candidates.append((detail+preference,center,top))
    if not candidates:
        return image.width//2,39
    _,center,top = min(candidates)
    return center,top


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
    period_font = ImageFont.truetype(font_path,52)
    width = round(max(draw.textlength(title,font=font),draw.textlength(period,font=period_font)))+26
    if hook:
        hook = hook.upper()
        for hook_size in range(60,25,-2):
            hook_font = _font(hook_size)
            hook_width = round(draw.textlength(hook,font=hook_font))+48
            if hook_width <= 568:
                break
        width = max(width,hook_width)
    center,top = quiet_lettering_position(image,width,size+(172 if hook else 80))
    lines = ((title,top,font),(period,top+size+13,period_font))
    areas = [draw.textbbox((center,y),label,anchor='mt',font=face) for label,y,face in lines]
    title_area = (min(area[0] for area in areas),areas[0][1],
                  max(area[2] for area in areas),areas[-1][3])
    fill,panel = lettering_colors(image,title_area)
    if contrast(luminance(fill),luminance(panel))<7:
        panel = (255,249,231) if luminance(fill)<.30 else (21,23,27)
    panel_used = calm_lettering_background(image,title_area,fill,panel)
    for (label,y,face),area in zip(lines,areas):
        color,outline = (fill,None) if panel_used else lettering_colors(image,area)
        draw.text((center,y),label,anchor='mt',font=face,fill=color,
                  stroke_width=0 if panel_used else 4 if label==title else 3,stroke_fill=outline)
    if hook:
        badge_top = top+size+87
        badge = (center-hook_width//2,badge_top,center+hook_width//2,badge_top+78)
        pill,letter = lettering_colors(image,badge)
        draw.rounded_rectangle(badge,radius=19,fill=pill,outline=letter,width=3)
        draw.text((center,badge_top+39),hook,anchor='mm',font=hook_font,fill=letter)
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
