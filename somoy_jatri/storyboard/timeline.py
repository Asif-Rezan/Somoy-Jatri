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


def repair_batch(model, batch, dossier, issues):
    import json
    from somoy_jatri.narration.text import normalize,validate_segment
    direct=[];remaining=[]
    for issue in issues:
        if isinstance(issue,dict) and issue.get('kind')=='citation':
            index=issue.get('index');ids=issue.get('correct_fact_ids')
            if (type(index)==int and 0<=index<len(batch) and isinstance(ids,list)
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
        'these historical vlog segments. Preserve Bangla text exactly when a citation or English visual '
        'correction is sufficient. Change narration only if it asserts an unsupported fact or is unnatural. '
        'Do not introduce new facts. Explicitly label uncertain artistic reconstruction. Keep narration '
        'length similar. Return {"patches":[{"index":0,"fact_ids":[0],"subject":"English subject",'
        '"visual":"English matching scene","text":"Bangla only if a rewrite is necessary"}]}. '
        'Indices are zero-based within this batch. Omit unchanged fields. '
        +json.dumps({'issues':issues,'dossier':dossier,'segments':batch},ensure_ascii=False))
    if indices:prompt+=' Return every required key '+str([f'segment_{i}' for i in indices])+'. Copy unchanged text exactly.'
    result=model.json(prompt,schema=schema) if schema else model.json(prompt)
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
        for attempt in range(3 if repair else 1):
            issue_schema={'type':'object','additionalProperties':False,'properties':{
                'index':{'type':'integer','minimum':0,'maximum':len(batch)-1},
                'kind':{'type':'string','enum':['citation','visual','narration','event']},
                'problem':{'type':'string'},'correct_fact_ids':{'type':'array','items':{
                    'type':'integer','minimum':0,'maximum':max(0,len(dossier['facts'])-1)}}},
                'required':['index','kind','problem','correct_fact_ids']}
            schema={'type':'object','additionalProperties':False,'properties':{
                'passed':{'type':'boolean'},'issues':{'type':'array','items':issue_schema}},
                'required':['passed','issues']}
            result=model.json('Review each Bangla utterance against its English visual/subject and '
                'fact_ids. Reject invented historical claims, anachronisms, mismatched subjects, and '
                'multiple visual events or incoherent Bangla. Allow explicitly labelled artistic reconstruction, fictional '
                'time travel and subjective reactions; these do not require invented factual citations. '
                'List only actual errors, not acceptable segments. Return a JSON object '
                '{"passed":bool,"issues":[{"index":0,"kind":"citation","problem":"...","correct_fact_ids":[0]}]}. '
                'Indices are ZERO-BASED within this batch. For citation-only errors provide all correct '
                'fact IDs, or [] when no citation is needed. For other error kinds use correct_fact_ids: []. '
                'Dossier: '+json.dumps(dossier,ensure_ascii=False)
                +' Segments: '+json.dumps(batch,ensure_ascii=False),schema=schema)
            if result.get('passed') is True:break
            print(json.dumps({'semantic_stage':'rejected','batch':offset//10+1,
                              'issues':result.get('issues',[])[:5]}),flush=True)
            if report_path is not None:
                save(report_path,{'passed':False,'batch':offset//10+1,'issues':result.get('issues',[])})
            if not repair or attempt==2:
                raise ValueError(f'Storyboard semantic review failed in batch {offset//10+1}')
            count=repair_batch(model,batch,dossier,result.get('issues',[]))
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
    fingerprint=hashlib.sha256(json.dumps([story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if path.exists():
        review=load(path)
        if review.get('passed') is True and review.get('fingerprint')==fingerprint:
            return review
    review=evaluate_semantics(story,dossier,report_path=path,repair=True)
    fingerprint=hashlib.sha256(json.dumps([story,dossier],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    save(path.parent/'story.json',story)
    review['fingerprint']=fingerprint
    save(path,review)
    return review
