"""Bangla packaging follows the reference's accurate title/question mechanism."""
import re
from somoy_jatri.scripts.groq import Groq


def generate(dossier, story):
    schema = {'type':'object', 'properties': {
        'title': {'type':'string'}, 'thumbnail_text': {'type':'string'},
        'description': {'type':'string'}},
        'required':['title','thumbnail_text','description'], 'additionalProperties':False}
    result = Groq().json(
        'Write accurate YouTube packaging in natural Bangla for this historical documentary. '
        'Return title (maximum 90 characters, subject near start), thumbnail_text '
        '(a complementary 2–5 word Bangla question answered in the episode), and description '
        '(2 Bangla sentences about the subject and evidence). No invented discoveries, '
        'sensational promises or English prose. Artistic reconstructions are not real footage. '
        f'Subject: {dossier["location"]}. Period: {dossier["period"]}. '
        f'Facts: {dossier["facts"]}. Narration sample: '
        + ' '.join(s['text'] for s in story['segments'][::10]), schema=schema)
    for key in schema['required']:
        text=result[key].strip()
        if not re.search(r'[\u0980-\u09ff]', text):
            raise ValueError('Packaging must be in Bangla')
        result[key]=text
    if len(result['title'])>100 or not 2<=len(result['thumbnail_text'].split())<=5:
        raise ValueError('Packaging length out of bounds')
    return result
