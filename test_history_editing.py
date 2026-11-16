import unittest

from history_animation import SIZE, compose_frame, shot_animation
from PIL import Image
from history_coverage import catalog, finalize_title, package, with_chapters
from history_editing import plan_edits


class HistoryEditingTests(unittest.TestCase):
    def test_packaging_preserves_title_format_and_uses_measured_chapter_offsets(self):
        topic = catalog()[0]
        story = {'evidence':topic,'scenes':[{}]*20}
        package(story,topic)
        lengths = [55]*20
        completed = with_chapters(finalize_title(story,sum(lengths)),lengths,sum(lengths))
        self.assertEqual(completed['title'],'The ENTIRE History of Ancient Rome in 18 Minutes')
        self.assertEqual(completed['thumbnail_text'],'WHAT SURVIVED?')
        self.assertIn('00:00 Early Rome and the Republic',completed['description'])
        self.assertIn('03:40 Carthage and the Crisis of the Republic',completed['description'])
        self.assertIn('\n\nSources\n',completed['description'])
        self.assertIn('Constantinople',completed['tags'])

    def test_capital_shift_uses_narrated_places_and_timestamps(self):
        shots = [
            {'start': 0, 'narration': 'Rome began in central Italy.'},
            {'start': 40, 'duration': 10, 'narration': 'A new capital at Constantinople in AD 330.',
             'word_offsets': [['Constantinople', 3.2]]},
            {'start': 80, 'narration': 'Imperial rule continued in Constantinople.'},
        ]
        plan_edits(shots,catalog()[0])
        self.assertEqual(shots[1]['edit']['shift'],('Rome','Constantinople'))
        self.assertEqual(shots[1]['edit']['map_start'],3.2)
        self.assertEqual(shots[1]['edit']['label'],'AD 330')
        self.assertEqual(shots[-1]['edit']['map'],shots[0]['edit']['map'])
        self.assertTrue(shots[-1]['edit']['closing'])

    def test_does_not_display_dates_missing_from_the_evidence(self):
        for date in ('AD 331','AD 27'):
            shots = [{'start': 0, 'narration': f'Rome in {date}.'}]
            plan_edits(shots,catalog()[0])
            self.assertNotIn('label',shots[0]['edit'])

    def test_cast_appears_only_during_the_aligned_action(self):
        words = [('The',0),('capital',.3),('changed.',.7),('Workers',4),
                 ('loaded',4.3),('cargo.',4.8)]
        spec = shot_animation('The capital changed. Workers loaded cargo.', islamic=False,
                              index=0, word_offsets=words, seconds=10)
        self.assertEqual(spec['start'],4.3)
        background = Image.new('RGB',SIZE,'#d5c7aa')
        self.assertEqual(compose_frame(background,spec,{},3,10).tobytes(),background.tobytes())
        self.assertNotEqual(compose_frame(background,spec,{},5,10).tobytes(),background.tobytes())
        self.assertEqual(compose_frame(background,spec,{},8,10).tobytes(),background.tobytes())

    def test_static_places_and_silent_windows_do_not_trigger_animation(self):
        self.assertIsNone(shot_animation('The city had a harbor and a road.',islamic=False,index=0))
        self.assertIsNone(shot_animation('Workers load cargo.',islamic=False,index=0,word_offsets=[]))

    def test_loading_cargo_animates_carrying_without_sensitive_depictions(self):
        self.assertEqual(shot_animation('Workers load cargo.',islamic=False,index=0)['action'],'carry')
        self.assertIsNone(shot_animation('A prophet traveled to a harbor.',islamic=True,index=0))
