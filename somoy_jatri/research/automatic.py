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
    used = {item.get('topic_id') for item in history[-10:]}
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
        pages.append({'id': f's{index}', 'url': url, 'text': text[:max(2000, 18000 // len(topic['sources']))]})
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


def enrich(dossier):
    """Append source-quoted facts without renumbering existing citations."""
    if len(dossier.get('facts',[]))>=8:return dossier
    pages=[]
    for source in dossier['sources']:
        response=requests.get(source['url'],timeout=30,headers={'User-Agent':'SomoyJatri/0.1'})
        response.raise_for_status()
        text=plain_text(response.text)
        start=text.find('Brief synthesis')
        if start>=0:text=text[start:]
        pages.append({'id':source['id'],'text':text[:max(2000, 18000 // len(dossier['sources']))]})
    result=Groq().json('Extract 12 distinct, atomic historical facts relevant to the supplied location '
        'and period. Use only the source text, excluding modern visitor information. Each claim must '
        'include a source_id and an exact source_quote of at least 20 characters copied from that source. '
        'Do not invent clothing, activities or dates absent from the source. Return {"facts": '
        '[{"claim":"...","source_id":"s1","source_quote":"exact quotation"}]}. '
        +json.dumps({'location':dossier['location'],'period':dossier['period'],'sources':pages},ensure_ascii=False))
    normalize=lambda text:re.sub(r'\s+',' ',text).strip().casefold()
    source_text={p['id']:normalize(p['text']) for p in pages}
    known={normalize(f['claim']) for f in dossier['facts']}
    added=0
    for fact in result.get('facts',[])[:16]:
        quote=fact.get('source_quote','');claim=fact.get('claim','');sid=fact.get('source_id')
        if (sid in source_text and len(quote)>=20 and normalize(quote) in source_text[sid]
                and claim.strip() and normalize(claim) not in known):
            dossier['facts'].append(fact);known.add(normalize(claim));added+=1
    print(json.dumps({'research_stage':'source_facts_enriched','added_facts':added,
                      'total_facts':len(dossier['facts'])}),flush=True)
    if len(dossier['facts'])<6:raise ValueError('Insufficient source-quoted research for the story')
    return dossier
