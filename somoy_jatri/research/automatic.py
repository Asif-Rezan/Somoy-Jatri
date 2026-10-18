"""Build a private-run research packet from a curated source list."""
import json
import re
from html import unescape
from pathlib import Path

import requests

from somoy_jatri.scripts.groq import Groq
from somoy_jatri.research.dossier import validate


def plain_text(html):
    html = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', html, flags=re.I | re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', unescape(html))).strip()


def choose(history, catalog=Path('docs/research/topics.json')):
    topics = json.loads(catalog.read_text(encoding='utf-8'))
    if not topics or len({t['id'] for t in topics}) != len(topics):
        raise ValueError('Topic catalog is empty or contains duplicate IDs')
    used = {item.get('topic_id') for item in history}
    available = [t for t in topics if t['id'] not in used]
    if not available:
        raise ValueError('Curated topics exhausted; add another sourced topic')
    return available[0]


def build(history):
    topic = choose(history)
    pages = []
    for index, url in enumerate(topic['sources'], 1):
        response = requests.get(url, timeout=30, headers={'User-Agent': 'SomoyJatri/0.1'})
        response.raise_for_status()
        text = plain_text(response.text)
        if len(text) < 500:
            raise ValueError('Source page has too little readable evidence: ' + url)
        pages.append({'id': f's{index}', 'url': url, 'text': text[:30000]})
    fields = ['politics', 'culture', 'clothing', 'buildings', 'tools', 'transportation',
              'food', 'trades', 'social_life', 'events']
    prompt = ('Create a cautious research packet for a PRIVATE AI historical reconstruction. '
              'Use ONLY the supplied source text. Do not infer undocumented details. For each '
              'context field use a sourced statement or "Unknown; reconstruct cautiously". '
              'Each fact must cite a source_id. Each source excerpt must be a SHORT EXACT '
              'contiguous quote from its supplied page. Return JSON with context fields, '
              'facts [{claim,source_id}], uncertain [strings], and sources '
              '[{id,title,url,excerpt}]. Include at least three distinct facts. '
              f'Location: {topic["location"]}. Period: {topic["period"]}. '
              f'Fields: {fields}. Source pages: {json.dumps(pages, ensure_ascii=False)}')
    packet = Groq().json(prompt)
    packet.update(location=topic['location'], period=topic['period'],
                  topic_id=topic['id'], research_method='automatic source extraction')
    if len(packet.get('facts', [])) < 3:
        raise ValueError('Automatic research returned too few facts')
    supplied = {p['id']: p for p in pages}
    if {s.get('id') for s in packet.get('sources', [])} != set(supplied):
        raise ValueError('Automatic research changed the source set')
    for source in packet['sources']:
        if source.get('url') != supplied[source['id']]['url']:
            raise ValueError('Automatic research changed a source URL')
        normalized = lambda t: re.sub(r'\s+', ' ', t).strip().casefold()
        if normalized(source.get('excerpt', '')) not in normalized(supplied[source['id']]['text']):
            raise ValueError('Automatic research supplied an unverified quote')
    # The source and excerpt checks run again immediately before generation.
    return validate(packet, live=True, require_review=False)
