"""Report only non-sensitive quota counters; never print raw API errors or credentials."""
import json
import os
import re

import requests

for model in ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3.8-27b']:
    response = requests.post('https://api.groq.com/openai/v1/chat/completions', timeout=60,
        headers={'Authorization':'Bearer '+os.environ['GROQ_API_KEY']},
        json={'model':model,'messages':[{'role':'user','content':'Reply OK.'}],'max_completion_tokens':16})
    payload=response.json()
    error=payload.get('error',{})
    message=error.get('message','')
    report={'model':model,'status':response.status_code,'error_code':error.get('code')}
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
