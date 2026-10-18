import hashlib
import json

import pytest

from scripts.stage_verified_story import require_verification, stage
from somoy_jatri.utils import save, load


def metadata(**updates):
    return dict(conclusion='success', status='completed',
                path='.github/workflows/verify-production.yml', head_sha='tested', **updates)


def test_failed_or_wrong_workflow_cannot_supply_story():
    for key, value in [('conclusion', 'failure'), ('status', 'in_progress'), ('path', 'other.yml')]:
        data=metadata();data[key]=value
        with pytest.raises(ValueError, match='successful full production verification'):
            require_verification(data, 'tested')


def test_changed_pipeline_cannot_reuse_live_verification():
    with pytest.raises(ValueError, match='Pipeline changed'):
        require_verification(metadata(), 'new', {'status':'ahead', 'files':[{'filename':'somoy_jatri/pipeline.py'}]})
    require_verification(metadata(), 'new', {'status':'ahead', 'files':[{'filename':'.github/workflows/generate.yml'}]})


def test_stage_requires_matching_receipt_and_copies_no_old_run_identity(tmp_path):
    source=tmp_path/'source';destination=tmp_path/'new-episode'
    story={'segments':[{'text':'আমি এখানে আছি।'}]};dossier={'facts':[]}
    fingerprint=hashlib.sha256(json.dumps([2,story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    save(source/'story.json',story);save(source/'research.json',dossier)
    save(source/'config.json',{'run_id':'old-episode'})
    save(source/'verification-review.json',{'passed':True,'segments':1,'fingerprint':fingerprint})
    stage(source,destination)
    assert set(p.name for p in destination.iterdir())=={'story.json','research.json','semantic-review.json'}
    assert load(destination/'story.json')==story
    story['segments'][0]['text']='অন্য কথা';save(source/'story.json',story)
    with pytest.raises(ValueError, match='receipt does not match'):
        stage(source,destination)
