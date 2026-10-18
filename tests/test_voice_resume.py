from dataclasses import asdict
import pytest
from somoy_jatri.config import Config
from somoy_jatri.pipeline import mock_story
from somoy_jatri.utils import save,load
from somoy_jatri.narration.providers import take_fingerprint,verified_take,save_verified_take
from somoy_jatri.narration.worker import generate_shard

ASR={'similarity':.9,'words':[{'word':'আমি','start':0,'end':1}]}


def test_verified_receipt_is_bound_to_audio_and_text(tmp_path):
    path=tmp_path/'voice.wav';path.write_bytes(b'original')
    save_verified_take(path,'text-a',ASR)
    assert verified_take(path,'text-a')==ASR
    assert verified_take(path,'text-b') is None
    path.write_bytes(b'changed')
    assert verified_take(path,'text-a') is None


def test_voice_worker_publishes_only_assigned_takes_and_reuses_old_audio(tmp_path,monkeypatch):
    root=tmp_path/'episode-123';root.mkdir();(root/'utterances').mkdir()
    save(root/'config.json',asdict(Config(mode='production',run_id=root.name)))
    story=mock_story();save(root/'story.json',story)
    old=root/'utterances/0000.wav';old.write_bytes(b'existing voice')
    save(old.with_suffix('.json'),{'fingerprint':take_fingerprint(story['segments'][0],'production')})
    calls=[]
    class Voice:
        def synthesize(self,text,emotion,intensity,path):
            calls.append(text);path.write_bytes(b'new voice')
    class Recognition:
        def align(self,*args,**kwargs):return ASR
    monkeypatch.setattr('somoy_jatri.narration.worker.provider',lambda mode:Voice())
    monkeypatch.setattr('somoy_jatri.narration.worker.aligner',Recognition)
    target=tmp_path/'shard'
    generate_shard(root,0,2,target)
    assert len(calls)==1  # Take zero was re-verified, not synthesized again.
    assert old.read_bytes()==b'existing voice'
    assert {p.name for p in (target/'utterances').iterdir()}=={'0000.wav','0000.json','0002.wav','0002.json'}
    # Valid receipts permit recovery without loading a voice or ASR model.
    monkeypatch.setattr('somoy_jatri.narration.worker.provider',lambda mode:pytest.fail('Loaded voice for cached takes'))
    monkeypatch.setattr('somoy_jatri.narration.worker.aligner',lambda:pytest.fail('Repeated ASR for cached takes'))
    generate_shard(root,0,2,tmp_path/'cached-shard')


def test_rejected_speech_cannot_be_cached(tmp_path):
    path=tmp_path/'voice.wav';path.write_bytes(b'bad')
    with pytest.raises(ValueError,match='rejected'):
        save_verified_take(path,'text',{'similarity':.2,'words':[{'word':'আমি'}]})


def test_private_automatic_research_does_not_fabricate_human_review():
    from somoy_jatri.validation.quality import require_research_review
    dossier={'research_method':'automatic source extraction'}
    require_research_review(dossier)
    assert 'reviewed_by' not in dossier
    with pytest.raises(ValueError,match='Research review missing'):
        require_research_review({'research_method':'manual'})


def test_semantic_receipt_is_invalidated_by_story_changes(tmp_path,monkeypatch):
    from somoy_jatri.storyboard.timeline import reviewed_story
    calls=[]
    monkeypatch.setattr('somoy_jatri.storyboard.timeline.evaluate_semantics',
        lambda *a,**kw:calls.append(a[0]) or {'passed':True})
    story={'segments':[{'text':'আমি এখানে আছি'}]};dossier={'facts':[]}
    receipt=tmp_path/'review.json'
    reviewed_story(story,dossier,receipt);reviewed_story(story,dossier,receipt)
    assert len(calls)==1
    story['segments'][0]['text']='আমি এখন ফিরছি'
    reviewed_story(story,dossier,receipt)
    assert len(calls)==2


@pytest.mark.parametrize('privacy',['public','unlisted'])
def test_automatic_research_still_cannot_upload_nonprivately(tmp_path,monkeypatch,privacy):
    from somoy_jatri.youtube.publish import upload
    monkeypatch.setenv('ALLOW_PUBLIC_UPLOAD','true')
    save(tmp_path/'research.json',{'research_method':'automatic source extraction'})
    with pytest.raises(ValueError,match='must remain private'):
        upload(tmp_path,privacy=privacy)
