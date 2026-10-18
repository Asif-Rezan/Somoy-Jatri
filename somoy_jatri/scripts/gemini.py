"""Gemini structured JSON fallback; credentials never enter URLs or logs."""
import json
import os
import time

import requests
from jsonschema import validate, ValidationError


class Gemini:
    def json(self, prompt, schema=None, temperature=.75, reasoning_effort='low'):
        key=os.environ['GEMINI_API_KEY']
        model=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
        config={'temperature':temperature,'maxOutputTokens':8192,
                'responseFormat':{'text':{'mimeType':'application/json'}}}
        if schema:config['responseFormat']['text']['schema']=schema
        body={'contents':[{'role':'user','parts':[{'text':'Return only a valid JSON object.\n'+prompt}]}],
              'generationConfig':config}
        for attempt in range(4):
            response=requests.post(
                'https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
                headers={'x-goog-api-key':key,'Content-Type':'application/json'},json=body,timeout=180)
            if not response.ok:
                if response.status_code in (429,500,502,503,504) and attempt<3:
                    try:delay=float(response.headers.get('Retry-After','30'))
                    except (TypeError,ValueError):delay=30.
                    delay=max(1.,min(300.,delay))
                    print(json.dumps({'gemini_stage':'retry','status':response.status_code,
                                      'wait_seconds':delay}),flush=True)
                    time.sleep(delay);continue
                print(json.dumps({'gemini_stage':'failed','status':response.status_code}),flush=True)
                raise RuntimeError('Gemini request failed, HTTP '+str(response.status_code))
            payload=response.json()
            candidates=payload.get('candidates',[])
            if not candidates or candidates[0].get('finishReason')!='STOP':
                raise ValueError('Gemini response blocked or incomplete')
            parts=candidates[0].get('content',{}).get('parts',[])
            text=''.join(p.get('text','') for p in parts if not p.get('thought'))
            try:
                result=json.loads(text)
                if not isinstance(result,dict):raise ValueError('JSON object required')
                if schema:validate(result,schema)
            except (ValueError, ValidationError):
                if attempt<3:
                    print(json.dumps({'gemini_stage':'invalid_json','attempt':attempt+1}),flush=True)
                    continue
                raise ValueError('Gemini returned invalid structured output') from None
            usage=payload.get('usageMetadata',{})
            print(json.dumps({'gemini_stage':'completed','model':model,**{
                k:usage[k] for k in ('promptTokenCount','candidatesTokenCount','totalTokenCount')
                if isinstance(usage.get(k),int)}}),flush=True)
            return result
        raise RuntimeError('Gemini retries exhausted')
