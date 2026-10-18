from somoy_jatri.storyboard.timeline import evaluate_semantics


def test_semantic_review_uses_small_batches(monkeypatch):
    seen = []
    monkeypatch.setenv('STORY_PACE_SECONDS', '0')
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',
                        lambda self, prompt, **kwargs: seen.append(prompt) or {'passed': True, 'issues': []})
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
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',lambda *a,**kwargs:next(responses))
    story={'segments':[{'text':'আমি এখানে দাঁড়িয়ে আছি।','subject':'ruins','visual':'Ruins',
        'fact_ids':[0],'emotion':'neutral','intensity':.5,'pause_after_ms':300}]}
    original=story['segments'][0]['text']
    result=evaluate_semantics(story,{'facts':[{'claim':'one'},{'claim':'two'}]},repair=True)
    assert result['passed'] is True
    assert story['segments'][0]['text']==original
    assert story['segments'][0]['fact_ids']==[1]
    assert story['segments'][0]['anchors']==['capital city']


def test_all_citation_only_corrections_are_applied_without_rewriting_audio():
    from somoy_jatri.storyboard.timeline import repair_batch
    class NoModel:
        def json(self,*args,**kwargs):raise AssertionError('Unnecessary rewriting request')
    batch=[{'text':'আমি এখানে আছি।','fact_ids':[0]},{'text':'সামনে একটি পিরামিড।','fact_ids':[0]}]
    original=[s['text'] for s in batch]
    issues=[{'index':0,'kind':'citation','correct_fact_ids':[1]},
            {'index':1,'kind':'citation','correct_fact_ids':[2]}]
    assert repair_batch(NoModel(),batch,{'facts':[{}, {}, {}]},issues)==2
    assert [s['text'] for s in batch]==original
    assert [s['fact_ids'] for s in batch]==[[1],[2]]


def test_empty_citation_fix_requires_content_repair():
    from somoy_jatri.storyboard.timeline import repair_batch
    class Model:
        called=False
        def json(self,prompt,**kwargs):
            self.called=True
            assert '"patches"' not in prompt
            assert 'segment_0' in prompt
            assert '"additionalProperties": false' in prompt
            return {'segment_0':{'text':'আমি এখানে দাঁড়িয়ে আছি।','subject':'ancient site',
                'visual':'An artistic reconstruction of the ancient site','fact_ids':[]}}
    model=Model()
    batch=[{'text':'আমি এখানে দাঁড়িয়ে আছি।','subject':'workers','visual':'Workers',
        'fact_ids':[0],'emotion':'neutral','intensity':.5,'pause_after_ms':300}]
    repair_batch(model,batch,{'facts':[{}]},
        [{'index':0,'kind':'citation','correct_fact_ids':[],'problem':'Unsupported construction claim'}])
    assert model.called
    assert batch[0]['subject']=='ancient site'
