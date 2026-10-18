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
    issues=[{'index':0,'kind':'citation','correct_fact_ids':[1],'requires_rewrite':False},
            {'index':1,'kind':'citation','correct_fact_ids':[2],'requires_rewrite':False}]
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


def test_wrong_direction_is_rewritten_even_with_correct_citation():
    from somoy_jatri.storyboard.timeline import repair_batch
    class Model:
        def json(self,prompt,**kwargs):
            assert 'REMOVE that claim from BOTH' in prompt
            return {'segment_0':{'text':'গিজার পিরামিডের পূর্বদিকে স্ফিংক্স রয়েছে।',
                'subject':'Great Sphinx','visual':'Sphinx east of the Giza pyramids','fact_ids':[0]}}
    batch=[{'text':'উত্তরদিকে স্ফিংক্স দেখা যাচ্ছে।','subject':'Sphinx north of pyramids',
        'visual':'Sphinx north of pyramids','fact_ids':[0],'emotion':'neutral','intensity':.5}]
    repair_batch(Model(),batch,{'facts':[{'claim':'Sphinx is east of the pyramids'}]},
        [{'index':0,'kind':'citation','problem':'Wrong compass direction','correct_fact_ids':[0],
          'requires_rewrite':True}])
    assert 'পূর্বদিকে' in batch[0]['text']
    assert batch[0]['visual']=='Sphinx east of the Giza pyramids'


def test_legacy_citation_verdict_does_not_preserve_unsupported_narration():
    from somoy_jatri.storyboard.timeline import repair_batch
    class Model:
        def json(self,*a,**kw):
            return {'segment_0':{'text':'মেমফিস প্রাচীন মিশরের রাজধানী ছিল।',
                'subject':'Memphis','visual':'Reconstruction of Memphis','fact_ids':[0]}}
    batch=[{'text':'গিজার উত্তরে প্রশাসনিক ভবন রয়েছে।','subject':'buildings','visual':'Buildings',
        'fact_ids':[0],'emotion':'neutral','intensity':.5}]
    repair_batch(Model(),batch,{'facts':[{'claim':'Memphis was a capital'}]},
        [{'index':0,'kind':'citation','correct_fact_ids':[0],'problem':'Unsupported buildings'}])
    assert batch[0]['text']=='মেমফিস প্রাচীন মিশরের রাজধানী ছিল।'


def test_passed_with_outstanding_issues_is_never_accepted(monkeypatch):
    import pytest
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',lambda *a,**k:
        {'passed':True,'issues':[{'index':0,'kind':'narration','problem':'Invented statue'}]})
    with pytest.raises(ValueError,match='semantic review failed'):
        evaluate_semantics({'segments':[{'text':'বাংলা'}]}, {'facts':[]})


def test_repeated_repairs_escalate_then_fail_closed(monkeypatch):
    import pytest
    prompts=[]
    def model(self,prompt,**kwargs):
        prompts.append(prompt)
        if prompt.startswith('Review'):
            return {'passed':False,'issues':[{'index':0,'kind':'narration',
                'problem':'Unsupported statue beside houses','requires_rewrite':True,'correct_fact_ids':[]}]}
        return {'segment_0':{'text':'আমি সামনে একটি মূর্তি দেখছি।',
            'subject':'statue','visual':'Statue beside houses','fact_ids':[]}}
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',model)
    story={'segments':[{'text':'আমি সামনে একটি মূর্তি দেখছি।','subject':'statue',
        'visual':'Statue beside houses','fact_ids':[],'emotion':'neutral','intensity':.5}]}
    with pytest.raises(ValueError,match='semantic review failed'):
        evaluate_semantics(story,{'facts':[]},repair=True)
    assert any('Replace the entire flagged segment' in p for p in prompts)
    assert len(prompts)==17


def test_review_uses_explicit_fact_and_segment_ids(monkeypatch):
    prompts=[]
    monkeypatch.setenv('STORY_PACE_SECONDS','0')
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json',lambda self,prompt,**kw:
        prompts.append(prompt) or {'passed':True,'issues':[]})
    facts=[{'claim':f'Fact {i}'} for i in range(6)]
    facts[5]={'claim':'Sphinx east of Giza pyramids'}
    evaluate_semantics({'segments':[{'text':'স্ফিংক্স','fact_ids':[5]}]}, {'facts':facts})
    assert '"fact_5": {"claim": "Sphinx east of Giza pyramids"}' in prompts[0]
    assert '"segment_0":' in prompts[0]
    assert 'Do not count entries' in prompts[0]


def test_repair_uses_same_explicit_ids_as_review():
    from somoy_jatri.storyboard.timeline import repair_batch
    class Model:
        def json(self,prompt,**kw):
            assert '"fact_0": {"claim": "Memphis was a capital"}' in prompt
            assert '"segment_0":' in prompt
            return {'segment_0':{'text':'মেমফিস প্রাচীন মিশরের রাজধানী ছিল।',
                'subject':'Memphis','visual':'Reconstruction of Memphis','fact_ids':[0]}}
    batch=[{'text':'আমি এখানে আছি।','subject':'Memphis','visual':'Memphis',
        'fact_ids':[0],'emotion':'neutral','intensity':.5}]
    repair_batch(Model(),batch,{'facts':[{'claim':'Memphis was a capital'}]},
        [{'index':0,'kind':'narration','requires_rewrite':True,'correct_fact_ids':[]}])


def test_repeated_failure_rebuilds_from_one_fact_without_rejected_wording():
    from somoy_jatri.storyboard.timeline import repair_batch
    class Model:
        def json(self,prompt,**kw):
            assert 'statue beside stone houses' not in prompt
            assert 'ONLY its ONE assigned fact' in prompt
            assert '"fact_id": 0' in prompt
            return {'segment_0':{'text':'মেমফিস প্রাচীন মিশরের রাজধানী ছিল।',
                'subject':'Memphis','visual':'Reconstruction of Memphis','fact_ids':[0]}}
    batch=[{'text':'মূর্তির পাশে পাথরের ঘর রয়েছে।','subject':'statue beside stone houses',
        'visual':'statue beside stone houses','fact_ids':[0],'emotion':'neutral','intensity':.5}]
    repair_batch(Model(),batch,{'facts':[{'claim':'Memphis was a capital'}]},
        [{'index':0,'kind':'narration','requires_rewrite':True,'correct_fact_ids':[],
          'problem':'Unsupported statue beside stone houses'}],attempt=1)
    assert batch[0]['text']=='মেমফিস প্রাচীন মিশরের রাজধানী ছিল।'
