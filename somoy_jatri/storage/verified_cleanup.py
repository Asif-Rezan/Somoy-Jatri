"""Verify a private YouTube upload before deleting tagged temporary Drive media."""
import hashlib
import json
import re
import time

from somoy_jatri.storage.drive import Store, drive_retry
from somoy_jatri.storage.safety import disposable
from somoy_jatri.youtube.publish import identity, service


def verify_video(store, run, client=None, wait_seconds=1800):
    if not re.fullmatch(r'episode-\d+', run):
        raise ValueError('Only generated episode run IDs can be cleaned')
    state_key = f'runs/{run}/upload.json'
    state = store.load(state_key, None)
    metadata = store.load(f'runs/{run}/metadata.json', None)
    if not state or not state.get('video_id') or state.get('thumbnail_uploaded') is not True or not metadata:
        raise ValueError('Complete upload, thumbnail and metadata required before cleanup')
    client = client or service()
    channel = identity(client)
    if state.get('channel') != channel or state.get('privacy') != 'private':
        raise ValueError('Private target channel mismatch')
    deadline = time.monotonic() + wait_seconds
    while True:
        items = client.videos().list(part='snippet,status,processingDetails,contentDetails',
                                     id=state['video_id']).execute().get('items', [])
        if len(items) != 1:
            raise ValueError('Uploaded video unavailable for verification')
        video = items[0]
        snippet, status = video['snippet'], video['status']
        if (snippet.get('channelId') != channel or snippet.get('title') != metadata['title']
                or snippet.get('description') != metadata['description']
                or set(snippet.get('tags', [])) != set(metadata.get('tags', []))
                or status.get('privacyStatus') != 'private'):
            raise ValueError('Private video identity or metadata mismatch')
        if (status.get('uploadStatus') in {'failed', 'rejected', 'deleted'}
                or video.get('processingDetails', {}).get('processingStatus') in {'failed', 'terminated'}):
            raise ValueError('YouTube processing failed')
        ready = (status.get('uploadStatus') == 'processed'
                 and video.get('processingDetails', {}).get('processingStatus') == 'succeeded'
                 and video.get('contentDetails', {}).get('definition') == 'hd')
        if ready:
            state.update(phase='verified', verification={'video_id': state['video_id'],
                         'private': True, 'metadata': True, 'processed': True, 'hd': True})
            store.save(state_key, state)
            return state
        if time.monotonic() >= deadline:
            raise TimeoutError('Private HD processing pending; temporary media retained')
        time.sleep(20)


def cleanup_remote(store, run, state):
    proof = state.get('verification', {})
    if (state.get('phase') != 'verified' or proof.get('video_id') != state.get('video_id')
            or not all(proof.get(k) is True for k in ('private', 'metadata', 'processed', 'hd'))):
        raise ValueError('Verified private HD upload required before cleanup')
    manifest = store.load(f'runs/{run}/checkpoint.json', None)
    if not manifest or manifest.get('project') != 'somoy-jatri' or manifest.get('run') != run:
        raise ValueError('Missing or foreign cleanup manifest')
    journal_key = f'runs/{run}/cleanup.json'
    journal = store.load(journal_key, None)
    if journal is None:
        files = []
        for entry in manifest['files']:
            name = entry['name']
            if not disposable(name):
                continue
            key = f'runs/{run}/{name}'
            file_id = store.find(key)
            if not file_id:
                raise ValueError('Missing temporary Drive file before cleanup')
            files.append({'id': file_id, 'name': name})
        journal = {'run': run, 'video_id': state['video_id'], 'files': files, 'deleted': []}
        store.save(journal_key, journal)
    if journal.get('run') != run or journal.get('video_id') != state['video_id']:
        raise ValueError('Cleanup journal identity mismatch')
    for entry in journal['files']:
        file_id, name = entry['id'], entry['name']
        if file_id in journal['deleted']:
            continue
        if not disposable(name):
            raise ValueError('Unsafe cleanup journal entry')
        key = f'runs/{run}/{name}'
        try:
            remote = drive_retry(lambda: store.client.files().get(fileId=file_id,
                fields='id,name,parents,appProperties,mimeType').execute())
        except Exception as error:
            if getattr(getattr(error, 'resp', None), 'status', None) == 404:
                journal['deleted'].append(file_id)
                store.save(journal_key, journal)
                continue
            raise
        props = remote.get('appProperties', {})
        if (remote.get('name') != key.replace('/', '__')
                or store.folder not in remote.get('parents', [])
                or props.get('workflow_key') != hashlib.sha256(key.encode()).hexdigest()
                or props.get('automation_run') != run or props.get('disposable') != 'v1'
                or remote.get('mimeType') == 'application/vnd.google-apps.folder'):
            raise ValueError('Remote cleanup identity mismatch')
        store.check_private(file_id)
        drive_retry(lambda: store.client.files().delete(fileId=file_id).execute())
        journal['deleted'].append(file_id)
        store.save(journal_key, journal)
    journal['complete'] = True
    store.save(journal_key, journal)
    return journal


def main():
    import os
    run = os.environ['RUN']
    store = Store()
    state = verify_video(store, run)
    journal = cleanup_remote(store, run, state)
    print(json.dumps({'run': run, 'video_id': state['video_id'],
                      'privacy': 'private', 'cleanup_complete': journal['complete'],
                      'deleted': len(journal['deleted'])}), flush=True)


if __name__ == '__main__':
    main()
