"""Exercise Windows dispatch with a local argv recorder, never an AI provider."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which('powershell')


def ps_string(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(os.name == 'nt' and SHELL, 'Windows PowerShell runtime check')
class AgentDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'requests').mkdir()
        self.request = self.folder / 'requests' / 'sample.json'
        self.capture = self.folder / 'argv.json'
        self.recorder = self.folder / 'recorder.py'
        self.recorder.write_text(
            'import json, os, sys\n'
            'from pathlib import Path\n'
            'Path(os.environ["AGENTDECK_TEST_CAPTURE"]).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n',
            encoding='utf-8',
        )
        self.env = dict(os.environ, AI_DEV_AGENTDECK_DIR=str(self.folder),
                        AGENTDECK_TEST_PYTHON=sys.executable,
                        AGENTDECK_TEST_RECORDER=str(self.recorder),
                        AGENTDECK_TEST_CAPTURE=str(self.capture))
        self.row = dict(id='sample', intent='fix', harness='claude', profile='roundtrip',
                        mode='auto', title='FIX', project=str(self.folder),
                        objective='Fix the quoted parser error.', context='SyntaxError',
                        prompt='Fix the parser.\nprint("hello world")\nPath: C:\\folder with spaces\\\n'
                               'Literal: `tick $value $(never-execute) & ; naïve\n'
                               'Escaped quote: \\" and "end\\"')

    def run_ps(self, code, shell=SHELL):
        script = self.folder / 'test.ps1'
        script.write_text("$ErrorActionPreference='Stop'\n" + code, encoding='utf-8-sig')
        return subprocess.run([shell, '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(script)],
                              env=self.env, text=True, encoding='utf-8', errors='replace',
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    def write_request(self, **updates):
        self.row.update(updates)
        self.request.write_text(json.dumps(self.row), encoding='utf-8')

    def runner(self, verify=False):
        return ('function claude-roundtrip { & $env:AGENTDECK_TEST_PYTHON $env:AGENTDECK_TEST_RECORDER @args }\n'
                '& ' + ps_string(ROOT / 'agentdeck/run-agent.ps1') + ' -Request ' + ps_string(self.request)
                + (' -VerifyOnly' if verify else ''))

    def test_native_wrapper_receives_exact_multiline_prompt_and_safe_flags(self):
        self.write_request()
        result = self.run_ps(self.runner())
        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = json.loads(self.capture.read_text('utf-8'))
        self.assertEqual(arguments, ['--permission-mode', 'acceptEdits', '--', self.row['prompt']])
        self.assertFalse(self.request.exists())
        receipt = json.loads((self.folder / 'receipts/sample.json').read_text('utf-8'))
        self.assertEqual(receipt['status'], 'launched')
        self.assertNotIn('prompt', receipt)
        self.assertNotIn('context', receipt)

    def test_verify_only_does_not_call_harness_or_remove_request(self):
        self.write_request()
        result = self.run_ps(self.runner(verify=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        result_row = json.loads(result.stdout)
        self.assertEqual(result_row['arguments'][-1], self.row['prompt'])
        self.assertEqual(result_row['command'], 'claude-roundtrip')
        self.assertTrue(self.request.exists())
        self.assertFalse(self.capture.exists())
        self.assertFalse((self.folder / 'receipts').exists())

    def test_powershell7_wrapper_preserves_multiline_quotes(self):
        modern = shutil.which('pwsh')
        if not modern:
            self.skipTest('PowerShell 7 is not installed')
        self.write_request()
        result = self.run_ps(self.runner(), shell=modern)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text('utf-8'))[-1], self.row['prompt'])

    def test_cli_failure_is_recorded_as_error_not_task_success(self):
        self.recorder.write_text('import sys\nsys.exit(9)\n', encoding='utf-8')
        self.write_request()
        result = self.run_ps(self.runner())
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.folder / 'receipts/sample.json').read_text('utf-8'))
        self.assertEqual(receipt['status'], 'error')
        self.assertIn('code 9', receipt['error'])

    def test_codex_uses_supported_sandbox_and_approval_flags(self):
        self.write_request(harness='codex')
        result = self.run_ps('function codex-roundtrip { throw "Should not run" }\n'
                             '& ' + ps_string(ROOT / 'agentdeck/run-agent.ps1')
                             + ' -VerifyOnly -Request ' + ps_string(self.request))
        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = json.loads(result.stdout)['arguments']
        self.assertEqual(arguments[:4], ['--sandbox','workspace-write','--ask-for-approval','on-request'])
        self.assertEqual(arguments[-1], self.row['prompt'])

    def test_start_process_preserves_spaced_paths_and_each_native_argument(self):
        expected = ['--distribution', 'Ubuntu 24.04', '--cd', 'C:\\Users\\Jane Smith\\project folder\\',
                    'shell:AppsFolder\\Example Application', 'literal "quoted" argument', '']
        arguments = self.folder / 'native-arguments.json'
        arguments.write_text(json.dumps([str(self.recorder), *expected]), encoding='utf-8')
        result = self.run_ps('. ' + ps_string(ROOT / 'agentdeck/context.ps1') + '\n'
                             '$values=Get-Content -LiteralPath ' + ps_string(arguments)
                             + ' -Raw -Encoding UTF8|ConvertFrom-Json\n'
                             'Start-Process -FilePath $env:AGENTDECK_TEST_PYTHON '
                             '-ArgumentList (Join-WindowsArguments $values) -WindowStyle Hidden -Wait')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text('utf-8')), expected)

    def test_empty_fix_does_not_launch_even_with_template_prompt(self):
        self.write_request(context='', objective='')
        result = self.run_ps(self.runner())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Nothing was launched', result.stderr)
        self.assertFalse(self.capture.exists())
        receipt = json.loads((self.folder / 'receipts/sample.json').read_text('utf-8'))
        self.assertEqual(receipt['status'], 'error')

    def test_missing_named_profile_never_falls_back_to_default(self):
        self.write_request(profile='missing')
        result = self.run_ps('function claude { throw "Wrong account was invoked" }\n' + self.runner())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('claude-missing', result.stderr)
        self.assertNotIn('Wrong account was invoked', result.stderr)
        self.assertFalse(self.capture.exists())

    def test_dispatcher_builds_fix_request_without_clipboard_or_launch(self):
        task = self.folder / 'task.json'
        task.write_text(json.dumps({key: self.row[key] for key in ('project','harness','profile','objective','context')}), encoding='utf-8')
        command = ('function claude-roundtrip { throw "Should not run" }\n'
                   '& ' + ps_string(ROOT / 'agentdeck/ai.ps1') + ' fix -ProfileLoaded -VerifyOnly -TaskInput ' + ps_string(task))
        result = self.run_ps(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan['request']['project'], str(self.folder))
        self.assertIn(self.row['context'], plan['request']['prompt'])
        self.assertIn('English', plan['request']['prompt'])
        self.assertEqual(plan['arguments'][-1], plan['request']['prompt'])
        self.assertEqual(list((self.folder / 'requests').glob('*.json')), [])

    def test_continue_requires_session_for_current_project_and_profile(self):
        (self.folder / 'state.json').write_text(json.dumps({
            'project': str(self.folder), 'profile': 'roundtrip',
            'sessions': [{'project': str(self.folder / 'different'), 'profile': 'roundtrip', 'harness': 'claude'}],
        }), encoding='utf-8')
        result = self.run_ps('function claude-roundtrip {}\n& ' + ps_string(ROOT / 'agentdeck/ai.ps1') + ' continue -ProfileLoaded -VerifyOnly')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No previous agent session', result.stderr)

    def write_custom_catalog(self):
        (self.folder / 'tools.json').write_text(json.dumps({'harnesses': [{
            'deck_id': 'a' * 16, 'tool': 'gemini', 'profile': 'work', 'command': 'gemini-work',
        }]}), encoding='utf-8')

    def test_detected_generic_cli_launches_exact_profile_without_guessed_flags(self):
        self.write_custom_catalog()
        (self.folder / 'state.json').write_text(json.dumps({'project': str(self.folder), 'profile': 'personal'}), encoding='utf-8')
        result = self.run_ps('function gemini-work {}\n& ' + ps_string(ROOT / 'agentdeck/ai.ps1')
                             + ' cli-' + 'a' * 16 + ' -ProfileLoaded -VerifyOnly')
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan['command'], 'gemini-work')
        self.assertEqual(plan['request']['profile'], 'work')
        self.assertEqual(plan['request']['mode'], 'interactive')
        self.assertEqual(plan['arguments'], [])
        self.request.write_text(json.dumps(plan['request']), encoding='utf-8')
        result = self.run_ps('function gemini-work { & $env:AGENTDECK_TEST_PYTHON $env:AGENTDECK_TEST_RECORDER @args }\n& '
                             + ps_string(ROOT / 'agentdeck/run-agent.ps1') + ' -Request ' + ps_string(self.request))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text('utf-8')), [])

    def test_detected_custom_profile_missing_never_falls_back_to_base_cli(self):
        self.write_custom_catalog()
        self.write_request(harness='gemini', profile='work', command='gemini-work', mode='interactive', prompt='')
        result = self.run_ps('function gemini { throw "Wrong account" }\n& '
                             + ps_string(ROOT / 'agentdeck/run-agent.ps1') + ' -Request ' + ps_string(self.request))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('gemini-work', result.stderr)
        self.assertNotIn('Wrong account', result.stderr)

    def test_generic_cli_rejects_unknown_commands_and_automatic_task_modes(self):
        self.write_custom_catalog()
        self.write_request(harness='gemini', profile='work', command='gemini-personal', mode='interactive', prompt='')
        command = ('function gemini-work {}; function gemini-personal {}\n& '
                   + ps_string(ROOT / 'agentdeck/run-agent.ps1') + ' -VerifyOnly -Request ' + ps_string(self.request))
        result = self.run_ps(command)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('absent from the installed catalog', result.stderr)
        self.write_request(command='gemini-work', mode='auto', prompt='Do a task')
        result = self.run_ps(command)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not supported for gemini', result.stderr)


if __name__ == '__main__':
    unittest.main()
