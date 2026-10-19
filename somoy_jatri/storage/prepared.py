"""Validate and repartition a completed voice checkpoint without generating new speech."""
from dataclasses import asdict
from pathlib import Path
from somoy_jatri.config import Config
from somoy_jatri.utils import load, save, duration
from somoy_jatri.storyboard.timeline import validate


def repartition(root, workers):
    config = Config(**load(root/'config.json'))
    if config.mode != 'production' or config.run_id != root.name:
        raise ValueError('A matching production voice checkpoint is required')
    if not 1 <= workers <= 16:
        raise ValueError('Use 1–16 image workers')
    total = duration(root/'narration.wav')
    if not 600 <= total <= 900:
        raise ValueError('Prepared narration must be 600–900 seconds')
    shots = load(root/'timeline.json')
    validate(shots, total)
    records = load(root/'narration.json')
    from somoy_jatri.narration.providers import audio_record_passed
    if not records or any(not audio_record_passed(r) for r in records):
        raise ValueError('Prepared Bengali speech verification is incomplete')
    if all('start' in r and 'end' in r for r in records):
        if abs(records[0]['start'])>.002 or abs(records[-1]['end']-total)>.002:
            raise ValueError('Prepared narration duration mismatch')
        if any(abs(a['end']-b['start'])>.002 for a,b in zip(records,records[1:])):
            raise ValueError('Prepared narration gap or overlap')
    if load(root/'semantic-review.json').get('passed') is not True:
        raise ValueError('Prepared semantic review has not passed')
    config.workers = workers
    save(root/'config.json', asdict(config))
    return {'shard': list(range(workers))}


if __name__ == '__main__':
    import os, json
    run = os.environ['RUN']
    Config(mode='production', run_id=run)  # Validate before reading any path.
    matrix = repartition(Path('output')/run, int(os.environ['WORKERS']))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write('matrix='+json.dumps(matrix)+'\n')
