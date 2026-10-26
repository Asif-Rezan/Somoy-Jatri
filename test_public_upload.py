"""Verify the actual upload request and visibility failure path without publishing media."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import workflow


class PublicUploadTests(unittest.TestCase):
    def upload(self, visibility):
        client, store = MagicMock(), MagicMock()
        client.channels().list().execute.return_value = {'items': [{'id': 'channel'}]}
        client.videos().insert().next_chunk.return_value = (None, {'id': 'video'})
        client.videos().list().execute.return_value = {'items': [{
            'status': {'privacyStatus': visibility, 'uploadStatus': 'processed'},
            'processingDetails': {'processingStatus': 'succeeded'}}]}
        state = {}
        with patch.dict(os.environ, {'EXPECTED_CHANNEL_ID': 'channel', 'YOUTUBE_TOKEN_JSON': '{}'}), patch.dict(sys.modules, {
            'google.oauth2.credentials': MagicMock(),
            'googleapiclient.discovery': MagicMock(build=MagicMock(return_value=client)),
            'googleapiclient.http': MagicMock()}):
            if visibility == 'public':
                workflow.upload_video('video.mp4', 'thumbnail.jpg', {
                    'title': 'Title', 'description': 'Subject and sources.', 'tags': []}, state, store, 'key')
            else:
                with self.assertRaisesRegex(RuntimeError, 'visibility'):
                    workflow.upload_video('video.mp4', 'thumbnail.jpg', {
                        'title': 'Title', 'description': 'Subject and sources.', 'tags': []}, state, store, 'key')
        self.assertEqual(client.videos().insert.call_args.kwargs['body']['status']['privacyStatus'], 'public')
        self.assertEqual(state['target_privacy'], 'public')
        self.assertEqual(state['upload_description'], 'Subject and sources.')
        client.thumbnails().set.assert_called_once()
        return state

    def test_upload_requests_public_and_omits_internal_credit(self):
        self.assertEqual(self.upload('public')['phase'], 'complete')

    def test_unexpected_private_upload_fails_verification(self):
        self.assertNotEqual(self.upload('private')['phase'], 'complete')
