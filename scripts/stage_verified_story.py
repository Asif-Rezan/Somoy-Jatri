"""Stage only a successful, current-code storyboard replay for a fresh video run."""
import hashlib
import json
import os
from pathlib import Path

import requests

from somoy_jatri.utils import load, save


def require_verification(metadata, current_sha, comparison=None):
    if (metadata.get('conclusion') != 'success' or metadata.get('status') != 'completed'
            or metadata.get('path') != '.github/workflows/verify-production.yml'):
        raise ValueError('A successful full production verification is required')
    if metadata.get('head_sha') != current_sha:
        # Permit later workflow/test-only changes, but never untested pipeline changes.
        if not comparison or comparison.get('status') != 'ahead' or len(comparison.get('files', [])) >= 300:
            raise ValueError('Cannot establish verified pipeline version')
        for item in comparison.get('files', []):
            paths = [item['filename'], item.get('previous_filename', '')]
            if any(p.startswith('somoy_jatri/') or p.startswith('requirements') or p == 'pyproject.toml'
                   for p in paths):
                raise ValueError('Pipeline changed after production verification')


def stage(source, destination):
    story = load(source / 'story.json')
    dossier = load(source / 'research.json')
    review = load(source / 'verification-review.json')
    fingerprint = hashlib.sha256(json.dumps([3, story, dossier], ensure_ascii=False,
                                            sort_keys=True).encode()).hexdigest()
    if (review.get('passed') is not True or review.get('fingerprint') != fingerprint
            or review.get('segments') != len(story.get('segments', [])) or not story.get('segments')):
        raise ValueError('Verified storyboard receipt does not match content')
    for name, data in [('story.json', story), ('research.json', dossier), ('semantic-review.json', review)]:
        save(destination / name, data)


def main():
    value = os.environ['RESEARCH_DOSSIER']
    if not value.startswith('verified:') or not value[9:].isdigit():
        raise ValueError('Expected verified:RUN_NUMBER')
    source_run = value[9:]
    api = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'}
    def get(path):
        response = requests.get(api + path, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    metadata = get('/actions/runs/' + source_run)
    current = os.environ['GITHUB_SHA']
    comparison = (get('/compare/' + metadata['head_sha'] + '...' + current)
                  if metadata.get('head_sha') != current else None)
    require_verification(metadata, current, comparison)
    if os.environ['VERIFIED_OPERATION'] == 'check':
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('source_run=' + source_run + '\n')
    else:
        stage(Path('output/verified-input'), Path('output') / os.environ['RUN'])


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'verified_story_stage': 'failed', 'error_type': type(error).__name__}))
        raise SystemExit(1)
