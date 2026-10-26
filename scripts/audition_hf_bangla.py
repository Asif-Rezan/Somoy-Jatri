"""Audition a fixed female Bangla HF model without changing production settings."""
from pathlib import Path
import json
import os
import time
import numpy as np
import soundfile as sf
import torch
from huggingface_hub import hf_hub_download
from TTS.api import TTS

REPO = 'kazol196295/bangla-vits-female-1.2'
REVISION = '9c5419799231ddc91641da2f3955556a5d52b66d'
TEXTS = [
    'হাজার বছর আগের মিশর। নীল নদের তীরে গড়ে উঠেছিল এক প্রাচীন সভ্যতা।',
    'নদী শুধু পানির উৎস ছিল না। কৃষিকাজ, যাতায়াত আর মানুষের দৈনন্দিন জীবনের সঙ্গে জড়িয়ে ছিল এই নদী।',
    'আজও মিশরের পিরামিড আর প্রত্নতাত্ত্বিক নিদর্শন সেই ইতিহাসের সাক্ষ্য বহন করছে।',
]


def main():
    torch.set_num_threads(4)
    torch.manual_seed(1729)
    # Restrict checkpoint deserialization even when the inference library calls torch.load.
    os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '1'
    model_path = hf_hub_download(REPO, 'best_model/best_model_step_0026910.pth', revision=REVISION, token=False)
    config_path = hf_hub_download(REPO, 'best_model/config.json', revision=REVISION, token=False)
    unsafe = torch.serialization.get_unsafe_globals_in_checkpoint(model_path)
    if unsafe:
        raise RuntimeError('Checkpoint needs unsupported pickle globals; audition stopped')
    voice = TTS(model_path=model_path, config_path=config_path, progress_bar=False).to('cpu')
    rate = voice.synthesizer.output_sample_rate
    chunks = []
    timings = []
    for index, text in enumerate(TEXTS):
        started = time.monotonic()
        audio = np.asarray(voice.tts(text=text, split_sentences=False), dtype=np.float32)
        seconds = len(audio) / rate
        if (not np.isfinite(audio).all() or not 1 <= seconds <= 40
                or float(np.max(np.abs(audio))) < .001):
            raise ValueError('Hugging Face model returned invalid audio')
        timings.append({'part':index + 1, 'speech_seconds':seconds,
            'inference_seconds':time.monotonic() - started})
        chunks.extend([audio, np.zeros(round(rate * .3), dtype=np.float32)])
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio)))
    if peak > .95:
        audio *= .95 / peak
    root = Path('output/hf-voice-audition')
    root.mkdir(parents=True, exist_ok=True)
    sf.write(root/'huggingface-bangla-female-vits-demo.wav', audio, rate, subtype='PCM_16')
    receipt = {'repo':REPO, 'revision':REVISION, 'speaker':'single female', 'texts':TEXTS,
        'sample_rate':rate, 'seconds':len(audio)/rate, 'timings':timings,
        'peak':float(np.max(np.abs(audio))), 'rms':float(np.sqrt(np.mean(audio**2))),
        'listening_approved':False, 'transcript_verified':False}
    (root/'audition.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({'passed':True, 'seconds':receipt['seconds'], 'model':REPO}), flush=True)


if __name__ == '__main__':
    main()
