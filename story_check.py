"""Credential-free smoke test of the actual Qwen runtime and structured output."""
import json
import os
from pathlib import Path

from story_cpu import MODEL_ID, StoryGenerationError, request_story
from workflow import narration_batch, story_outline_schema, narration_schema
from islamic_content import catalog
from jsonschema import Draft202012Validator


def check():
    # Exercise the exact topic-enriched schemas before loading a large model.
    # A one-chapter narration probe alone cannot detect outline-construction bugs.
    for topic in catalog():
        Draft202012Validator.check_schema(story_outline_schema(topic))
    for begin in (1, 6, 11, 16):
        keys = [f'chapter_{i:02}' for i in range(begin, begin+5)]
        Draft202012Validator.check_schema(narration_schema(keys, 110))
    def ask(prompt, limit, schema):
        result = request_story('chat/completions', {'model': MODEL_ID,
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'schema': schema}},
            'max_completion_tokens': 512, 'temperature': .7})
        return json.loads(result['choices'][0]['message']['content'])
    parts = narration_batch('Write chapter_01 as a sourced English Islamic documentary opening. '
        'Use only these facts: Samarra was an Abbasid capital from 836 to 892 and preserves mosque and palace remains. '
        'Write about 110 words explaining the evidence and its limits. Do not invent dates, people, dialogue or events.',
        ['chapter_01'], 110, ask)
    from video_packaging import HOOK_SCHEMA
    hook = ask('Return a specific uppercase 2-5 word thumbnail question about the surviving minaret at Samarra. '
               'Use at most 30 characters including spaces and the final question mark.', 128,
               {'type': 'object', 'properties': {'thumbnail_text': HOOK_SCHEMA},
                'required': ['thumbnail_text'], 'additionalProperties': False})
    Draft202012Validator(HOOK_SCHEMA).validate(hook['thumbnail_text'])
    return {'check': 'Qwen script generation readiness', 'passed': True, 'model': MODEL_ID,
            'narration_words': len(parts[0].split())}


if __name__ == '__main__':
    try:
        print(json.dumps(check()), flush=True)
    except (StoryGenerationError, ImportError) as error:
        reason = str(error) if isinstance(error, StoryGenerationError) else 'Install requirements-story.txt before running Qwen'
        print(json.dumps({'check': 'Qwen script generation readiness', 'passed': False, 'reason': reason}), flush=True)
        if os.getenv('GITHUB_ACTIONS') == 'true':
            print('::error title=Qwen readiness failed::' + reason, flush=True)
            if os.getenv('GITHUB_STEP_SUMMARY'):
                with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as stream:
                    stream.write('## Qwen readiness failed\n\n' + reason + '\n')
        raise SystemExit(1)
