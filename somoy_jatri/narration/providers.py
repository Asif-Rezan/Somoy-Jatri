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

VOICE_RENDER_VERSION = 'bangla-documentary-v2'


def documentary_caption(named_voice=False):
    if named_voice:
        voice = os.getenv('TTS_VOICE', 'Arjun')
        if voice not in {'Arjun', 'Aditi', 'Tapan', 'Rashmi', 'Arnav', 'Riya'}:
            raise ValueError('Select a documented Bengali speaker')
        return (f'{voice} delivers calm, neutral Bengali narration at a moderate pace, '
                'with clear articulation and natural pauses, in a very clear close recording without background noise.')
    # Match the fine-tune's attribute-based training descriptions.
    return 'A Bengali male speaker speaks at a moderate pace in a very clear recording.'


class IndicParlerTTS:
    """Fixed documentary delivery; ignore legacy per-scene emotion fields."""
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
        caption = documentary_caption(self.named_voice)
        d = self.description(caption, return_tensors='pt')
        p = self.tokenizer(text, return_tensors='pt')
        with self.torch.random.fork_rng(devices=[]), self.torch.inference_mode():
            self.torch.manual_seed(1729)
            audio = self.model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask, do_sample=False)
        write_wav(path, audio.cpu().numpy().squeeze(), self.model.config.sampling_rate)


ONLINE_VOICE = 'bn-BD-PradeepNeural'
ONLINE_RATE = '-8%'


class OnlineBanglaTTS:
    """One Bangladesh Bangla narrator for the entire episode; no emotion switching."""
    def synthesize(self, text, emotion, intensity, path):
        import edge_tts
        import subprocess
        import tempfile
        import time
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='somoy-online-voice-', dir=path.parent) as work:
            mp3 = Path(work) / 'speech.mp3'
            wav = Path(work) / 'speech.wav'
            for attempt in range(3):
                try:
                    edge_tts.Communicate(text, ONLINE_VOICE, rate=ONLINE_RATE,
                        pitch='+0Hz', volume='+0%', connect_timeout=20,
                        receive_timeout=90).save_sync(str(mp3))
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp3),
                        '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)],
                        capture_output=True, check=True, timeout=120)
                    # Audio validation occurs before the file becomes cacheable.
                    from somoy_jatri.audio import read_wav
                    samples = read_wav(wav)
                    if not len(samples) or not np.isfinite(samples).all() or np.max(np.abs(samples)) < .001:
                        raise ValueError('Online voice returned invalid audio')
                    wav.replace(path)
                    return
                except Exception:
                    if attempt == 2:
                        raise RuntimeError('Online Bangla narration failed after three attempts; retry when the service is available') from None
                    time.sleep(2 ** attempt)


def provider(mode):
    if mode == 'mock':
        return MockTTS()
    backend = os.getenv('TTS_BACKEND', 'edge-tts')
    if backend == 'edge-tts':
        return OnlineBanglaTTS()
    if backend == 'indic-parler':
        return IndicParlerTTS()
    raise ValueError('Unsupported production voice provider')



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
    import json
    if os.getenv('TTS_BACKEND', 'edge-tts') == 'edge-tts':
        return hashlib.sha256(json.dumps({'text': segment['text'], 'mode': mode,
            'backend': 'edge-tts', 'voice': ONLINE_VOICE, 'rate': ONLINE_RATE,
            'pitch': '+0Hz', 'volume': '+0%', 'version': 'online-documentary-v1'},
            sort_keys=True).encode()).hexdigest()
    return hashlib.sha256(json.dumps({'text': segment['text'], 'mode': mode,
        'model': os.getenv('TTS_MODEL', 'Tanmoyshome/bn-parler-tts'),
        'caption': documentary_caption(os.getenv('TTS_MODEL') == 'ai4bharat/indic-parler-tts'),
        'voice': os.getenv('TTS_VOICE', 'Arjun'), 'version': VOICE_RENDER_VERSION}, sort_keys=True).encode()).hexdigest()



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


def measure_take(path):
    """Validate audio itself; transcription similarity is not an image/voice gate."""
    from somoy_jatri.audio import read_wav, RATE
    import subprocess
    try:samples=read_wav(path)
    except subprocess.CalledProcessError:raise ValueError('Unreadable narration audio') from None
    seconds=len(samples)/RATE
    if not np.isfinite(samples).all() or not .3<=seconds<=60:
        raise ValueError('Invalid narration audio duration or samples')
    peak=float(np.max(np.abs(samples)))
    rms=float(np.sqrt(np.mean(samples**2)))
    if peak<.001 or rms<.0005 or float(np.mean(np.abs(samples)>=.999))>.001:
        raise ValueError('Narration audio is silent or clipped')
    return {'method':'measured-audio','passed':True,'seconds':seconds,'peak':peak,'rms':rms,
            'transcript_verified':False}


def measured_take(path, fingerprint):
    from somoy_jatri.utils import load, digest
    stamp=path.with_suffix('.json')
    if not path.exists() or not stamp.exists():return None
    receipt=load(stamp)
    if receipt.get('fingerprint')!=fingerprint or receipt.get('sha256')!=digest(path):return None
    try:return measure_take(path)
    except ValueError:return None


def save_measured_take(path,fingerprint,audio):
    from somoy_jatri.utils import save,digest
    checked=measure_take(path)
    save(path.with_suffix('.json'),{'fingerprint':fingerprint,'sha256':digest(path),'audio':checked})


def synthesize_measured(tts,segment,path,reuse=False,attempts=3):
    import json
    for attempt in range(attempts):
        if not reuse or attempt:tts.synthesize(segment['text'],segment['emotion'],segment['intensity'],path)
        try:return measure_take(path)
        except ValueError:
            print(json.dumps({'voice_stage':'audio_rejected','attempt':attempt+1}),flush=True)
    raise ValueError('Narration audio failed checks after three takes')


def audio_record_passed(record):
    audio=record.get('audio',{})
    # Existing ASR-verified receipts remain valid for older saved episodes.
    return (audio.get('method')=='measured-chapter-audio' and audio.get('passed') is True
            and .3<=audio.get('seconds',0)<=180 and audio.get('rms',0)>=.0005) or (audio.get('method')=='measured-audio' and audio.get('passed') is True
            and .3<=audio.get('seconds',0)<=60 and audio.get('rms',0)>=.0005) or (
                record.get('asr',{}).get('similarity',0)>=.65 and bool(record.get('asr',{}).get('words')))
