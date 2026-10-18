import math
from somoy_jatri.research.evidence import indexed_dossier, indexed_segments

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


def repair_batch(model, batch, dossier, issues, attempt=0):
    import json
    from somoy_jatri.narration.text import normalize,validate_segment
    direct=[];remaining=[]
    for issue in issues:
        if (isinstance(issue,dict) and issue.get('kind')=='citation'
                and issue.get('requires_rewrite') is False):
            index=issue.get('index');ids=issue.get('correct_fact_ids')
            if (type(index)==int and 0<=index<len(batch) and isinstance(ids,list) and ids
                    and all(type(i)==int and 0<=i<len(dossier['facts']) for i in ids)):
                batch[index]['fact_ids']=ids;direct.append(index);continue
        remaining.append(issue)
    if not remaining:return len(direct)
    issues=remaining
    indices=sorted({i['index'] for i in issues if isinstance(i,dict) and type(i.get('index'))==int})
    schema=None
    if indices:
        item={'type':'object','additionalProperties':False,'properties':{
            'text':{'type':'string'},'subject':{'type':'string'},'visual':{'type':'string'},
            'fact_ids':{'type':'array','items':{'type':'integer','minimum':0,
                'maximum':max(0,len(dossier['facts'])-1)}}},
            'required':['text','subject','visual','fact_ids']}
        schema={'type':'object','additionalProperties':False,'properties':{
            f'segment_{i}':item for i in indices},'required':[f'segment_{i}' for i in indices]}
    prompt=('Correct ONLY actual factual, citation, or Bangla/English scene mismatches in '
        'these historical vlog segments. Treat every listed issue as a required correction. '
        'When no fact supports a claim, REMOVE that claim from BOTH Bangla narration and English '
        'subject/visual. A new citation or changing a compass direction cannot fix unsupported narration. '
        'Do not preserve an incorrect assertion merely to preserve the original wording. '
        'Rewrite it as a simple paraphrase of ONE supplied fact, or a subjective reaction with an '
        'explicitly labelled reconstruction in BOTH languages. Do not add buildings, statues, workers, '
        'spatial relationships, materials or activities not established by the cited fact. '
        'Preserve Bangla exactly only when it is already supported and only its citation needs changing. '
        'Do not introduce new facts. Keep narration '
        'length similar. Use the explicit segment_N keys for indices and fact_N keys for fact_ids. '
        'Return the integer N, never a source ID or a counted array position. '
        +json.dumps({'issues':issues,'dossier':indexed_dossier(dossier),'segments':indexed_segments(batch)},ensure_ascii=False))
    if attempt:
        prompt+=(' Previous repair did not resolve every error. Replace the entire flagged segment '
            'with a fresh, simpler, evidence-grounded utterance; do not make another superficial edit. '
            'Check every assertion in text AND visual against the cited fact before responding.')
        if indices and dossier['facts']:
            assignments={}
            for i in indices:
                if not 0<=i<len(batch):raise ValueError('Invalid semantic correction index')
                candidates=[f for issue in issues if isinstance(issue,dict) and issue.get('index')==i
                            for f in issue.get('correct_fact_ids',[])] + batch[i].get('fact_ids',[])
                fact_id=next((f for f in candidates if type(f)==int and 0<=f<len(dossier['facts'])),
                             i%len(dossier['facts']))
                assignments[f'segment_{i}']={'fact_id':fact_id,'fact':dossier['facts'][fact_id]}
            # Exclude the rejected wording entirely: negating or lightly editing it can
            # retain the unsupported relationship that caused the previous rejection.
            prompt=('Replace the entire flagged segment with a fresh, simple Bangla utterance '
                'of 10–20 words and at most 220 characters. For each segment use ONLY its ONE assigned '
                'fact below. Paraphrase that fact accurately and cite its explicit fact_id. '
                'The English subject/visual must illustrate only that same fact, with no invented '
                'objects, actions, compass directions or spatial relationships. Label visual '
                'reconstructions explicitly. Do not infer details or combine facts. '
                'No original narration is supplied because it contained unsupported assertions. '
                +json.dumps(assignments,ensure_ascii=False))
    if indices:
        prompt+=' Return ONLY a JSON object matching this schema: '+json.dumps(schema)+'. Copy unchanged text exactly.'
    else:
        prompt+=' Return {"patches":[{"index":0,"fact_ids":[0],"subject":"English subject","visual":"English matching scene"}]}. Omit unchanged fields.'
    result=(model.json(prompt,schema=schema,temperature=.2,reasoning_effort='medium')
            if schema else model.json(prompt))
    patches=([dict(index=i,**result[f'segment_{i}']) for i in indices] if schema else result.get('patches',[]))
    if not patches:raise ValueError('Semantic repair returned no corrections')
    seen=set()
    for patch in patches:
        index=patch.get('index')
        if type(index)!=int or not 0<=index<len(batch) or index in seen:
            raise ValueError('Invalid semantic correction index')
        seen.add(index);segment=dict(batch[index])
        for key in ('text','subject','visual','fact_ids'):
            if key in patch:segment[key]=patch[key]
        if 'text' in patch:segment['text']=normalize(segment['text'])
        validate_segment(segment)
        if not isinstance(segment.get('subject'),str) or not segment['subject'].strip() or not isinstance(segment.get('visual'),str) or not segment['visual'].strip():
            raise ValueError('Semantic correction lacks a visual')
        ids=segment.get('fact_ids',[])
        if not isinstance(ids,list) or any(type(i)!=int or not 0<=i<len(dossier['facts']) for i in ids):
            raise ValueError('Semantic correction has invalid fact references')
        segment['anchors']=[segment['subject']]
        batch[index].clear();batch[index].update(segment)
    return len(patches)+len(direct)


