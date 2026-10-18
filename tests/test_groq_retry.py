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
