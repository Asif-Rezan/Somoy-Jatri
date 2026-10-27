"""Regression coverage for the package-download timeout in daily validation."""
import subprocess
import unittest
from unittest.mock import Mock, patch

import system_dependencies as deps


class SystemDependencyTests(unittest.TestCase):
    def setUp(self):
        release = patch.object(deps.platform, 'freedesktop_os_release',
                               return_value={'VERSION_CODENAME': 'noble'})
        release.start()
        self.addCleanup(release.stop)

    def test_working_runner_never_contacts_package_mirror(self):
        with patch.object(deps, 'available', return_value=True), patch.object(deps, 'apt') as apt:
            deps.install(['ffmpeg', 'fonts-dejavu-core'])
        apt.assert_not_called()

    def test_narration_installs_only_missing_speech_tool_without_optional_packages(self):
        installed = {'ffmpeg', 'fonts-dejavu-core'}
        def apt(arguments, seconds, options=()):
            if '--no-download' in arguments:
                installed.add('espeak-ng')
        with patch.object(deps, 'available', side_effect=lambda package: package in installed), \
             patch.object(deps, 'apt', side_effect=apt) as run:
            deps.install(['ffmpeg', 'fonts-dejavu-core', 'espeak-ng'])
        self.assertEqual(run.call_args_list[1].args,
            (['install', '--download-only', '--yes', '--no-install-recommends', 'espeak-ng'], 120, []))
        self.assertIn('--no-download', run.call_args_list[2].args[0])

    def test_slow_mirror_retries_then_recovers(self):
        installed = set()
        def apt(arguments, seconds, options=()):
            if '--no-download' in arguments:
                installed.add('ffmpeg')
        calls = [subprocess.CalledProcessError(124, 'timeout'), None, None, None]
        def flaky(arguments, seconds, options=()):
            error = calls.pop(0)
            if error:
                raise error
            apt(arguments, seconds, options)
        with patch.object(deps, 'available', side_effect=lambda package: package in installed), \
             patch.object(deps, 'apt', side_effect=flaky) as run, patch.object(deps.time, 'sleep'):
            deps.install(['ffmpeg'])
        self.assertEqual(run.call_count, 4)
        self.assertEqual(run.call_args_list[0].args[2], [])
        self.assertIn('Dir::Etc::sourceparts=-', run.call_args_list[1].args[2])

    def test_permanent_mirror_outage_has_bounded_failure(self):
        with patch.object(deps, 'available', return_value=False), \
             patch.object(deps, 'apt', side_effect=subprocess.TimeoutExpired('apt', 90)) as run, \
             patch.object(deps.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'both runner and official Ubuntu mirrors'):
                deps.install(['ffmpeg'])
        self.assertEqual(run.call_count, 2)

    def test_successful_install_must_pass_tool_verification(self):
        with patch.object(deps, 'available', return_value=False), \
             patch.object(deps, 'apt') as run, patch.object(deps.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'both runner and official Ubuntu mirrors'):
                deps.install(['ffmpeg'])
        self.assertEqual(run.call_count, 6)

    def test_apt_timeout_covers_children_and_disables_recommended_packages(self):
        with patch.object(deps.subprocess, 'run') as run:
            deps.apt(['install', '--yes', '--no-install-recommends', 'espeak-ng'], 180)
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ['sudo', 'timeout', '--kill-after=10s', '180s'])
        self.assertIn('DEBIAN_FRONTEND=noninteractive', command)
        self.assertEqual(run.call_args.kwargs['timeout'], 210)
        self.assertTrue(run.call_args.kwargs['check'])

    def test_ffmpeg_requires_both_encoder_and_probe(self):
        with patch.object(deps, 'probe', side_effect=['ffmpeg version', '']):
            self.assertFalse(deps.available('ffmpeg'))

    def test_font_fallback_is_not_mistaken_for_required_font(self):
        with patch.object(deps, 'probe', return_value='Liberation Sans'):
            self.assertFalse(deps.available('fonts-dejavu-core'))
        with patch.object(deps, 'probe', return_value='DejaVu Sans'):
            self.assertTrue(deps.available('fonts-dejavu-core'))

    def test_unknown_package_rejected_before_commands_run(self):
        with patch.object(deps, 'apt') as apt:
            with self.assertRaises(ValueError):
                deps.install(['unexpected-package'])
        apt.assert_not_called()

    def test_fallback_keeps_signature_verification_and_isolates_sources(self):
        from pathlib import Path
        with deps.alternate_sources() as options:
            filename = options[1].split('=', 1)[1]
            content = Path(filename).read_text()
            self.assertIn('https://archive.ubuntu.com/ubuntu noble', content)
            self.assertIn('https://security.ubuntu.com/ubuntu noble-security', content)
            self.assertIn('signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg', content)
            self.assertNotIn('trusted=yes', content)
            self.assertIn('Dir::Etc::sourceparts=-', options)
        self.assertFalse(Path(filename).exists())

    def test_bad_release_cannot_be_used_as_source_configuration(self):
        with patch.object(deps.platform, 'freedesktop_os_release',
                          return_value={'VERSION_CODENAME': 'noble injected'}):
            with self.assertRaisesRegex(RuntimeError, 'Ubuntu release'):
                with deps.alternate_sources():
                    self.fail('Invalid release accepted')

    def test_download_stall_switches_sources_before_installing_any_package(self):
        installed = False
        calls = []
        def apt(arguments, seconds, options=()):
            nonlocal installed
            calls.append((arguments, options))
            if '--download-only' in arguments and not options:
                raise subprocess.TimeoutExpired('primary-download', seconds)
            if '--no-download' in arguments:
                installed = True
        with patch.object(deps, 'available', side_effect=lambda _: installed), \
             patch.object(deps, 'apt', side_effect=apt), patch.object(deps.time, 'sleep'):
            deps.install(['ffmpeg'])
        installs = [(arguments, options) for arguments, options in calls if '--no-download' in arguments]
        self.assertEqual(len(installs), 1)
        self.assertIn('Dir::Etc::sourceparts=-', installs[0][1])
        self.assertEqual(len([arguments for arguments, _ in calls if '--download-only' in arguments]), 2)
