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


def test_citation_repair_preserves_narration_and_is_reviewed_again(monkeypatch):
    responses=iter([
        {'passed':False,'issues':['Wrong fact citation']},
        {'patches':[{'index':0,'fact_ids':[1],'subject':'capital city','visual':'The ancient capital city'}]},
        {'passed':True,'issues':[]}])
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',lambda *a:next(responses))
    story={'segments':[{'text':'আমি এখানে দাঁড়িয়ে আছি।','subject':'ruins','visual':'Ruins',
        'fact_ids':[0],'emotion':'neutral','intensity':.5,'pause_after_ms':300}]}
    original=story['segments'][0]['text']
    result=evaluate_semantics(story,{'facts':[{'claim':'one'},{'claim':'two'}]},repair=True)
    assert result['passed'] is True
    assert story['segments'][0]['text']==original
    assert story['segments'][0]['fact_ids']==[1]
    assert story['segments'][0]['anchors']==['capital city']
