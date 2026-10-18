import wave
import numpy as np
from somoy_jatri.utils import run

RATE = 24000

def write_wav(path, samples, rate=RATE):
    samples = np.asarray(samples, dtype=np.float32)
    if not np.isfinite(samples).all() or len(samples) == 0:
        raise ValueError('Invalid audio samples')
    if np.max(np.abs(samples)) > 1:
        raise ValueError('Clipping audio')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1 if samples.ndim == 1 else samples.shape[1])
        f.setsampwidth(2); f.setframerate(rate)
        f.writeframes((samples * 32767).astype('<i2').tobytes())

def read_wav(path):
    raw = run_audio(path)
    return np.frombuffer(raw, dtype='<f4').copy()

def run_audio(path):
    import subprocess
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le',
        '-ac', '1', '-ar', str(RATE), 'pipe:1'], capture_output=True, check=True).stdout

def concatenate(parts, output):
    # Independently synthesized utterances preserve actual measured event boundaries.
    arrays, boundaries, offset = [], [], 0.0
    for path, pause in parts:
        samples = read_wav(path)
        if np.max(np.abs(samples)) < .001: raise ValueError('Silent narration')
        n = min(120, len(samples)//2)
        samples[:n] *= np.linspace(0, 1, n)
        samples[-n:] *= np.linspace(1, 0, n)
        spoken = len(samples)/RATE
        boundaries.append({'start': offset, 'speech_end': offset+spoken,
                           'end': offset+spoken+pause/1000})
        arrays.extend([samples, np.zeros(round(pause*RATE/1000), dtype=np.float32)])
        offset = boundaries[-1]['end']
    joined = np.concatenate(arrays)
    joined *= .78 / max(float(np.max(np.abs(joined))), .001)
    write_wav(output, joined)
    return boundaries

def duck_gain(voice, base=.13):
    # Fast attack envelope with release smoothing, never boosts music above base.
    block = 480
    envelope = np.zeros(len(voice), dtype=np.float32)
    previous = 0.0
    for i in range(0, len(voice), block):
        rms = float(np.sqrt(np.mean(voice[i:i+block]**2)))
        activity = min(1., rms/.025)
        previous = max(activity, previous*.88)
        envelope[i:i+block] = base * (1-.78*previous)
    return envelope
