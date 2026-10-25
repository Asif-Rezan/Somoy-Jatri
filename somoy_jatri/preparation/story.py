"""Rezan-After-Dark outline/four-batch process, adapted to sourced Bangla history."""
import copy
import json
import os
import re
from somoy_jatri.preparation.story_cpu import MODEL_ID, request_story
from somoy_jatri.narration.text import normalize

FORMAT = 'reference-chapters-v1'
KEYS = [f'chapter_{i:02}' for i in range(1,21)]
CTA = ' কোন সময়ের ইতিহাস পরের পর্বে দেখতে চান? মন্তব্যে জানান, ভালো লাগলে লাইক দিন এবং সময় যাত্রীর সঙ্গে থাকতে সাবস্ক্রাইব করুন।'


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def ask(prompt, limit, schema, temperature=.7):
    result=request_story('chat/completions', {'model':MODEL_ID,
        'messages':[{'role':'user','content':prompt}],
        'response_format':{'type':'json_schema','json_schema':{
            'name':'somoy_chapters','strict':True,'schema':schema}},
        'temperature':temperature,'max_completion_tokens':limit})
    return json.loads(result['choices'][0]['message']['content'])


def text_schema(lower, upper):
    # Same word-count grammar as the reference, including Bengali letters/marks/dari.
    word=r"[\u0980-\u09ffA-Za-z0-9][\u0980-\u09ffA-Za-z0-9,.;:!?'\-]*"
    final=r"[\u0980-\u09ffA-Za-z0-9][\u0980-\u09ffA-Za-z0-9'\-]*[।.!?]"
    return {'type':'string','pattern':'^'+word+'( '+word+'){'+str(lower-2)+','+str(upper-2)+'} '+final+'$'}


def narration_batch(prompt, keys, target, request=ask):
    lower,upper=max(35,target-10),target+20
    schema=obj({'narrations':obj({key:text_schema(lower,upper) for key in keys})})
    feedback=''
    for attempt in range(3):
        group=request(prompt+feedback+f'\nUse exactly {lower}–{upper} Bangla words per chapter, separated by single spaces. '
            'Use complete sentences ending with Bengali dari or ordinary punctuation. No headings or spoken directions.',6000,schema)
        values=group.get('narrations',{})
        if set(values)!=set(keys) or not all(isinstance(values[k],str) for k in keys):
            raise ValueError('Narration batch must contain all five assigned chapters')
        counts={key:len(values[key].split()) for key in keys}
        if all(lower<=count<=upper for count in counts.values()):
            if any(not re.search(r'[\u0980-\u09ff]',values[k]) for k in keys):
                raise ValueError('Narration must be Bangla')
            return [normalize(values[key]) for key in keys]
        print(json.dumps({'prepare_stage':'chapter_word_retry','attempt':attempt+1,'word_counts':counts}),flush=True)
        feedback=f'\nRevise this draft to the required counts. Actual counts: {counts}. Draft: '+json.dumps(group,ensure_ascii=False)
    raise RuntimeError('Chapter word targets failed after three attempts')


def validate(story, dossier):
    if story.get('format')!=FORMAT or len(story.get('scenes',[]))!=20:
        raise ValueError('Reference preparation requires twenty chapters')
    if not isinstance(story.get('title'),str) or not 1<=len(story['title'])<=100:
        raise ValueError('Invalid chapter story title')
    for scene in story['scenes']:
        if not scene.get('narration') or not re.search(r'[\u0980-\u09ff]',scene['narration']):
            raise ValueError('Missing Bangla chapter narration')
        if not scene.get('summary') or not scene.get('image_prompt'):
            raise ValueError('Missing chapter outline')
        if not isinstance(scene.get('fact_ids'),list) or any(type(i)!=int or not 0<=i<len(dossier['facts']) for i in scene['fact_ids']):
            raise ValueError('Invalid chapter fact citation')
    words=sum(len(s['narration'].split()) for s in story['scenes'])
    if not 700<=words<=4000:
        raise ValueError('Narration word total outside bounded chapter range')
    if not story['scenes'][-1]['narration'].endswith(CTA):
        raise ValueError('Final Bangla CTA missing')
    return story


