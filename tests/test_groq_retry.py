import os
import pytest

@pytest.fixture(autouse=True)
def legacy_text_backend(monkeypatch):
    monkeypatch.setenv('TEXT_BACKEND', 'groq')

from somoy_jatri.scripts.groq import Groq


def test_rate_limit_waits_for_server_reset(monkeypatch):
    delays = []
    calls = []

    class Response:
        def __init__(self, status, headers, payload):
            self.status_code = status
            self.headers = headers
            self.payload = payload
            self.ok = status == 200

        def json(self):
            return self.payload

    responses = [
        Response(429, {'Retry-After': '61'}, {'error': {'message': 'Rate limited'}}),
        Response(200, {}, {'choices': [{'message': {'content': '{"ok": true}'}}]}),
    ]
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',
                        lambda *args, **kwargs: calls.append(kwargs) or responses.pop(0))
    monkeypatch.setattr('somoy_jatri.scripts.groq.time.sleep', delays.append)

    assert Groq().json('test') == {'ok': True}
    assert len(calls) == 2
    assert delays == [61.0]


def test_long_rate_limit_reset_is_not_shortened_to_three_minutes():
    from somoy_jatri.scripts.groq import _retry_delay
    class Response:
        status_code = 429
        headers = {'Retry-After': '940'}
    assert _retry_delay(Response(), 0) == 940


def test_reset_message_with_hours_is_understood():
    from somoy_jatri.scripts.groq import _retry_delay
    class Response:
        status_code = 429
        headers = {}
        def json(self):
            return {'error': {'message': 'Please try again in 0h15m20.5s.'}}
    assert _retry_delay(Response(), 0) == 922.5


def test_long_quota_wait_uses_available_model_without_bypassing_validation(monkeypatch):
    calls = []
    class Response:
        def __init__(self, status):
            self.status_code = status
            self.ok = status == 200
            self.headers = {'Retry-After': '900'}
        def json(self):
            return ({'error': {'code': 'rate_limit_exceeded'}} if not self.ok else
                    {'choices': [{'message': {'content': '{"ok": true}'}}]})
    responses = [Response(429), Response(200)]
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr(Groq, 'unavailable_until', {})
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',
        lambda *a, **kw: calls.append(kw['json']) or responses.pop(0))
    monkeypatch.setattr('somoy_jatri.scripts.groq.time.sleep',
        lambda delay: (_ for _ in ()).throw(AssertionError('Unexpected wait')))
    assert Groq().json('test') == {'ok': True}
    assert [c['model'] for c in calls] == ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']
    assert calls[1]['reasoning_effort'] == 'low'
    assert calls[1]['max_completion_tokens'] == 4096


def test_every_json_request_explicitly_instructs_json(monkeypatch):
    calls=[]
    class Response:
        status_code=200
        ok=True
        def json(self):return {'choices':[{'message':{'content':'{"passed":true}'}}]}
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',
        lambda *a,**kw:calls.append(kw['json']) or Response())
    assert Groq().json('Review this scene')['passed']
    assert 'JSON' in calls[0]['messages'][0]['content']


def test_repeated_invalid_json_switches_model_and_preserves_schema(monkeypatch):
    calls=[]
    class Response:
        headers={}
        def __init__(self,status):self.status_code=status;self.ok=status==200
        def json(self):
            return ({'error':{'code':'json_validate_failed'}} if not self.ok else
                    {'choices':[{'message':{'content':'{"ok":true}'}}]})
    responses=iter([Response(400),Response(429),Response(400),Response(200)])
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    monkeypatch.setattr(Groq,'unavailable_until',{})
    monkeypatch.setattr('somoy_jatri.scripts.groq.requests.post',
        lambda *a,**kw:calls.append(kw['json']) or next(responses))
    monkeypatch.setattr('somoy_jatri.scripts.groq.time.sleep',lambda _:None)
    schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
    assert Groq().json('test',schema=schema)=={'ok':True}
    assert [c['model'] for c in calls]==['openai/gpt-oss-120b']*3+['openai/gpt-oss-20b']
    assert all(c['response_format']['json_schema']['schema']==schema for c in calls)
