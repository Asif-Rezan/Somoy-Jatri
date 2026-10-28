"""Story-aware YouTube packaging for sourced Islamic documentary."""
import json
import re
import time
from thumbnail_design import hook_layout

CLICKBAIT = re.compile(r'\b(?:shocking|unbelievable|exposed|proof|finally revealed|they hid|you won.t believe)\b', re.I)
VAGUE_HOOK = re.compile(r'^(?:WHAT HAPPENED|THE HIDDEN TRUTH|WHAT IS THIS|WHAT\'S INSIDE)\?$', re.I)
PRODUCTION_DETAILS = re.compile(r'\b(?:music\s*rnn|magenta|kokoro|qwen|whisper|ffmpeg|hugging\s*face|text.to.speech|AI.generated|AI.assisted|generated (?:music|audio|images|narration)|synthesized|production pipeline)\b', re.I)
QUESTION_OPENERS = {'HOW', 'WHY', 'WHAT', 'WHO', 'WHERE'}
# Enforce the mechanical question format during local Qwen decoding, not just
# after spending several minutes generating each complete package.
def hook_pattern():
    # llama.cpp selects `pattern` before `maxLength`, rather than intersecting
    # them. Bound the grammar itself to 30 characters, including spaces and ?.
    def word(limit):
        return r" [A-Z][A-Z0-9'-]{0," + str(limit - 1) + "}"
    endings = [word(12), word(11) * 2, word(7) * 3]
    # Five-word questions may have one longer subject word, e.g. BEHIND.
    endings += [''.join(word(8 if i == long else 4) for i in range(4))
                for long in range(4)]
    return r"^(HOW|WHY|WHAT|WHO|WHERE)(" + '|'.join(endings) + r")\?$"


HOOK_SCHEMA = {'type': 'string', 'maxLength': 30, 'pattern': hook_pattern()}



def _plain(value):
    return re.sub(r'\s+', ' ', value).strip()


def artwork_candidate(prompt, topic):
    """Use the curated composition when generated artwork misses mechanical limits.

    Never truncate a scene or append an anchor to unrelated generated content.
    The replacement still passes every visual validation below.
    """
    anchor = topic['thumbnail_anchor']
    if 25 <= len(prompt) <= 220 and anchor.casefold() in prompt.casefold():
        return prompt
    curated = _plain(topic['thumbnail_visual_story'])
    return curated if anchor.casefold() in curated.casefold() else f'{anchor}. {curated}'


def thumbnail_generation_prompt(visual_story, text):
    """Ask diffusion for the complete thumbnail, including its exact typography."""
    return (f'YouTube thumbnail, bold readable text "{text}" on the left, '
            f'{visual_story.strip().rstrip(".")}. '
            'One large focal subject, dramatic plausible lighting, strong contrast, '
            'uncluttered 16:9 composition. Exact English lettering, large bold type, '
            'phone readable, safe margins. No additional words, logos or people.')


def description_parts(payload, topic):
    """Repair mechanical description failures using only the curated topic facts."""
    keyword = topic['search_phrase']
    intro = _plain(payload.get('description_intro', ''))
    details = _plain(payload.get('description_details', ''))
    # Sensational claims must be rejected, even if another constraint also fails.
    if CLICKBAIT.search(intro) or CLICKBAIT.search(details):
        raise ValueError('Description contains prohibited clickbait')
    if (PRODUCTION_DETAILS.search(intro) or not 80 <= len(intro) <= 400 or keyword.casefold() not in
            re.split(r'(?<=[.!?])\s', intro, maxsplit=1)[0].casefold()):
        intro = (f'{keyword}: a sourced English documentary exploring evidence and meaning, '
                 'historical context and careful reflection from Somoy Jatri.')
    if PRODUCTION_DETAILS.search(details) or not 80 <= len(details) <= 800:
        facts = [_plain(fact) for fact in topic.get('facts', []) if _plain(fact)]
        if not facts:
            raise ValueError('Description fallback requires curated story seeds')
        details = ' '.join(facts) + ' This episode distinguishes documented evidence from illustration and reflection.'
    if (not 80 <= len(intro) <= 400 or not 80 <= len(details) <= 800
            or CLICKBAIT.search(intro) or CLICKBAIT.search(details)):
        raise ValueError('Curated description exceeds metadata constraints')
    if not intro.endswith(('.', '?', '!')):
        intro += '.'
    return intro, details


