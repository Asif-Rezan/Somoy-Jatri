import re
import unicodedata
from num2words import num2words

EMOTIONS = {'neutral', 'curious', 'excited', 'amazed', 'happy', 'concerned', 'reflective', 'soft', 'dramatic'}
PRONUNCIATION = {'BCE': 'খ্রিস্টপূর্ব', 'CE': 'খ্রিস্টাব্দ', 'Giza': 'গিজা', 'Pompeii': 'পম্পেই', 'Rome': 'রোম', 'Baghdad': 'বাগদাদ', 'Mohenjo-daro': 'মহেঞ্জোদারো'}

def normalize(text, dictionary=None):
    text = unicodedata.normalize('NFC', text)
    text = text.translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
    text = re.sub(r'(\d+)\s*BCE\b', r'খ্রিস্টপূর্ব \1', text)
    text = re.sub(r'(\d+)\s*CE\b', r'খ্রিস্টাব্দ \1', text)
    for key, value in {**PRONUNCIATION, **(dictionary or {})}.items():
        text = text.replace(key, value)
    text = re.sub(r'\d+', lambda m: num2words(int(m.group()), lang='bn'), text)
    return re.sub(r'\s+', ' ', text).strip()

def emotion(text):
    if '?' in text or 'কি ' in text: return 'curious'
    if '!' in text: return 'amazed'
    if 'ভাব' in text: return 'reflective'
    return 'neutral'

def validate_segment(s):
    if not re.search(r'[\u0980-\u09ff]', s['text']):
        raise ValueError('Narration must contain Bangla')
    if s.get('emotion') not in EMOTIONS or not 0 <= s.get('intensity', 0.5) <= 1:
        raise ValueError('Invalid emotional direction')
    if not 0 <= s.get('pause_after_ms', 250) <= 1500:
        raise ValueError('Pause outside natural bounds')
    # Short independent utterances avoid model truncation and permit event-level alignment.
    if len(s['text']) > 260:
        raise ValueError('Split long utterances into semantic events (<=260 characters)')
