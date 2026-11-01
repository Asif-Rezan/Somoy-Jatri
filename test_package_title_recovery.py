"""Prevent the production title failure and cached semantic-retry loop."""
import copy
import json
from pathlib import Path
import re
import unittest
from jsonschema import Draft202012Validator
from video_packaging import title_schema, repair_title_format, request_package
import test_packaging as fixtures


class TitleRecoveryTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.PackagingTests()
        fixture.setUp()
        self.topic=fixture.topic
        self.payload=fixture.payload
        self.story=fixture.story

    def test_all_three_missing_subject_titles_recover_without_rewriting_script(self):
        for key in ('option_a','option_b','option_c'):
            self.payload[key]['title']='An interesting story about old stonework'
        before=copy.deepcopy(self.story['scenes'])
        calls=[]
        def ask(*args):
            calls.append(args)
            return self.payload
        result=request_package(self.story,self.topic,ask,
            pause=lambda _:self.fail('Mechanical title repair must not regenerate the package'))
        self.assertEqual(len(calls),1)
        self.assertTrue(result['title'].startswith(self.topic['search_phrase']+': '))
        self.assertTrue(35<=len(result['title'])<=75)
        self.assertEqual(result['scenes'],before)
        self.assertEqual(self.payload['option_a']['title'],'An interesting story about old stonework')

    def test_decoder_pattern_alone_enforces_subject_and_length_for_every_topic(self):
        for topic in json.loads(Path('islamic_topics.json').read_text()):
            keyword=topic['search_phrase']
            schema=title_schema(keyword)
            prefix=keyword+': '
            valid=prefix+'Evidence and historical context'
            self.assertTrue(Draft202012Validator(schema).is_valid(valid),keyword)
            self.assertIsNotNone(re.fullmatch(schema['pattern'],valid))
            for bad in ('A title without the correct subject at all',prefix+'x',prefix+'x'*80):
                self.assertIsNone(re.fullmatch(schema['pattern'],bad),bad)
            payload=copy.deepcopy(self.payload)
            for key in ('option_a','option_b','option_c'):
                payload[key]['title']='Too short'
            recovered=repair_title_format(payload,topic)
            for key in ('option_a','option_b','option_c'):
                self.assertTrue(Draft202012Validator(schema).is_valid(recovered[key]['title']))

    def test_repeated_invalid_metadata_uses_three_distinct_cache_keys(self):
        self.payload['description_intro']='Shocking proof exposed'
        cache={}
        def ask(prompt,*args):
            cache.setdefault(prompt,copy.deepcopy(self.payload))
            return cache[prompt]
        before=copy.deepcopy(self.story)
        with self.assertRaisesRegex(ValueError,'prohibited clickbait'):
            request_package(self.story,self.topic,ask,pause=lambda _:None)
        self.assertEqual(len(cache),3)
        self.assertEqual(self.story,before)

    def test_unsafe_titles_are_not_silently_repaired(self):
        for key in ('option_a','option_b','option_c'):
            self.payload[key]['title']='Shocking truth exposed'
        recovered=repair_title_format(self.payload,self.topic)
        self.assertEqual(recovered,self.payload)
        with self.assertRaises(ValueError):
            request_package(self.story,self.topic,lambda *args:self.payload,pause=lambda _:None)
