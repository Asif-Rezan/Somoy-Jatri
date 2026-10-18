import copy
import json
import numpy as np
import pytest
from pathlib import Path
from somoy_jatri.config import Config
from somoy_jatri.narration.text import normalize,emotion,validate_segment
from somoy_jatri.narration.providers import provider,MockTTS
from somoy_jatri.storyboard.timeline import build,validate,shard
from somoy_jatri.pipeline import mock_story,prepare,finish
from somoy_jatri.utils import load,save

@pytest.fixture
def prepared(tmp_path,monkeypatch):
    monkeypatch.setenv('OUTPUT_ROOT',str(tmp_path))
    config=Config(run_id='sample')
    shots=prepare(config)
    return config,shots


def test_normalize_dates():
    text=normalize('২৫০০ BCE ও 2026 CE, Giza')
    assert 'খ্রিস্টপূর্ব' in text and 'দুই হাজার পাঁচশত' in text
    assert 'খ্রিস্টাব্দ' in text and 'গিজা' in text and '2026' not in text

def test_century_and_dictionary():
    assert normalize('২১ শতক',{'শতক':'শতাব্দী'})=='একুশ শতাব্দী'

def test_emotional_direction():
    assert emotion('কোথায় এলাম?')=='curious'
    assert emotion('দেখো!')=='amazed'
    for s in mock_story()['segments']:validate_segment(s)
    with pytest.raises(ValueError):validate_segment(dict(text='English only',emotion='neutral'))

def test_secret_free_provider():
    assert isinstance(provider('mock'),MockTTS)

def test_duration_and_config():
    with pytest.raises(ValueError):Config(mode='production',target=30)
    with pytest.raises(ValueError):Config(run_id='../escape')
    with pytest.raises(ValueError):Config(workers=64)

def test_actual_audio_drives_shots(prepared):
    config,shots=prepared
    narration=load(config.root/'narration.json')
    assert shots[1]['start']==narration[0]['end']
    assert len({round(s['end']-s['start'],3) for s in shots})>1
    assert all(abs(s['end']-s['start']-7)>.01 for s in shots)

def test_timeline_rejects_gap_and_overlap(prepared):
    _,shots=prepared
    for delta in [-.1,.1]:
        bad=copy.deepcopy(shots);bad[1]['start']+=delta
        with pytest.raises(ValueError):validate(bad,shots[-1]['end'])

def test_timeline_rejects_nan(prepared):
    _,shots=prepared;shots[0]['end']=float('nan')
    with pytest.raises(ValueError):validate(shots,10)

def test_prompt_correspondence(prepared):
    _,shots=prepared
    assert 'pottery merchant' in shots[1]['prompt']
    shots[1]['anchors']=['smartphone']
    with pytest.raises(ValueError):validate(shots,shots[-1]['end'])

def test_shards_complete_and_disjoint(prepared):
    _,shots=prepared
    results=[s['id'] for i in range(4) for s in shard(shots,i,4)]
    assert len(results)==len(set(results))==len(shots)
    with pytest.raises(ValueError):shard(shots,5,4)

def test_music_moods_and_fades(prepared):
    from somoy_jatri.music.scoring import plan,score
    _,shots=prepared;cues=plan(shots);audio=score(cues,shots[-1]['end'])
    assert len(cues)==3
    assert len(audio)==round(shots[-1]['end']*24000)
    assert abs(audio[0])<.00001 and abs(audio[-1])<.00001
    for c in cues[:-1]:
        boundary=round(c['end']*24000)
        assert np.max(np.abs(np.diff(audio[boundary-5:boundary+5])))<.03

def test_ducking():
    from somoy_jatri.audio import duck_gain
    silence=np.zeros(24000);speech=np.ones(24000)*.15
    assert np.mean(duck_gain(speech))<np.mean(duck_gain(silence))*.3

def test_bangla_subtitles(prepared):
    from somoy_jatri.subtitles.captions import generate
    config,shots=prepared;generate(config.root,shots)
    assert 'বন্ধুরা' in (config.root/'captions.srt').read_text()
    assert 'Noto Sans Bengali' in (config.root/'captions.ass').read_text()

def test_ffmpeg_command():
    from somoy_jatri.renderer.ffmpeg import clip_command
    args=clip_command(Path('image.png'),Path('out.mp4'),4.3,'pan_right',1920,1080,30)
    assert isinstance(args,list) and 'libx264' in args and args[args.index('-frames:v')+1]==129
    assert 's=1920x1080' in args[args.index('-vf')+1]

def test_bengali_asr_rejects_english(monkeypatch):
    # Model import must be optional for offline operation.
    import sys,types
    monkeypatch.setitem(sys.modules,'faster_whisper',types.SimpleNamespace(WhisperModel=object))
    monkeypatch.setenv('ALIGNMENT_MODEL','base.en')
    from somoy_jatri.alignment.timing import BengaliASR
    with pytest.raises(ValueError):BengaliASR()

