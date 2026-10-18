import pytest
from somoy_jatri.narration.providers import synthesize_verified

SEGMENT = {'text': 'আমি এখানে আছি', 'emotion': 'curious', 'intensity': .5}

class Voice:
    def __init__(self): self.calls = 0
    def synthesize(self, *args): self.calls += 1

class Recognition:
    def __init__(self, scores): self.scores = iter(scores)
    def align(self, *args, **kwargs):
        assert kwargs == {'strict': False}
        return {'similarity': next(self.scores), 'words': [{'word': 'আমি'}]}


def test_bad_take_is_regenerated(tmp_path):
    voice = Voice()
    result = synthesize_verified(voice, Recognition([.25, .88]), SEGMENT, tmp_path/'voice.wav')
    assert voice.calls == 2
    assert result['similarity'] == .88


def test_repeated_bad_takes_fail_without_lowering_threshold(tmp_path):
    voice = Voice()
    with pytest.raises(ValueError, match='three voice takes'):
        synthesize_verified(voice, Recognition([.25, .3, .64]), SEGMENT, tmp_path/'voice.wav')
    assert voice.calls == 3


def test_cached_good_take_is_verified_without_resynthesis(tmp_path):
    voice = Voice()
    synthesize_verified(voice, Recognition([.88]), SEGMENT, tmp_path/'voice.wav', reuse=True)
    assert voice.calls == 0
