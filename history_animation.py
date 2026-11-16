"""Compose anonymous animated characters onto narration-aligned history shots."""
import math
import re
import subprocess

from PIL import Image, ImageDraw, ImageOps

from character_rig import character

SIZE = (1280, 720)
FPS = 30


def shot_animation(narration, *, islamic, index):
    """Only select actions supported by the spoken window."""
    if re.search(r'\b(?:prophets?|angels?|divine|allah|companions?|muhammad)\b', narration, re.I):
        return None
    if re.search(r'\b(?:cargo|unload\w*|load(?:ed|ing)|dockworkers)\b', narration, re.I):
        action = 'carry'
    elif re.search(r'\b(?:sail\w*|fleet|ships?|navy|harbou?r|ports?)\b', narration, re.I):
        action = 'point'
    elif re.search(r'\b(?:merchant\w*|trade|market\w*|goods|crafts\w*|pottery)\b', narration, re.I):
        action = 'carry'
    elif re.search(r'\b(?:march\w*|travel\w*|migrat\w*|routes?|roads?|cross\w*|retreat\w*)\b', narration, re.I):
        action = 'walk'
    elif re.search(r'\b(?:fort\w*|temple\w*|build\w*|mosque\w*|palace\w*|architect\w*|castle\w*|monument\w*)\b', narration, re.I):
        action = 'point'
    else:
        return None
    paired = bool(re.search(r'\b(?:merchants|travelers|workers|families|groups|traders)\b', narration, re.I))
    return {'action': action, 'islamic': islamic, 'female': bool(index % 2), 'paired': paired}


def _actor(draw, x, ground, **pose):
    draw.ellipse((x-37, ground-5, x+37, ground+7), fill=(29, 19, 13, 103))
    character(draw, x, ground, **pose)


def draw_frame(background, spec, t):
    frame = background.copy()
    draw = ImageDraw.Draw(frame, 'RGBA')
    move = spec['action'] in {'walk', 'carry'}
    duration = 7.5
    x = 228 + 76 * min(t, duration) if move else 348
    _actor(draw, x, 661, scale=1.1, facing=1, islamic=spec['islamic'],
           female=spec['female'], blink=t % 3.4 > 3.29,
           walk_phase=t*7.8 if move and t < duration else None,
           basket=spec['action'] == 'carry', point=spec['action'] == 'point' and t >= 1.2)
    if spec['paired']:
        _actor(draw, x-121, 641, scale=.94, facing=1, islamic=spec['islamic'],
               female=not spec['female'], walk_phase=t*7.8+1 if move and t < duration else None)
    return frame


def compose_frame(background, spec, edit, t, seconds):
    from history_editing import draw_edit

    frame = draw_frame(background,spec,t) if spec else background.copy()
    if t >= seconds * .57 and not edit.get('closing'):
        inset = 36 if spec else 51
        frame = frame.resize(SIZE,Image.Resampling.BILINEAR,
                             box=(inset,inset//2,SIZE[0]-inset,SIZE[1]-inset//2))
    return draw_edit(frame,edit,t,seconds)


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
