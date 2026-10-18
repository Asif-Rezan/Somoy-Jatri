import json

import pytest

from somoy_jatri.research.automatic import choose, build


def test_auto_topic_uses_each_curated_topic_once(tmp_path):
    catalog = tmp_path / 'topics.json'
    catalog.write_text(json.dumps([{'id': 'a'}, {'id': 'b'}]))
    assert choose([], catalog)['id'] == 'a'
    assert choose([{'topic_id': 'a'}], catalog)['id'] == 'b'
    with pytest.raises(ValueError, match='exhausted'):
        choose([{'topic_id': 'a'}, {'topic_id': 'b'}], catalog)


def test_auto_research_rejects_unknown_citation(monkeypatch):
    monkeypatch.setattr('somoy_jatri.research.automatic.choose', lambda history: {
        'id': 'a', 'location': 'Site', 'period': 'Period', 'sources': ['https://example.org/a']})
    class Response:
        text = '<p>' + ('Documented evidence. ' * 50) + '</p>'
        def raise_for_status(self): pass
    monkeypatch.setattr('somoy_jatri.research.automatic.requests.get', lambda *a, **k: Response())
    monkeypatch.setattr('somoy_jatri.research.automatic.Groq.json', lambda *a: {
        'facts': [{'claim': 'Claim', 'source_id': 'unknown'}] * 3})
    with pytest.raises(ValueError, match='unknown source'):
        build([])
