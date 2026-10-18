from urllib.parse import urlparse
import requests

FIELDS = ('period', 'location', 'politics', 'culture', 'clothing', 'buildings', 'tools',
          'transportation', 'food', 'trades', 'social_life', 'events', 'facts', 'uncertain', 'sources')

def validate(dossier, live=False, require_review=True):
    if any(not dossier.get(f) for f in FIELDS): raise ValueError('Incomplete research dossier')
    sources = {s['id']: s for s in dossier['sources']}
    if len(sources) != len(dossier['sources']): raise ValueError('Duplicate source ID')
    for s in sources.values():
        if urlparse(s['url']).scheme != 'https' or not s.get('excerpt') or not s.get('title'):
            raise ValueError('Source URL, title and evidence excerpt required')
        if live:
            response = requests.get(s['url'], timeout=30, headers={'User-Agent': 'SomoyJatri/0.1'})
            response.raise_for_status()
            # A reachable page is not proof of a claim: human-reviewed evidence is also required.
            from html import unescape
            import re
            html = unescape(response.text)
            html = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', html, flags=re.I | re.S)
            page = re.sub(r'<[^>]+>', ' ', html)
            plain = lambda t: re.sub(r'\s+', ' ', t).strip().casefold()
            if plain(s['excerpt']) not in plain(page):
                raise ValueError('Source evidence excerpt not found on current page')
    if any(f.get('source_id') not in sources for f in dossier['facts']):
        raise ValueError('Unsourced documented fact')
    if live and require_review and not dossier.get('reviewed_by'):
        raise ValueError('Production requires source-backed dossier reviewed by a person')
    return dossier
