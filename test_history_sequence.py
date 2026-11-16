import unittest

from PIL import Image

from history_animation import shot_animation
from history_editing import plan_edits
from history_coverage import catalog
from history_sequence import artifact_image, comparison, draw_sequence, plan_sequence


class HistorySequenceTests(unittest.TestCase):
    def test_catalog_produces_source_matched_edits_and_three_recap_beats(self):
        subject = 'Ancient Rome'
        entries = [(0,'Roman tradition dates the foundation to 753 BC.','Early Rome settlement'),
                   (8,'Augustus encouraged building.','Imperial Rome plaza'),
                   (12,'Constantinople became a new capital.','Constantinople waterfront'),
                   (17,'The West lost its emperor.','Italian landscape'),
                   (18,'The Eastern Empire continued.','Constantinople harbor'),
                   (19,'The story concludes.','Central Italy')]
        shots = [dict(index=i,start=i*10,duration=10,chapter=chapter,narration=narration,visual_action=visual)
                 for i,(chapter,narration,visual) in enumerate(entries)]
        plan_edits(shots,catalog()[0])
        plan_sequence(shots,subject)
        self.assertIn('uncertainty',shots[0]['edit'])
        self.assertEqual(shots[1]['edit']['artifact'][3],'246866')
        self.assertEqual(shots[2]['edit']['reveal'],5.2)
        self.assertEqual([shot['edit']['recap'][0] for shot in shots[-4:-1]],[1,2,3])
        self.assertEqual(comparison(shots,subject)['shots'],[0,1])
        shots[1]['visual_action'] = 'A harbor in another city'
        self.assertIsNone(comparison(shots,subject))

    def test_artifact_card_draws_a_bundled_museum_image(self):
        photo = artifact_image('augustus.jpg')
        self.assertGreater(photo.width,100)
        frame = Image.new('RGB',(1280,720),'black')
        draw_sequence(frame,{'artifact': ('augustus.jpg','Gold aureus of Augustus','20–19 BCE','246866')},3,10)
        self.assertNotEqual(frame.getpixel((700,60)),(0,0,0))

    def test_building_action_requires_a_spoken_task(self):
        self.assertEqual(shot_animation('Workers lay bricks.',islamic=False,index=0)['action'],'build')
        self.assertIsNone(shot_animation('The building program grew.',islamic=False,index=0))