def choose_package(story, topic, payload):
    """Use a concise, accurate title and matching thumbnail hook; retain alternatives for review."""
    keyword = topic['search_phrase']
    candidates = [payload.get(key, {}) for key in ('option_a', 'option_b', 'option_c')]
    valid = []
    rejected = []
    for name, option in zip(('option_a', 'option_b', 'option_c'), candidates):
        title = _plain(option.get('title', ''))
        text = _plain(option.get('thumbnail_text', ''))
        prompt = artwork_candidate(_plain(option.get('thumbnail_prompt', '')), topic)
        if not 35 <= len(title) <= 75 or keyword.casefold() not in title[:52].casefold():
            rejected.append(f'{name}: title must be 35-75 characters and contain the exact subject within its first 52 characters')
            continue
        if 'somoy' in text.casefold() or 'jatri' in text.casefold():
            rejected.append(f'{name}: thumbnail text must not include channel branding')
            continue
        if CLICKBAIT.search(title) or CLICKBAIT.search(text):
            rejected.append(f'{name}: title or thumbnail question uses prohibited clickbait')
            continue
        hook_words = text.rstrip('?').split()
        if (not text.endswith('?') or not 2 <= len(hook_words) <= 5 or len(text) > 30
                or hook_words[0].upper() not in QUESTION_OPENERS or VAGUE_HOOK.fullmatch(text)):
            rejected.append(f'{name}: thumbnail needs a specific 2-5 word question, max 30 characters, ending ?, starting HOW/WHY/WHAT/WHO/WHERE')
            continue
        try:
            hook_layout(text)
        except ValueError:
            rejected.append(f'{name}: thumbnail question cannot fit at readable size')
            continue
        if not 25 <= len(prompt) <= 220 or topic['thumbnail_anchor'].casefold() not in prompt.casefold():
            rejected.append(f'{name}: artwork prompt must be 25-220 characters and contain the exact anchor phrase')
            continue
        if any(re.search(r'\b'+re.escape(term)+r'\b', prompt, re.I)
               for term in topic.get('thumbnail_forbidden_terms', [])):
            rejected.append(f'{name}: artwork prompt contains a forbidden visual element, even if phrased as a negative instruction')
            continue
        if text.casefold() in title.casefold():
            rejected.append(f'{name}: thumbnail question repeats the title')
            continue
        score = 5 if title.casefold().startswith(keyword.casefold()) else 0
        score += 2 if 45 <= len(title) <= 65 else 0
        score += 1 if '?' in title else 0
        score += 2 if len(hook_words) <= 4 else 0
        score += 1 if any(word in text.casefold() for word in topic['thumbnail_anchor'].casefold().split()) else 0
        visual_story = topic['thumbnail_visual_story'].strip().rstrip('.')
        # Keep exact lettering and the curated visual anchor ahead of style instructions.
        artwork_prompt = thumbnail_generation_prompt(visual_story, text)
        valid.append((score, {'title': title, 'thumbnail_text': text, 'thumbnail_prompt': artwork_prompt}))
    if not valid:
        raise ValueError('No accurate, readable YouTube title and thumbnail pair: ' + '; '.join(rejected))
    valid.sort(key=lambda pair: pair[0], reverse=True)
    best = valid[0][1]
    intro, details = description_parts(payload, topic)
    relevant_text = ' '.join([keyword, topic['category']] + topic.get('facts', []))
    relevant_stems = {word[:5] for word in re.findall(r'[a-z]{5,}', relevant_text.casefold())
                      if word not in {'history', 'ancient', 'historical', 'documentary', 'archaeology'}}
    base_tags = [keyword, topic['category'], 'Islamic history' if topic.get('kind') == 'history' else 'hadith explained', 'Islamic documentary', 'Somoy Jatri']
    if 'archaeolog' in topic['category'].casefold() or 'ancient structure' in topic['category'].casefold():
        base_tags.append('archaeology')
    tags = []
    for tag in base_tags + payload.get('tags', []):
        tag = _plain(tag)
        if tag not in base_tags and not any(word[:5] in relevant_stems for word in
                                            re.findall(r'[a-z]{5,}', tag.casefold())):
            continue
        if tag and tag.casefold() not in [item.casefold() for item in tags] and len(tag) <= 40:
            tags.append(tag)
    tags = tags[:12]
    if len(','.join(tags)) > 400:
        raise ValueError('Video tags exceed YouTube metadata budget')
    from islamic_content import source_notes
    if topic.get('source_records'):
        notes = source_notes(topic)
    else:
        notes = 'Sources: ' + ' '.join(topic.get('sources', []))
    description = f'{intro}\n\n{details}\n\nExplore Islamic history and hadith with Somoy Jatri. Subscribe for more sourced documentaries.\n\n{notes}'
    if len(description) > 4500:
        raise ValueError('Video description exceeds upload budget')
    story.update(best, description=description, tags=tags, search_phrase=keyword,
                 packaging_alternatives=[item[1] for item in valid[1:]])
    return story


