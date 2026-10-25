"""Reference-style, credentials-free Qwen CPU readiness test before video setup."""
from somoy_jatri.preparation.story import ask,obj,text_schema
import re
result=ask('Write one complete natural Bangla sentence of 8 to 12 words as text.',256,obj({'text':text_schema(8,12)}))
if not re.search(r'[\u0980-\u09ff]',result['text']):
    raise ValueError('Expected real Bengali output from local Qwen')
print('Qwen3-4B local Bengali readiness passed',flush=True)
