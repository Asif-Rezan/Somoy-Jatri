import copy
import pytest
from jsonschema import Draft202012Validator
from somoy_jatri.preparation.story import KEYS, generate, publishing_metadata


VALID = {'title': 'গিজার ইতিহাস', 'thumbnail_text': 'ভেতরে কী আছে?',
         'description': 'প্রাচীন মিশরের ইতিহাস। তথ্যের আলোকে নির্মাণ।'}


@pytest.mark.parametrize('field,value', [
    ('title', 'English title'), ('title', 'ক' * 101),
    ('thumbnail_text', 'ইতিহাস'), ('thumbnail_text', 'এক দুই তিন চার পাঁচ ছয়'),
    ('description', 'English description'), ('description', None),
])
def test_metadata_validation_retries_only_rejected_output(field, value, capsys):
    calls = []
    def request(prompt, limit, schema):
        calls.append(prompt)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(VALID)
        return {**VALID, field: value} if len(calls) == 1 else VALID.copy()
    assert publishing_metadata('Evidence and outline', request) == VALID
    assert len(calls) == 2
    assert 'Evidence and outline' in calls[1]
    assert 'failed these checks' in calls[1]
    assert 'publishing_metadata_retry' in capsys.readouterr().out


def test_invalid_metadata_exhausts_bounded_retries():
    calls = []
    def request(*args):
        calls.append(args)
        return {**VALID, 'thumbnail_text': 'ইতিহাস'}
    with pytest.raises(ValueError, match='after three attempts'):
        publishing_metadata('Evidence', request)
    assert len(calls) == 3


def test_metadata_retry_keeps_all_completed_narration():
    calls = []
    def request(prompt, limit, schema):
        calls.append(schema)
        properties = schema['properties']
        if 'scenes' in properties:
            return {'title': VALID['title'], 'scenes': {
                key: {'summary': 'প্রাচীন গিজা', 'image_prompt': 'Ancient Giza', 'fact_ids': [0]}
                for key in KEYS}}
        if 'narrations' in properties:
            return {'narrations': {key: ' '.join(['ইতিহাস'] * 74) + ' দেখি।'
                for key in properties['narrations']['properties']}}
        package = copy.deepcopy(VALID)
        if len(calls) == 6:
            package['thumbnail_text'] = 'ইতিহাস'
        return package
    dossier = {'location': 'Giza', 'period': 'Old Kingdom', 'uncertain': [],
               'facts': [{'claim': 'Giza is in Egypt.'}]}
    story = generate(dossier, [], request)
    assert len(story['scenes']) == 20
    assert story['packaging'] == VALID
    assert len(calls) == 7
    assert sum('narrations' in schema['properties'] for schema in calls) == 4
