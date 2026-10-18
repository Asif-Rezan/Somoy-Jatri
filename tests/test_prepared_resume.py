import pytest
from dataclasses import asdict
from somoy_jatri.config import Config
from somoy_jatri.pipeline import mock_story
from somoy_jatri.storyboard.timeline import build
from somoy_jatri.storage.prepared import repartition
from somoy_jatri.utils import save, load


@pytest.fixture
def checkpoint(tmp_path, monkeypatch):
    root = tmp_path/'episode-123'
    root.mkdir()
    save(root/'config.json', asdict(Config(mode='production',run_id=root.name)))
    story = mock_story()
    dossier = {'location':'Giza', 'period':'Old Kingdom', 'buildings':'stone', 'clothing':'linen'}
    bounds = [{'start':i*200,'speech_end':(i+1)*200-.3,'end':(i+1)*200} for i in range(3)]
    save(root/'timeline.json', build(story,bounds,dossier))
    save(root/'narration.json',[{'asr':{'similarity':.9,'words':[{'word':'আমি'}]}} for _ in range(3)])
    save(root/'semantic-review.json',{'passed':True})
    (root/'narration.wav').write_bytes(b'unchanged voice fixture')
    monkeypatch.setattr('somoy_jatri.storage.prepared.duration',lambda path:600)
    return root


def test_resume_changes_only_worker_partition(checkpoint):
    before = {p.name:p.read_bytes() for p in checkpoint.iterdir() if p.name!='config.json'}
    assert repartition(checkpoint,16) == {'shard':list(range(16))}
    assert load(checkpoint/'config.json')['workers'] == 16
    assert before == {p.name:p.read_bytes() for p in checkpoint.iterdir() if p.name!='config.json'}


def test_resume_rejects_failed_speech(checkpoint):
    save(checkpoint/'narration.json',[{'asr':{'similarity':.2}}]*3)
    with pytest.raises(ValueError,match='speech verification'):
        repartition(checkpoint,16)


def test_resume_rejects_failed_semantic_review(checkpoint):
    save(checkpoint/'semantic-review.json',{'passed':False})
    with pytest.raises(ValueError,match='semantic review'):
        repartition(checkpoint,16)
