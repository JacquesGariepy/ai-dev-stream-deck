import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import shutil
import unittest
from unittest.mock import patch
import zipfile

from aidev.agents import arguments_for, build_prompt, WORKFLOWS, TEXT_PROMPTS
from aidev.discovery import discover, find_entry
from aidev.i18n import resolve_language, tr
from aidev.runtime import capture_context, prepare
from aidev.storage import data_dir, save_json

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='AI Dev tests ')
        self.path = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'AI_DEV_DATA_DIR': str(self.path / 'private')})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def mission(self, tool='codex'):
        return {'tool':tool, 'project':str(self.path), 'objective':'Fix "quoted" input; keep $variables and `backticks` literal.\nThen verify.',
                'english_confirmed':True, 'workflow':'review', 'context':str(self.path/'snapshot.json')}

    def test_language_preference_and_fallback(self):
        self.assertEqual(resolve_language('auto','fr-CA'),'fr')
        self.assertEqual(resolve_language('auto','en-US'),'en')
        self.assertEqual(resolve_language('auto','ja-JP'),'en')
        self.assertEqual(resolve_language('en','fr-CA'),'en')
        self.assertEqual(resolve_language('fr','en-US'),'fr')
        self.assertNotEqual(tr('heading','fr'),tr('heading','en'))

    def test_ui_language_cannot_change_agent_protocol(self):
        mission=self.mission()
        for language in ('fr','en'):
            save_json(data_dir()/'settings.json',{'language':language})
            prompt=build_prompt(mission)
            self.assertIn('Use English',prompt)
            self.assertIn('Do not modify project files.',prompt)
            self.assertNotIn('Objectif',prompt)
            self.assertIn(mission['objective'],prompt)

    def test_unconfirmed_objective_is_not_sent(self):
        mission=self.mission();mission['english_confirmed']=False
        with self.assertRaises(ValueError):build_prompt(mission)

    def test_all_workflow_instructions_are_english(self):
        for flow in WORKFLOWS:
            mission=self.mission();mission['workflow']=flow
            self.assertIn('Workflow: ',build_prompt(mission))
            self.assertTrue(WORKFLOWS[flow].isascii())

    def test_harness_argument_adapters(self):
        for tool in ('codex','claude','agy'):
            args=arguments_for({'tool':tool},self.mission(tool))
            self.assertIn(self.mission()['objective'],args[-1])
            self.assertEqual(args[-2],'--prompt-interactive' if tool=='agy' else '--')
        self.assertEqual(arguments_for({'tool':'codex'},self.mission())[:2],['--sandbox','read-only'])
        self.assertEqual(arguments_for({'tool':'agy'},self.mission('agy'))[:2],['--mode','plan'])

    def test_unknown_harness_only_opens_interactively(self):
        with self.assertRaises(ValueError):arguments_for({'tool':'future-tool'},self.mission('future-tool'))
        self.assertEqual(arguments_for({'tool':'future-tool'},{'objective':''}),[])

    def test_profile_selection_uses_exact_command(self):
        catalog={'entries':[{'tool':'codex','profile':'work','command':'codex-work'},
                            {'tool':'claude','profile':'work','command':'claude-work'}]}
        self.assertEqual(find_entry(catalog,'codex','work')['command'],'codex-work')
        self.assertIsNone(find_entry(catalog,'codex','work','claude-work'))

    def test_private_state_is_outside_source(self):
        self.assertFalse(data_dir().is_relative_to(ROOT))
        save_json(data_dir()/'settings.json',{'language':'fr'})
        self.assertEqual(json.loads((data_dir()/'settings.json').read_text())['language'],'fr')

    def test_git_context_and_distinct_mission_snapshots(self):
        project=self.path/'project with spaces';project.mkdir()
        subprocess.run(['git','init',str(project)],check=True,capture_output=True)
        (project/'sample.txt').write_text('not read by context')
        context=capture_context(project)
        data=json.loads(context.read_text())
        self.assertTrue(data['status']['ok'])
        self.assertIn('sample.txt',data['status']['output'])
        entry={'tool':'codex','profile':'work','command':'codex-work','available':True}
        first=json.loads(prepare(entry,project,'review','Review the current changes.',True).read_text())
        second=json.loads(prepare(entry,project,'plan','Plan a focused correction.',True).read_text())
        self.assertNotEqual(first['context'],second['context'])
        self.assertTrue(Path(first['context']).exists())
        self.assertEqual(first['outcome'],'unverified')
        self.assertIsNone(first['cost'])
        self.assertIsNone(first['tokens'])

    def test_unavailable_profile_is_blocked(self):
        with self.assertRaises(ValueError):prepare({'available':False},self.path,'implement')

    @unittest.skipUnless(os.name=='nt' and shutil.which('pwsh'), 'PowerShell 7 integration requires Windows')
    def test_powershell_discovers_and_invokes_profile_without_evaluating_arguments(self):
        script=self.path/'profile fixture.ps1'
        result_file=self.path/'received.json'
        request=self.path/'request.json'
        native_args=['--flag','a "quoted" value','line1\nline2',"$(throw 'must stay literal')",'C:\\space here\\file']
        save_json(request,{'tool':'codex','profile':'fixture','command':'codex-fixture-alias','project':str(self.path),'arguments':native_args})
        script.write_text('''param($LaunchScript,$RequestPath,$ResultPath)
function Resolve-AiExecutable { param($Tool); (Get-Command pwsh -CommandType Application | Select-Object -First 1).Source }
function Get-AiProfileDir { param($Tool,$ProfileName); Join-Path $env:TEMP 'ai-dev-nonexistent-fixture' }
function Invoke-AiProfile { param($Tool,$ProfileName,[object[]]$ToolArgs)
    [IO.File]::WriteAllText($ResultPath,(ConvertTo-Json -InputObject @($ToolArgs)),[Text.UTF8Encoding]::new($false))
}
function codex-fixture { Invoke-AiProfile -Tool 'codex' -ProfileName 'fixture' -ToolArgs $args }
Set-Alias codex-fixture-alias codex-fixture
& $LaunchScript -RequestPath $RequestPath
''',encoding='utf-8')
        result=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(script),
                               '-LaunchScript',str(ROOT/'aidev/scripts/Launch.ps1'),'-RequestPath',str(request),'-ResultPath',str(result_file)],
                              capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result_file.read_text()),native_args)

    def test_stream_deck_export_has_subpages_and_english_prompts(self):
        spec=importlib.util.spec_from_file_location('deck_generator',ROOT/'scripts/stream_deck.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        output=module.generate(self.path/'deck.streamDeckProfile',{'Model':'test-device'},'fr',self.path/'links')
        with zipfile.ZipFile(output) as archive:
            manifests=[json.loads(archive.read(name)) for name in archive.namelist() if name.endswith('manifest.json')]
            page_names={m.get('Name') for m in manifests}
            self.assertTrue({'home','prompts','editor','web'}.issubset(page_names))
            for manifest in manifests:
                for controller in manifest.get('Controllers',[]):
                    self.assertLessEqual(len(controller.get('Actions') or {}),15)
            editor=next(m for m in manifests if m.get('Name')=='editor')
            self.assertEqual(len(editor['Controllers'][0]['Actions']),15)
            actions=[a for m in manifests for c in m.get('Controllers',[]) for a in (c.get('Actions') or {}).values()]
            for launcher in ('cursor','vscode','orca','monitor','factory','factory-status','files','guide','status','mission','codex','claude','agy'):
                self.assertTrue(any((launcher+'.lnk') in a['Settings'].get('path','') for a in actions),launcher)
            keys=[a['Settings']['Hotkeys'][0] for a in actions if a['UUID'].endswith('system.hotkey')]
            self.assertTrue(any(k['KeyCmd'] and k['KeyShift'] and k['NativeCode']==83 for k in keys))
            self.assertTrue(any(k['NativeCode']==113 and k['QTKeyCode']==16777265 for k in keys))
            self.assertTrue(any(k['NativeCode']==123 and k['QTKeyCode']==16777275 for k in keys))
            self.assertFalse(any(a['UUID'].endswith('system.website') for a in actions))
            web=next(m for m in manifests if m.get('Name')=='web')
            web_actions=web['Controllers'][0]['Actions'].values()
            self.assertTrue(any('web-work.lnk' in a['Settings'].get('path','') for a in web_actions))
            self.assertTrue(any('browser.lnk' in a['Settings'].get('path','') for a in web_actions))
            prompts=[a for a in actions if a['UUID'].endswith('system.text')]
            self.assertEqual(len(prompts),len(TEXT_PROMPTS))
            for prompt in prompts:
                self.assertTrue(prompt['Settings']['pastedText'].startswith('Communicate in English.'))
                self.assertFalse(prompt['Settings']['isSendingEnter'])


if __name__=='__main__':unittest.main()
