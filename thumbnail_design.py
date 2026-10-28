"""Thumbnail hook validation and export of complete generated artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
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
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert('RGB').save(output, quality=89, optimize=True)
    if output.stat().st_size >= 2*1024*1024:
        image.convert('RGB').save(output, quality=78, optimize=True)
    if output.stat().st_size >= 2*1024*1024:
        raise RuntimeError('Thumbnail exceeds YouTube size limit')
    return output
