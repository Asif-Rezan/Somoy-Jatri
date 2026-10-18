import math

NEGATIVE = 'anime, cartoon, illustration, CGI, smartphones, cars, electric lights, modern buildings, text, watermark, visible narrator'
MOTIONS = {'stable', 'slow_forward', 'slow_backward', 'pan_left', 'pan_right', 'tilt_up', 'handheld', 'zoom'}

def build(story, bounds, dossier):
    if len(story['segments']) != len(bounds): raise ValueError('Missing narration boundary')
    shots, memories = [], {}
    for i, (segment, b) in enumerate(zip(story['segments'], bounds)):
        scene = segment['scene']
        memories.setdefault(scene, {'layout': dossier['buildings'], 'clothing': dossier['clothing'],
            'weather': 'clear', 'time_of_day': 'daylight', 'camera_direction': 'forward'})
        memory = memories[scene]
        subject = segment['subject']
        prompt = (f'{subject}. {segment["visual"]}. First-person POV, photorealistic documentary travel footage. '
                  f'{dossier["location"]}, {dossier["period"]}. '
                  f'Consistent layout: {memory["layout"]}. Clothing: {memory["clothing"]}. '
                  'Natural daylight, eye-level framing, period tools, geographically consistent architecture. '
                  'Narrator behind camera. No modern objects, no fantasy.')
        shots.append(dict(segment, id=f'shot_{i:04}', start=b['start'], end=b['end'],
                          speech_end=b['speech_end'], narration=segment['text'], prompt=prompt,
                          negative_prompt=NEGATIVE, continuity=memory.copy()))
    validate(shots, bounds[-1]['end'])
    return shots

def validate(shots, total):
    if not shots or not math.isfinite(total) or total <= 0: raise ValueError('Empty timeline')
    cursor = 0.
    ids = set()
    for s in shots:
        if s['id'] in ids: raise ValueError('Duplicate shot')
        ids.add(s['id'])
        if not all(math.isfinite(s[k]) for k in ('start', 'end')): raise ValueError('Nonfinite timing')
        if abs(s['start']-cursor) > .002 or s['end'] <= s['start']:
            raise ValueError('Gap, overlap or nonpositive shot')
        if s.get('motion') not in MOTIONS: raise ValueError('Unsupported camera motion')
        anchors = s.get('anchors', [])
        if not anchors or not all(a.casefold() in s['prompt'].casefold() for a in anchors):
            raise ValueError('Prompt missing visual anchors')
        if not s['narration'].strip(): raise ValueError('Missing narration')
        cursor = s['end']
    if abs(cursor-total) > .002: raise ValueError('Timeline duration mismatch')


def evaluate_semantics(story, dossier, report_path=None):
    # Deterministic anchors alone cannot verify cross-language meaning.
    from somoy_jatri.scripts.groq import Groq
    import json
    import os
    import time
    segments = story['segments']
    for offset in range(0, len(segments), 10):
        batch = segments[offset:offset + 10]
        result = Groq().json('Review each Bangla utterance against its English visual/subject and fact_ids. '
            'Reject invented facts, anachronisms, mismatched subjects, and multiple visual events in one segment. '
            'Return {"passed": bool, "issues": [strings]}. Dossier: '+json.dumps(dossier, ensure_ascii=False)
            +' Segments: '+json.dumps(batch, ensure_ascii=False))
        if result.get('passed') is not True:
            print(json.dumps({'semantic_stage':'rejected','batch':offset//10+1,
                              'issues':result.get('issues',[])[:5]}),flush=True)
            if report_path is not None:
                from somoy_jatri.utils import save
                save(report_path, {'passed':False,'batch':offset//10+1,'issues':result.get('issues',[])})
            raise ValueError(f'Storyboard semantic review failed in batch {offset // 10 + 1}')
        if offset + 10 < len(segments):
            time.sleep(float(os.getenv('STORY_PACE_SECONDS', '10')))
    return {'passed': True, 'method': 'batched model review', 'segments': len(segments)}


def shard(shots, index, count):
    if not 1 <= count <= 16 or not 0 <= index < count: raise ValueError('Invalid shard')
    return [s for i,s in enumerate(shots) if i % count == index]


def reviewed_story(story, dossier, path):
    """Cache review only for the exact normalized story and source packet."""
    import hashlib, json
    from somoy_jatri.utils import load, save
    fingerprint=hashlib.sha256(json.dumps([story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if path.exists():
        review=load(path)
        if review.get('passed') is True and review.get('fingerprint')==fingerprint:
            return review
    review=evaluate_semantics(story,dossier,report_path=path)
    review['fingerprint']=fingerprint
    save(path,review)
    return review
