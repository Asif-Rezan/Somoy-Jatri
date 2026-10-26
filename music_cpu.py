"""Render MusicRNN notes as a restrained documentary bed, with mellow sustained pads and gentle, low-register melody."""
import json
import math
import secrets
from pathlib import Path
import subprocess
import wave
import numpy as np

MUSIC_CREDIT = ''


def render_sequence(sequence, path, seed=None):
    # A saved seed keeps recovery reproducible; a new video gets new entropy.
    seed = int(sequence.get('arrangement_seed', secrets.randbits(63)) if seed is None else seed)
    rng = np.random.default_rng(seed)
    tempo = float(rng.uniform(58, 66))
    root = int(rng.choice([57, 59, 60]))
    rate, step = 48000, 60 / tempo / 4
    seconds = float(sequence['totalQuantizedSteps']) * step + 5
    if not 5 < seconds <= 600 or not sequence.get('notes'):
        raise ValueError('Music sequence must contain notes and a bounded duration')
    audio = np.zeros((math.ceil(seconds * rate), 2), dtype=np.float32)
    timeline = np.arange(len(audio), dtype=np.float32) / rate
    # Gentle minor-pentatonic phrases avoid close semitone clashes and piercing lead tones.
    # This is a synthesized documentary arrangement, not a claim of traditional performance.
    scale = (0, 3, 5, 7, 10)
    tonic = 440 * 2 ** ((root - 81) / 12)
    for frequency, gain in ((tonic, .003), (tonic * 1.5, .006)):
        bed = np.sin(2 * np.pi * frequency * timeline) * (.7 + .3 * np.sin(timeline * .2)**2)
        audio += (bed * gain)[:, None]
    for index, note in enumerate(sequence['notes']):
        if index % 8:
            continue
        start = int(int(note['quantizedStartStep']) * step * rate)
        if not 0 <= start < len(audio):
            raise ValueError('Music note outside timeline')
        pitch = int(note['pitch'])
        relative = (pitch - root) % 12
        degree = min(scale, key=lambda value: abs(value - relative))
        pitch = root + degree
        count = min(int(rng.uniform(6.5, 8.5) * rate), len(audio) - start)
        t = np.arange(count, dtype=np.float32) / rate
        hz = 440 * 2 ** ((pitch - 69) / 12)
        # Bowed/wind phrases swell in and release slowly: no struck-key or pluck envelope.
        length = count / rate
        envelope = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 1.4
        # A rounded fundamental with very quiet overtones, without sharp bow noise,
        # breath hiss, high flute doubling, vibrato or percussion transients.
        phase = 2*np.pi*hz*t
        tone = (np.sin(phase) + .12*np.sin(2*phase) + .025*np.sin(3*phase))
        signal = tone * envelope * .04
        pan = float(rng.uniform(.42, .58))
        audio[start:start+count, 0] += signal * np.sqrt(1-pan)
        audio[start:start+count, 1] += signal * np.sqrt(pan)
    # Diffuse stereo reflections from the dry signal, not repeated feedback echoes.
    # Staggered delays and gentle damping give space without metallic ringing.
    dry = audio.copy()
    for delay, gain in ((.071, .12), (.113, .10), (.179, .08), (.293, .065), (.467, .045), (.733, .025)):
        shift = int((delay + rng.uniform(-.006, .006)) * rate)
        reflected = dry[:-shift, ::-1]
        audio[shift:] += reflected * gain
    # Gentle saturation rounds occasional percussion peaks before final headroom.
    # Smooth residual high frequencies before mastering. A short symmetric window
    # avoids filter ringing and retains the warm fundamental melody.
    kernel = np.hanning(97)
    kernel /= kernel.sum()
    for channel in range(2):
        audio[:, channel] = np.convolve(audio[:, channel], kernel, mode='same')
    fade = min(5 * rate, len(audio)//2)
    audio[:fade] *= np.linspace(0, 1, fade)[:, None]
    audio[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = float(np.max(np.abs(audio)))
    if not np.isfinite(audio).all() or peak < .001:
        raise RuntimeError('Generated music is silent or invalid')
    audio *= .24 / peak
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((audio * 32767).astype('<i2').tobytes())
    return seconds


def generate(path):
    notes_path = path.with_suffix('.notes.json')
    subprocess.run(['node', str(Path(__file__).with_name('music_rnn.cjs')), str(notes_path)], check=True)
    sequence = json.loads(notes_path.read_text())
    sequence['arrangement_seed'] = secrets.randbits(63)
    sequence['arrangement_style'] = 'soft-historical-ambient-v3'
    notes_path.write_text(json.dumps(sequence))
    seconds = render_sequence(sequence, path)
    print(json.dumps({'check': 'Generated documentary music audio', 'passed': True,
                      'duration_seconds': round(seconds, 2)}), flush=True)


if __name__ == '__main__':
    import sys
    generate(Path(sys.argv[1]))
