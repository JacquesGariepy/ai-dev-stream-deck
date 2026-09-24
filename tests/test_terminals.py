import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from aidev.terminals import installed_terminals, launch_terminal, terminal_command, TerminalPicker


class TerminalTests(unittest.TestCase):
    def test_wsl_distributions_utf16_and_executable_deduplication(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder)/'shell.exe'; exe.touch()
            lookup = lambda name: str(exe) if name in ('cmd', 'wsl') else None
            result = subprocess.CompletedProcess([], 0, 'Ubuntu\r\nDebian\r\n'.encode('utf-16-le'), b'')
            with patch('aidev.terminals.shutil.which', side_effect=lookup), \
                 patch('aidev.terminals.settings', return_value={'terminal_custom': [str(exe)]}), \
                 patch('aidev.terminals.subprocess.run', return_value=result) as run:
                entries, issues = installed_terminals()
            self.assertEqual([e['distro'] for e in entries if e['kind']=='wsl'], ['Ubuntu', 'Debian'])
            self.assertEqual(sum(e['executable']==str(exe.resolve()) and e['distro'] is None for e in entries), 1)
            self.assertEqual(issues, [])
            self.assertEqual(run.call_args.args[0][1:], ['--list', '--quiet'])

    def test_wsl_failure_does_not_hide_other_terminals(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder)/'wsl.exe'; exe.touch()
            with patch('aidev.terminals.shutil.which', return_value=str(exe)), \
                 patch('aidev.terminals.settings', return_value={}), \
                 patch('aidev.terminals.subprocess.run', side_effect=subprocess.TimeoutExpired('wsl', 8)):
                entries, issues = installed_terminals()
            self.assertTrue(entries)
            self.assertIn('WSL:', issues[0])

    def test_argument_paths_are_literal_and_bash_keeps_project(self):
        with tempfile.TemporaryDirectory(prefix='terminal space ') as folder:
            exe=Path(folder)/'shell.exe'; exe.touch()
            entry={'kind':'wsl', 'executable':str(exe), 'distro':'Ubuntu Test'}
            args, cwd=terminal_command(entry, folder)
            self.assertEqual(args, [str(exe), '--distribution', 'Ubuntu Test', '--cd', str(Path(folder).resolve())])
            entry['kind']='bash'
            with patch('aidev.terminals.subprocess.Popen') as popen:
                launch_terminal(entry, folder)
            self.assertEqual(popen.call_args.kwargs['env']['CHERE_INVOKING'], '1')
            self.assertEqual(popen.call_args.kwargs['cwd'], cwd)
            self.assertNotIn('shell', popen.call_args.kwargs)
            entry['kind']='powershell'
            self.assertEqual(terminal_command(entry, folder)[0], [str(exe), '-NoLogo'])

    def test_missing_executable_or_project_does_not_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('aidev.terminals.subprocess.Popen') as popen:
                with self.assertRaises(FileNotFoundError):
                    launch_terminal({'kind':'cmd','executable':str(Path(folder)/'missing.exe')}, folder)
                popen.assert_not_called()

    @unittest.skipUnless(os.name=='nt', 'Windows Tk')
    def test_picker_async_population_and_exact_selection(self):
        entries=[{'id':'cmd', 'label':'CMD', 'kind':'cmd', 'executable':'cmd.exe'},
                 {'id':'ps', 'label':'PowerShell', 'kind':'powershell', 'executable':'pwsh.exe'}]
        config={'language':'fr','terminal_last':'ps','project':str(Path.cwd())}
        with patch('aidev.terminals.settings', return_value=config), \
             patch('aidev.terminals.installed_terminals', return_value=(entries, [])), \
             patch('aidev.terminals.launch_terminal') as launch, patch('aidev.terminals.save_settings'):
            panel=TerminalPicker()
            try:
                panel.root.withdraw()
                deadline=time.monotonic()+3
                while not panel.list.get_children() and time.monotonic()<deadline:
                    panel.root.update(); time.sleep(.02)
                self.assertEqual(panel.list.selection(), ('1',))
                self.assertIn('Choisir un terminal', panel.root.title())
                panel.submit()
                launch.assert_called_once_with(entries[1], config['project'])
            finally:
                try: panel.root.destroy()
                except Exception: pass


if __name__=='__main__': unittest.main()
