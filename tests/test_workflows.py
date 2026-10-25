from pathlib import Path
import yaml
from packaging.requirements import Requirement


def test_linux_narration_dependencies_use_matching_cpu_wheels():
    requirements = [Requirement(line) for line in Path('requirements-tts.txt').read_text().splitlines()
                    if line.startswith(('torch==', 'torchaudio=='))]
    linux = {req.name: str(req.specifier) for req in requirements
             if req.marker.evaluate({'sys_platform': 'linux'})}
    assert linux == {'torch': '==2.7.1+cpu', 'torchaudio': '==2.7.1+cpu'}
    assert '--extra-index-url https://download.pytorch.org/whl/cpu' in Path('requirements-tts.txt').read_text()

def test_workflow_structure():
    for path in Path('.github/workflows').glob('*.yml'):
        doc=yaml.safe_load(path.read_text())
        assert 'jobs' in doc and doc.get('permissions',{}).get('contents')=='read'
        text=path.read_text()
        assert 'youtube-dark-psychology-automation' not in text
        if path.name != 'daily.yml':
            assert not any(line.lstrip().startswith('schedule:') for line in text.splitlines())
