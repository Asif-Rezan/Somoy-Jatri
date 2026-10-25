import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from somoy_jatri.scripts.groq import Groq
from somoy_jatri.scripts import qwen_text
from somoy_jatri.config import Config


def test_default_text_uses_reference_model_without_cloud_key(monkeypatch):
    monkeypatch.delenv('TEXT_BACKEND', raising=False)
    monkeypatch.delenv('STORY_PROVIDER', raising=False)
    monkeypatch.setenv('GROQ_API_KEY', 'must-not-be-used')
    post = Mock(return_value=Mock(ok=True, json=lambda: {'choices': [
        {'finish_reason': 'stop', 'message': {'content': '{"title":"বাংলা"}'}}]}))
    monkeypatch.setattr(qwen_text.requests, 'post', post)
    assert Groq().json('বাংলায় লিখুন') == {'title': 'বাংলা'}
    args, kwargs = post.call_args
    assert args[0] == 'http://127.0.0.1:8080/v1/chat/completions'
    assert kwargs['json']['model'] == 'Qwen/Qwen3.5-9B'
    assert 'headers' not in kwargs


@pytest.mark.parametrize('url', ['https://example.com/v1', 'http://192.168.1.1/v1',
                                  'http://user:pass@localhost/v1'])
def test_qwen_rejects_external_server(monkeypatch, url):
    monkeypatch.setenv('QWEN_BASE_URL', url)
    with pytest.raises(RuntimeError, match='loopback'):
        qwen_text.request({})


def test_incomplete_qwen_never_falls_back(monkeypatch):
    monkeypatch.setattr(qwen_text.requests, 'post', Mock(return_value=Mock(ok=True,
        json=lambda: {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]})))
    with pytest.raises(RuntimeError, match='no external fallback'):
        Groq().json('test')


def test_production_config_needs_no_groq_key(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.setenv('RESEARCH_DOSSIER', 'auto')
    Config(mode='production', workers=20).preflight()


def test_twenty_shards_cover_every_image_once():
    from somoy_jatri.storyboard.timeline import shard
    shots = [{'id': str(i)} for i in range(103)]
    assigned = [s['id'] for index in range(20) for s in shard(shots,index,20)]
    assert len(assigned) == len(set(assigned)) == 103


def test_generation_starts_local_model_before_prepare():
    text = Path('.github/workflows/generate.yml').read_text()
    assert text.index('bash scripts/setup_qwen.sh') < text.index('cli prepare')
    assert 'max-parallel: 20' in text
    assert 'TEXT_BACKEND: qwen-local' in text
