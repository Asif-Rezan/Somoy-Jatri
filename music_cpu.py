"""Render MusicRNN notes as a restrained documentary bed, with sustained strings, airy flute and soft frame drums."""
import json
import math
from pathlib import Path
import subprocess
import wave
import numpy as np

MUSIC_CREDIT = ''


def render_sequence(sequence, path):
    rate, step = 24000, 60 / 76 / 4
    seconds = float(sequence['totalQuantizedSteps']) * step + 5
    if not 5 < seconds <= 600 or not sequence.get('notes'):
        raise ValueError('Music sequence must contain notes and a bounded duration')
    audio = np.zeros((math.ceil(seconds * rate), 2), dtype=np.float32)
    timeline = np.arange(len(audio), dtype=np.float32) / rate
    # Hijaz-inspired D mode, instrumental only; warm texture rather than sub-bass drones.
    # This is a synthesized documentary arrangement, not a claim of traditional performance.
    scale = (0, 1, 4, 5, 7, 8, 10)
    for frequency, gain in ((146.83, .012), (220, .008)):
        bed = np.sin(2 * np.pi * frequency * timeline) * (.7 + .3 * np.sin(timeline * .2)**2)
        audio += (bed * gain)[:, None]
    rng = np.random.default_rng(76)
    for onset in np.arange(0, seconds - 2, 60 / 76 * 2):
        start = int(onset * rate)
        t = np.arange(min(rate // 3, len(audio)-start), dtype=np.float32) / rate
        drum = (.7 * np.sin(2*np.pi*(110*t - 25*t*t)) + .12*rng.normal(size=len(t)))
        audio[start:start+len(t)] += (drum * np.exp(-t*24) * .018)[:, None]
    for index, note in enumerate(sequence['notes']):
        if index % 8:
            continue
        start = int(int(note['quantizedStartStep']) * step * rate)
        if not 0 <= start < len(audio):
            raise ValueError('Music note outside timeline')
        pitch = int(note['pitch'])
        relative = (pitch - 62) % 12
        degree = min(scale, key=lambda value: abs(value - relative))
        pitch = 62 + degree
        count = min(6 * rate, len(audio) - start)
        t = np.arange(count, dtype=np.float32) / rate
        hz = 440 * 2 ** ((pitch - 69) / 12)
        # Bowed/wind phrases swell in and release slowly: no struck-key or pluck envelope.
        length = count / rate
        envelope = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 1.4
        vibrato = .035 * np.sin(2*np.pi*4.2*t)
        strings = sum((1 / harmonic**1.7) * (
            np.sin(2*np.pi*hz*harmonic*t + vibrato*harmonic) +
            .45*np.sin(2*np.pi*hz*harmonic*1.0015*t + .3))
            for harmonic in range(1, 8))
        # A sustained breathy flute response, with air smoothed to avoid a hiss.
        breath = rng.normal(0, 1, count)
        breath = np.convolve(breath, np.ones(24)/24, mode='same')
        flute = (np.sin(2*np.pi*hz*2*t + vibrato) +
                 .12*np.sin(2*np.pi*hz*4*t) + .07*breath)
        signal = (strings * .045 + flute * .025) * envelope
        pan = .35 + .3 * (index % 3) / 2
        audio[start:start+count, 0] += signal * (1-pan)
        audio[start:start+count, 1] += signal * pan
    for delay, gain in ((.43, .18), (.81, .09)):
        shift = int(delay * rate)
        audio[shift:] += audio[:-shift, ::-1].copy() * gain
    fade = min(5 * rate, len(audio)//2)
    audio[:fade] *= np.linspace(0, 1, fade)[:, None]
    audio[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = float(np.max(np.abs(audio)))
    if not np.isfinite(audio).all() or peak < .001:
        raise RuntimeError('Generated music is silent or invalid')
    audio *= .55 / peak
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((audio * 32767).astype('<i2').tobytes())
    return seconds


def generate(path):
    notes_path = path.with_suffix('.notes.json')
    subprocess.run(['node', str(Path(__file__).with_name('music_rnn.cjs')), str(notes_path)], check=True)
    seconds = render_sequence(json.loads(notes_path.read_text()), path)
    print(json.dumps({'check': 'Generated documentary music audio', 'passed': True,
                      'duration_seconds': round(seconds, 2)}), flush=True)


if __name__ == '__main__':
    import sys
    generate(Path(sys.argv[1]))
