from difflib import SequenceMatcher
import re
from somoy_jatri.utils import duration
import json

def canonical(text):
    return re.sub(r'[^\w]', '', text)

class BengaliASR:
    def __init__(self):
        import os
        from faster_whisper import WhisperModel
        model = os.getenv('ALIGNMENT_MODEL', 'small')
        if model.endswith('.en'): raise ValueError('English-only aligner forbidden')
        self.model = WhisperModel(model, device='cpu', compute_type='int8')

    def align(self, path, text, strict=True):
        segments, info = self.model.transcribe(str(path), language='bn', word_timestamps=True,
                                               beam_size=5, vad_filter=False)
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
        if any(w['start'] < 0 or w['end'] > total+.1 for w in words):
            raise ValueError('ASR timestamp outside audio')
        # Segment-level TTS timing is authoritative; ASR timestamps refine captions only.
        return {'words': words, 'similarity': similarity, 'recognized': recognized}
