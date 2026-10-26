from somoy_jatri.scripts.groq import generate


def test_long_story_is_batched_and_normalizes_directions(monkeypatch):
    monkeypatch.setenv('STORY_PACE_SECONDS', '0')
    calls = []
    def fake_json(self, prompt):
        calls.append(prompt)
        return {'segments': [{'text': 'আমি এখানে একটি পুরোনো দেয়াল দেখছি।',
            'subject': 'old wall', 'visual': 'An old wall in the documented site',
            'emotion': 'surprised', 'intensity': 2, 'pause_after_ms': 3000,
            'motion': 'fly', 'fact_ids': [0]} for _ in range(14)]}
    monkeypatch.setattr('somoy_jatri.scripts.groq.Groq.json', fake_json)
    dossier = {'location': 'Giza', 'facts': [{'claim': 'A fact', 'source_id': 's1'}]}
    monkeypatch.setattr('somoy_jatri.packaging.generate', lambda *args: {'title':'গিজার ইতিহাস', 'thumbnail_text':'ভেতরে কী আছে?', 'description':'গিজার ইতিহাস।'})
    story = generate(dossier, 720, [])
    assert len(calls) == 20
    assert len(story['segments']) == 140
    assert story['segments'][0]['emotion'] == 'neutral'
    assert story['segments'][0]['intensity'] == .5
    assert all(s['emotion']=='neutral' and s['mood']=='neutral' for s in story['segments'])
    assert story['segments'][0]['pause_after_ms'] == 1500
    assert story['segments'][0]['motion'] == 'stable'