def generate(dossier, previous, request=ask):
    evidence=json.dumps({'location':dossier['location'],'period':dossier['period'],
        'facts':dossier['facts'],'uncertain':dossier['uncertain']},ensure_ascii=False)
    recent=[{'title':str(x.get('topic',x.get('title','')))[:100]} for x in previous[-10:]]
    scene=obj({'summary':{'type':'string'},'image_prompt':{'type':'string'},
        'fact_ids':{'type':'array','items':{'type':'integer','minimum':0,'maximum':len(dossier['facts'])-1}}})
    outline=request('Plan twenty concise chapters for an original Bangla first-person historical time-travel vlog. '
        'Time travel is fictional. History must use ONLY the supplied evidence. No horror, invented dialogue, '
        'unsupported dates or discoveries. Explicitly label uncertain details as reconstruction. '
        'Each chapter advances the visit without repeating earlier chapters. Return a Bangla title (max 90 characters), '
        'then chapter_01 through chapter_20 with a Bangla summary, a concise English image_prompt, '
        'and fact_ids using zero-based fact indices; subjective reactions may use []. '
        f'Evidence: {evidence}. Recent topics to avoid: {recent}. No full narration or publishing metadata yet.',
        3000,obj({'title':{'type':'string'},'scenes':obj({key:scene for key in KEYS})}))
    target=int(os.getenv('STORY_CHAPTER_WORD_TARGET','75'))
    if not 55<=target<=110:raise ValueError('Bangla chapter target must be 55–110 words')
    scenes=[outline['scenes'][key] for key in KEYS]
    prior=''
    for begin in (0,5,10,15):
        keys=KEYS[begin:begin+5]
        prompt=('Write only the assigned five chapters of this original Bangla historical time-travel vlog. '
            'Natural conversational Bangladeshi Bangla. Use ONLY the evidence for historical statements. '
            'Distinguish subjective reactions and explicitly labelled reconstructions from documented facts. '
            'Never invent buildings, people, activities, motives or dialogue absent from the evidence. '
            'Develop the assigned observations and their uncertainty without adding history. '
            'No headings, introductions repeated between chapters, or calls to action. '
            f'Target {target} words per chapter. Evidence: {evidence}. '
            f'Title: {outline["title"]}. Assigned events: '+json.dumps(dict(zip(keys,scenes[begin:begin+5])),ensure_ascii=False)
            +f'. Previous ending: {prior[-500:]}. Return narrations keyed by {keys}.')
        parts=narration_batch(prompt,keys,target,request)
        for scene,text in zip(scenes[begin:begin+5],parts):scene['narration']=text
        prior=parts[-1]
        print(json.dumps({'prepare_stage':'narration_batch_complete','chapters':f'{begin+1}-{begin+5}'}),flush=True)
    scenes[-1]['narration']+=CTA
    story={'format':FORMAT,'title':outline['title'],'scenes':scenes,'topic_id':dossier.get('topic_id'),
        'tags':['সময় যাত্রী','বাংলা ইতিহাস','সময়ভ্রমণ']}
    validate(story,dossier)
    # Publishing metadata follows complete narration, as in the reference.
    package=request('Create accurate Bangla YouTube packaging for this sourced time-travel episode. '
        'Return title (max 90 characters), thumbnail_text (a complementary 2–5 word Bangla question answered by the episode), '
        'and description (two short Bangla sentences about the subject and evidence). No sensational or unsupported promises. '
        f'Evidence: {evidence}. Title: {story["title"]}. Chapter outline: '
        +json.dumps([s['summary'] for s in scenes],ensure_ascii=False),1200,
        obj({k:{'type':'string'} for k in ['title','thumbnail_text','description']}))
    if any(not re.search(r'[\u0980-\u09ff]',v) for v in package.values()) or len(package['title'])>100 or not 2<=len(package['thumbnail_text'].split())<=5:
        raise ValueError('Invalid Bangla publishing metadata')
    story.update(title=package['title'],packaging=package)
    return validate(story,dossier)


def revise(story,dossier,ratio,direction,indices,request=ask):
    validate(story,dossier)
    result=copy.deepcopy(story)
    for start in range(0,len(indices),5):
        group=indices[start:start+5]
        original={KEYS[i]:story['scenes'][i]['narration'].removesuffix(CTA) for i in group}
        targets={key:max(35,min(180,round(len(text.split())*ratio))) for key,text in original.items()}
        schema=obj({key:text_schema(max(25,n-max(3,round(n*.05))),n+max(3,round(n*.05))) for key,n in targets.items()})
        values=request(f'Revise only these Bangla historical chapters to {direction} their narration. '
            'Preserve chapter order, meaning, factual anchors and uncertainty. No invented historical details or calls to action. '
            f'Target words: {targets}. Evidence: '+json.dumps(dossier['facts'],ensure_ascii=False)
            +'. Chapter text: '+json.dumps(original,ensure_ascii=False),6000,schema,.35)
        if set(values)!=set(original):raise ValueError('Duration revision omitted a selected chapter')
        for i in group:
            text=normalize(values[KEYS[i]])
            count=len(text.split());target=targets[KEYS[i]]
            if not max(25,round(target*.7))<=count<=round(target*1.3):raise ValueError('Duration revision missed word target')
            result['scenes'][i]['narration']=text+(CTA if i==19 else '')
    return validate(result,dossier)
