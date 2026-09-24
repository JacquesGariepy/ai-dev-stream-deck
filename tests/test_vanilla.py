"""Clean-install guarantees, independent of the maintainer's workstation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
from aidev.orchestrators import selected
from aidev.storage import settings, save_json
from aidev.runtime import capture_context, prepare

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vanilla_deck',ROOT/'scripts/stream_deck.py')
deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)


class VanillaTests(unittest.TestCase):
    def test_empty_install_has_no_provider_desktop_or_orchestrator_preferences(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder,'AI_DEV_FACTORY':''}):
            self.assertEqual(settings(),{})
            self.assertEqual(selected()['kind'],'none')
            archive=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'en',Path(folder)/'links',[],installed_apps={})
            with zipfile.ZipFile(archive) as stream:
                pages=[json.loads(stream.read(n)) for n in stream.namelist() if '/Profiles/' in n and n.endswith('manifest.json')]
            actions=[a for p in pages for c in p.get('Controllers',[]) for a in (c.get('Actions') or {}).values()]
            targets=[Path(a['Settings'].get('path','').strip('"')).stem for a in actions]
            self.assertFalse({'codex','claude','agy','cursor','vscode','orca'} & set(targets))
            self.assertFalse(any(target.startswith('profile-') for target in targets))
            self.assertEqual(settings(),{})

    def test_any_available_harness_can_be_featured_on_home(self):
        with tempfile.TemporaryDirectory() as folder:
            entries=[{'tool':'custom-engine','profile':'local','command':'my-engine','available':True,'kind':'powershell'}]
            archive=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'en',Path(folder)/'links',entries,installed_apps={})
            with zipfile.ZipFile(archive) as stream:
                pages=[json.loads(stream.read(n)) for n in stream.namelist() if n.endswith('manifest.json')]
            home=next(p for p in pages if p.get('Name')=='home')
            self.assertIn('CUSTOM-ENGINE',[a['Name'] for a in home['Controllers'][0]['Actions'].values()])

    def test_device_selection_requires_choice_when_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,identifier in (('one','device-a'),('duplicate','device-a')):
                save_json(root/(name+'.sdProfile')/'manifest.json',{'Device':{'Model':'20GBA9901','UUID':identifier}})
            self.assertEqual(deck.select_device(root)['UUID'],'device-a')
            save_json(root/'two.sdProfile/manifest.json',{'Device':{'Model':'20GBA9901','UUID':'device-b'}})
            with self.assertRaises(ValueError):deck.select_device(root)
            self.assertEqual(deck.select_device(root,'device-b')['UUID'],'device-b')

    def test_missing_project_does_not_use_current_checkout(self):
        with self.assertRaises(ValueError):capture_context('')
        with self.assertRaises(ValueError):prepare({'available':True},'','implement')

    @unittest.skipUnless(os.name=='nt','Windows Tk')
    def test_clean_panel_opens_without_installed_harnesses_or_saved_project(self):
        from aidev.ui import Panel
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder,'AI_DEV_FACTORY':''}), patch('aidev.ui.discover',return_value={'entries':[]}) as discover:
            panel=Panel()
            try:
                panel.root.withdraw()
                deadline=time.monotonic()+3
                while panel.detecting and time.monotonic()<deadline:
                    panel.root.update();time.sleep(.02)
                panel.root.update()
                self.assertEqual(panel.project.get(),'')
                self.assertEqual(panel.tool.get(),'')
                self.assertEqual(str(panel.open_button['state']),'disabled')
                self.assertEqual(settings(),{})
                discover.assert_called_once()
            finally:panel.root.destroy()


if __name__=='__main__':unittest.main()
