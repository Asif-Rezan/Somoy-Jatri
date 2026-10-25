import copy
import json
import re
from pathlib import Path
from unittest.mock import Mock
import numpy as np
import pytest
from jsonschema import validate
from somoy_jatri.preparation import story as s, pipeline as p, story_cpu as cpu
from somoy_jatri.utils import save,load,digest
from somoy_jatri.audio import RATE,write_wav
from somoy_jatri.config import Config


def dossier():
    return {'location':'Giza','period':'Old Kingdom','facts':[{'claim':'Stone pyramids survive.','source_id':'s1'}],
            'uncertain':['Other details are reconstruction.']}


def draft():
    text=' '.join(['আমি প্রাচীন স্থাপত্যের ইতিহাস নিয়ে ভাবছি।']*12)
    return {'format':s.FORMAT,'title':'গিজার ইতিহাস','scenes':[
        {'narration':text+(s.CTA if i==19 else ''),'summary':'প্রাচীন স্থাপত্যের পর্যবেক্ষণ',
         'image_prompt':'Stone pyramid in the desert','fact_ids':[0]} for i in range(20)]}


def test_reference_outline_then_four_batches_and_packaging(monkeypatch):
    calls=[]
    def request(prompt,limit,schema,*args):
        calls.append(schema)
        props=schema['properties']
        if 'scenes' in props:
            return {'title':'গিজার ইতিহাস','scenes':{key:{'summary':'প্রাচীন স্থাপত্যের পর্যবেক্ষণ',
                'image_prompt':'Ancient stone pyramid','fact_ids':[0]} for key in s.KEYS}}
        if 'narrations' in props:
            text=' '.join(['আমি']*74)+' ভাবছি।'
            return {'narrations':{key:text for key in props['narrations']['properties']}}
        return {'title':'গিজার ইতিহাস','thumbnail_text':'ভেতরে কী আছে?','description':'প্রাচীন স্থাপত্যের ইতিহাস।'}
    result=s.generate(dossier(),[],request)
    assert len(calls)==6
    assert [len(c['properties']['narrations']['properties']) for c in calls[1:5]]==[5]*4
    assert len(result['scenes'])==20 and result['scenes'][-1]['narration'].endswith(s.CTA)
    assert all(not chapter['narration'].endswith(s.CTA) for chapter in result['scenes'][:-1])


def test_bengali_word_grammar_and_bounded_repairs():
    schema=s.text_schema(3,5)
    validate('আমি এখানে দাঁড়িয়ে আছি।',schema)
    with pytest.raises(Exception):validate('আমি আছি।',schema)
    calls=[]
    def request(prompt,limit,schema):
        calls.append(prompt)
        return {'narrations':{'chapter_01':'আমি আছি।'}}
    with pytest.raises(RuntimeError,match='three attempts'):
        s.narration_batch('write',['chapter_01'],75,request)
    assert len(calls)==3


def test_reference_cpu_runtime_never_calls_hosted_api(monkeypatch):
    result={'choices':[{'finish_reason':'stop','message':{'content':'{"ready":true}'}}]}
    model=Mock(tokenize=Mock(return_value=[1]),create_chat_completion=Mock(return_value=result))
    monkeypatch.setattr(cpu,'load_model',lambda:model)
    post=Mock(side_effect=AssertionError('external text call'))
    monkeypatch.setattr('requests.post',post)
    payload={'model':cpu.MODEL_ID,'messages':[{'role':'user','content':'private text'}],
        'max_completion_tokens':128,'response_format':{'json_schema':{'schema':s.obj({'ready':{'type':'boolean'}})}}}
    original=copy.deepcopy(payload)
    assert cpu.request_story('chat/completions',payload)==result
    assert payload==original and not post.called
    assert model.create_chat_completion.call_args.kwargs['response_format']['schema']==payload['response_format']['json_schema']['schema']


def test_invalid_local_json_retries_only_three_times(monkeypatch):
    model=Mock(tokenize=Mock(return_value=[1]),create_chat_completion=Mock(return_value={
        'choices':[{'finish_reason':'length','message':{'content':'private incomplete text'}}]}))
    monkeypatch.setattr(cpu,'load_model',lambda:model)
    with pytest.raises(cpu.StoryGenerationError,match='three attempts'):
        cpu.request_story('chat/completions',{'model':cpu.MODEL_ID,'messages':[{'role':'user','content':'private'}],
            'response_format':{'json_schema':{'schema':s.obj({'text':{'type':'string'}})}}})
    assert model.create_chat_completion.call_count==3


def test_cpu_context_overflow_stops_before_inference(monkeypatch):
    model=Mock(tokenize=Mock(return_value=[1]*cpu.CONTEXT_TOKENS))
    monkeypatch.setattr(cpu,'load_model',lambda:model)
    with pytest.raises(cpu.StoryGenerationError,match='context budget'):
        cpu.request_story('chat/completions',{'messages':[{'role':'user','content':'x'}],
            'response_format':{'json_schema':{'schema':s.obj({'text':{'type':'string'}})}}})
    model.create_chat_completion.assert_not_called()


def test_chapter_cache_is_bound_to_text_audio_and_voice(tmp_path,monkeypatch):
    class Voice:
        calls=0
        def synthesize(self,text,emotion,intensity,path):
            self.calls+=1
            write_wav(path,.1*np.sin(np.arange(RATE)*.05))
    voice=Voice()
    p.chapter_audio(tmp_path,0,'আমি এখন এখানে দাঁড়িয়ে আছি।',voice)
    first=voice.calls
    p.chapter_audio(tmp_path,0,'আমি এখন এখানে দাঁড়িয়ে আছি।',voice)
    assert voice.calls==first
    p.chapter_audio(tmp_path,0,'আমি এখন অন্য কথা ভাবছি।',voice)
    assert voice.calls>first
    first=voice.calls
    monkeypatch.setenv('TTS_VOICE','Riya')
    p.chapter_audio(tmp_path,0,'আমি এখন অন্য কথা ভাবছি।',voice)
    assert voice.calls>first


