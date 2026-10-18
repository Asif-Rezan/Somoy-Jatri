import os
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    mode: str = 'mock'
    run_id: str = 'preview'
    workers: int = 4
    captions: bool = True
    music: bool = True
    target: int = 720

    def __post_init__(self):
        if self.mode not in {'mock', 'production'}:
            raise ValueError('mode must be mock or production')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', self.run_id):
            raise ValueError('Unsafe run identifier')
        if not 1 <= self.workers <= 16:
            raise ValueError('Use 1–16 independent image workers')
        if self.mode == 'production' and not 600 <= self.target <= 900:
            raise ValueError('Production target must be 600–900 seconds')

    @property
    def root(self):
        return Path(os.getenv('OUTPUT_ROOT', 'output')) / self.run_id

    def preflight(self):
        if self.mode == 'production':
            for name in ('GROQ_API_KEY', 'RESEARCH_DOSSIER'):
                if not os.getenv(name):
                    raise ValueError(name + ' is required for production preparation')
            if os.getenv('TTS_BACKEND', 'indic-parler') != 'indic-parler':
                raise ValueError('Unverified production voice provider')
