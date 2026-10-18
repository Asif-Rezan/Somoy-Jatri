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
    print(json.dumps({'research_stage': 'topic_selected', 'topic_id': topic['id']}), flush=True)
    pages = []
    for index, url in enumerate(topic['sources'], 1):
        response = requests.get(url, timeout=30, headers={'User-Agent': 'SomoyJatri/0.1'})
        response.raise_for_status()
        text = plain_text(response.text)
        if len(text) < 500:
            raise ValueError('Source page has too little readable evidence: ' + url)
        pages.append({'id': f's{index}', 'url': url, 'text': text[:30000]})
    print(json.dumps({'research_stage': 'sources_loaded', 'count': len(pages)}), flush=True)
    fields = ['politics', 'culture', 'clothing', 'buildings', 'tools', 'transportation',
              'food', 'trades', 'social_life', 'events']
    prompt = ('Create a cautious research packet for a PRIVATE AI historical reconstruction. '
              'Use ONLY the supplied source text. Do not infer undocumented details. For each '
              'context field use a sourced statement or "Unknown; reconstruct cautiously". '
              'Each fact must cite a source_id from the provided pages. Return a single JSON '
              'object with these exact top-level keys: politics, culture, clothing, buildings, '
              'tools, transportation, food, trades, social_life, events (all strings); facts '
              '(array of at least three {claim,source_id} objects); uncertain (array of strings). '
              'Do not return a sources key. Only state details directly supported by the pages. '
              f'Location: {topic["location"]}. Period: {topic["period"]}. '
              f'Fields: {fields}. Source pages: {json.dumps(pages, ensure_ascii=False)}')
    packet = Groq().json(prompt)
    print(json.dumps({'research_stage': 'model_returned'}), flush=True)
    if isinstance(packet.get('dossier'), dict):
        packet = packet['dossier']
    for field in fields:
        if not isinstance(packet.get(field), str) or not packet[field].strip():
            packet[field] = 'Unknown; reconstruct cautiously'
    if not packet.get('uncertain'):
        packet['uncertain'] = ['Details absent from the sources are artistic reconstruction.']
    packet['sources'] = []
    for page in pages:
        text = page['text']
        anchor = text.find('Brief synthesis')
        excerpt = text[anchor + len('Brief synthesis'):].strip()[:120] if anchor >= 0 else text[:120]
        packet['sources'].append({'id': page['id'], 'url': page['url'],
                                  'title': topic['location'] + ' — UNESCO World Heritage Centre',
                                  'excerpt': excerpt})
    packet.update(location=topic['location'], period=topic['period'],
                  topic_id=topic['id'], research_method='automatic source extraction')
    if len(packet.get('facts', [])) < 3:
        raise ValueError('Automatic research returned too few facts')
    if any(f.get('source_id') not in {p['id'] for p in pages} for f in packet['facts']):
        raise ValueError('Automatic research cited an unknown source')
    # The source and excerpt checks run again immediately before generation.
    result = validate(packet, live=True, require_review=False)
    print(json.dumps({'research_stage': 'packet_validated', 'facts': len(result['facts'])}), flush=True)
    return result
