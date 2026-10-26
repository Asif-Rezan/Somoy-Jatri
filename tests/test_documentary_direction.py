import pytest
from somoy_jatri.preparation.story import validate_documentary, narration_batch, KEYS
from somoy_jatri.narration.providers import documentary_caption, take_fingerprint


def test_documentary_rejects_host_without_rejecting_word_substrings():
    for text in ['আমি এখানে দাঁড়িয়ে আছি।', 'আমাদের সামনে পিরামিড।']:
        with pytest.raises(ValueError, match='first-person'):
            validate_documentary(text)
    validate_documentary('পিরামিডের ইতিহাসে আমিরদের ভূমিকা বর্ণিত হয়েছে।')


def test_narration_rewrites_first_person_batch():
    calls=[]
    def request(prompt, *args):
        calls.append(prompt)
        word='আমি' if len(calls)==1 else 'ইতিহাস'
        return {'narrations':{k:' '.join([word]*74)+' রয়েছে।' for k in KEYS[:5]}}
    result=narration_batch('Write history',KEYS[:5],75,request)
    assert len(calls)==2 and 'objective third-person' in calls[-1]
    assert all('আমি' not in text for text in result)


def test_voice_delivery_and_cache_ignore_scene_emotions(monkeypatch):
    monkeypatch.delenv('TTS_MODEL',raising=False)
    monkeypatch.setenv('TTS_EMOTION_ENABLED','true')
    a={'text':'প্রাচীন ইতিহাস।','emotion':'excited','intensity':1}
    b=dict(a,emotion='soft',intensity=.1)
    assert take_fingerprint(a,'production')==take_fingerprint(b,'production')
    assert 'male speaker' in documentary_caption()
    monkeypatch.setenv('TTS_VOICE','Arjun')
    assert documentary_caption(True).startswith('Arjun delivers calm, neutral')
