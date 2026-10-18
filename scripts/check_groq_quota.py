"""Report only non-sensitive quota counters; never print raw API errors or credentials."""
import json
import os
import re

import requests

def full_request():
    from somoy_jatri.utils import load
    from somoy_jatri.scripts.groq import Groq
    from somoy_jatri.storyboard.timeline import evaluate_semantics
    captured={}
    count=0
    os.environ['STORY_PACE_SECONDS']='0'
    class Captured(Exception): pass
    def capture(self,prompt,**kwargs):
        nonlocal count
        count+=1
        if count<int(os.getenv('PROBE_BATCH','4')):
            return {'passed':True,'issues':[]}
        captured.update(prompt=prompt,**kwargs)
        raise Captured()
    Groq.json=capture
    try:
        evaluate_semantics(load('output/quota-input/story.json'),load('output/quota-input/research.json'))
    except Captured:
        return captured
    raise ValueError('No storyboard request captured')


probe=full_request() if os.path.exists('output/quota-input/story.json') else None

for model in ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3.8-27b']:
    options=({'reasoning_effort':'medium'} if model.startswith('openai/gpt-oss-') or model=='qwen/qwen3.8-27b' else {})
    body=({'model':model,**options,'max_completion_tokens':4096,
           'messages':[{'role':'user','content':'Return only a valid JSON object.\n'+probe['prompt']}],
           'response_format':{'type':'json_schema','json_schema':{'name':'somoy_response','strict':True,'schema':probe['schema']}},'temperature':0}
          if probe else {'model':model,'messages':[{'role':'user','content':'Reply OK.'}],'max_completion_tokens':16})
    response = requests.post('https://api.groq.com/openai/v1/chat/completions', timeout=60,
        headers={'Authorization':'Bearer '+os.environ['GROQ_API_KEY']},
        json=body)
    payload=response.json()
    error=payload.get('error',{})
    message=error.get('message','')
    report={'probe':'storyboard-batch-'+os.getenv('PROBE_BATCH','4') if probe else 'minimal','model':model,'status':response.status_code,'error_code':error.get('code')}
    scope=re.search(r'(tokens|requests) per (minute|day)',message,re.I)
    if scope:report['quota_scope']=scope.group(0)
    delay=re.search(r'try again in\s*((?:\d+(?:\.\d+)?[hms]\s*)+)',message,re.I)
    if delay:report['reset_delay']=delay.group(1).strip()
    for label in ['Limit','Used','Requested']:
        match=re.search(r'\b'+label+r'\s*:?\s*([\d,.]+)',message,re.I)
        if match:report[label.lower()]=match.group(1).rstrip('.')
    for key in ['retry-after','x-ratelimit-limit-tokens','x-ratelimit-remaining-tokens',
                'x-ratelimit-reset-tokens','x-ratelimit-remaining-requests','x-ratelimit-reset-requests']:
        value=response.headers.get(key)
        if value and re.fullmatch(r'[\d.hms\s]+',value):report[key]=value
    print(json.dumps(report),flush=True)
