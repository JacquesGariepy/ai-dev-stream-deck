"""Windows integration checks using isolated projects and native Shell Links."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SHELLS = list(dict.fromkeys(filter(None, (shutil.which('powershell'), shutil.which('pwsh')))))


@unittest.skipUnless(os.name == 'nt' and SHELLS, 'Windows PowerShell integration')
class NativeActionsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='AgentDeck native validation ')
        self.root = Path(self.temporary.name)
        self.environment = dict(os.environ)
        self.bin = self.root / 'fixture commands'
        self.bin.mkdir()
        self.capture = self.root / 'arguments.json'
        self.environment.update(PATH=str(self.bin) + os.pathsep + self.environment['PATH'],
                                NATIVE_ACTION_CAPTURE=str(self.capture))

    def tearDown(self):
        self.temporary.cleanup()

    def run_ps(self, shell, script, *arguments, input=None):
        return subprocess.run([shell, '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                               '-File', str(script), *map(str, arguments)], env=self.environment,
                              input=input, capture_output=True, text=True, timeout=35)

    def fixture_command(self, name, exit_code=0):
        (self.bin / (name + '.ps1')).write_text(
            '[IO.File]::WriteAllText($env:NATIVE_ACTION_CAPTURE, '
            '(ConvertTo-Json -InputObject @($args)), [Text.UTF8Encoding]::new($false))\n'
            "Write-Output 'fixture output available for FIX'\n"
            f'exit {exit_code}\n', encoding='utf-8')

    def run_task(self, shell, project, kind='test'):
        return self.run_ps(shell, ROOT / 'agentdeck/run-task.ps1', '-Kind', kind,
                           '-Project', project, '-StateDirectory', self.root / 'private state')

    def test_project_detection_arguments_and_failure_context(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.fixture_command('dotnet')
                dotnet = self.root / 'dotnet project [literal]'
                dotnet.mkdir(exist_ok=True)
                solution = dotnet / 'Example.sln'
                solution.write_text('fixture', encoding='utf-8')
                result = self.run_task(shell, dotnet, 'build')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()), ['build', str(solution)])

                self.fixture_command('python', 7)
                pytest = self.root / 'pytest project'
                (pytest / 'tests').mkdir(parents=True, exist_ok=True)
                (pytest / 'tests/test_example.py').write_text('def test_example():\n    assert False\n')
                result = self.run_task(shell, pytest)
                self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()), ['-m', 'pytest'])
                failure_path = self.root / 'private state/last-failure.json'
                failure = json.loads(failure_path.read_text())
                self.assertEqual(Path(failure['project']), pytest)
                self.assertEqual(failure['exitCode'], 7)
                self.assertIn('fixture output available for FIX', failure['outputTail'])

                self.fixture_command('python')
                unit = self.root / 'unittest project'
                (unit / 'tests').mkdir(parents=True, exist_ok=True)
                (unit / 'tests/test_example.py').write_text(
                    'import unittest\nclass Example(unittest.TestCase):\n'
                    '    def test_example(self):\n        self.assertTrue(True)\n')
                result = self.run_task(shell, unit)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()),
                                 ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
                self.assertEqual(json.loads(failure_path.read_text()), failure,
                                 'A success must not erase the last failed task context')

    def test_no_task_and_unsafe_script_names_do_not_start_another_command(self):
        self.fixture_command('npm')
        project = self.root / 'project ; $literal'
        project.mkdir()
        (project / 'package.json').write_text(json.dumps({'scripts': {'test:unit;echo': 'ignored'}}))
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.capture.unlink(missing_ok=True)
                result = self.run_task(shell, project)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn('No conventional test script', result.stdout)
                self.assertFalse(self.capture.exists())
                (project / 'package.json').write_text(json.dumps({'scripts': {'test:unit': 'ignored'}}))
                result = self.run_task(shell, project)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()), ['run', 'test:unit'])
                (project / 'package.json').write_text(json.dumps({'scripts': {'test:unit;echo': 'ignored'}}))

    def test_native_links_survive_short_paths_and_preserve_unowned_shortcuts(self):
        helper = self.root / 'verify links.ps1'
        helper.write_text(r'''param($Creator, $Root)
$ErrorActionPreference = 'Stop'
$folder = Join-Path $Root 'launchers with spaces'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$fso = New-Object -ComObject Scripting.FileSystemObject
$short = $fso.GetFolder($folder).ShortPath
$shell = New-Object -ComObject WScript.Shell
$target = (Get-Command powershell -CommandType Application | Select-Object -First 1).Source
$working = Join-Path $Root 'custom runtime'
New-Item -ItemType Directory -Path $working -Force | Out-Null
$script = Join-Path $working 'ai.ps1'
$arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '" fix'
$manifest = Join-Path $Root 'manifest.json'
$entries = @('ai-fix','ai-retired','ai-customized') | ForEach-Object {
    [pscustomobject]@{name=$_; target=$target; arguments=$arguments; workingDirectory=$working}
}
ConvertTo-Json -InputObject @($entries) | Set-Content -LiteralPath $manifest -Encoding UTF8
& $Creator -ManifestPath $manifest -OutputDirectory $short
if (-not (Test-Path -LiteralPath (Join-Path $folder 'ai-retired.lnk'))) { throw 'Short path cleanup deleted a generated link.' }
$unownedPath = Join-Path $folder 'ai-user-owned.lnk'
$unowned = $shell.CreateShortcut($unownedPath)
$unowned.TargetPath = $target; $unowned.Arguments = '-NoProfile'; $unowned.Save()
$before = [Convert]::ToBase64String([IO.File]::ReadAllBytes($unownedPath))
$customizedPath = Join-Path $folder 'ai-customized.lnk'
$customized = $shell.CreateShortcut($customizedPath)
$customized.Arguments = '-NoProfile'; $customized.Save()
ConvertTo-Json -InputObject @($entries[0]) | Set-Content -LiteralPath $manifest -Encoding UTF8
& $Creator -ManifestPath $manifest -OutputDirectory $short
if (Test-Path -LiteralPath (Join-Path $folder 'ai-retired.lnk')) { throw 'Owned retired shortcut was retained.' }
if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($unownedPath)) -cne $before) { throw 'User shortcut was changed.' }
if (-not (Test-Path -LiteralPath $customizedPath)) { throw 'Customized shortcut was deleted.' }
$link = $shell.CreateShortcut((Join-Path $folder 'ai-fix.lnk'))
if ($link.TargetPath -ine $target -or $link.Arguments -cne $arguments -or $link.WorkingDirectory -ine $working) { throw 'Windows link contents do not match.' }
Write-Output 'Native COM verified; retired owned shortcut removed; user shortcut preserved.'
''', encoding='utf-8')
        for index, shell in enumerate(SHELLS):
            with self.subTest(shell=shell):
                folder = self.root / f'shell {index}'
                folder.mkdir()
                result = self.run_ps(shell, helper, '-Creator', ROOT / 'scripts/Create-AgentShortcuts.ps1',
                                     '-Root', folder)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Native COM verified', result.stdout)

    def test_installer_prepares_deep_profile_outside_long_backup_path(self):
        profile_id = '01234567-89ab-cdef-0123-456789abcdef.sdProfile'
        image_entry = profile_id + '/Profiles/01234567-89ab-cdef-0123-456789abcdef/Images/unstash-git.png'
        archive = self.root / 'generated.streamDeckProfile'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr(profile_id + '/manifest.json', json.dumps({'Name': 'AI Dev Agentic'}))
            output.writestr(image_entry, b'fixture image')
        for index, shell in enumerate(SHELLS):
            with self.subTest(shell=shell):
                profiles = self.root / f'profiles{index}'
                profiles.mkdir()
                backup = self.root / ('package-' + 'x' * 65) / ('runtime-' + 'y' * 35) / 'backups'
                backup.mkdir(parents=True, exist_ok=True)
                self.assertGreater(len(str(backup / ('stage-' + 'a' * 32) / image_entry)), 260)
                result = self.run_ps(shell, ROOT / 'scripts/Install-AgentProfile.ps1',
                                     '-ProfilePath', archive, '-ProfilesRoot', profiles,
                                     '-BackupRoot', backup, '-PrepareOnly')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                preparation = json.loads(result.stdout)
                stage = Path(preparation['Stage'])
                self.assertEqual(stage.parent, profiles)
                self.assertEqual((stage / image_entry).read_bytes(), b'fixture image')
                self.assertFalse(Path(preparation['Target']).exists(), 'Preparation must not install or replace profiles')

    def test_git_confirmation_and_selection_in_an_isolated_repository(self):
        git = shutil.which('git')
        if not git:
            self.skipTest('Git unavailable')
        for index, shell in enumerate(SHELLS):
            with self.subTest(shell=shell):
                project = self.root / f'git fixture {index}'
                project.mkdir()
                def invoke(*arguments):
                    return subprocess.run([git, '-C', str(project), *arguments], check=True,
                                          text=True, capture_output=True).stdout
                invoke('init')
                invoke('config', 'user.name', 'Fixture')
                invoke('config', 'user.email', 'fixture@example.invalid')
                (project / 'example.txt').write_text('initial\n')
                invoke('add', '.')
                invoke('commit', '-m', 'fixture initial')
                initial_branch = invoke('branch', '--show-current').strip()
                (project / 'example.txt').write_text('modified\n')
                runner = ROOT / 'agentdeck/run-git.ps1'
                result = self.run_ps(shell, runner, '-Action', 'stage', '-Project', project, input='n\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(invoke('diff', '--cached', '--name-only'), '')
                result = self.run_ps(shell, runner, '-Action', 'stage', '-Project', project, input='y\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(invoke('diff', '--cached', '--name-only').strip(), 'example.txt')
                result = self.run_ps(shell, runner, '-Action', 'branch', '-Project', project,
                                     input='feature/fixture\ny\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(invoke('branch', '--show-current').strip(), 'feature/fixture')
                branches = invoke('for-each-ref', '--format=%(refname:short)', 'refs/heads/').splitlines()
                selection = branches.index(initial_branch) + 1
                result = self.run_ps(shell, runner, '-Action', 'switch', '-Project', project,
                                     input=f'{selection}\ny\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(invoke('branch', '--show-current').strip(), initial_branch)
                result = self.run_ps(shell, runner, '-Action', 'stash', '-Project', project, input='y\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(invoke('status', '--porcelain').strip(), '')
                result = self.run_ps(shell, runner, '-Action', 'unstash', '-Project', project, input='1\ny\n')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('modified', (project / 'example.txt').read_text())
                self.assertTrue(invoke('stash', 'list').strip(), 'Apply must preserve the saved stash')


if __name__ == '__main__':
    unittest.main()
