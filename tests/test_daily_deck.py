import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('daily_deck',ROOT/'scripts/stream_deck.py')
deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)


class DailyDeckTests(unittest.TestCase):
    def test_daily_home_icons_media_keys_and_two_distinct_work_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'fr',Path(folder)/'links',[],installed_apps={'capture'})
            with zipfile.ZipFile(archive) as stream:
                pages={n:json.loads(stream.read(n)) for n in stream.namelist() if '/Profiles/' in n and n.endswith('manifest.json')}
                home=next(p for p in pages.values() if p['Name']=='home')
                actions=list(home['Controllers'][0]['Actions'].values())
                self.assertEqual(len(actions),15)
                self.assertEqual([a['Name'] for a in actions[:2]],['DEV','AGENTIC'])
                self.assertNotEqual(actions[0]['Settings']['ProfileUUID'],actions[1]['Settings']['ProfileUUID'])
                media_page=next(p for p in pages.values() if p['Name']=='media')
                media={a['Settings']['Hotkeys'][0]['NativeCode']:a['Settings']['Hotkeys'][0]['QTKeyCode'] for a in media_page['Controllers'][0]['Actions'].values() if 'Hotkeys' in a['Settings']}
                self.assertEqual(media[179],0x01000086)
                self.assertEqual(media[173],0x01000071)
                self.assertFalse(any('spotify.lnk' in a['Settings'].get('path','') for a in actions))
                desktop=next(p for p in pages.values() if p['Name']=='desktop')
                desktop_actions=list(desktop['Controllers'][0]['Actions'].values())
                display_mode=next(a for a in desktop_actions if a['Name']=='MODE ECRAN')
                self.assertTrue(display_mode['Settings']['Hotkeys'][0]['KeyCmd'])
                self.assertEqual(display_mode['Settings']['Hotkeys'][0]['NativeCode'],80)
                self.assertTrue(any(a['Name']=='ECRAN GAUCHE' and a['Settings']['Hotkeys'][0]['KeyShift'] for a in desktop_actions))
                report=deck.audit_profile(archive)
                self.assertEqual(report['buttons'],sum(len(p['Controllers'][0]['Actions'] or {}) for p in pages.values()))
                for filename,page in pages.items():
                    for controller in page['Controllers']:
                        for button in (controller['Actions'] or {}).values():
                            asset=filename.rsplit('/',1)[0]+'/'+button['States'][0]['Image']
                            self.assertTrue(stream.read(asset).startswith(b'\x89PNG'))
                            self.assertEqual(button['States'][0]['TitleAlignment'],'bottom')

    def test_spotify_uses_local_install_or_explicit_browser_choice(self):
        from aidev.__main__ import main
        for available in (True,False):
            with patch('sys.argv',['ai-dev','--action','spotify']), patch('aidev.migration.migrate_legacy'), \
                 patch('aidev.desktop.installed_tools',return_value={'spotify':'Spotify.exe'} if available else {}), \
                 patch('aidev.desktop.open_tool') as launch, patch('aidev.browsers.browser_dialog') as browser:
                main()
                if available:launch.assert_called_once_with('spotify');browser.assert_not_called()
                else:browser.assert_called_once_with('https://open.spotify.com/');launch.assert_not_called()


if __name__=='__main__':unittest.main()
