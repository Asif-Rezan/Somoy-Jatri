"""Replay a retained production storyboard; never synthesize, upload or clean media."""
import json
from pathlib import Path

from somoy_jatri.narration.text import normalize, validate_segment
from somoy_jatri.research.dossier import validate
from somoy_jatri.storyboard.timeline import reviewed_story
from somoy_jatri.utils import load


def main():
    root = Path('output/storyboard-replay')
    dossier = load(root / 'research.json')
    validate(dossier, live=True,
             require_review=dossier.get('research_method') != 'automatic source extraction')
    story = load(root / 'story.json')
    if not story.get('segments'):
        raise ValueError('Replay storyboard is empty')
    for segment in story['segments']:
        segment['text'] = normalize(segment['text'])
        validate_segment(segment)
    # A retained review is reusable only for the exact same normalized story and dossier.
    # reviewed_story recomputes its fingerprint and reruns model review if either changed.
    receipt=root/'verification-review.json'
    if not receipt.exists() and (root/'semantic-review.json').exists():
        from somoy_jatri.utils import save
        save(receipt,load(root/'semantic-review.json'))
    from somoy_jatri.narration.providers import measure_take
    paths=sorted((root/'utterances').glob('*.wav'))
    for path in paths:measure_take(path)
    if paths:print(json.dumps({'verification_stage':'saved_audio_checked','takes':len(paths)}),flush=True)
    result = reviewed_story(story, dossier, root / 'verification-review.json')
    if result.get('passed') is not True:
        raise ValueError('Storyboard replay did not pass')
    print(json.dumps({'verification_stage': 'storyboard_passed',
                      'segments': len(story['segments'])}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'verification_stage': 'failed', 'error_type': type(error).__name__}), flush=True)
        raise SystemExit(1)
