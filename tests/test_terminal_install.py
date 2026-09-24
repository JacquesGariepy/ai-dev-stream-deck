"""Install the terminal loader only into isolated fake profile/runtime folders."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'agentdeck/install-terminal.ps1'
SHELLS = list(dict.fromkeys(filter(None, (shutil.which('powershell'), shutil.which('pwsh')))))


@unittest.skipUnless(os.name == 'nt' and SHELLS, 'Windows terminal installer integration')
class TerminalInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='AgentDeck terminal installer ')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_ps(self, shell, script, *arguments, env=None):
        return subprocess.run([shell, '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                               '-File', str(script), *map(str, arguments)], capture_output=True,
                              text=True, timeout=25, env=env)

    def fixture(self, name):
        location = self.root / name
        runtime = location / "runtime 'quoted' & $literal"
        runtime.mkdir(parents=True)
        profile = location / "profile 'quoted' & $literal" / 'profile.ps1'
        profile.parent.mkdir()
        (runtime / 'terminal.ps1').write_text('''$script:FixtureRuntimeRoot = $PSScriptRoot
function Invoke-AIDevGit {
    param($Action)
    [pscustomobject]@{action=$Action; runtime=$script:FixtureRuntimeRoot}
}
function PrivateFixtureFunction { throw 'This helper should not be exported.' }
''', encoding='utf-8')
        return runtime, profile

    def install(self, shell, runtime, profile):
        result = self.run_ps(shell, INSTALLER, '-RuntimePath', runtime, '-ProfilePath', profile)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_original_profile_backup_and_idempotent_loader_on_both_shells(self):
        original_text = '# Custom configuration: café, résumé\r\n$global:FixturePreserved = "kept"\r\n'
        for shell_index, shell in enumerate(SHELLS):
            for encoding in ('utf-8', 'utf-8-sig', 'utf-16'):
                with self.subTest(shell=shell, encoding=encoding):
                    runtime, profile = self.fixture(f'{shell_index}-{encoding}')
                    original = original_text.encode(encoding)
                    profile.write_bytes(original)
                    first = self.install(shell, runtime, profile)
                    self.assertTrue(first['changed'])
                    self.assertTrue(Path(first['profile']).samefile(profile))
                    updated = profile.read_bytes()
                    self.assertTrue(updated.decode(encoding).startswith(original_text))
                    self.assertEqual(updated.decode(encoding).count('# BEGIN AI Dev terminal integration'), 1)
                    backups = list((runtime / 'backups').glob('powershell-profile-*.ps1'))
                    self.assertEqual(len(backups), 1)
                    self.assertEqual(backups[0].read_bytes(), original)
                    second = self.install(shell, runtime, profile)
                    self.assertFalse(second['changed'])
                    self.assertEqual(profile.read_bytes(), updated)
                    self.assertEqual(list((runtime / 'backups').glob('powershell-profile-*.ps1')), backups)

    def test_loader_imports_stub_from_literal_runtime_path_with_spaces_quotes_and_metacharacters(self):
        wrapper = self.root / 'load fixture.ps1'
        wrapper.write_text('''param($FixtureProfile)
$ErrorActionPreference = 'Stop'
# PowerShell 7 prepends its normal user module directories at startup. Set
# fixture precedence afterwards so an installed real module cannot be used.
$fixtureModuleRoot = Join-Path (Split-Path -Parent $FixtureProfile) 'Modules'
$env:PSModulePath = $fixtureModuleRoot + [IO.Path]::PathSeparator + $env:PSModulePath
. $FixtureProfile
$expectedModule = Join-Path $fixtureModuleRoot 'AIDevTerminal\\AIDevTerminal.psm1'
$actualModulePath = (Get-Item -LiteralPath (Get-Command Invoke-AIDevGit).Module.Path).FullName
$expectedModulePath = (Get-Item -LiteralPath $expectedModule).FullName
if ($actualModulePath -ine $expectedModulePath) { throw 'The isolated fixture module was not imported.' }
$result = Invoke-AIDevGit -Action status
[pscustomobject]@{result=$result; preserved=$global:FixturePreserved;
    module=(Get-Command Invoke-AIDevGit).ModuleName;
    privateExported=($null -ne (Get-Command PrivateFixtureFunction -ErrorAction SilentlyContinue))} | ConvertTo-Json -Depth 5
''', encoding='utf-8')
        for index, shell in enumerate(SHELLS):
            with self.subTest(shell=shell):
                runtime, profile = self.fixture(f'load-{index}')
                profile.write_text('$global:FixturePreserved = "kept"\n', encoding='utf-8')
                self.install(shell, runtime, profile)
                module_root = profile.parent / 'Modules'
                environment = dict(os.environ)
                environment['PSModulePath'] = str(module_root) + os.pathsep + environment.get('PSModulePath', '')
                result = self.run_ps(shell, wrapper, '-FixtureProfile', profile, env=environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                response = json.loads(result.stdout)
                self.assertEqual(response['result']['action'], 'status')
                self.assertTrue(Path(response['result']['runtime']).samefile(runtime))
                self.assertEqual(response['preserved'], 'kept')
                self.assertEqual(response['module'], 'AIDevTerminal')
                self.assertFalse(response['privateExported'])
                saved_runtime = json.loads((module_root / 'AIDevTerminal/runtime.json').read_text())['path']
                self.assertTrue(Path(saved_runtime).samefile(runtime))

    def test_bomless_ansi_profile_text_is_not_silently_corrupted(self):
        # Windows profiles historically use the system ANSI code page as well
        # as UTF-8; a backup alone does not prevent corruption of the live file.
        for index, shell in enumerate(SHELLS):
            with self.subTest(shell=shell):
                runtime, profile = self.fixture(f'ansi-{index}')
                original = '# Réglages personnels: été\r\n$fixture = "café"\r\n'.encode('cp1252')
                profile.write_bytes(original)
                result = self.run_ps(shell, INSTALLER, '-RuntimePath', runtime, '-ProfilePath', profile)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                updated = profile.read_bytes()
                self.assertTrue(updated.startswith(original), 'Appending the loader must preserve existing ANSI bytes')
                backups = list((runtime / 'backups').glob('powershell-profile-*.ps1'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
