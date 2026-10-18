import json
import os
import time
import requests

class Groq:
    def json(self, prompt):
        key = os.environ['GROQ_API_KEY']
        for attempt in range(4):
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': 'Bearer '+key}, timeout=180,
                json={'model': os.getenv('STORY_MODEL', 'openai/gpt-oss-120b'),
                      'messages': [{'role': 'user', 'content': prompt}],
                      'response_format': {'type': 'json_object'}, 'temperature': .75})
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(min(2**attempt, 8)); continue
            if not response.ok:
                raise RuntimeError('Groq request failed, HTTP '+str(response.status_code))
            return json.loads(response.json()['choices'][0]['message']['content'])
        raise RuntimeError('Groq retries exhausted')


def generate(dossier, target, previous, feedback=''):
    schema = {'title': 'Bangla title', 'tags': ['Bangla history', 'Time travel vlog'],
        'segments': [{'text': 'Short natural Bangla utterance, one visual event',
            'emotion': 'curious', 'intensity': .5, 'pause_after_ms': 300,
            'chapter': 'arrival', 'scene': 'market', 'subject': 'pottery merchant',
            'visual': 'English description of this exact narrated action',
            'anchors': ['pottery', 'merchant'], 'motion': 'stable',
            'mood': 'curious', 'ambient': 'market', 'fact_ids': []}]}
    return Groq().json('Generate an ORIGINAL first-person Bangladeshi female time-travel vlog, directly '
        'in conversational Bangla, no textbook phrasing. Fictional time travel only, no horror. '
        'Hook, arrival, exploration, daily activities, monument, reflection, return, like/comment/subscribe. '
        'One utterance per distinct visual event, <=260 characters each. Expand or split complex sentences. '
        'Each visual and English subject MUST express exactly its Bangla utterance. '
        'Only dossier facts may be asserted; every factual segment must cite fact_ids (zero-based fact indexes). '
        'Uncertain details must be identified as reconstructions in narration. '
        f'Target spoken duration {target} seconds, roughly {target*2} Bangla words. '
        f'Previous titles to avoid: {previous}. Revision feedback: {feedback}. '
        f'Dossier: {json.dumps(dossier, ensure_ascii=False)}. '
        'Return ONLY JSON in schema '+json.dumps(schema, ensure_ascii=False))
