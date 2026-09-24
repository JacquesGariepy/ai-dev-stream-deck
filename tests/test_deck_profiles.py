import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from aidev.deck_profiles import load_selection, save_selections, selection_id

ROOT = Path(__file__).resolve().parents[1]


def entry(tool='codex', profile='work', available=True, command=None):
    return dict(tool=tool, profile=profile, command=command or tool+'-'+profile,
                kind='powershell', available=available, initialized=True)


class DeckProfileTests(unittest.TestCase):
    def test_private_selection_roundtrip_and_traversal_rejection(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR':folder}):
            rows=[entry(command='custom "quoted" alias'),entry(profile='personal')]
            save_selections(rows)
            self.assertEqual(load_selection(selection_id(rows[0]))['command'],rows[0]['command'])
            self.assertNotEqual(selection_id(rows[0]),selection_id(rows[1]))
            with self.assertRaises(ValueError): load_selection('../settings')
            with self.assertRaises(ValueError): load_selection('a'*64)

    def test_all_profiles_are_reachable_and_paginated_without_key_overflow(self):
        spec=importlib.util.spec_from_file_location('deck', ROOT/'scripts/stream_deck.py')
        deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
        rows=[entry(profile='account-'+str(n)) for n in range(25)]
        rows += [entry(tool='cursor',available=False)]
        rows += [entry(tool='tool-'+str(n)) for n in range(13)]
        with tempfile.TemporaryDirectory() as folder:
            path=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'fr',Path(folder)/'links',rows)
            with zipfile.ZipFile(path) as archive:
                pages={Path(name).parent.name.lower():json.loads(archive.read(name)) for name in archive.namelist() if '/Profiles/' in name and name.endswith('manifest.json')}
            home=next(key for key,page in pages.items() if page['Name']=='home')
            visited=set()
            def walk(key):
                if key in visited:return
                visited.add(key)
                buttons=pages[key]['Controllers'][0]['Actions'] or {}
                self.assertLessEqual(len(buttons),15)
                for button in buttons.values():
                    if button['UUID'].endswith('profile.openchild'):
                        target=button['Settings']['ProfileUUID'].lower()
                        self.assertIn(target,pages)
                        walk(target)
            walk(home)
            actions=[button for key in visited for button in (pages[key]['Controllers'][0]['Actions'] or {}).values()]
            action_ids=[a['ActionID'] for a in actions]
            self.assertEqual(len(action_ids),len(set(action_ids)))
            targets=[a['Settings']['ProfileUUID'] for a in actions if a['UUID'].endswith('profile.openchild')]
            self.assertEqual(len(targets),len(set(targets)), 'Native folders must have exactly one parent')
            for row in rows:
                expected='profile-'+selection_id(row)+'.lnk'
                matches=[a for a in actions if expected in a['Settings'].get('path','')]
                self.assertEqual(len(matches),2 if row['tool'] in ('codex','claude','agy') else 1,expected)
                if not row['available']:
                    self.assertTrue(matches[0]['States'][0]['Title'].startswith('!'))
            self.assertTrue(any('deck-refresh-fr.lnk' in a['Settings'].get('path','') for a in actions))
            self.assertTrue(any(pages[key]['Name'].endswith('-1') for key in visited))

    @unittest.skipUnless(os.name=='nt','Windows Tk interface')
    def test_exact_button_overrides_remembered_account_and_missing_button_fails(self):
        import time
        from aidev.ui import Panel
        from aidev.storage import save_settings
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR':folder}):
            save_settings({'profiles':{'codex':'codex-personal'}})
            rows=[entry(),entry(profile='personal')]
            with patch('aidev.ui.discover',return_value={'entries':rows}):
                panel=Panel(initial_selection=rows[0])
                try:
                    panel.root.withdraw()
                    deadline=time.monotonic()+3
                    while panel.detecting and time.monotonic()<deadline:
                        panel.root.update();time.sleep(.02)
                    self.assertEqual(panel.profile_rows[panel.profile.get()]['command'],'codex-work')
                finally:panel.root.destroy()
            with patch('aidev.ui.discover',return_value={'entries':[rows[1]]}):
                panel=Panel(initial_selection=rows[0])
                try:
                    panel.root.withdraw()
                    deadline=time.monotonic()+3
                    while panel.detecting and time.monotonic()<deadline:
                        panel.root.update();time.sleep(.02)
                    self.assertEqual(panel.profile.get(),'')
                    self.assertEqual(str(panel.open_button['state']),'disabled')
                    self.assertEqual(panel.catalog_error,panel.text('profile_removed'))
                finally:panel.root.destroy()


if __name__=='__main__':unittest.main()
