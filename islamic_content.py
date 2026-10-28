"""Sourced English Islamic documentaries; provenance checks are not scholarly grading."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

FORMAT = 'islamic-documentary'
CTA_MARKER = ' Which topic should Somoy Jatri explore next? '
CTA = CTA_MARKER + 'Leave a comment, like this video, and subscribe to Somoy Jatri for more Islamic history and hadith lessons.'
VISUAL_POLICY = ('Object and architecture only: empty courtyards, period buildings, landscapes, books and everyday objects. '
    'No people, portraits, prophets, companions, angels, divine figures, invented Arabic lettering or legible sacred text. '
    'An illustrative reconstruction is not evidence of a specific historical scene.')
CONTENT_POLICY = ('Write English educational documentary narration in the third person. Use ONLY the supplied claims. '
    'No fictional plot, first-person host, invented dialogue, dates, motives, miracles, quotations, Quran verses or hadith. '
    'Hadith meanings must be explicitly presented as paraphrases with the supplied collection and report reference. '
    'Never invent a chain of narration or assign a new authenticity grade. '
    'Distinguish sourced reports from modern reflection and explicitly hypothetical examples. '
    'Do not derive legal rulings, guarantee rewards for new practices, attack sects, or treat disputed history as certain. '
    'For history explain chronology and evidence; for hadith explain the supplied meaning without adding religious claims. '
    'When evidence is limited, explain its limits instead of padding it with invented facts.')


def catalog():
    topics = json.loads(Path(__file__).with_name('islamic_topics.json').read_text())
    for topic in topics:
        validate_topic(topic)
    return topics


def validate_topic(topic):
    if topic.get('kind') not in {'history', 'hadith'} or not topic.get('claims') or not topic.get('sources'):
        raise ValueError('Islamic topics require sourced claims and a content kind')
    records = {s['id']:s for s in topic.get('source_records', [])}
    if len(records) != len(topic.get('source_records', [])):
        raise ValueError('Duplicate source identifiers')
    for source in records.values():
        if urlparse(source['url']).scheme != 'https' or source['url'] not in topic['sources']:
            raise ValueError('Source requires a matching HTTPS reference')
    ids = [c['id'] for c in topic['claims']]
    if len(set(ids)) != len(ids) or any(not c['text'] or c['source_id'] not in records for c in topic['claims']):
        raise ValueError('Invalid sourced claim')
    if topic['kind'] == 'hadith' and not topic.get('hadith'):
        raise ValueError('Hadith topic requires collection and report references')
    for report in topic.get('hadith', []):
        if (report.get('source_id') not in records or not report.get('reference')
                or report.get('quotation_mode') != 'paraphrase_only'
                or report.get('classification') != 'Sahih collection'):
            raise ValueError('Hadith reference or paraphrase policy missing')
    return topic


def validate_narration(text):
    if re.search(r'[\u0600-\u06ff\u0980-\u09ff]',text):
        raise ValueError('Narration must be English')
    if '"' in text or re.search(r'\b(?:the prophet|allah|god) (?:said|says|promised)\b',text,re.I):
        raise ValueError('Use sourced paraphrases, not generated religious quotations')
    if re.search(r'\b(?:I am|I was|I saw|my journey|we arrived)\b',text,re.I):
        raise ValueError('First-person vlog narration is not permitted')


def validate_content(story):
    if story.get('format') != FORMAT or story.get('fictional') is not False:
        raise ValueError('A sourced Islamic documentary is required; old stories cannot be resumed')
    if len(story.get('scenes', [])) != 20:
        raise ValueError('Islamic documentaries require twenty chapters')
    topic = validate_topic(story.get('evidence', {}))
    if story.get('topic_id') != topic['id']:
        raise ValueError('Episode topic and source packet differ')
    ids = {c['id'] for c in topic['claims']}
    for scene in story['scenes']:
        if not scene.get('claim_ids') or not set(scene['claim_ids']) <= ids:
            raise ValueError('Every chapter must cite valid supplied claim IDs')
        validate_narration(scene['narration'])
    return story


def source_notes(topic):
    validate_topic(topic)
    rows = [f"{s['title']}: {s['url']}" for s in topic['source_records']]
    return ('Sources and report references:\n'+'\n'.join(rows)+'\n\n'
        'Hadith meanings are English paraphrases, not verbatim translations or new authenticity assessments. '
        'Visual reconstructions are illustrative. '
        'Educational discussion, not a personal religious ruling.')


def safe_visual(action, topic, fallback=None):
    # Broad exclusions intentionally prefer an object illustration over a sacred figure reenactment.
    if re.search(r'\b(?:people|person|human|men|women|children|man|woman|child|faces?|portraits?|prophets?|muhammad|companions?|angels?|allah|god|scholars?|crowd|travelers?|merchants?|workers?|rulers?|caliphs?|figures?|silhouettes?)\b',action,re.I):
        action = safe_visual(fallback,topic) if fallback else topic['thumbnail_visual_story']
    return action


class SourceGroundingError(ValueError):
    """Review feedback that can be used for a bounded, re-audited repair."""
    def __init__(self, issues):
        self.issues = issues
        super().__init__('Source-grounding review rejected narration; no media will be generated: '
                         + json.dumps(issues, ensure_ascii=True))


def audit_narration(story, ask):
    story.pop('grounding_review', None)
    schema = {'type':'object','properties':{'passed':{'type':'boolean'},
        'issues':{'type':'array','items':{'type':'string'}}},'required':['passed','issues'],'additionalProperties':False}
    result = ask('Check every sentence of this English Islamic documentary against ONLY its supplied evidence. '
        'Reject invented historical or religious assertions, quotations, narrator chains, authenticity grades, '
        'unlabelled hypothetical examples, certainty beyond the sources, and fatwas. '
        'Reflections are allowed only when explicitly distinguished from a reported teaching. '
        'Identify the chapter number and specific unsupported assertion in each issue. '
        'The closing viewer question and like/comment/subscribe request are channel engagement, not historical claims. '
        'Return passed=true only when all narration is supported or clearly labelled reflection. '
        + json.dumps({'evidence':story['evidence'],'chapters':[
            {'narration':s['narration'],'claim_ids':s['claim_ids']} for s in story['scenes']]}),1600,schema)
    if result.get('passed') is not True or result.get('issues'):
        raise SourceGroundingError(result.get('issues') or ['Review did not explicitly pass'])
    story['grounding_review'] = {'passed':True,'method':'same-model-evidence-review',
        'not_independent_scholarly_verification':True}


def select_topic(topics, previous, day):
    """Prefer least recently used subjects, then avoid the last two content pillars."""
    import datetime
    history = [item for item in previous if isinstance(item, dict)]
    last_seen = {item.get('topic_id'): index for index, item in enumerate(history)}
    recent = {item.get('topic_id') for item in history[-10:]}
    available = [topic for topic in topics if topic['id'] not in recent]
    if not available:
        oldest = min(last_seen.get(topic['id'], -1) for topic in topics)
        available = [topic for topic in topics if last_seen.get(topic['id'], -1) == oldest]
    by_id = {topic['id']: topic for topic in topics}
    pillars = {by_id.get(item.get('topic_id'), {}).get('content_pillar') for item in history[-2:]}
    varied = [topic for topic in available if topic.get('content_pillar') not in pillars]
    pool = varied or available
    return pool[datetime.date.fromisoformat(day).toordinal() % len(pool)]