def evaluate_semantics(story, dossier, report_path=None, repair=False):
    from somoy_jatri.scripts.groq import Groq
    import json,os,time
    from somoy_jatri.utils import save
    segments=story['segments'];model=Groq()
    for offset in range(0,len(segments),10):
        batch=segments[offset:offset+10]
        for attempt in range(9 if repair else 1):
            issue_schema={'type':'object','additionalProperties':False,'properties':{
                'index':{'type':'integer','minimum':0,'maximum':len(batch)-1},
                'kind':{'type':'string','enum':['citation','visual','narration','event']},
                'problem':{'type':'string'},'requires_rewrite':{'type':'boolean'},
                'correct_fact_ids':{'type':'array','items':{
                    'type':'integer','minimum':0,'maximum':max(0,len(dossier['facts'])-1)}}},
                'required':['index','kind','problem','requires_rewrite','correct_fact_ids']}
            schema={'type':'object','additionalProperties':False,'properties':{
                'passed':{'type':'boolean'},'issues':{'type':'array','items':issue_schema}},
                'required':['passed','issues']}
            result=model.json('Review each Bangla utterance against its English visual/subject and '
                'fact_ids. Reject invented historical claims, anachronisms, mismatched subjects, and '
                'multiple visual events or incoherent Bangla. Allow explicitly labelled artistic reconstruction, fictional '
                'time travel and subjective reactions; these do not require invented factual citations. '
                'Review EVERY segment and list ALL actual errors in one response, not just the first. '
                'Use only the supplied evidence; do not reject it based on outside knowledge. '
                'Do not treat an explicitly subjective observation, lighting, shadow or reconstruction as '
                'a documented historical assertion unless it also asserts unsupported historical detail. '
                'Return a JSON object with passed and issues. passed must be false whenever issues is nonempty. '
                'Each fact and segment has an EXPLICIT ID: fact_N and segment_N. Return integer N in '
                'correct_fact_ids and index. Do not count entries or use source IDs as fact IDs. '
                'requires_rewrite=false is allowed ONLY when '
                'the existing narration and visual are fully supported and changing fact_ids alone fixes it. '
                'A wrong direction, unsupported building/activity, or contradiction requires_rewrite=true '
                'even if a relevant fact ID exists. Provide correct_fact_ids when supported, otherwise []. '
                'Dossier: '+json.dumps(indexed_dossier(dossier),ensure_ascii=False)
                +' Segments: '+json.dumps(indexed_segments(batch),ensure_ascii=False),schema=schema,
                temperature=0,reasoning_effort='medium')
            if result.get('passed') is True and result.get('issues') == []:break
            print(json.dumps({'semantic_stage':'rejected','batch':offset//10+1,
                              'issues':result.get('issues',[])[:5]}),flush=True)
            if report_path is not None:
                save(report_path,{'passed':False,'batch':offset//10+1,'issues':result.get('issues',[])})
            if not repair or attempt==8:
                raise ValueError(f'Storyboard semantic review failed in batch {offset//10+1}')
            count=repair_batch(model,batch,dossier,result.get('issues',[]),attempt=attempt)
            if report_path is not None:save(report_path.parent/'story.json',story)
            print(json.dumps({'semantic_stage':'repaired','batch':offset//10+1,'corrections':count}),flush=True)
        if offset+10<len(segments):time.sleep(float(os.getenv('STORY_PACE_SECONDS','10')))
    return {'passed':True,'method':'batched model review','segments':len(segments)}


def shard(shots, index, count):
    if not 1 <= count <= 16 or not 0 <= index < count: raise ValueError('Invalid shard')
    return [s for i,s in enumerate(shots) if i % count == index]


def reviewed_story(story, dossier, path):
    """Cache review only for the exact normalized story and source packet."""
    import hashlib, json
    from somoy_jatri.utils import load, save
    fingerprint=hashlib.sha256(json.dumps([3,story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if path.exists():
        review=load(path)
        if review.get('passed') is True and review.get('fingerprint')==fingerprint:
            return review
    review=evaluate_semantics(story,dossier,report_path=path,repair=True)
    fingerprint=hashlib.sha256(json.dumps([3,story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    save(path.parent/'story.json',story)
    review['fingerprint']=fingerprint
    save(path,review)
    return review
