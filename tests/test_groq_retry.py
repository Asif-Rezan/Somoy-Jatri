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
