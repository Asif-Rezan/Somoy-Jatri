import json
import os
import time
import re
import requests


def _retry_delay(response, attempt):
    """Honor Groq's rate-limit delay without printing its response body."""
    if response.status_code == 429:
        header = response.headers.get('Retry-After', '')
        try:
            return max(1., min(3600., float(header)))
        except ValueError:
            pass
        try:
            message = response.json().get('error', {}).get('message', '')
        except (ValueError, AttributeError):
            message = ''
        match = re.search(r'try again in\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s', message, re.I)
        if match:
            return max(1., min(3600., 3600 * int(match.group(1) or 0) + 60 * int(match.group(2) or 0) + float(match.group(3)) + 2))
        return 65.
    return min(2 ** attempt, 30)

class Groq:
    def json(self, prompt):
        key = os.environ['GROQ_API_KEY']
        for attempt in range(8):
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': 'Bearer '+key}, timeout=180,
                json={'model': os.getenv('STORY_MODEL', 'openai/gpt-oss-120b'),
                      'messages': [{'role': 'user', 'content': prompt}],
                      'response_format': {'type': 'json_object'}, 'temperature': .75})
            try:
                error_code = str(response.json().get('error', {}).get('code') or '') if not response.ok else ''
            except (ValueError, AttributeError):
                error_code = ''
            retryable_json = response.status_code == 400 and error_code in {
                'json_validate_failed', 'json_parse_failed', 'json_error'}
            if (response.status_code in (429, 500, 502, 503, 504) or retryable_json) and attempt < 7:
                delay = _retry_delay(response, attempt)
                print(json.dumps({'groq_stage': 'retry', 'status': response.status_code,
                                  'error_code': error_code[:80], 'attempt': attempt + 1,
                                  'wait_seconds': round(delay, 1)}), flush=True)
                time.sleep(delay)
                continue
            if not response.ok:
                print(json.dumps({'groq_stage': 'failed', 'status': response.status_code,
                                  'error_code': error_code[:80]}), flush=True)
                raise RuntimeError('Groq request failed, HTTP '+str(response.status_code))
            payload = response.json()
            usage = payload.get('usage', {})
            print(json.dumps({'groq_stage': 'completed', **{
                k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                if isinstance(usage.get(k), int)}}), flush=True)
            return json.loads(payload['choices'][0]['message']['content'])
        raise RuntimeError('Groq retries exhausted')


