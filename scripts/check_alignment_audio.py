"""Check the real Whisper decoder before expensive story and speech generation."""
import tempfile
from pathlib import Path
import numpy as np
from faster_whisper.audio import decode_audio
from somoy_jatri.audio import write_wav


def check():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'alignment-check.wav'
        samples = .1 * np.sin(2 * np.pi * 220 * np.arange(24000) / 24000)
        write_wav(path, samples)
        decoded = decode_audio(str(path), sampling_rate=16000)
        if len(decoded) != 16000 or not np.isfinite(decoded).all():
            raise ValueError('Whisper audio decoding failed')
    print('Whisper audio decoding passed')


if __name__ == '__main__':
    check()
