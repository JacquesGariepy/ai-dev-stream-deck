import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from aidev.runtime import run_mission, spawn_terminal
from aidev.storage import save_json


class RuntimeTests(unittest.TestCase):
    def test_invalid_receipts_are_preserved_and_never_launch_discovery(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR': folder}):
            path = Path(folder) / 'mission.json'
            for content in (None, 'null', '[]', '{broken', '{}', '{"tool": 42}'):
                with self.subTest(content=content):
                    path.unlink(missing_ok=True)
                    if content is not None:
                        path.write_text(content)
                    with patch('aidev.runtime.discover') as discover, contextlib.redirect_stderr(io.StringIO()) as errors:
                        self.assertEqual(run_mission(path), 1)
                    discover.assert_not_called()
                    self.assertIn(str(path.resolve()), errors.getvalue())
                    self.assertNotIn('NoneType', errors.getvalue())
                    self.assertEqual(path.read_text() if path.exists() else None, content)

    def test_missing_receipt_cli_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'launch.py'),
                                     '--run', str(Path(folder) / 'absent.json')],
                                    env={**os.environ, 'AI_DEV_DATA_DIR': folder}, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Mission file not found', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_runner_records_exit_and_removes_request(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR': folder}):
            path = Path(folder) / 'mission.json'
            mission = {'tool': 'codex', 'profile': 'work', 'command': 'codex-work', 'project': folder}
            save_json(path, mission)
            catalog = {'psVersion': '7.4', 'powershell': 'pwsh'}
            with patch('aidev.runtime.discover', return_value=catalog), \
                 patch('aidev.runtime.find_entry', return_value={**mission, 'available': True}), \
                 patch('aidev.runtime.arguments_for', return_value=[]), \
                 patch('aidev.runtime.subprocess.run', return_value=subprocess.CompletedProcess([], 7)), \
                 patch('aidev.runtime.sys.stdin', None), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_mission(path), 7)
            receipt = json.loads(path.read_text())
            self.assertEqual(receipt['status'], 'exited')
            self.assertEqual(receipt['exit_code'], 7)
            self.assertFalse(path.with_suffix('.launch.json').exists())

    def test_discovery_error_is_recorded_without_secondary_exception(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR': folder}):
            path = Path(folder) / 'mission.json'
            save_json(path, {'tool': 'codex', 'profile': 'work', 'command': 'codex-work', 'project': folder})
            with patch('aidev.runtime.discover', side_effect=RuntimeError('profile unavailable')), \
                 patch('aidev.runtime.sys.stdin', None), contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_mission(path), 1)
            self.assertEqual(json.loads(path.read_text())['error'], 'profile unavailable')
            self.assertEqual(json.loads(path.read_text())['status'], 'launch_error')

    def test_terminal_receives_absolute_path_before_changing_directory(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path = Path(folder) / 'mission with spaces.json'
            save_json(path, {'tool': 'codex', 'profile': 'work', 'command': 'codex-work', 'project': folder})
            with patch('aidev.runtime.shutil.which', return_value='wt'), patch('aidev.runtime.subprocess.Popen') as popen:
                spawn_terminal(path.relative_to(Path.cwd()))
            self.assertEqual(popen.call_args.args[0][-2:], ['--run', str(path.resolve())])


if __name__ == '__main__':
    unittest.main()
