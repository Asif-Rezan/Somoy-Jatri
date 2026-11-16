"""Compose anonymous animated characters onto narration-aligned history shots."""
import math
import re
import subprocess

from PIL import Image, ImageDraw, ImageOps

from character_rig import character

SIZE = (1280, 720)
FPS = 30


ACTION_PATTERNS = {
    'carry': re.compile(
        r'\b(?:carry(?:ing)?|carr(?:ies|ied)|(?:un)?load(?:ed|ing|s)?) '
        r'(?:(?:their|the|a|some|wooden|heavy|clay) )*(?:cargo|goods|baskets?|crates?|pots?|sacks?|supplies|tools)\b',
        re.I),
    'walk': re.compile(
        r'\b(?:workers?|merchants?|traders?|sailors?|travelers?|travellers?|soldiers?|families|people|residents?) '
        r'(?:(?:who|were|are|then) )*(?:walk\w*|march\w*|travel\w*|cross\w*|move[ds]?)\b', re.I),
    'build': re.compile(
        r'\b(?:builders?|workers?|craftspeople|masons?) '
        r'(?:(?:who|were|are|then) )*(?:stack\w*|lay\w*|cut\w*) (?:stone|brick|stones|bricks)\b', re.I),
    'point': re.compile(
        r'\b(?:guides?|workers?|sailors?|traders?|residents?) '
        r'(?:(?:who|were|are|then) )*(?:point\w*|gesture\w*) (?:at|to|toward|towards)\b', re.I),
}


def shot_animation(narration, *, islamic, index, word_offsets=None, seconds=10):
    """Schedule only a depicted action described by the spoken words."""
    if re.search(r'\b(?:prophets?|angels?|divine|allah|companions?|muhammad)\b', narration, re.I):
        return None
    if word_offsets is not None and not word_offsets:
        return None
    tokens = [word for word,_ in word_offsets] if word_offsets else narration.split()
    spoken = ' '.join(tokens)
    matches = [(match.start(), action, match)
               for action, pattern in ACTION_PATTERNS.items() for match in pattern.finditer(spoken)]
    if not matches:
        return None
    _, action, match = min(matches,key=lambda entry: entry[0])
    if word_offsets:
        first = spoken[:match.start()].count(' ')
        last = spoken[:match.end()].count(' ')
        start = max(0, word_offsets[first][1])
        end = min(seconds,max(start+2.2,word_offsets[last][1]+1.4),start+4.5)
    else:
        start, end = 0, min(seconds,4.5)
    if end-start < .7:
        return None
    before = spoken[max(0, match.start()-40):match.start()]
    paired = bool(re.search(r'\b(?:merchants|travelers|travellers|workers|families|traders|dockworkers)\b',
                            before+match.group(),re.I))
    return {'action': action, 'islamic': islamic, 'female': bool(index % 2),
            'paired': paired, 'start': start, 'end': end}


def _actor(draw, x, ground, **pose):
    draw.ellipse((x-37, ground-5, x+37, ground+7), fill=(29, 19, 13, 103))
    character(draw, x, ground, **pose)


def draw_frame(background, spec, t):
    frame = background.copy()
    draw = ImageDraw.Draw(frame, 'RGBA')
    move = spec['action'] in {'walk', 'carry'}
    x = 228 + 110*t if move else 348
    _actor(draw, x, 661, scale=1.1, facing=1, islamic=spec['islamic'],
           female=spec['female'], blink=t % 3.4 > 3.29,
           walk_phase=t*7.8 if move else None,
           basket=spec['action'] == 'carry',
           point=spec['action'] in {'point','build'} and t >= .2,
           wave=(math.sin(t*6)*.6 if spec['action'] == 'build' else None))
    if spec['action'] == 'build':
        for row in range(2):
            for brick in range(3-row):
                left = x+83+brick*30+row*14
                top = 642-row*15
                draw.rounded_rectangle((left,top,left+27,top+13),radius=2,
                                       fill='#b68b62',outline='#6b4a32',width=2)
        brick_y = 607+round(7*math.sin(t*6))
        draw.rounded_rectangle((x+68,brick_y,x+94,brick_y+13),radius=3,
                               fill='#cf9f71',outline='#6b4a32',width=2)
    if spec['paired']:
        _actor(draw, x-121, 641, scale=.94, facing=1, islamic=spec['islamic'],
               female=not spec['female'], walk_phase=t*7.8+1 if move else None)
    return frame


def compose_frame(background, spec, edit, t, seconds):
    from history_editing import draw_edit
    from history_sequence import draw_sequence

    frame = background.copy()
    if spec and spec.get('start',0) <= t < spec.get('end',seconds):
        start, end = spec.get('start',0), spec.get('end',seconds)
        cast = draw_frame(background,spec,t-start)
        opacity = min(1,(t-start)/.18,(end-t)/.18)
        frame = Image.blend(frame,cast,opacity) if opacity < 1 else cast
    if t >= seconds * .57 and not edit.get('closing'):
        inset = 36 if spec else 51
        frame = frame.resize(SIZE,Image.Resampling.BILINEAR,
                             box=(inset,inset//2,SIZE[0]-inset,SIZE[1]-inset//2))
    return draw_sequence(draw_edit(frame,edit,t,seconds),edit,t,seconds)


def animated_clip(image, seconds, target, spec, edit=None):
    with Image.open(image) as source:
        background = ImageOps.fit(source.convert('RGB'), SIZE, Image.Resampling.LANCZOS)
    edit = edit or {}
    frames = max(1, round(seconds * FPS))
    filters = (f'scale=1920:1080,fade=t=in:st=0:d=0.2,'
               f'fade=t=out:st={max(0,seconds-.2)}:d=0.2,format=yuv420p')
    command = ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', '1280x720', '-framerate', str(FPS), '-i', 'pipe:0', '-vf', filters,
               '-frames:v', str(frames), '-an', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '21', '-movflags', '+faststart', str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        try:
            for frame in range(frames):
                encoder.stdin.write(compose_frame(background,spec,edit,frame/FPS,seconds).tobytes())
        finally:
            encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Could not encode the animated history shot')


def thumbnail_cast(image, *, islamic):
    draw = ImageDraw.Draw(image)
    character(draw, 213, 812, scale=1.95, facing=1, islamic=islamic, point=True)
    character(draw, 470, 805, scale=1.83, female=True, islamic=islamic, wave=math.pi/4)
