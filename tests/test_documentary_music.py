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


def test_chapter_music_tracks_dominant_mood_and_intensity():
    shots=[dict(start=0,end=7,chapter='arrival',mood='curious'),
           dict(start=7,end=10,chapter='arrival',mood='amazed'),
           dict(start=10,end=20,chapter='discovery',mood='excited'),
           dict(start=20,end=30,chapter='return',mood='soft')]
    cues=plan(shots)
    assert [c['mood'] for c in cues]==['curious','excited','soft']
    assert cues[1]['intensity']>cues[0]['intensity']>cues[2]['intensity']


def test_musicrnn_receives_each_chapter_mood(tmp_path,monkeypatch):
    from somoy_jatri.music.scoring import MusicRNN
    from somoy_jatri.audio import write_wav
    moods=[]
    def generate(path,mood):
        moods.append(mood)
        t=np.arange(25*RATE)/RATE
        write_wav(path,.1*np.sin(2*np.pi*220*t))
    monkeypatch.setattr('somoy_jatri.music.music_cpu.generate',generate)
    cues=[dict(start=0,end=10,mood='curious',intensity=.4,fade=1.5),
          dict(start=10,end=20,mood='dramatic',intensity=.65,fade=1.5)]
    audio=MusicRNN(tmp_path).compose(20,cues)
    assert moods==['curious','dramatic']
    assert len(audio)==20*RATE and np.isfinite(audio).all()
    # Overlap never drops the soundtrack to silence at the chapter boundary.
    assert np.sqrt(np.mean(audio[10*RATE-240:10*RATE+240]**2))>.001


def test_music_renderer_changes_tempo_with_mood(tmp_path):
    from somoy_jatri.music.music_cpu import render_sequence
    sequence={'totalQuantizedSteps':512,'notes':[
        {'pitch':62,'quantizedStartStep':0,'quantizedEndStep':4}]}
    calm=render_sequence(sequence,tmp_path/'calm.wav',mood='soft')
    excited=render_sequence(sequence,tmp_path/'excited.wav',mood='excited')
    assert calm>excited
