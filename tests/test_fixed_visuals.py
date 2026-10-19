import numpy as np
import pytest
from somoy_jatri.audio import write_wav
from somoy_jatri.narration.providers import measure_take,measured_take,save_measured_take,synthesize_measured
from somoy_jatri.pipeline import mock_story
from somoy_jatri.storyboard.timeline import build
from somoy_jatri.subtitles.captions import generate
from somoy_jatri.utils import save


def test_fixed_schedule_crosses_speech_boundaries_and_short_final_shot():
    story=mock_story()
    bounds=[{'start':0,'speech_end':2,'end':2.3},
            {'start':2.3,'speech_end':12,'end':12.3},
            {'start':12.3,'speech_end':20.8,'end':21.1}]
    dossier={'location':'Giza','period':'ancient','buildings':'stone','clothing':'linen'}
    shots=build(story,bounds,dossier)
    assert [(s['start'],s['end']) for s in shots]==[(0,7),(7,14),(14,21),(21,21.1)]
    assert len({s['id'] for s in shots})==4


def test_caption_sentence_can_span_image_cut(tmp_path):
    save(tmp_path/'narration.json',[{'start':5,'speech_end':9,'end':9.3,'text':'আমি নদীর দিকে তাকিয়ে আছি','audio':{}}])
    generate(tmp_path,[{'start':0,'speech_end':7,'narration':'wrong image text'}])
    content=(tmp_path/'captions.srt').read_text()
    assert '00:00:05,000 --> 00:00:09,000' in content
    assert 'আমি' in content and 'wrong' not in content


def test_audio_receipt_checks_samples_without_transcription(tmp_path):
    path=tmp_path/'voice.wav'
    write_wav(path,.1*np.sin(np.arange(24000)*.1))
    audio=measure_take(path)
    assert audio['passed'] and not audio['transcript_verified']
    save_measured_take(path,'text-a',audio)
    assert measured_take(path,'text-a')['passed']
    assert measured_take(path,'text-b') is None
    write_wav(path,np.zeros(24000))
    assert measured_take(path,'text-a') is None
    with pytest.raises(ValueError,match='silent'):measure_take(path)


def test_silent_voice_is_regenerated_instead_of_accepted(tmp_path):
    class Voice:
        calls=0
        def synthesize(self,text,emotion,intensity,path):
            self.calls+=1
            write_wav(path,np.zeros(24000) if self.calls==1 else .1*np.sin(np.arange(24000)*.1))
    voice=Voice()
    assert synthesize_measured(voice,mock_story()['segments'][0],tmp_path/'voice.wav')['passed']
    assert voice.calls==2


def test_modest_duration_correction_preserves_audio_and_measured_boundaries(tmp_path):
    from somoy_jatri.audio import fit_narration
    from somoy_jatri.utils import duration
    path=tmp_path/'narration.wav'
    write_wav(path,.1*np.sin(np.arange(round(1.9*24000))*.1))
    bounds=[{'start':0,'speech_end':.9,'end':1},{'start':1,'speech_end':1.8,'end':1.9}]
    result=fit_narration(path,bounds,maximum=1.8,target=1.75)
    assert result[-1]['end']==pytest.approx(duration(path))
    assert result[0]['end']==result[1]['start']
    assert 1.6<result[-1]['end']<=1.8
    assert bounds[-1]['end']==1.9


def test_large_overrun_is_not_forced_into_tempo_limit(tmp_path):
    from somoy_jatri.audio import fit_narration
    bounds=[{'start':0,'speech_end':1100,'end':1101}]
    assert fit_narration(tmp_path/'not-read.wav',bounds) is bounds