def generate(dossier, target, previous, feedback=''):
    import re
    from somoy_jatri.narration.text import EMOTIONS, emotion
    from somoy_jatri.storyboard.timeline import MOTIONS

    ratio = re.search(r'Adjust total words by ratio ([0-9.]+)', feedback)
    scale = max(.6, min(1.6, float(ratio.group(1)))) if ratio else 1.0
    per_chapter = max(9, min(22, round(14 * scale)))
    chapters = [
        ('hook', 'A concrete mystery or observation grounded in the dossier'),
        ('arrival', 'Arrival in the documented place and period'),
        ('landscape', 'Geography, routes and visible setting supported by evidence'),
        ('architecture', 'Documented buildings and their spatial details'),
        ('people', 'Daily activities supported by evidence; mark unknown details as reconstruction'),
        ('tools', 'Objects, tools and work supported by evidence'),
        ('movement', 'Transport and movement through the setting'),
        ('exchange', 'Food, trade or social life where sources support them'),
        ('reflection', 'What the surviving evidence establishes and leaves uncertain'),
        ('return', 'Return to the present and a brief like/comment/subscribe invitation'),
    ]
    template = {'segments': [{'text': 'One short natural Bangla utterance',
        'subject': 'One English visual subject', 'visual': 'Matching English visual',
        'fact_ids': [0]}]}
    segments = []
    model = Groq()
    prior = ''
    for index, (chapter, purpose) in enumerate(chapters):
        chapter_segments = []
        for batch in range(6):
            needed = per_chapter - len(chapter_segments)
            if needed <= 0:
                break
            ask = min(7, needed)
            prompt = ('Write a short part of an ORIGINAL first-person Bangladeshi female time-travel vlog '
                'in natural conversational Bangla. Fictional time travel only, no horror. '
                f'Chapter {index+1}/10: {chapter}. Purpose: {purpose}. '
                f'Return exactly {ask} distinct visual utterances, each 10–20 Bangla words '
                'and at most 220 characters. One visual event per utterance. '
                'Every factual statement must cite zero-based fact_ids from the dossier; '
                'never invent history, dialogue, dates, motives or unsupported activities. '
                'Clearly call uncertain visual details reconstruction. English visual and subject must '
                'match the Bangla utterance. '
                f'Previous ending for continuity: {prior}. Previous titles: {previous}. '
                f'Revision feedback: {feedback}. Dossier: {json.dumps(dossier, ensure_ascii=False)}. '
                'Return ONLY a JSON object matching this shape: '+json.dumps(template, ensure_ascii=False))
            result = model.json(prompt)
            part = result.get('segments')
            if not isinstance(part, list) or not part:
                raise ValueError(f'Chapter {chapter} returned no visual utterances')
            part = part[:ask]
            print(json.dumps({'story_stage': 'part_received', 'chapter': chapter,
                              'batch': batch + 1, 'segments': len(part)}), flush=True)
            chapter_segments.extend(part)
            prior = str(part[-1].get('text', ''))[-160:]
            if len(chapter_segments) < per_chapter:
                time.sleep(float(os.getenv('STORY_PACE_SECONDS', '10')))
        if len(chapter_segments) < per_chapter:
            raise ValueError(f'Chapter {chapter} remained incomplete after six parts')
        for raw in chapter_segments:
            if not isinstance(raw, dict) or not isinstance(raw.get('text'), str):
                raise ValueError(f'Chapter {chapter} returned an invalid utterance')
            subject = str(raw.get('subject') or raw.get('visual') or '').strip()
            visual = str(raw.get('visual') or subject).strip()
            if not subject or not visual:
                raise ValueError(f'Chapter {chapter} lacks a visual subject')
            raw_emotion = str(raw.get('emotion', '')).lower()
            try: intensity = float(raw.get('intensity', .5))
            except (TypeError, ValueError): intensity = .5
            try: pause = int(raw.get('pause_after_ms', 300))
            except (TypeError, ValueError): pause = 300
            ids = raw.get('fact_ids', [])
            if not isinstance(ids, list) or any(not isinstance(i, int) or i < 0 or i >= len(dossier['facts']) for i in ids):
                raise ValueError(f'Chapter {chapter} has an invalid fact citation')
            segments.append({'text': raw['text'].strip(), 'subject': subject, 'visual': visual,
                'fact_ids': ids, 'emotion': raw_emotion if raw_emotion in EMOTIONS else emotion(raw['text']),
                'intensity': max(0., min(1., intensity)), 'pause_after_ms': max(0, min(1500, pause)),
                'chapter': chapter, 'scene': chapter, 'anchors': [subject],
                'motion': raw.get('motion') if raw.get('motion') in MOTIONS else 'stable',
                'mood': raw_emotion if raw_emotion in EMOTIONS else 'neutral',
                'ambient': raw.get('ambient') or 'wind'})
        print(json.dumps({'story_stage': 'chapter_complete', 'chapter': chapter,
                          'segments': len(chapter_segments)}), flush=True)
        if index < len(chapters) - 1:
            time.sleep(float(os.getenv('STORY_PACE_SECONDS', '10')))
    if len(segments) < 80:
        raise ValueError('Long-form story has too few visual utterances')
    return {'title': f'{dossier["location"]} ভ্রমণ | সময় যাত্রী',
            'tags': ['Bangla history', 'Somoy Jatri', 'Time travel vlog'],
            'segments': segments}
