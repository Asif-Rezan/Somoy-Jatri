from types import SimpleNamespace
from unittest.mock import Mock
import sys
import numpy as np
import pytest
from somoy_jatri.audio import write_wav, RATE
from somoy_jatri.narration.providers import provider, OnlineBanglaTTS, take_fingerprint, ONLINE_VOICE


def test_online_voice_is_default_and_fixed_despite_scene_controls(monkeypatch,tmp_path):
    monkeypatch.delenv('TTS_BACKEND',raising=False)
    monkeypatch.setenv('TTS_VOICE','different-old-voice')
    calls=[]
    class Speech:
        def __init__(self,text,voice,**kwargs):calls.append((text,voice,kwargs))
        def save_sync(self,path):
            t=np.arange(RATE)/RATE
            write_wav(path,.1*np.sin(2*np.pi*180*t))
    monkeypatch.setitem(sys.modules,'edge_tts',SimpleNamespace(Communicate=Speech))
    voice=provider('production')
    assert isinstance(voice,OnlineBanglaTTS)
    for mood in ['amazed','soft']:
        voice.synthesize('প্রাচীন ইতিহাস।',mood,1,tmp_path/f'{mood}.wav')
        assert (tmp_path/f'{mood}.wav').exists()
    assert calls[0]==calls[1]
    assert calls[0][1]==ONLINE_VOICE=='bn-BD-NabanitaNeural'
    assert calls[0][2]['rate']=='-8%'
    assert not list(tmp_path.glob('somoy-online-voice-*'))


def test_online_service_outage_retries_without_local_voice_fallback(monkeypatch,tmp_path):
    broken=Mock(side_effect=ConnectionError('private service detail'))
    monkeypatch.setitem(sys.modules,'edge_tts',SimpleNamespace(Communicate=broken))
    monkeypatch.setattr('time.sleep',lambda seconds:None)
    path=tmp_path/'voice.wav'
    with pytest.raises(RuntimeError,match='after three attempts') as error:
        OnlineBanglaTTS().synthesize('ইতিহাস।','neutral',.5,path)
    assert broken.call_count==3 and not path.exists()
    assert 'private service detail' not in str(error.value)


def test_voice_receipts_change_when_switching_backends(monkeypatch):
    text={'text':'প্রাচীন ইতিহাস।'}
    monkeypatch.setenv('TTS_BACKEND','indic-parler')
    local=take_fingerprint(text,'production')
    monkeypatch.setenv('TTS_BACKEND','edge-tts')
    assert local!=take_fingerprint(text,'production')
