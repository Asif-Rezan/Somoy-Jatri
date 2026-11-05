"""Inspect dedicated Somoy Jatri storage without exposing credentials or file contents."""
import collections
import json
from workflow import Store, drive_retry


def inventory(store):
    files, token = [], None
    while True:
        page = drive_retry(lambda: store.client.files().list(
            q=f"'{store.folder}' in parents and trashed = false",
            fields='nextPageToken,files(id,name,size,mimeType,appProperties,modifiedTime)',
            pageSize=1000, pageToken=token).execute())
        files.extend(page.get('files', []))
        token = page.get('nextPageToken')
        if not token:
            return files


def main():
    store = Store()
    print(json.dumps({'quota': store.client.about().get(fields='storageQuota').execute()['storageQuota']}), flush=True)
    files = inventory(store)
    groups = collections.defaultdict(list)
    for file in files:
        parts = file['name'].split('__', 2)
        run = parts[1] if len(parts) == 3 and parts[0] == 'runs' else '(other)'
        groups[run].append(file)
    for run, entries in sorted(groups.items()):
        state = store.load(f'runs/{run}/state.json', {}) if run != '(other)' else {}
        print(json.dumps({'run': run, 'files': len(entries), 'bytes': sum(int(f.get('size', 0)) for f in entries),
            'phase': state.get('phase'), 'video_id': state.get('video_id'),
            'verified': state.get('verification'),
            'modified': max(f['modifiedTime'] for f in entries),
            'largest': [{'name':f['name'], 'bytes':int(f.get('size',0))} for f in sorted(entries,key=lambda f:int(f.get('size',0)),reverse=True)[:3]]}),flush=True)
    print(json.dumps({'folder_files':len(files),'folder_bytes':sum(int(f.get('size',0)) for f in files)}),flush=True)


if __name__ == '__main__':
    main()
