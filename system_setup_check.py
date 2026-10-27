"""Live Linux smoke check, including deliberate primary-mirror failure."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import system_dependencies as deps


def check(force_failover=False):
    real_available, real_apt = deps.available, deps.apt
    inspected = set()
    failed_primary = False

    def require_install(package):
        # Exercise setup even if this particular runner already has every tool.
        if package not in inspected:
            inspected.add(package)
            return False
        return real_available(package)

    def apt(arguments, seconds, options=()):
        nonlocal failed_primary
        if force_failover and not failed_primary:
            # Reproduce the incident's package-download stall specifically.
            # Leave the real signed-repository update/download/install to fallback.
            if arguments == ['update']:
                return
            failed_primary = True
            raise subprocess.TimeoutExpired('simulated-primary-download', seconds)
        return real_apt(arguments, seconds, options)

    with patch.object(deps, 'available', side_effect=require_install), \
         patch.object(deps, 'apt', side_effect=apt):
        deps.install(['ffmpeg', 'fonts-dejavu-core', 'espeak-ng'])
    if force_failover and not failed_primary:
        raise RuntimeError('Failover branch was not exercised')
    with tempfile.TemporaryDirectory() as directory:
        captions = Path(directory)/'captions.srt'
        captions.write_text('1\n00:00:00,000 --> 00:00:01,000\nSetup check\n')
        clip = Path(directory)/'clip.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
            'color=c=black:s=320x180:d=1', '-vf', f'subtitles={captions}',
            '-c:v', 'libx264', str(clip)], check=True, timeout=30)
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams',
            '-of', 'json', str(clip)], capture_output=True, text=True, check=True, timeout=15)
        video = json.loads(result.stdout)['streams'][0]
        if (video['width'], video['height']) != (320, 180):
            raise RuntimeError('Actual captioned video encoding failed')
    audio = subprocess.run(['espeak-ng', '--stdout', 'Setup check'],
                           check=True, capture_output=True, timeout=15).stdout
    if not audio.startswith(b'RIFF') or len(audio) <= 44:
        raise RuntimeError('Speech dependency did not produce WAV audio')
    print(json.dumps({'check': 'Live system setup and captioned encoding',
                      'passed': True, 'forced_mirror_failover': force_failover}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force-failover', action='store_true')
    check(parser.parse_args().force_failover)
