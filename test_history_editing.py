import unittest

from history_animation import shot_animation
from history_coverage import catalog
from history_editing import plan_edits


class HistoryEditingTests(unittest.TestCase):
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

    def test_loading_cargo_animates_carrying_without_sensitive_depictions(self):
        self.assertEqual(shot_animation('Workers load cargo.',islamic=False,index=0)['action'],'carry')
        self.assertIsNone(shot_animation('A prophet traveled to a harbor.',islamic=True,index=0))
