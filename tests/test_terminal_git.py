"""Current-shell Git integration; all Git work uses disposable repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SHELL=shutil.which('powershell')
GIT=shutil.which('git')


def quoted(value):
    return "'"+str(value).replace("'", "''")+"'"


@unittest.skipUnless(os.name=='nt' and SHELL and GIT, 'Windows PowerShell and Git are required')
class TerminalGitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='agent deck terminal ')
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    def run_shell(self, code, shell=SHELL):
        script=self.folder/'check.ps1'
        script.write_text("$ErrorActionPreference='Stop'\n"+code, encoding='utf-8-sig')
        return subprocess.run([shell,'-NoLogo','-NoProfile','-NonInteractive','-File',str(script)],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                              encoding='utf-8',errors='replace',timeout=30)

    def test_all_chords_register_on_both_powershell_versions(self):
        for shell in dict.fromkeys(filter(None,(SHELL,shutil.which('pwsh')))):
            with self.subTest(shell=shell):
                result=self.run_shell('. '+quoted(ROOT/'agentdeck/terminal.ps1')+'\n'
                                      '@(Get-PSReadLineKeyHandler | Where-Object {$_.Function -like "AIDevGit*"} '
                                      '| Select-Object Key,Function)|ConvertTo-Json -Compress',shell)
                self.assertEqual(result.returncode,0,result.stderr)
                rows=json.loads(result.stdout)
                self.assertEqual(len(rows),11)
                self.assertEqual({row['Key'] for row in rows},{f'Ctrl+Alt+F{i}' for i in range(13,24)})

    def test_busy_input_buffer_is_never_changed_or_submitted(self):
        result=self.run_shell('. '+quoted(ROOT/'agentdeck/terminal.ps1')+'\n'
                              '$script:inserted="";$script:submitted=$false;$script:rejected=$false\n'
                              '$accepted=Invoke-AIDevGitPromptAction -Action status -ReadBuffer {"unfinished command"} '
                              '-InsertLine {param($text) $script:inserted=$text} '
                              '-SubmitLine {$script:submitted=$true} -RejectLine {$script:rejected=$true}\n'
                              '@{accepted=$accepted;inserted=$script:inserted;submitted=$script:submitted;'
                              'rejected=$script:rejected}|ConvertTo-Json -Compress')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),dict(accepted=False,inserted='',submitted=False,rejected=True))

    def test_empty_prompt_submits_only_fixed_action_command(self):
        result=self.run_shell('. '+quoted(ROOT/'agentdeck/terminal.ps1')+'\n'
                              '$script:inserted="";$script:submitted=$false\n'
                              '$accepted=Invoke-AIDevGitPromptAction -Action diff -ReadBuffer {""} '
                              '-InsertLine {param($text) $script:inserted=$text} '
                              '-SubmitLine {$script:submitted=$true} -RejectLine {throw "Rejected"}\n'
                              '@{accepted=$accepted;inserted=$script:inserted;submitted=$script:submitted}|ConvertTo-Json -Compress')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),dict(accepted=True,inserted='Invoke-AIDevGit -Action diff',submitted=True))

    def test_existing_binding_is_preserved_and_reimport_is_idempotent(self):
        result=self.run_shell('Import-Module PSReadLine\n'
                              'Set-PSReadLineKeyHandler -Chord Ctrl+Alt+F13 -BriefDescription MyOwnBinding -ScriptBlock {}\n'
                              '. '+quoted(ROOT/'agentdeck/terminal.ps1')+' -WarningAction SilentlyContinue\n'
                              '. '+quoted(ROOT/'agentdeck/terminal.ps1')+' -WarningAction SilentlyContinue\n'
                              '@(Get-PSReadLineKeyHandler | Where-Object {$_.Key -like "Ctrl+Alt+F*"} '
                              '| Select-Object Key,Function)|ConvertTo-Json -Compress')
        self.assertEqual(result.returncode,0,result.stderr)
        # Dot-sourced scripts have no common WarningAction parameter; discard warnings above JSON.
        rows=json.loads(result.stdout[result.stdout.index('['):])
        mapping={row['Key']:row['Function'] for row in rows}
        self.assertEqual(mapping['Ctrl+Alt+F13'],'MyOwnBinding')
        self.assertEqual(sum(name.startswith('AIDevGit') for name in mapping.values()),10)

    def test_git_uses_current_directory_even_after_module_import_elsewhere(self):
        first=self.folder/'first repository';second=self.folder/'second repository'
        for path in (first,second):
            path.mkdir()
            subprocess.run([GIT,'init','--quiet',str(path)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (first/'FIRST_ONLY.txt').write_text('first',encoding='utf-8')
        (second/'SECOND_ONLY.txt').write_text('second',encoding='utf-8')
        result=self.run_shell('Set-Location -LiteralPath '+quoted(first)+'\n'
                              '. '+quoted(ROOT/'agentdeck/terminal.ps1')+'\n'
                              'Set-Location -LiteralPath '+quoted(second)+'\n'
                              'Invoke-AIDevGit -Action status\n'
                              'Write-Output ("AFTER="+(Get-Location).ProviderPath)')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SECOND_ONLY.txt',result.stdout)
        self.assertNotIn('FIRST_ONLY.txt',result.stdout)
        locations=[line.removeprefix('AFTER=') for line in result.stdout.splitlines() if line.startswith('AFTER=')]
        self.assertEqual(len(locations),1)
        # PowerShell expands Windows 8.3 aliases (for example RUNNER~1).
        # File identity proves we stayed in the repository regardless of spelling.
        self.assertTrue(Path(locations[0]).samefile(second))

    def test_git_failure_does_not_close_the_calling_shell(self):
        plain=self.folder/'not a repository'
        plain.mkdir()
        result=self.run_shell('. '+quoted(ROOT/'agentdeck/terminal.ps1')+'\n'
                              'Set-Location -LiteralPath '+quoted(plain)+'\n'
                              'Invoke-AIDevGit -Action status\n'
                              'Write-Output "CALLING_SHELL_CONTINUED"')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Git action could not run',result.stdout)
        self.assertIn('CALLING_SHELL_CONTINUED',result.stdout)


if __name__=='__main__':unittest.main()
