import unittest

from history_animation import SIZE, compose_frame, shot_animation
from PIL import Image
from history_coverage import catalog, finalize_title, package, with_chapters
from history_editing import plan_edits


class HistoryEditingTests(unittest.TestCase):
    def test_thumbnail_lettering_changes_with_background_and_stays_readable(self):
        from thumbnail_design import contrast, lettering_colors, luminance

        fills = []
        for background in ((144,198,242),(228,162,112),(39,43,75)):
            image = Image.new('RGB',(120,60),background)
            fill,outline = lettering_colors(image,(0,0,120,60))
            self.assertGreaterEqual(contrast(luminance(fill),luminance(background)),4.5)
            self.assertGreaterEqual(contrast(luminance(fill),luminance(outline)),4.5)
            fills.append(fill)
        self.assertEqual(len(set(fills)),3)

    def test_thumbnail_finds_open_space_on_either_side(self):
        from PIL import ImageDraw
        from thumbnail_design import quiet_lettering_position

        artwork = Image.new('RGB',(1280,720),'#d4cbb4')
        draw = ImageDraw.Draw(artwork)
        for x in range(630,1280,12):
            draw.rectangle((x,0,x+5,600),fill='#1b202a')
        left, top = quiet_lettering_position(artwork,470,230)
        self.assertLess(left,600)
        self.assertLess(top,150)
        right, _ = quiet_lettering_position(artwork.transpose(Image.Transpose.FLIP_LEFT_RIGHT),470,230)
        self.assertGreater(right,680)

    def test_busy_artwork_gets_a_solid_local_contrast_panel(self):
        from thumbnail_design import calm_lettering_background

        smooth = Image.new('RGB',(180,100),'#d2bd9e')
        box = (70,30,145,65)
        self.assertFalse(calm_lettering_background(smooth,box,(33,35,58),(248,244,224)))
        for y in range(25,70):
            for x in range(70,110):
                smooth.putpixel((x,y),(34,39,49))
        self.assertTrue(calm_lettering_background(smooth,box,(33,35,58),(248,244,224)))
        self.assertEqual(smooth.getpixel((85,45)),(248,244,224))
        self.assertEqual(smooth.getpixel((0,0)),(210,189,158))

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
