import numpy as np
from somoy_jatri.audio import RATE
from somoy_jatri.music.scoring import plan, score


def test_documentary_bed_continues_across_image_cuts_and_mood_changes():
    shots=[dict(start=0,end=7,chapter='arrival',mood='curious'),
           dict(start=7,end=14,chapter='arrival',mood='amazed'),
           dict(start=14,end=16.5,chapter='river',mood='reflective')]
    cues=plan(shots)
    assert len(cues)==2
    assert cues[0]['start']==0 and cues[0]['end']==14
    assert all(c['style']=='historical_documentary' and c['ducking'] for c in cues)
    audio=score(cues,16.5)
    assert len(audio)==round(16.5*RATE)
    assert np.isfinite(audio).all()
    assert .001<float(np.sqrt(np.mean(audio**2)))<.1
    assert np.max(np.abs(audio))<.2
    assert audio[0]==0 and audio[-1]==0
