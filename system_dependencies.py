"""Reuse hosted-runner tools; install only missing, required Ubuntu packages."""
import os
import shutil
import subprocess
import sys
import time

PACKAGES = {'ffmpeg', 'fonts-dejavu-core', 'espeak-ng'}


def probe(command):
    if not shutil.which(command[0]):
        return ''
    try:
        result = subprocess.run(command, check=True, capture_output=True,
                                text=True, timeout=15)
        return result.stdout + result.stderr
    except (OSError, subprocess.SubprocessError):
        return ''


def available(package):
    if package == 'ffmpeg':
        return bool(probe(['ffmpeg', '-version']) and probe(['ffprobe', '-version']))
    if package == 'fonts-dejavu-core':
        families = probe(['fc-match', '--format=%{family}', 'DejaVu Sans'])
        return 'dejavu sans' in {name.strip().lower() for name in families.split(',')}
    if package == 'espeak-ng':
        return bool(probe(['espeak-ng', '--version']))
    raise ValueError('Unsupported system package: ' + package)


def apt(arguments, seconds):
    # GNU timeout also terminates apt's download children. A Python-only timeout
    # could leave child processes holding the package manager lock on retry.
    subprocess.run(['sudo', 'timeout', '--kill-after=10s', f'{seconds}s',
        'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
        '-o', 'Acquire::Retries=2', '-o', 'Acquire::http::Timeout=20',
        '-o', 'Acquire::https::Timeout=20', *arguments],
        check=True, timeout=seconds + 30)


def install(packages):
    packages = list(dict.fromkeys(packages))
    if not packages or not set(packages) <= PACKAGES:
        raise ValueError('Request only ffmpeg, fonts-dejavu-core or espeak-ng')
    missing = [package for package in packages if not available(package)]
    if not missing:
        print('Required system tools already work; skipping package downloads.', flush=True)
        return
    print('Installing missing system packages: ' + ', '.join(missing), flush=True)
    for attempt in range(2):
        try:
            apt(['update'], 90)
            apt(['install', '--yes', '--no-install-recommends', *missing], 180)
            if not all(available(package) for package in packages):
                raise RuntimeError('Required system tools failed verification after installation')
            return
        except (OSError, subprocess.SubprocessError, RuntimeError):
            if attempt == 1:
                raise RuntimeError('System dependency setup failed after two bounded attempts; '
                                   'check Ubuntu mirror availability before generating media') from None
            print('System package download failed; retrying once.', flush=True)
            time.sleep(2)


if __name__ == '__main__':
    try:
        install(sys.argv[1:])
    except (ValueError, RuntimeError) as error:
        if os.getenv('GITHUB_ACTIONS') == 'true':
            print('::error title=System dependency setup failed::' + str(error), flush=True)
        else:
            print(str(error), file=sys.stderr)
        sys.exit(1)
