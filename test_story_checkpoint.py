"""Preparation recovery keeps an accepted story without weakening validation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import long_video as lv


class StoryCheckpointTests(unittest.TestCase):
    def test_resume_saved_story_does_not_generate_another_episode(self):
        story = json.loads(Path('sample-story.json').read_text())
        store = MagicMock()
        store.load.side_effect = [{}, story]
        with tempfile.TemporaryDirectory() as directory, patch.object(lv, 'ROOT', Path(directory)), \
             patch('long_video.w.Store', return_value=store), \
             patch('long_video.w.make_story') as generate, \
             patch.dict('os.environ', {'GENERATE_FRESH_STORY': 'true', 'STORY_FILE': ''}):
            lv.stage_story()
            self.assertEqual(json.loads((Path(directory)/'story.json').read_text()), story)
            generate.assert_not_called()

    def test_invalid_checkpoint_is_not_silently_used_or_replaced(self):
        story = json.loads(Path('sample-story.json').read_text())
        story['fictional'] = True
        store = MagicMock()
        store.load.side_effect = [{}, story]
        with tempfile.TemporaryDirectory() as directory, patch.object(lv, 'ROOT', Path(directory)), \
             patch('long_video.w.Store', return_value=store), \
             patch('long_video.w.make_story') as generate, \
             patch.dict('os.environ', {'GENERATE_FRESH_STORY': 'true', 'STORY_FILE': ''}):
            with self.assertRaises(ValueError):
                lv.stage_story()
            generate.assert_not_called()
            store.save.assert_not_called()

    def test_new_story_is_checkpointed_before_narration(self):
        story = json.loads(Path('sample-story.json').read_text())
        store = MagicMock()
        store.load.side_effect = [{}, None, []]
        with tempfile.TemporaryDirectory() as directory, patch.object(lv, 'ROOT', Path(directory)), \
             patch('long_video.w.Store', return_value=store), \
             patch('long_video.w.make_story', return_value=copy.deepcopy(story)), \
             patch.dict('os.environ', {'GENERATE_FRESH_STORY': 'true', 'STORY_FILE': ''}):
            lv.stage_story()
            self.assertTrue(store.save.call_args.args[0].endswith('/staged-story.json'))
            self.assertEqual(store.save.call_args.args[1], story)

    def test_packaging_failure_resumes_generated_chapters_from_private_cache(self):
        import workflow as w
        import islamic_content as c
        from unittest.mock import Mock
        story = json.loads(Path('sample-story.json').read_text())
        topic = story['evidence']
        saved = {}
        cache = Mock()
        cache.load.side_effect = lambda key, default: copy.deepcopy(saved.get(key, default))
        cache.save.side_effect = lambda key, value: saved.update({key: copy.deepcopy(value)})

        def request(endpoint, payload):
            properties = payload['response_format']['json_schema']['schema']['properties']
            if 'scenes' in properties:
                value = {key: story[key] for key in ('title', 'protagonist_name', 'character_description')}
                value['scenes'] = {f'chapter_{i:02}': {
                    key: scene[key] for key in ('summary', 'image_prompt', 'claim_ids')}
                    for i, scene in enumerate(story['scenes'], 1)}
            elif 'narrations' in properties:
                text = ' '.join(['Evidence'] * 109) + ' remains.'
                value = {'narrations': {key: text for key in properties['narrations']['properties']}}
            else:
                value = {'passed': True, 'issues': []}
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]}

        def package(outline, topic, ask):
            for key in ('title', 'description', 'tags', 'thumbnail_text', 'thumbnail_prompt'):
                outline[key] = story[key]

        with patch('islamic_content.catalog', return_value=[topic]), \
             patch.object(w, 'request_story', side_effect=request) as generate, \
             patch('video_packaging.request_package', side_effect=RuntimeError('packaging failed')):
            with self.assertRaisesRegex(RuntimeError, 'packaging failed'):
                w.make_story('2026-10-27', [], checkpoint=cache)
            self.assertEqual(generate.call_count, 6)
        with patch('islamic_content.catalog', return_value=[topic]), \
             patch.object(w, 'request_story', side_effect=AssertionError('Must resume')) as generate, \
             patch('video_packaging.request_package', side_effect=package):
            result = w.make_story('2026-10-27', [], checkpoint=cache)
            self.assertEqual(len(result['scenes']), 20)
            self.assertTrue(result['grounding_review']['passed'])
            generate.assert_not_called()
