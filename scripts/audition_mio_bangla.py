"""Audition free Indic-Mio with its inference project's fixed female preset."""
from pathlib import Path
import hashlib
import io
import json
import time
import urllib.request
import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from miocodec import MioCodecModel

MODEL = 'SPRINGLab/Indic-Mio'
REVISION = '25feace00ca76c71c40b1e8d921fd3c2943c545e'
CODEC = 'Aratako/MioCodec-25Hz-24kHz'
CODEC_REVISION = '3a737f0de2c6324cb2fe40c1fbd1056c7add423d'
PRESET_REVISION = '2763e0910b251510c6b6a432e5f605d57c5e7ff5'
PRESET_SHA256 = '5a386d2ee0b48036586fc322da0ccf4b88f585ef9162e0371a9999637ebd7645'
TEXTS = [
    'হাজার বছর আগের মিশর। নীল নদের তীরে গড়ে উঠেছিল এক প্রাচীন সভ্যতা।',
    'নদী শুধু পানির উৎস ছিল না। কৃষিকাজ আর মানুষের দৈনন্দিন জীবনের সঙ্গে জড়িয়ে ছিল এই নদী।',
    'আজও মিশরের পিরামিড আর প্রত্নতাত্ত্বিক নিদর্শন সেই ইতিহাসের সাক্ষ্য বহন করছে।',
]


def main():
    torch.set_num_threads(4)
    torch.manual_seed(1729)
    root = Path('output/mio-voice-audition')
    root.mkdir(parents=True, exist_ok=True)
    url = f'https://raw.githubusercontent.com/Aratako/MioTTS-Inference/{PRESET_REVISION}/presets/en_female.pt'
    data = urllib.request.urlopen(url, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != PRESET_SHA256:
        raise ValueError('Female preset checksum changed')
    embedding = torch.load(io.BytesIO(data), map_location='cpu', weights_only=True)
    if isinstance(embedding, dict):
        embedding = embedding.get('global_embedding', embedding.get('embedding'))
    embedding = torch.as_tensor(embedding, dtype=torch.float32).squeeze()
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, token=False)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION,
        token=False, torch_dtype=torch.float32, attn_implementation='sdpa').eval()
    codec = MioCodecModel.from_pretrained(CODEC, revision=CODEC_REVISION).eval()
    rate = int(codec.config.sample_rate)
    if not codec.config.use_wave_decoder:
        raise ValueError('Audition requires the native waveform decoder')
    chunks = []
    timings = []
    for index, text in enumerate(TEXTS):
        started = time.monotonic()
        prompt = tokenizer.apply_chat_template([{'role':'user','content':text}],
            tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors='pt')
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=1024, do_sample=True,
                temperature=.8, top_p=.9)
            generated = output[0, inputs['input_ids'].shape[1]:].tolist()
            if len(generated) >= 1024:
                raise ValueError('Speech generation did not finish within the token budget')
            codes = [value - 151669 for value in generated if 151669 <= value < 164469]
            if len(codes) < 25:
                raise ValueError('Insufficient generated speech tokens')
            audio = codec.decode(global_embedding=embedding,
                content_token_indices=torch.tensor(codes,dtype=torch.long)).float().cpu().numpy().squeeze()
        seconds = len(audio)/rate
        if audio.ndim != 1 or not np.isfinite(audio).all() or not 1 <= seconds <= 40 or np.max(np.abs(audio)) < .001:
            raise ValueError('Invalid model audio')
        timings.append({'part':index+1,'speech_seconds':seconds,'inference_seconds':time.monotonic()-started})
        chunks.extend([audio,np.zeros(round(rate*.3),dtype=np.float32)])
        print(json.dumps({'stage':'sample_part_ready','part':index+1,'seconds':seconds}),flush=True)
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio)))
    if peak > .95: audio *= .95/peak
    sf.write(root/'indic-mio-bangla-female-demo.wav',audio,rate,subtype='PCM_16')
    receipt = {'model':MODEL,'revision':REVISION,'codec':CODEC,'codec_revision':CODEC_REVISION,
        'preset':'MioTTS-Inference/en_female','preset_revision':PRESET_REVISION,
        'sample_rate':rate,'seconds':len(audio)/rate,'texts':TEXTS,'timings':timings,
        'peak':float(np.max(np.abs(audio))),'rms':float(np.sqrt(np.mean(audio**2))),
        'listening_approved':False,'transcript_verified':False}
    (root/'audition.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':True,'seconds':receipt['seconds']}),flush=True)


if __name__ == '__main__':
    main()
