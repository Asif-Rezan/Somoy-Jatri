from somoy_jatri.storyboard.timeline import evaluate_semantics


def test_semantic_review_uses_small_batches(monkeypatch):
    seen = []
    monkeypatch.setenv('STORY_PACE_SECONDS', '0')
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',
                        lambda self, prompt: seen.append(prompt) or {'passed': True, 'issues': []})
    story = {'segments': [{'text': 'বাংলা', 'subject': 'wall', 'visual': 'A wall', 'fact_ids': []}
                          for _ in range(21)]}
    result = evaluate_semantics(story, {'facts': []})
    assert result['passed'] is True
    assert result['segments'] == 21
    assert len(seen) == 3
