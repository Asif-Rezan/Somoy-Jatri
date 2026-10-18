from pathlib import Path
from typing import Protocol
import os
import numpy as np
from somoy_jatri.audio import write_wav

class BanglaTTSProvider(Protocol):
    def synthesize(self, text: str, emotion: str, intensity: float, path: Path) -> None: ...

class MockTTS:
    """Audible tone fixture, NEVER speech and NEVER permitted for upload."""
    def synthesize(self, text, emotion, intensity, path):
        seconds = 1.4 + len(text) / 55
        t = np.arange(int(24000 * seconds)) / 24000
        envelope = np.minimum(t/.03, 1) * np.minimum((seconds-t)/.06, 1)
        write_wav(path, .12*np.sin(2*np.pi*220*t)*envelope)

class IndicParlerTTS:
    """Bengali female voice; the public model has no named speaker control."""
    def __init__(self):
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        self.torch = torch
        torch.set_num_threads(int(os.getenv('CPU_THREADS', '2')))
        model = os.getenv('TTS_MODEL', 'Tanmoyshome/bn-parler-tts')
        self.named_voice = model == 'ai4bharat/indic-parler-tts'
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(model).to('cpu').eval()
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.description = AutoTokenizer.from_pretrained(self.model.config.text_encoder._name_or_path)

    def synthesize(self, text, emotion, intensity, path):
        styles = {'curious': 'conversational', 'excited': 'happy', 'amazed': 'surprised',
                  'concerned': 'slightly fearful', 'reflective': 'calm narration',
                  'soft': 'soft narration', 'dramatic': 'expressive narration'}
        if self.named_voice:
            voice = os.getenv('TTS_VOICE', 'Aditi')
            if voice not in {'Aditi', 'Rashmi', 'Riya'}:
                raise ValueError('Select a documented Bengali female speaker')
            style = styles.get(emotion, emotion)
            if os.getenv('TTS_EMOTION_ENABLED', 'true') != 'true': style = 'neutral'
            caption = (f'{voice}, a Bengali female speaker, delivers {style} speech at a moderate pace, '
                       'with natural pauses and very clear audio, close recording without background noise.')
        else:
            caption = 'A Bengali female speaker speaks at a moderate pace in a very clear recording.'
        d = self.description(caption, return_tensors='pt')
        p = self.tokenizer(text, return_tensors='pt')
        with self.torch.inference_mode():
            audio = self.model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        write_wav(path, audio.cpu().numpy().squeeze(), self.model.config.sampling_rate)


def provider(mode):
    return MockTTS() if mode == 'mock' else IndicParlerTTS()


def synthesize_verified(tts, aligner, segment, path, reuse=False, attempts=3):
    """Retry a bad voice take without relaxing the transcription quality gate."""
    import json
    for attempt in range(attempts):
        if not reuse or attempt:
            tts.synthesize(segment['text'], segment['emotion'], segment['intensity'], path)
        result = aligner.align(path, segment['text'], strict=False)
        if result['similarity'] >= .65 and result['words']:
            return result
        print(json.dumps({'voice_stage': 'take_rejected', 'attempt': attempt + 1,
                          'similarity': round(result['similarity'], 3)}), flush=True)
    raise ValueError('Bengali narration did not match after three voice takes')


def take_fingerprint(segment, mode):
    import hashlib
    # Keep compatibility with fingerprints already saved by the production workflow.
    return hashlib.sha256((segment['text']+segment['emotion']+str(segment['intensity'])+
        os.getenv('TTS_MODEL','indic-parler')+os.getenv('TTS_VOICE','Aditi')+mode).encode()).hexdigest()


def verified_take(path, fingerprint):
    from somoy_jatri.utils import load, digest
    stamp = path.with_suffix('.json')
    if not path.exists() or not stamp.exists(): return None
    receipt = load(stamp)
    asr = receipt.get('asr', {})
    if (receipt.get('fingerprint') == fingerprint and receipt.get('sha256') == digest(path)
            and asr.get('similarity', 0) >= .65 and asr.get('words')):
        return asr
    return None


def save_verified_take(path, fingerprint, asr):
    from somoy_jatri.utils import save, digest
    if asr.get('similarity', 0) < .65 or not asr.get('words'):
        raise ValueError('Cannot cache rejected speech')
    save(path.with_suffix('.json'), {'fingerprint':fingerprint,'sha256':digest(path),'asr':asr})
