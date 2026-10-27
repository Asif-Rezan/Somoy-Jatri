"""Reuse hosted-runner tools; install only missing, required Ubuntu packages."""
from contextlib import contextmanager, nullcontext
import os
import platform
from pathlib import Path
import re
import tempfile
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


@contextmanager
def alternate_sources():
    """Use signed official repositories without editing the runner's sources."""
    codename = platform.freedesktop_os_release().get('VERSION_CODENAME', '')
    if not re.fullmatch(r'[a-z]+', codename):
        raise RuntimeError('Cannot determine Ubuntu release for mirror failover')
    with tempfile.TemporaryDirectory(prefix='somoy-apt-') as directory:
        source = Path(directory)/'sources.list'
        key = '[signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg]'
        source.write_text('\n'.join([
            f'deb {key} https://archive.ubuntu.com/ubuntu {codename} main restricted universe multiverse',
            f'deb {key} https://archive.ubuntu.com/ubuntu {codename}-updates main restricted universe multiverse',
            f'deb {key} https://security.ubuntu.com/ubuntu {codename}-security main restricted universe multiverse',
        ]) + '\n')
        yield ['-o', f'Dir::Etc::sourcelist={source}',
               '-o', 'Dir::Etc::sourceparts=-', '-o', 'APT::Get::List-Cleanup=0']


def apt(arguments, seconds, source_options=()):
    # GNU timeout also terminates apt's download children. A Python-only timeout
    # could leave child processes holding the package manager lock on retry.
    subprocess.run(['sudo', 'timeout', '--kill-after=10s', f'{seconds}s',
        'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
        '-o', 'Acquire::Retries=2', '-o', 'Acquire::http::Timeout=20',
        '-o', 'Acquire::https::Timeout=20', '-o', 'APT::Update::Error-Mode=any',
        *source_options, *arguments],
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
            source = nullcontext([]) if attempt == 0 else alternate_sources()
            with source as options:
                apt(['update'], 60, options)
                # Time limits affect downloads, not half-installed packages.
                # Keep downloaded archives so failover resumes remaining work.
                apt(['install', '--download-only', '--yes', '--no-install-recommends', *missing],
                    120 if attempt == 0 else 240, options)
                apt(['install', '--no-download', '--yes', '--no-install-recommends', *missing],
                    120, options)
            if not all(available(package) for package in packages):
                raise RuntimeError('Required system tools failed verification after installation')
            return
        except (OSError, subprocess.SubprocessError, RuntimeError):
            if attempt == 1:
                raise RuntimeError('System dependency setup failed on both runner and official Ubuntu mirrors; '
                                   'no media was generated on this runner') from None
            print('Runner mirror failed or stalled; switching to signed official Ubuntu repositories.', flush=True)
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
