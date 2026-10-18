import json
import os
from somoy_jatri.utils import load,save


def service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    return build('youtube','v3',credentials=Credentials.from_authorized_user_info(
        json.loads(os.environ['YOUTUBE_TOKEN_JSON'])),cache_discovery=False)


def identity(client):
    expected=os.getenv('EXPECTED_CHANNEL_ID')
    if not expected:raise ValueError('EXPECTED_CHANNEL_ID required; refusing upload')
    actual=client.channels().list(part='id',mine=True).execute().get('items',[])
    if [c['id'] for c in actual]!=[expected]:raise ValueError('Target YouTube channel mismatch')
    return expected


def validate_privacy(privacy):
    if privacy not in {'private','unlisted','public'}:raise ValueError('Invalid privacy')
    if privacy!='private' and os.getenv('ALLOW_PUBLIC_UPLOAD')!='true':
        raise ValueError('Explicit ALLOW_PUBLIC_UPLOAD=true required')


def upload(root,privacy='private',client=None,persist=None):
    validate_privacy(privacy)
    if os.getenv('UPLOAD_ENABLED')!='true':raise ValueError('Uploads disabled')
    qc=load(root/'qc.json');config=load(root/'config.json')
    if config['mode']!='production' or qc.get('production_ready') is not True:
        raise ValueError('Mock or incomplete output cannot upload')
    from somoy_jatri.validation.quality import validate_final
    validate_final(root,production=True)
    client=client or service();channel=identity(client)
    state_path=root/'upload.json';state=load(state_path) if state_path.exists() else {}
    def journal():
        save(state_path,state)
        if persist:persist(state_path)
    if state.get('channel') not in (None,channel):raise ValueError('Upload state channel mismatch')
    if state.get('video_id'):
        remote=client.videos().list(part='snippet,status,processingDetails',id=state['video_id']).execute()['items']
        if len(remote)!=1 or remote[0]['snippet']['channelId']!=channel:
            raise ValueError('Existing video cannot be verified; never reinsert')
        if remote[0]['status'].get('privacyStatus')!=state['privacy']:
            raise ValueError('Remote privacy differs from upload state')
        if remote[0].get('processingDetails',{}).get('processingStatus')=='succeeded':
            if not state.get('thumbnail_uploaded'):
                client.thumbnails().set(videoId=state['video_id'],media_body=str(root/'thumbnail.jpg')).execute()
                state['thumbnail_uploaded']=True
            state['phase']='verified';journal()
        return state
    if state.get('phase') in {'starting','uploading','ambiguous'}:
        # No blind reinsertion after timeout. Resumable session recovery needs explicit reconciliation.
        raise RuntimeError('Ambiguous prior upload: reconcile video ID before retry; no duplicate inserted')
    metadata=load(root/'metadata.json')
    state.update(phase='starting',channel=channel,privacy=privacy);journal()
    from googleapiclient.http import MediaFileUpload
    request=client.videos().insert(part='snippet,status',body={
        'snippet':metadata,'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False,
                                   'containsSyntheticMedia':True}},
        media_body=MediaFileUpload(str(root/'video.mp4'),chunksize=8*1024*1024,resumable=True))
    try:
        result=None
        while result is None:
            _,result=request.next_chunk(num_retries=3)
            state.update(phase='uploading');journal()
        state.update(phase='uploaded',video_id=result['id']);journal()
        client.thumbnails().set(videoId=result['id'],media_body=str(root/'thumbnail.jpg')).execute()
        state['thumbnail_uploaded']=True;journal()
    except Exception:
        state['phase']='uploaded' if state.get('video_id') else 'ambiguous';journal()
        raise RuntimeError('Upload interrupted; preserve checkpoint and reconcile before retry') from None
    return state