def test_duration_revision_changes_only_selected_chapter_audio(tmp_path,monkeypatch):
    original=draft();calls=[]
    monkeypatch.setattr(p,'chapter_audio',lambda root,i,text,tts: calls.append(i) or (30 if text.startswith('সংশোধিত') else 50))
    monkeypatch.setattr(p.dc,'select_revisions',lambda lengths,direction:([4,5],.7))
    def revise(story,*args):
        result=copy.deepcopy(story)
        result['scenes'][4]['narration']='সংশোধিত অধ্যায়।'
        result['scenes'][5]['narration']='সংশোধিত অধ্যায়।'
        return result
    monkeypatch.setattr(p.scripts,'revise',revise)
    # Accept the first rewrite to isolate which chapters get resynthesized.
    monkeypatch.setattr(p.dc,'valid',lambda seconds:seconds<1000)
    result,lengths=p.correct_duration(tmp_path,original,dossier(),object())
    assert calls[:20]==list(range(20)) and calls[20:]==[4,5]
    assert result['scenes'][3]==original['scenes'][3]


def test_timed_windows_follow_audio_not_proportional_chapter_position():
    lengths=[1.]*19+[11.]
    words=[[{'word':f'শব্দ{i}','start':0.,'end':length}] for i,length in enumerate(lengths)]
    shots=p.shot_plan(draft(),lengths,words)
    assert shots[-1]['chapter_index']==19
    assert shots[0]['chapter_index']<7
    assert [x['start'] for x in shots]==[0,7,14,21,28]
    assert shots[-1]['end']==30
    with pytest.raises(ValueError,match='timing'):
        bad=copy.deepcopy(words);bad[0][0]['end']=2
        p.shot_plan(draft(),lengths,bad)


def test_preparation_storyboard_and_resume_manifest(tmp_path,monkeypatch):
    monkeypatch.setenv('OUTPUT_ROOT',str(tmp_path))
    config=Config(mode='production',run_id='episode-123')
    root=config.root;root.mkdir();story=draft()
    save(root/'story.json',story);save(root/'research.json',dossier())
    def chapter(root,i,text,tts):
        path=root/f'narration-{i:02}.wav'
        samples=.1*np.sin(np.arange(30*RATE)*.05)
        write_wav(path,samples)
        save(path.with_suffix('.meta.json'),{'audio_sha256':digest(path),'fingerprint':p.fingerprint(text)})
        return 30.
    monkeypatch.setattr(p,'chapter_audio',chapter)
    monkeypatch.setattr('somoy_jatri.narration.providers.provider',lambda mode:object())
    class ASR:
        def align(self,*args,**kwargs):return {'words':[
            {'word':'আমি','start':0.,'end':10.}, {'word':'ইতিহাস','start':10.,'end':20.},
            {'word':'দেখছি।','start':20.,'end':30.}]}
    monkeypatch.setattr('somoy_jatri.alignment.timing.BengaliASR',ASR)
    shots=p.prepare_audio(config)
    assert len(shots)==86 and shots[-1]['end']==600
    batches=[]
    def request(prompt,limit,schema,*args):
        batches.append(list(schema['properties']))
        return {key:'Ancient stone pyramid standing in a sunlit desert landscape with weathered limestone blocks' for key in schema['properties']}
    p.storyboard(root,request)
    assert len(batches)==11 and all(len(x)==8 for x in batches[:-1])
    p.refine_plan(root)
    assert load(root/'semantic-review.json')['method']=='reference-schema-and-evidence-validation'
    p.storyboard(root,lambda *a:pytest.fail('Regenerated cached timed prompts'))
    # Same text with changed audio cannot reuse timestamp cache.
    path=root/'narration-00.wav';write_wav(path,.1*np.sin(np.arange(RATE)*.08))
    with pytest.raises(ValueError,match='changed'):
        # The combined narration fingerprint, not a loose presence check, guards final stages.
        (root/'story.json').write_text('{}')
        p.verify_preparation(root)


def test_curated_history_stays_private(tmp_path,monkeypatch):
    from somoy_jatri.youtube.publish import upload
    save(tmp_path/'research.json',{'research_method':'curated source catalog'})
    monkeypatch.setenv('ALLOW_PUBLIC_UPLOAD','true')
    with pytest.raises(ValueError,match='must remain private'):upload(tmp_path,privacy='public')


def test_new_workflow_uses_reference_stages_and_smaller_runtime():
    import yaml
    doc=yaml.safe_load(Path('.github/workflows/generate.yml').read_text())
    assert doc['env']['STORY_MODEL']==cpu.MODEL_ID
    steps=doc['jobs']['prepare']['steps']
    scripts='\n'.join(x.get('run','') for x in steps)
    assert scripts.index('cli stage-story')<scripts.index('cli prepare --run-id')<scripts.index('cli storyboard')<scripts.index('cli refine-plan')
    assert 'setup_qwen.sh' not in '\n'.join(x.get('run','') for x in steps if x.get('name')!='Start legacy Qwen only for old verified artifacts')
    assert doc['jobs']['prepare']['timeout-minutes']==150
