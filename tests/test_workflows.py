from pathlib import Path
import yaml

def test_workflow_structure():
    for path in Path('.github/workflows').glob('*.yml'):
        doc=yaml.safe_load(path.read_text())
        assert 'jobs' in doc and doc.get('permissions',{}).get('contents')=='read'
        text=path.read_text()
        assert 'youtube-dark-psychology-automation' not in text
        assert not any(line.lstrip().startswith('schedule:') for line in text.splitlines()) # scheduling requires documented explicit enablement
