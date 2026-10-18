"""Local OAuth; tokens remain outside Git and are never printed."""
import json
import os
from pathlib import Path
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES={'drive':['https://www.googleapis.com/auth/drive.file'],
        'youtube':['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly']}

def main():
    kind=sys.argv[1]
    if kind not in SCOPES:raise ValueError('Choose drive or youtube')
    target=Path(kind+'_token.json')
    if target.exists():raise ValueError('Token already exists; refusing overwrite')
    flow=InstalledAppFlow.from_client_secrets_file('client_secrets.json',SCOPES[kind])
    credentials=flow.run_local_server(host='127.0.0.1',port=0,open_browser=False,prompt='consent',access_type='offline')
    if not credentials.refresh_token:raise ValueError('Missing refresh token')
    if kind=='drive' and os.getenv('EXPECTED_DRIVE_EMAIL'):
        client=build('drive','v3',credentials=credentials)
        email=client.about().get(fields='user(emailAddress)').execute()['user']['emailAddress']
        if email.casefold()!=os.environ['EXPECTED_DRIVE_EMAIL'].casefold():raise ValueError('Wrong Drive account')
    if kind=='youtube':
        expected=os.environ['EXPECTED_CHANNEL_ID']
        client=build('youtube','v3',credentials=credentials)
        channels=client.channels().list(part='id',mine=True).execute()['items']
        if [c['id'] for c in channels]!=[expected]:raise ValueError('Wrong YouTube channel')
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(credentials.to_json())
    print('OAuth verified; token saved privately to '+str(target))

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('OAuth failed: '+type(e).__name__+'; no credentials printed.')
        raise SystemExit(1)
