"""Render and verify a 30-second animated history preview."""
import argparse
import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageOps

from character_rig import character
from thumbnail_design import render_history_thumbnail

ASSETS = Path(__file__).resolve().parent / 'assets' / 'character-preview'
SIZE = (1280, 720)
FPS = 24
SECONDS = 30


def actor(draw, x, ground, *, scale, facing=0, female=False, phase=None, wave=None, blink=False):
    radius = 35 * scale
    draw.ellipse((x-radius, ground-5*scale, x+radius, ground+7*scale), fill=(29, 19, 13, 105))
    character(draw, x, ground, scale=scale, facing=facing, female=female,
              walk_phase=phase, wave=wave, blink=blink, islamic=False)


def render_frame(views, seconds):
    scene = min(int(seconds // 10), len(views) - 1)
    t = seconds - 10 * scene
    frame = views[scene].copy()
    draw = ImageDraw.Draw(frame, 'RGBA')
    blink = t % 3.2 > 3.08
    if scene == 0:
        actor(draw, 88 + 75 * min(t, 8.2), 649, scale=1.0,
              facing=1 if t < 8.2 else 0, phase=8*t if t < 8.2 else None,
              wave=7*t if t >= 8.2 else None, blink=blink)
    elif scene == 1:
        actor(draw, 330, 666, scale=1.18, facing=1,
              wave=6*t if 0.8 < t < 5.0 else None, blink=blink)
        actor(draw, 1130 - 62 * min(t, 6.4), 653, scale=1.12, female=True,
              facing=-1, phase=8*t if t < 6.4 else None,
              wave=7*t if t >= 6.4 else None)
    else:
        actor(draw, 385, 667, scale=1.29, blink=blink,
              wave=7*t if 1 < t < 4.8 else None)
        actor(draw, 776 + 13 * min(t, 7), 650, scale=1.23, female=True,
              facing=0, wave=7*t if 4 <= t < 9 else None, blink=not blink and t % 4 > 3.9)
    return frame


def verify(video):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(video)], check=True, capture_output=True, text=True)
    report = json.loads(result.stdout)
    stream = next(s for s in report['streams'] if s['codec_type'] == 'video')
    if ((stream['width'], stream['height']) != SIZE
            or int(stream['nb_frames']) != FPS * SECONDS
            or not math.isclose(float(report['format']['duration']), SECONDS, abs_tol=0.04)):
        raise RuntimeError('Preview must contain 30 seconds of 1280x720 video at 24 fps')
    if not any(s['codec_type'] == 'audio' for s in report['streams']):
        raise RuntimeError('Preview is missing the narration track')


def render(output, narration=ASSETS / 'rome-narration.wav'):
    output.mkdir(parents=True, exist_ok=True)
    source = ASSETS / 'rome.jpg'
    with Image.open(ASSETS / 'rome-plaza.jpg') as original:
        wide = ImageOps.fit(original.convert('RGB'), SIZE, Image.Resampling.LANCZOS)
    views = (wide, wide.crop((42, 96, 1114, 699)).resize(SIZE, Image.Resampling.LANCZOS),
             wide.crop((175, 69, 1279, 690)).resize(SIZE, Image.Resampling.LANCZOS))

    with Image.open(source) as original:
        thumbnail_art = ImageOps.fit(original.convert('RGB'), SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(thumbnail_art, 'RGBA')
    actor(draw, 229, 828, scale=2.04, facing=1, wave=0.5)
    actor(draw, 472, 819, scale=1.92, female=True, facing=0, wave=1.4)
    artwork = output / '.thumbnail-art.png'
    thumbnail_art.save(artwork)
    try:
        render_history_thumbnail(artwork, 'Rome', 'c. 750 BC – AD 476', output / 'thumbnail.jpg')
    finally:
        artwork.unlink()

    video = output / 'sample.mp4'
    command = ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', '1280x720', '-framerate', str(FPS), '-i', 'pipe:0',
               '-i', str(narration), '-af', 'apad', '-c:a', 'aac', '-b:a', '128k',
               '-t', str(SECONDS), '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for frame in range(SECONDS * FPS):
            encoder.stdin.write(render_frame(views, frame / FPS).tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('FFmpeg could not encode the sample')
    verify(video)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output/animated-history-preview'))
    render(parser.parse_args().output)
