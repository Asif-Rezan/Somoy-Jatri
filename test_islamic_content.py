import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import islamic_content as c
import workflow as w


class ContentTests(unittest.TestCase):
    def fixture(self):
        return json.loads(Path('sample-story.json').read_text())

    def test_catalog_contains_cited_history_and_hadith(self):
        topics=c.catalog()
        self.assertEqual({t['kind'] for t in topics},{'history','hadith'})
        self.assertEqual(len({t['id'] for t in topics}),len(topics))
        for topic in topics:
            self.assertTrue(topic['claims'])
            self.assertTrue(all(s['url'].startswith('https://') for s in topic['source_records']))
            if topic['kind']=='hadith':
                self.assertTrue(topic['hadith'][0]['reference'].startswith('Sahih al-Bukhari'))
                self.assertEqual(topic['hadith'][0]['quotation_mode'],'paraphrase_only')

    def test_source_story_fixture_passes_and_old_formats_do_not(self):
        story=self.fixture()
        w.validate_story(c.validate_content(story))
        for field,value in [('format','horror-story'),('fictional',True)]:
            broken=copy.deepcopy(story);broken[field]=value
            with self.assertRaises(ValueError):c.validate_content(broken)
        story['scenes'][0]['claim_ids']=['invented']
        with self.assertRaisesRegex(ValueError,'claim IDs'):c.validate_content(story)

    def test_no_generated_religious_quotes_or_vlog(self):
        for text in ['The Prophet said something invented.', 'Allah promised this result.',
                     'The source states "an invented quotation".', 'I saw the city.','বাংলা narration']:
            with self.subTest(text=text),self.assertRaises(ValueError):c.validate_narration(text)
        c.validate_narration('The meaning reported in Sahih al-Bukhari 1 is paraphrased here.')

    def test_production_validation_rejects_legacy_story(self):
        story=self.fixture();story['format']='bangla-old-format'
        with patch.dict('os.environ',{'CONTENT_TYPE':'islamic-documentary'}):
            with self.assertRaises(ValueError):w.validate_story(story)

    def test_hosted_images_cannot_use_paid_inference(self):
        with patch.dict('os.environ',{'IMAGE_BACKEND':'hf'}),patch('huggingface_hub.InferenceClient') as remote:
            with self.assertRaisesRegex(ValueError,'hosted image inference is disabled'):
                w.make_image('An empty courtyard',Path('unused.png'))
            remote.assert_not_called()

    def test_missing_hadith_reference_is_rejected(self):
        topic=next(t for t in c.catalog() if t['kind']=='hadith')
        topic['hadith'][0].pop('reference')
        with self.assertRaises(ValueError):c.validate_topic(topic)

    def test_source_review_rejection_stops_before_media(self):
        with self.assertRaisesRegex(ValueError,'Source-grounding'):
            c.audit_narration(self.fixture(),lambda *args:{'passed':False,'issues':['unsupported claim']})
        story=self.fixture()
        c.audit_narration(story,lambda *args:{'passed':True,'issues':[]})
        self.assertTrue(story['grounding_review']['not_independent_scholarly_verification'])

    def test_rejected_review_exposes_feedback_and_clears_stale_approval(self):
        story = self.fixture()
        story['grounding_review'] = {'passed': True}
        with self.assertRaises(c.SourceGroundingError) as failure:
            c.audit_narration(story, lambda *args: {'passed': False, 'issues': ['Chapter 3: invented date']})
        self.assertEqual(failure.exception.issues, ['Chapter 3: invented date'])
        self.assertIn('invented date', str(failure.exception))
        self.assertNotIn('grounding_review', story)

    def test_figures_are_replaced_by_object_composition(self):
        topic=c.catalog()[0]
        for prompt in ['The Prophet teaching a crowd','A caliph and a scholar','An angel in the sky']:
            self.assertEqual(c.safe_visual(prompt,topic),topic['thumbnail_visual_story'])
        self.assertEqual(c.safe_visual('An empty stone courtyard',topic),'An empty stone courtyard')

    def test_every_topic_outline_schema_is_valid_and_chapters_are_independent(self):
        from jsonschema import Draft202012Validator
        for topic in c.catalog():
            with self.subTest(topic=topic['id']):
                schema = w.story_outline_schema(topic)
                Draft202012Validator.check_schema(schema)
                chapters = schema['properties']['scenes']['properties']
                self.assertEqual(len(chapters), 20)
                for chapter in chapters.values():
                    self.assertEqual(chapter['required'].count('claim_ids'), 1)
                    self.assertEqual(chapter['properties']['claim_ids']['items']['enum'],
                                     [claim['id'] for claim in topic['claims']])
                chapters['chapter_01']['required'].append('mutation-probe')
                chapters['chapter_01']['properties']['claim_ids']['items']['enum'].append('probe')
                self.assertNotIn('mutation-probe', chapters['chapter_02']['required'])
                self.assertNotIn('probe', chapters['chapter_02']['properties']['claim_ids']['items']['enum'])
                self.assertNotIn('probe', [claim['id'] for claim in topic['claims']])

    def test_generation_preserves_reference_outline_four_batches_then_package(self):
        topic=c.catalog()[0];calls=[]
        def request(endpoint,payload):
            from jsonschema import Draft202012Validator
            schema = payload['response_format']['json_schema']['schema']
            Draft202012Validator.check_schema(schema)
            props=schema['properties']
            prompt=payload['messages'][0]['content'];calls.append(prompt)
            if 'scenes' in props:
                value={'title':'Abbasid Samarra','protagonist_name':'','character_description':'Empty courtyard',
                    'scenes':{f'chapter_{i:02}':{'summary':'Surviving architecture','image_prompt':'Empty brick courtyard',
                        'claim_ids':['c1']} for i in range(1,21)}}
            elif 'narrations' in props:
                text=' '.join(['Evidence']*109)+ ' remains.'
                value={'narrations':{key:text for key in props['narrations']['properties']}}
            elif 'passed' in props:value={'passed':True,'issues':[]}
            else:raise AssertionError('Unexpected model stage')
            Draft202012Validator(schema).validate(value)
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}
        def package(story,topic,ask):
            story.update(description=c.source_notes(topic),tags=['Islamic history'],
                thumbnail_text='WHY THIS MINARET?',thumbnail_prompt=topic['thumbnail_visual_story'])
        with patch('islamic_content.catalog',return_value=[topic]),patch.object(w,'request_story',side_effect=request),patch('video_packaging.request_package',side_effect=package):
            story=w.make_story('2026-10-26',[])
        self.assertEqual(len(story['scenes']),20)
        self.assertEqual(sum('Return narrations with exact' in prompt for prompt in calls),4)
        self.assertFalse(story['fictional'])
        self.assertIn('source',story['description'].lower())
        self.assertTrue(story['scenes'][-1]['narration'].endswith(c.CTA))
        c.validate_content(story)
