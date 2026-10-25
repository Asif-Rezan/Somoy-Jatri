from difflib import SequenceMatcher
from somoy_jatri.utils import load, save


def reserve(path, topic, run, topic_id=None):
    history = load(path) if path.exists() else []
    for item in history:
        if item['run'] == run: return
    for item in history[-10:]:
        if SequenceMatcher(None, topic.casefold(), item['topic'].casefold()).ratio() > .82:
            raise ValueError('Similar topic already reserved; select another research dossier')
    history.append({'topic': topic, 'run': run, 'topic_id': topic_id})
    save(path, history)
