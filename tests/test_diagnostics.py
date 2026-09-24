"""Read-only diagnostic routing and isolated Windows execution checks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'agentdeck/run-diagnostics.ps1'
SHELLS = list(dict.fromkeys(filter(None, (shutil.which('powershell'), shutil.which('pwsh')))))
ACTIONS = ['ports', 'processes', 'connection', 'dns', 'routes', 'path', 'disk',
           'startup', 'wsl', 'docker', 'longpaths']


@unittest.skipUnless(os.name == 'nt' and SHELLS, 'Windows diagnostics integration')
class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='AgentDeck diagnostics ')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_script(self, shell, *arguments, script=SCRIPT, env=None):
        return subprocess.run([shell, '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                               '-File', str(script), *map(str, arguments)],
                              env=env, text=True, capture_output=True, timeout=25)

    def test_plans_are_complete_deterministic_and_never_inspect_the_workstation(self):
        wrapper = self.root / 'plans.ps1'
        wrapper.write_text('''param($DiagnosticScript)
function Get-Command { throw 'Discovery must not run in plan mode.' }
function Get-Process { throw 'Process inspection must not run in plan mode.' }
function Get-CimInstance { throw 'CIM must not run in plan mode.' }
function Get-ItemProperty { throw 'Registry inspection must not run in plan mode.' }
function Read-Host { throw 'Input must not be requested in plan mode.' }
$rows = foreach ($action in @('ports','processes','connection','dns','routes','path','disk','startup','wsl','docker','longpaths')) {
    & $DiagnosticScript -Action $action -HostName example.invalid -Port 8443 -Plan | ConvertFrom-Json
}
ConvertTo-Json -InputObject @($rows) -Depth 6
''', encoding='utf-8')
        previous = None
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-DiagnosticScript', SCRIPT, script=wrapper)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                plans = json.loads(result.stdout)
                self.assertEqual([row['action'] for row in plans], ACTIONS)
                self.assertTrue(all(row['readOnly'] and row['commands'] for row in plans))
                self.assertEqual([row['action'] for row in plans if row['hostRequired']], ['connection', 'dns'])
                self.assertEqual(next(row['port'] for row in plans if row['action'] == 'connection'), 8443)
                if previous is not None:
                    self.assertEqual(plans, previous)
                previous = plans

    def test_missing_docker_is_an_explicit_failure(self):
        environment = dict(os.environ, PATH=str(self.root))
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-Action', 'docker', env=environment)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn('docker.exe was not found', result.stdout)

    def test_connection_key_prompts_for_host_and_port_without_defaulting_silently(self):
        wrapper = self.root / 'connection fixture.ps1'
        capture = self.root / 'connection.json'
        wrapper.write_text('''param($DiagnosticScript, $Capture)
$global:diagnosticFixtureReplies = New-Object 'System.Collections.Generic.Queue[string]'
$global:diagnosticFixtureReplies.Enqueue('example.invalid')
$global:diagnosticFixtureReplies.Enqueue('8443')
function Read-Host { param($Prompt); return $global:diagnosticFixtureReplies.Dequeue() }
function Test-NetConnection {
    param($ComputerName, $Port)
    [IO.File]::WriteAllText($Capture, (@{host=$ComputerName;port=$Port} | ConvertTo-Json))
    return [pscustomobject]@{RemoteAddress='127.0.0.1'; SourceAddress='127.0.0.1'; TcpTestSucceeded=$true}
}
& $DiagnosticScript -Action connection
exit $LASTEXITCODE
''', encoding='utf-8')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-DiagnosticScript', SCRIPT, '-Capture', capture, script=wrapper)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(capture.read_text()), {'host': 'example.invalid', 'port': 8443})

    def test_path_lists_duplicates_and_missing_folders_without_other_environment_values(self):
        present = self.root / 'present folder'
        present.mkdir()
        missing = self.root / 'missing folder'
        secret = 'PRIVATE_DIAGNOSTIC_SENTINEL_849273'
        environment = dict(os.environ, PATH=f'{present};{present};{missing};', DIAGNOSTIC_SECRET=secret)
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-Action', 'path', env=environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Duplicate', result.stdout)
                self.assertIn('missing folder', result.stdout)
                self.assertIn('empty entry: current directory', result.stdout)
                self.assertIn('True', result.stdout)
                self.assertIn('False', result.stdout)
                self.assertNotIn(secret, result.stdout + result.stderr)
                self.assertFalse(missing.exists(), 'Inspecting PATH must not create missing directories')

    def test_longpaths_reads_real_windows_status_and_isolated_git_setting(self):
        if not shutil.which('git'):
            self.skipTest('Git unavailable')
        configuration = self.root / 'gitconfig'
        configuration.write_text('[core]\n    longpaths = true\n', encoding='utf-8')
        original = configuration.read_bytes()
        environment = dict(os.environ, GIT_CONFIG_GLOBAL=str(configuration), GIT_CONFIG_NOSYSTEM='1')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-Action', 'longpaths', '-Project', self.root, env=environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Windows LongPathsEnabled:', result.stdout)
                self.assertIn('Git core.longpaths', result.stdout)
                self.assertIn('true', result.stdout)
                self.assertEqual(configuration.read_bytes(), original)

    def test_denied_process_sources_do_not_report_success_with_no_rows(self):
        wrapper = self.root / 'denied.ps1'
        wrapper.write_text('''param($DiagnosticScript)
function Get-CimInstance { throw 'Access denied by CIM fixture.' }
function Get-Process { throw 'Access denied by process fixture.' }
& $DiagnosticScript -Action processes
exit $LASTEXITCODE
''', encoding='utf-8')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-DiagnosticScript', SCRIPT, script=wrapper)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn('Access denied', result.stdout)
                self.assertIn('Diagnostics failed:', result.stdout)

    def test_localized_netstat_states_still_identify_listener_owners(self):
        native = self.root / 'netstat-fixture.cmd'
        native.write_text('@echo off\necho TCP 0.0.0.0:8443 0.0.0.0:0 ECOUTE 42\n'
                          'echo TCP [::]:9443 [::]:0 HORCHEN 43\n'
                          'echo TCP 127.0.0.1:30001 127.0.0.1:443 ESTABLISHED 44\n'
                          'echo UDP 0.0.0.0:5353 *:* 42\n', encoding='ascii')
        wrapper = self.root / 'netstat wrapper.ps1'
        wrapper.write_text('''param($DiagnosticScript, $NativeFixture)
$global:diagnosticNetstatPath = $NativeFixture
function Get-Command {
    param($Name, $CommandType, $ErrorAction)
    if ($Name -eq 'Get-NetTCPConnection') { return $null }
    if ($Name -eq 'netstat.exe') { return [pscustomobject]@{Source=$global:diagnosticNetstatPath} }
    throw ('Unexpected command: ' + $Name)
}
function Get-Process {
    [pscustomobject]@{Id=42;ProcessName='fixture-server'}
    [pscustomobject]@{Id=43;ProcessName='fixture-ipv6'}
}
& $DiagnosticScript -Action ports
exit $LASTEXITCODE
''', encoding='utf-8')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_script(shell, '-DiagnosticScript', SCRIPT, '-NativeFixture', native, script=wrapper)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                for expected in ('8443', '9443', '5353', 'fixture-server', 'fixture-ipv6'):
                    self.assertIn(expected, result.stdout)
                self.assertNotIn('30001', result.stdout, 'Connected sockets are not listeners')


if __name__ == '__main__':
    unittest.main()
