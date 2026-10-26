"""Reference-style real voice readiness, using the Bengali production adapter."""
from pathlib import Path
import tempfile
from somoy_jatri.narration.providers import provider
from somoy_jatri.preparation.pipeline import chapter_audio
voice=provider('production')
with tempfile.TemporaryDirectory(prefix='somoy-voice-check-') as directory:
    root=Path(directory)
    for i,text in enumerate(['প্রাচীন মিশরের ইতিহাসে স্থাপত্যের বিশেষ গুরুত্ব রয়েছে।',
                             'প্রত্নতাত্ত্বিক নিদর্শন থেকে সেই সময়ের সমাজ সম্পর্কে জানা যায়।']):
        chapter_audio(root,i,text,voice)
print('Bengali production voice readiness passed',flush=True)
