"""Render and verify a 30-second animated history preview."""
import argparse
import hashlib
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


SCENES = (
    ('rome-settlement.jpg',
     'Unoccupied early Iron Age settlement in central Italy, round thatched huts, wood fences, grassy hills, wide dirt path across the foreground.',
     'Rome began among small settlements in central Italy. Early communities lived in simple huts before Rome grew into a city.'),
    ('rome-plaza.jpg',
     'Unoccupied imperial Rome plaza, Colosseum on the left, Roman temples and terracotta roofs, wide flat stone pavement across the foreground.',
     'The Roman Republic expanded around the Mediterranean. Under Augustus, Rome entered its imperial age, and monumental buildings reshaped the city.'),
    ('rome-harbor.jpg',
     'Unoccupied late antique Constantinople harbor, wooden sailing ships, fortified shoreline and rooftops, wide stone quay across the foreground.',
     'Power shifted east to Constantinople. The last emperor in Italy was deposed in four seventy-six, and the Eastern Roman Empire continued.'),
)
SCENE_SECONDS = SECONDS // len(SCENES)


def generate_backgrounds(scenes, output):
    from image_cpu import generate

    paths = []
    for index, (_, setting, narration) in enumerate(scenes, 1):
        prompt = (f'{setting} Eye-level wide shot, fine ink and warm watercolor. '
                  'Open ground across the lower third, no people, no lettering.')
        digest = hashlib.sha256(f'{index}:{setting}:{narration}'.encode()).digest()
        seed = int.from_bytes(digest[:4], 'big')
        image = output / f'scene-{index:02}.png'
        print(f'Generating background {index}/{len(scenes)}: {setting}', flush=True)
        generate(prompt, image, seed=seed, illustrated=True)
        paths.append(image)
    return paths


def actor(draw, x, ground, *, scale, facing=0, female=False, phase=None, wave=None,
          blink=False, basket=False, point=False):
    radius = 35 * scale
    draw.ellipse((x-radius, ground-5*scale, x+radius, ground+7*scale), fill=(29, 19, 13, 105))
    character(draw, x, ground, scale=scale, facing=facing, female=female,
              walk_phase=phase, wave=wave, blink=blink, basket=basket, point=point,
              islamic=False)


def render_frame(views, seconds):
    scene = min(int(seconds // SCENE_SECONDS), len(views) - 1)
    t = seconds - SCENE_SECONDS * scene
    frame = views[scene].copy()
    draw = ImageDraw.Draw(frame, 'RGBA')
    blink = t % 3.2 > 3.08

    if scene == 0:
        # At the settlement, a resident carries a basket along the village path.
        steps = min(t, 8.2)
        actor(draw, 140 + 81 * steps, 661, scale=1.13, facing=1,
              phase=8*t if t < 8.2 else None, basket=True, blink=blink)
    elif scene == 1:
        # The guide turns toward the imperial buildings as the other resident arrives.
        steps = min(t, 4.5)
        actor(draw, 656, 665, scale=1.17, facing=-1, point=t >= 4.5, blink=blink)
        actor(draw, 1160 - 61 * steps, 644, scale=1.1, female=True,
              facing=-1, phase=8*t if t < 4.5 else None)
    else:
        # On the quay, a farewell gesture marks the transition east.
        steps = min(t, 6.7)
        actor(draw, 275, 665, scale=1.19, facing=1, wave=6*t if 2 < t < 8 else None, blink=blink)
        actor(draw, 513 + 62 * steps, 645, scale=1.06, female=True,
              facing=1, phase=8*t if t < 6.7 else None, point=t >= 6.7)
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


def render(output, narration=ASSETS / 'rome-narration.wav', *, ai_backgrounds=False):
    output.mkdir(parents=True, exist_ok=True)
    source = ASSETS / 'rome.jpg'
    backgrounds = (generate_backgrounds(SCENES, output / 'backgrounds') if ai_backgrounds
                   else [ASSETS / filename for filename, _, _ in SCENES])
    views = []
    for background in backgrounds:
        with Image.open(background) as original:
            views.append(ImageOps.fit(original.convert('RGB'), SIZE, Image.Resampling.LANCZOS))

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
    parser.add_argument('--ai-backgrounds', action='store_true',
                        help='Generate each scene background with the CPU diffusion model')
    args = parser.parse_args()
    render(args.output, ai_backgrounds=args.ai_backgrounds)
