from difflib import SequenceMatcher
import re
import math
from somoy_jatri.utils import duration
import json
import time
import requests

def canonical(text):
    return re.sub(r'[^\w]', '', text)

def bounded_words(words, total):
    """ASR can timestamp decoder padding; caption cues must fit decoded audio."""
    if not math.isfinite(total) or total <= 0:
        raise ValueError('Audio duration must be positive')
    bounded = []
    adjusted = 0
    for word in words:
        start, end = float(word['start']), float(word['end'])
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError('ASR returned non-finite word timing')
        clipped_start = max(0.0, min(total, start))
        clipped_end = max(0.0, min(total, end))
        adjusted += (clipped_start != start or clipped_end != end)
        if clipped_end > clipped_start:
            bounded.append({**word, 'start': clipped_start, 'end': clipped_end})
    if adjusted:
        print(json.dumps({'alignment_stage': 'bounded_caption_timing',
                          'adjusted_words': adjusted, 'audio_seconds': round(total, 3)}), flush=True)
    if words and not bounded:
        raise ValueError('ASR returned no word timing within audio')
    return bounded


class BengaliASR:
    def __init__(self):
        import os
        from faster_whisper import WhisperModel
        model = os.getenv('ALIGNMENT_MODEL', 'base')
        if model.endswith('.en'): raise ValueError('English-only aligner forbidden')
        self.model = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=2)

    def align(self, path, text, strict=True):
        segments, info = self.model.transcribe(str(path), language='bn', word_timestamps=True,
                                               beam_size=3, vad_filter=False)
        segments = list(segments)
        recognized = ''.join(s.text for s in segments)
        similarity = SequenceMatcher(None, canonical(text), canonical(recognized)).ratio()
        words = [{'word': w.word, 'start': w.start, 'end': w.end}
                 for s in segments for w in s.words or [] if w.end > w.start]
        print(json.dumps({'alignment_stage': 'recognized', 'similarity': round(similarity, 3),
                          'word_count': len(words)}), flush=True)
        if strict and (similarity < .65 or not words):
            raise ValueError('Bengali ASR/script mismatch; review pronunciation before continuing')
        total = duration(path)
        words = bounded_words(words, total)
        # Segment-level TTS timing is authoritative; ASR timestamps refine captions only.
        return {'words': words, 'similarity': similarity, 'recognized': recognized}


class GroqASR:
    """Multilingual Whisper with Bengali word timestamps on the configured Groq account."""
    def __init__(self):
        import os
        self.key = os.environ['GROQ_API_KEY']

    def align(self, path, text, strict=True):
        from somoy_jatri.scripts.groq import _retry_delay
        for attempt in range(8):
            with open(path, 'rb') as audio:
                response = requests.post('https://api.groq.com/openai/v1/audio/transcriptions',
                    headers={'Authorization': 'Bearer ' + self.key},
                    files={'file': (path.name, audio, 'audio/wav')},
                    data={'model': 'whisper-large-v3', 'language': 'bn',
                          'response_format': 'verbose_json', 'timestamp_granularities[]': 'word'},
                    timeout=180)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 7:
                delay = _retry_delay(response, attempt)
                print(json.dumps({'alignment_stage': 'retry', 'status': response.status_code,
                                  'wait_seconds': round(delay, 1)}), flush=True)
                time.sleep(delay)
                continue
            if not response.ok:
                raise RuntimeError('Groq transcription failed, HTTP ' + str(response.status_code))
            result = response.json()
            break
        recognized = result.get('text', '')
        similarity = SequenceMatcher(None, canonical(text), canonical(recognized)).ratio()
        words = [{'word': w['word'], 'start': w['start'], 'end': w['end']}
                 for w in result.get('words', []) if w['end'] > w['start']]
        print(json.dumps({'alignment_stage': 'recognized', 'similarity': round(similarity, 3),
                          'word_count': len(words)}), flush=True)
        if strict and (similarity < .65 or not words):
            raise ValueError('Bengali ASR/script mismatch; review pronunciation before continuing')
        total = duration(path)
        words = bounded_words(words, total)
        return {'words': words, 'similarity': similarity, 'recognized': recognized}


def aligner():
    import os
    return GroqASR() if os.getenv('ALIGNMENT_BACKEND', 'local') == 'groq' else BengaliASR()
