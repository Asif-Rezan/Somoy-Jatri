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