def request_package(story, topic, ask, pause=None):
    pause = pause or time.sleep
    text = {'type': 'string', 'maxLength': 220}
    option = {'type': 'object', 'properties': {
              'title': {'type': 'string', 'minLength': 35, 'maxLength': 75},
              'thumbnail_text': HOOK_SCHEMA, 'thumbnail_prompt': text},
              'required': ['title', 'thumbnail_text', 'thumbnail_prompt'], 'additionalProperties': False}
    schema = {'type': 'object', 'properties': {
        'option_a': option, 'option_b': option, 'option_c': option,
        'description_intro': {'type': 'string', 'maxLength': 400},
        'description_details': {'type': 'string', 'maxLength': 800},
        'tags': {'type': 'array', 'minItems': 4, 'maxItems': 8,
                 'items': {'type': 'string', 'maxLength': 40}}},
        'required': ['option_a', 'option_b', 'option_c', 'description_intro', 'description_details', 'tags'],
        'additionalProperties': False}
    outline = [scene.get('summary', '') for scene in story['scenes']]
    prompt = f'''Create YouTube packaging for an English sourced Islamic documentary story.
Search subject phrase: {topic['search_phrase']}
Category: {topic['category']}
No people, prophets, companions, angels or divine figures in any visual.
No unsupported historical or religious promises; use only supplied claims.
Sourced claims: {json.dumps(topic['facts'])}
Episode outline: {json.dumps(outline)}
Existing title: {story['title']}
Return three DISTINCT title-thumbnail pairs (option_a, option_b, option_c).
Make the three angles distinct: historical significance, a concrete question, and a clear learning benefit.
Prefer concise titles of 45-65 characters; avoid branding or repeated keywords.
Each title: 35-75 characters, put the exact search subject phrase in the first 52 characters,
accurately describe the documented subject and its significance, use normal capitalization.
Avoid generic "mystery revealed" wording, sensational certainty, false true-story claims and misleading clickbait.
Prefer 2-4 words on the thumbnail. Use one large subject on the right, strong separation
from an uncluttered background and bold integrated typography on the left. Choose a palette suited to the subject;
no collages, fake sacred text, arrows or invented dramatic events.
Thumbnail text: a SPECIFIC unresolved question with a curiosity gap, 2-5 short words,
maximum 30 characters, ending in ?. Use UPPERCASE words with single spaces.
Start with HOW, WHY, WHAT, WHO or WHERE. Each following word is at most 12 characters.
The question must be addressed in this episode. Avoid vague
questions such as WHAT HAPPENED? or promises of secret religious knowledge.
Create a concrete curiosity gap: the title identifies the subject and the hook raises one
specific unanswered question about a visible detail, documented change or historical consequence.
Reveal enough context to make the question meaningful, but leave its answer for the video.
The script must actually answer it; never imply suppressed evidence or secret religious knowledge.
Complement the title without repeating its phrasing. It must be legible on a phone.
Do not include SOMOY JATRI, channel names, logos or branding anywhere in the thumbnail.
Use the entire text area for the curiosity hook.
Thumbnail's illustrative visual anchor: {topic['thumbnail_anchor']}.
The image must tell this illustrative visual story: {topic['thumbnail_visual_story']}.
Do not mention or depict these elements in thumbnail artwork: {json.dumps(topic.get('thumbnail_forbidden_terms', []))}.
Omit forbidden words entirely, including negative phrases such as "no gore"; the renderer handles exclusions.
Thumbnail prompt: 25-220 characters, include the exact visual-anchor phrase, and add
a specific scene composition that builds on the visual story. Make the historical artifact, architectural detail,
landscape or object relationship the source of curiosity even with no words visible.
Place the intriguing detail on the RIGHT and leave dark space on the LEFT for the question.
Use dramatic but plausible light and depth. The image generator will render the exact thumbnail_text as integrated lettering. No extra labels, arrows, logos,
graphic gore or sexual imagery.
Description intro: 80-400 characters, put the exact subject phrase naturally in the FIRST sentence
and introduce the sourced subject clearly. Description details: 80-800 characters, unique to this episode,
describe the evidence and its limits. Never invent hadith, quotations, dates or claims. No legal rulings.
Descriptions must discuss only the subject and viewer learning value, with a specific opening
that answers search intent. No internal tool names, AI generation, production methods or music credits.
Tags: 4-8 concise specific search variants, including sensible spelling variants if useful;
no unrelated trend tags, hashtags, or keyword stuffing. Return only the requested JSON.'''
    feedback = ''
    for attempt in range(3):
        if attempt:
            pause(1)  # Local CPU inference has no hosted-provider rate limit.
        result = ask(prompt + feedback, 2600, schema)
        try:
            return choose_package(story, topic, result)
        except ValueError as error:
            print(json.dumps({'check': 'Islamic packaging', 'attempt': attempt+1,
                              'passed': False, 'reason': str(error)}), flush=True)
            if attempt == 2:
                raise
            feedback = ('\nYour previous response failed validation: ' + str(error) +
                        '\nPrevious metadata: ' + json.dumps(result) +
                        '\nCorrect these issues. Return the complete requested JSON; '
                        'keep metadata faithful to the source evidence and do not invent historical or religious claims.')
