"""Verify configured accounts and private storage without generating or uploading a video."""
import json
import os

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from somoy_jatri.storage.drive import Store


def main():
    response = requests.get('https://api.groq.com/openai/v1/models',
        headers={'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY']}, timeout=30)
    response.raise_for_status()
    model = os.getenv('STORY_MODEL', 'openai/gpt-oss-120b')
    if model not in {item['id'] for item in response.json()['data']}:
        raise ValueError('Configured story model is unavailable')
    print(json.dumps({'check': 'Groq authorization and model availability', 'passed': True}), flush=True)

    store = Store()
    account = store.client.about().get(fields='user(emailAddress)').execute()['user']['emailAddress']
    if account.casefold() != os.environ['EXPECTED_DRIVE_EMAIL'].casefold():
        raise ValueError('Unexpected Drive account')
    marker = {'project': 'Somoy Jatri Automation', 'connection_verified': True}
    store.save('connection-check.json', marker)
    if store.load('connection-check.json', {}) != marker:
        raise ValueError('Drive checkpoint round trip failed')
    print(json.dumps({'check': 'Drive account, private root and checkpoint read/write', 'passed': True}), flush=True)

    info = json.loads(os.environ['YOUTUBE_TOKEN_JSON'])
    if not info.get('refresh_token'):
        raise ValueError('YouTube refresh credentials missing')
    youtube = build('youtube', 'v3', credentials=Credentials.from_authorized_user_info(info), cache_discovery=False)
    channels = youtube.channels().list(part='id,snippet', mine=True).execute()['items']
    if [channel['id'] for channel in channels] != [os.environ['EXPECTED_CHANNEL_ID']]:
        raise ValueError('Unexpected YouTube channel')
    print(json.dumps({'check': 'YouTube channel identity', 'passed': True,
                      'channel_id': channels[0]['id'], 'channel_title': channels[0]['snippet']['title']}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'connections_passed': False, 'error_type': type(error).__name__}), flush=True)
        raise SystemExit(1)
