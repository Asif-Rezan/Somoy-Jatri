"""Exercise all twenty real Bengali chapters without publishing scripts or calling Google."""
import json
from somoy_jatri.preparation.pipeline import catalog_dossier
from somoy_jatri.preparation.story import generate,validate
packet=catalog_dossier([])
story=validate(generate(packet,[]),packet)
print(json.dumps({'check':'reference twenty-chapter Bangla story','passed':True,
    'chapters':len(story['scenes']),'words':sum(len(s['narration'].split()) for s in story['scenes'])}),flush=True)
