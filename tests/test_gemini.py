import json

import pytest

from somoy_jatri.scripts.gemini import Gemini
from somoy_jatri.scripts.groq import Groq

@pytest.fixture(autouse=True)
def reset_gemini_models(monkeypatch):
    monkeypatch.setattr(Gemini,'unavailable_until',{})


SCHEMA={'type':'object','properties':{'passed':{'type':'boolean'}},
        'required':['passed'],'additionalProperties':False}


class Response:
    def __init__(self,status=200,text='{"passed":true}',finish='STOP',headers=None):
        self.status_code=status;self.ok=status==200;self.headers=headers or {}
        self.text=text;self.finish=finish
    def json(self):
        if not self.ok:return {'error':{'code':'rate_limit_exceeded','message':'secret error body'}}
        return {'candidates':[{'finishReason':self.finish,'content':{'parts':[
            {'text':'private reasoning','thought':True},{'text':self.text}]}}]}


def test_gemini_uses_header_auth_and_preserves_schema(monkeypatch,capsys):
    calls=[]
    monkeypatch.setenv('GEMINI_API_KEY','secret-api-key')
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',
        lambda url,**kw:calls.append((url,kw)) or Response())
    assert Gemini().json('Review',schema=SCHEMA)=={'passed':True}
    url,call=calls[0]
    assert 'secret-api-key' not in url
    assert call['headers']['x-goog-api-key']=='secret-api-key'
    assert call['json']['generationConfig']['responseFormat']['text']['schema']==SCHEMA
    assert 'secret-api-key' not in capsys.readouterr().out


def test_gemini_rejects_invalid_schema_output(monkeypatch):
    calls=[]
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',
        lambda *a,**kw:calls.append(kw) or Response(text='{"passed":"yes"}'))
    with pytest.raises(ValueError,match='invalid structured output'):
        Gemini().json('Review',schema=SCHEMA)
    assert len(calls)==6


@pytest.mark.parametrize('finish',['MAX_TOKENS','SAFETY'])
def test_gemini_never_accepts_partial_or_blocked_output(monkeypatch,finish):
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',lambda *a,**kw:Response(finish=finish))
    with pytest.raises(ValueError,match='blocked or incomplete'):
        Gemini().json('Review',schema=SCHEMA)


def test_gemini_honors_retry_after_without_logging_error_body(monkeypatch,capsys):
    delays=[];responses=iter([Response(429,headers={'Retry-After':'12'}),Response()])
    monkeypatch.setenv('GEMINI_FALLBACK_MODELS','')
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',lambda *a,**kw:next(responses))
    monkeypatch.setattr('somoy_jatri.scripts.gemini.time.sleep',delays.append)
    assert Gemini().json('Review',schema=SCHEMA)['passed']
    assert delays==[12.]
    assert 'secret error body' not in capsys.readouterr().out


def test_all_groq_daily_quotas_fall_back_to_gemini_with_same_validation(monkeypatch):
    calls=[]
    monkeypatch.setenv('GROQ_API_KEY','groq-test')
    monkeypatch.setenv('GEMINI_API_KEY','gemini-test')
    monkeypatch.setattr(Groq,'unavailable_until',{})
    def post(url,**kw):
        calls.append((url,kw))
        return Response(429,headers={'Retry-After':'1200'}) if 'groq.com' in url else Response()
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',post)
    monkeypatch.setattr('somoy_jatri.scripts.groq.time.sleep',lambda _:pytest.fail('Unnecessary Groq quota wait'))
    assert Groq().json('Review',schema=SCHEMA)=={'passed':True}
    assert len(calls)==4
    assert 'generativelanguage.googleapis.com' in calls[-1][0]
    assert calls[-1][1]['json']['generationConfig']['responseFormat']['text']['schema']==SCHEMA


def test_groq_auth_error_is_not_hidden_by_gemini(monkeypatch):
    calls=[]
    monkeypatch.setenv('GROQ_API_KEY','bad')
    monkeypatch.setenv('GEMINI_API_KEY','gemini-test')
    monkeypatch.setattr(Groq,'unavailable_until',{})
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',
        lambda url,**kw:calls.append(url) or Response(401))
    with pytest.raises(RuntimeError,match='HTTP 401'):Groq().json('Review')
    assert len(calls)==1


def test_explicit_gemini_provider_can_be_verified_without_groq(monkeypatch):
    monkeypatch.setenv('STORY_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','gemini-test')
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',lambda url,**kw:
        Response() if 'generativelanguage.googleapis.com' in url else pytest.fail('Unexpected Groq request'))
    assert Groq().json('Review',schema=SCHEMA)=={'passed':True}


def test_gemini_quota_can_use_available_flash_lite_without_waiting(monkeypatch):
    calls=[]
    monkeypatch.setenv('GEMINI_API_KEY','test')
    def post(url,**kw):
        calls.append((url,kw))
        return Response(429) if 'gemini-3.8-flash:' in url else Response()
    monkeypatch.setattr('somoy_jatri.scripts.gemini.requests.post',post)
    monkeypatch.setattr('somoy_jatri.scripts.gemini.time.sleep',lambda _:pytest.fail('Unexpected wait'))
    assert Gemini().json('Review',schema=SCHEMA)=={'passed':True}
    assert len(calls)==2
    assert 'gemini-3.5-flash-lite:' in calls[-1][0]
    assert calls[-1][1]['json']['generationConfig']['responseFormat']['text']['schema']==SCHEMA
