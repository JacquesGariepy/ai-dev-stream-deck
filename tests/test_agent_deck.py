import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from aidev.shelllink import read_link, shell_link

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agent_deck_script',ROOT/'scripts/agent_deck.py')
script=importlib.util.module_from_spec(spec);spec.loader.exec_module(script)
SCRIPT='C:\\Tools\\ai-dev\\agentdeck\\ai.ps1'


class AgentDeckTests(unittest.TestCase):
    def test_every_key_is_native_or_an_agent_shortcut_never_the_panel(self):
        with tempfile.TemporaryDirectory() as folder:
            output,audit=script.generate(Path(folder)/'deck.zip',{'Model':'20GBA9901'},SCRIPT,'C:\\Links',Path(folder)/'links',
                                         native_shortcuts=False)
            self.assertGreater(audit['website'],0)
            with zipfile.ZipFile(output) as archive:
                pages={json.loads(archive.read(n))['Name']:json.loads(archive.read(n)) for n in archive.namelist() if '/Profiles/' in n and n.endswith('manifest.json')}
            home=pages['home']['Controllers'][0]['Actions']
            self.assertEqual([home[f'{c},0']['Name'] for c in range(5)],['ASK','FIX','REVIEW','COMMIT','EXPLAIN'])
            for link in (Path(folder)/'links').glob('*.lnk'):
                parsed=read_link(link.read_bytes())
                self.assertTrue(parsed['target'].lower().endswith('powershell.exe'))
                self.assertIn('-WindowStyle Hidden',parsed['arguments'])
                self.assertIn('"'+SCRIPT+'"',parsed['arguments'])
                self.assertNotIn('launch.py',parsed['arguments'])

    def test_intents_define_harness_mode_and_prompt(self):
        intents=json.loads((ROOT/'agentdeck/intents.json').read_text('utf-8'))
        for name,value in intents['intents'].items():
            self.assertIn(value['harness'],('claude','codex','agy'),name)
            self.assertIn(value['mode'],('auto','readonly'),name)
            self.assertTrue(value['prompt'])
        self.assertIn('Never push',intents['guardrails'])

    def test_shell_link_roundtrip_and_validation(self):
        data=shell_link('C:\\Windows\\notepad.exe','"C:\\a b\\x.txt"','C:\\a b')
        self.assertEqual(read_link(data),{'target':'C:\\Windows\\notepad.exe','show':7,'working_dir':'C:\\a b','arguments':'"C:\\a b\\x.txt"'})
        with self.assertRaises(ValueError):shell_link('relative.exe')


if __name__=='__main__':unittest.main()
