"""Reference-style real voice readiness, using the Bengali production adapter."""
from pathlib import Path
import tempfile
from somoy_jatri.narration.providers import provider
from somoy_jatri.preparation.pipeline import chapter_audio
voice=provider('production')
with tempfile.TemporaryDirectory(prefix='somoy-voice-check-') as directory:
    root=Path(directory)
    for i,text in enumerate(['বন্ধুরা, আজ আমরা ইতিহাসের পথে নতুন এক যাত্রায় বেরিয়েছি।',
                             'প্রাচীন স্থাপত্যের সামনে দাঁড়িয়ে সময়ের পরিবর্তন নিয়ে ভাবছি।']):
        chapter_audio(root,i,text,voice)
print('Bengali production voice readiness passed',flush=True)