def test_upload_channel_identity():
    from somoy_jatri.youtube.publish import identity
    class Fake:
        def channels(self):return self
        def list(self,**kw):return self
        def execute(self):return {'items':[{'id':'wrong'}]}
    import os
    from unittest.mock import patch
    with patch.dict(os.environ,{'EXPECTED_CHANNEL_ID':'right'}):
        with pytest.raises(ValueError):identity(Fake())
    with patch.dict(os.environ,{},clear=True):
        with pytest.raises(ValueError):identity(Fake())

def test_public_opt_in(monkeypatch):
    from somoy_jatri.youtube.publish import validate_privacy
    monkeypatch.delenv('ALLOW_PUBLIC_UPLOAD',raising=False)
    validate_privacy('private')
    with pytest.raises(ValueError):validate_privacy('public')

def test_ambiguous_upload_no_reinsert(tmp_path,monkeypatch):
    from somoy_jatri.youtube.publish import upload
    monkeypatch.setenv('UPLOAD_ENABLED','true');monkeypatch.setenv('EXPECTED_CHANNEL_ID','right')
    save(tmp_path/'qc.json',{'production_ready':True});save(tmp_path/'config.json',{'mode':'production'})
    save(tmp_path/'upload.json',{'phase':'ambiguous','channel':'right'})
    monkeypatch.setattr('somoy_jatri.validation.quality.validate_final',lambda *a,**kw:None)
    class Fake:
        def channels(self):return self
        def list(self,**kw):return self
        def execute(self):return {'items':[{'id':'right'}]}
        def videos(self):raise AssertionError('Must not reinsert')
    with pytest.raises(RuntimeError,match='Ambiguous'):upload(tmp_path,client=Fake())

def test_mock_never_uploads(prepared,monkeypatch):
    from somoy_jatri.youtube.publish import upload
    config,_=prepared;save(config.root/'qc.json',{'production_ready':False})
    monkeypatch.setenv('UPLOAD_ENABLED','true')
    with pytest.raises(ValueError,match='Mock'):upload(config.root)

def test_topic_duplicates(tmp_path):
    from somoy_jatri.topics.history import reserve
    path=tmp_path/'history.json'
    reserve(path,'Ancient Egypt market','one');reserve(path,'Ancient Egypt market','one')
    with pytest.raises(ValueError):reserve(path,'Ancient Egypt markets','two')

def test_research_requires_evidence():
    from somoy_jatri.research.dossier import validate
    with pytest.raises(ValueError):validate({'location':'Egypt'})

def test_safe_checkpoint_and_cleanup(prepared):
    from somoy_jatri.storage.safety import checkpoint,cleanup
    config,_=prepared;root=config.root
    (root/'youtube_token.json').write_text('TOPSECRET')
    entries=checkpoint(root)
    assert 'youtube_token.json' not in [e['name'] for e in entries]
    save(root/'qc.json',{'passed':True});save(root/'upload.json',{'phase':'ambiguous'})
    with pytest.raises(ValueError):cleanup(root)
    save(root/'upload.json',{'phase':'verified'})
    cleanup(root)
    assert (root/'story.json').exists() and (root/'youtube_token.json').exists()

def test_drive_recovery_checksum(prepared,tmp_path):
    from somoy_jatri.storage.safety import checkpoint,restore
    config,_=prepared;root=config.root
    entries=checkpoint(root);manifest=load(root/'checkpoint.json')
    blob={e['name']:(root/e['name']).read_bytes() for e in entries}
    class Store:
        def load(self,*a):return manifest
        def find(self,key):return key.split('/',2)[2]
        def download(self,fid,target):target.write_bytes(blob[fid])
    for e in entries:(root/e['name']).unlink()
    restore(root,Store());assert (root/'story.json').exists()
    manifest['files'][0]['sha256']='invalid'
    with pytest.raises(ValueError):restore(root,Store())

def test_cleanup_traversal(prepared):
    from somoy_jatri.storage.safety import cleanup
    config,_=prepared;root=config.root
    save(root/'qc.json',{'passed':True})
    save(root/'checkpoint.json',{'project':'other','run':root.name,'files':[]})
    with pytest.raises(ValueError):cleanup(root)

def test_actual_ffmpeg_end_to_end(prepared):
    from somoy_jatri.images.providers import generate_shard
    config,shots=prepared
    for i in range(config.workers):generate_shard(config.root,shots,i,config.workers,'mock')
    qc=finish(config)
    assert qc['passed'] and not qc['production_ready']
    assert qc['duration']>5 and (config.root/'video.mp4').stat().st_size>10000
