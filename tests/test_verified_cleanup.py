import hashlib

import pytest

from somoy_jatri.storage.verified_cleanup import cleanup_remote


def test_remote_cleanup_requires_private_hd_proof():
    with pytest.raises(ValueError, match='Verified private HD'):
        cleanup_remote(None, 'episode-123', {'phase': 'verified', 'video_id': 'abc'})


def test_remote_cleanup_deletes_only_tagged_run_media():
    run = 'episode-123'
    key = f'runs/{run}/video.mp4'
    class FileAPI:
        def __init__(self): self.deleted = []
        def get(self, **kwargs):
            assert kwargs['fileId'] == 'media-id'
            return self
        def delete(self, **kwargs):
            self.deleted.append(kwargs['fileId'])
            return self
        def execute(self):
            return {'name': key.replace('/', '__'), 'parents': ['folder'],
                    'appProperties': {'workflow_key': hashlib.sha256(key.encode()).hexdigest(),
                                      'automation_run': run, 'disposable': 'v1'},
                    'mimeType': 'video/mp4'}
    class Client:
        def __init__(self): self.api = FileAPI()
        def files(self): return self.api
    class Store:
        folder = 'folder'
        def __init__(self): self.client = Client(); self.data = {
            f'runs/{run}/checkpoint.json': {'project': 'somoy-jatri', 'run': run,
                'files': [{'name': 'video.mp4'}, {'name': 'story.json'}]}}
        def load(self, key, default): return self.data.get(key, default)
        def save(self, key, value): self.data[key] = value
        def find(self, key): return 'media-id' if key.endswith('/video.mp4') else None
        def check_private(self, file_id): assert file_id == 'media-id'
    store = Store()
    state = {'phase': 'verified', 'video_id': 'abc', 'verification': {
        'video_id': 'abc', 'private': True, 'metadata': True, 'processed': True, 'hd': True}}
    journal = cleanup_remote(store, run, state)
    assert journal['complete'] and journal['deleted'] == ['media-id']
    assert store.client.api.deleted == ['media-id']
    cleanup_remote(store, run, state)
    assert store.client.api.deleted == ['media-id']


def test_remote_cleanup_rejects_untagged_media():
    run = 'episode-123'
    class FileAPI:
        def get(self, **kwargs): return self
        def execute(self): return {'name': 'runs__episode-123__video.mp4',
            'parents': ['folder'], 'appProperties': {}, 'mimeType': 'video/mp4'}
        def delete(self, **kwargs): raise AssertionError('Must not delete')
    class Client:
        def files(self): return FileAPI()
    class Store:
        folder = 'folder'
        client = Client()
        def load(self, key, default):
            if key.endswith('/checkpoint.json'):
                return {'project': 'somoy-jatri', 'run': run, 'files': [{'name': 'video.mp4'}]}
            return default
        def find(self, key): return 'media-id'
        def save(self, key, value): pass
    state = {'phase': 'verified', 'video_id': 'abc', 'verification': {
        'video_id': 'abc', 'private': True, 'metadata': True, 'processed': True, 'hd': True}}
    with pytest.raises(ValueError, match='identity mismatch'):
        cleanup_remote(Store(), run, state)
