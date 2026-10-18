import numpy as np
from somoy_jatri.audio import write_wav
from somoy_jatri.alignment.timing import GroqASR


def test_groq_alignment_uses_bengali_word_timestamps(monkeypatch, tmp_path):
    path = tmp_path / 'sample.wav'
    write_wav(path, np.zeros(24000))
    captured = {}

    class Response:
        status_code = 200
        ok = True

        def json(self):
            return {'text': 'আমি এখানে আছি', 'words': [
                {'word': 'আমি', 'start': 0.1, 'end': 0.3},
                {'word': 'এখানে', 'start': 0.3, 'end': 0.6},
                {'word': 'আছি', 'start': 0.6, 'end': 0.9}]}

    def post(url, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr('somoy_jatri.alignment.timing.requests.post', post)
    result = GroqASR().align(path, 'আমি এখানে আছি')
    assert result['similarity'] == 1
    assert len(result['words']) == 3
    assert captured['data']['language'] == 'bn'
    assert captured['data']['timestamp_granularities[]'] == 'word'
