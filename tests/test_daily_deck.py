import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('daily_deck',ROOT/'scripts/stream_deck.py')
deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)


def pages_of(archive):
    with zipfile.ZipFile(archive) as stream:
        return {n:json.loads(stream.read(n)) for n in stream.namelist() if '/Profiles/' in n and n.endswith('manifest.json')}


def page(pages,name):
    return next(p for p in pages.values() if p['Name']==name)


def keys(page):
    return page['Controllers'][0]['Actions'] or {}


class ExpertDeckTests(unittest.TestCase):
    def generate(self,folder,model='20GBA9901',language='fr',entries=None,installed=frozenset({'capture'}),**extra):
        return deck.generate(Path(folder)/'deck.zip',{'Model':model,'UUID':'x'},language,Path(folder)/'links',entries or [],installed_apps=set(installed),**extra)

    def test_cockpit_home_has_fixed_agentic_dev_and_system_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=self.generate(folder)
            pages=pages_of(archive)
            home=keys(page(pages,'home'))
            self.assertEqual(len(home),15)
            self.assertEqual(home['0,0']['Name'],'MISSION')
            self.assertEqual(home['4,0']['Name'],'SESSIONS')
            self.assertEqual([home[f'{c},1']['Name'] for c in range(5)],['TERMINAL','EDITEUR','GIT','BUILD TEST','PROMPTS'])
            self.assertEqual([home[f'{c},2']['Name'] for c in range(5)],['AGENTIC','DEV','SYSTEME','MEDIA','ACTUALISER'])
            # Without harnesses, the harness slots keep useful agentic keys instead of shifting the layout.
            self.assertEqual([home[f'{c},0']['Name'] for c in (1,2,3)],['PROFILS','CONTEXTE','AI WEB'])
            self.assertFalse(any(a['UUID'].endswith('backtoparent') for a in home.values()))
            report=deck.audit_profile(archive)
            self.assertEqual(report['buttons'],sum(len(keys(p)) for p in pages.values()))
            with zipfile.ZipFile(archive) as stream:
                for filename,value in pages.items():
                    for button in keys(value).values():
                        self.assertTrue(stream.read(filename.rsplit('/',1)[0]+'/'+button['States'][0]['Image']).startswith(b'\x89PNG'))
                        self.assertEqual(button['States'][0]['TitleAlignment'],'bottom')

    def test_back_is_always_top_left_and_media_desktop_keys_are_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            pages=pages_of(self.generate(folder))
            for value in pages.values():
                if value['Name'] in ('home',''):continue
                self.assertTrue(keys(value)['0,0']['UUID'].endswith('backtoparent'),value['Name'])
            media={a['Settings']['Hotkeys'][0]['NativeCode']:a['Settings']['Hotkeys'][0]['QTKeyCode'] for a in keys(page(pages,'media')).values() if 'Hotkeys' in a['Settings']}
            self.assertEqual(media[179],0x01000086);self.assertEqual(media[173],0x01000071)
            desktop=list(keys(page(pages,'desktop')).values())
            mode=next(a for a in desktop if a['Name']=='MODE ECRAN')
            self.assertTrue(mode['Settings']['Hotkeys'][0]['KeyCmd']);self.assertEqual(mode['Settings']['Hotkeys'][0]['NativeCode'],80)
            self.assertTrue(any(a['Name']=='ECRAN GAUCHE' and a['Settings']['Hotkeys'][0]['KeyShift'] for a in desktop))
            self.assertFalse(any('spotify.lnk' in a['Settings'].get('path','') for p in pages.values() for a in keys(p).values()))

    def test_git_and_run_pages_expose_one_press_expert_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            pages=pages_of(self.generate(folder,language='en'))
            git={Path(a['Settings'].get('path','').strip('"')).stem for a in keys(page(pages,'git-ops')).values()}
            for action in ('status','diff','log','fetch','pull','push','stage','commit','branch','switch','stash','unstash'):
                self.assertIn('git-'+action,git)
            run={Path(a['Settings'].get('path','').strip('"')).stem for a in keys(page(pages,'run')).values()}
            self.assertTrue({'task-build','task-test','task-lint','task-dev','task-types','task-format','project-tasks'}<=run)
            agentic={Path(a['Settings'].get('path','').strip('"')).stem for a in keys(page(pages,'agentic')).values()}
            self.assertTrue({'mission-plan','mission-implement','mission-review','mission-debug','mission-test','mission-handoff'}<=agentic)

    def test_every_supported_grid_paginates_with_more_bottom_right(self):
        rows=[{'tool':'tool-%d'%n,'profile':'p','command':'c%d'%n,'kind':'powershell','available':True} for n in range(6)]
        for model,(cols,grid_rows) in (('20GAI9901',(3,2)),('20GBD9901',(4,2)),('20GBA9901',(5,3)),('20GAT9901',(8,4))):
            with tempfile.TemporaryDirectory() as folder:
                archive=self.generate(folder,model=model,entries=rows)
                report=deck.audit_profile(archive)
                self.assertGreater(report['pages'],10)
                for value in pages_of(archive).values():
                    for position,button in keys(value).items():
                        col,row=map(int,position.split(','))
                        self.assertLess(col,cols);self.assertLess(row,grid_rows)
                        if button['Name'] in ('MORE','SUITE') and button['UUID'].endswith('openchild'):
                            self.assertEqual(position,f'{cols-1},{grid_rows-1}',model)
                home=keys(page(pages_of(archive),'home'))
                self.assertEqual(home['0,0']['Name'],'MISSION')
                if cols*grid_rows<15:self.assertIn(home[f'{cols-1},{grid_rows-1}']['Name'],('MORE','SUITE'))

    def test_grid_override_and_unknown_model_default(self):
        self.assertEqual(deck.Grid.parse('8x4').capacity,32)
        with self.assertRaises(ValueError):deck.Grid.parse('1x1')
        self.assertEqual(deck.Grid.for_device({'Model':'unknown'}),deck.Grid(5,3))
        with tempfile.TemporaryDirectory() as folder:
            archive=deck.generate(Path(folder)/'d.zip',{'Model':'custom'},'en',Path(folder)/'l',[],installed_apps=set(),grid='4x2')
            self.assertTrue(all(len(keys(p))<=8 for p in pages_of(archive).values()))

    def test_shortcut_manifest_matches_the_powershell_validation(self):
        built=deck.build('en',[{'tool':'codex','profile':'work','command':'codex-work','kind':'powershell','available':True}],set(),
                         [{'id':'a'*64,'name':'Claude','category':'agentic'}],[{'id':'b'*64,'name':'fs','host':'Claude'}])
        script=(ROOT/'scripts/Create-Shortcuts.ps1').read_text()
        name=re.compile(re.search(r"\$namePattern = '([^']+)'",script).group(1))
        arguments=re.compile(re.search(r"\$argumentPattern = '([^']+)'",script).group(1))
        manifest=built.shortcut_manifest()
        for entry in manifest:
            self.assertTrue(name.fullmatch(entry['name']),entry)
            self.assertTrue(arguments.fullmatch(entry['arguments']),entry)
        names={entry['name'] for entry in manifest}
        self.assertTrue({'git-push','task-test','mission-plan','terminal','factory','deck-refresh-fr'}<=names)
        from aidev.deck_layout import command_line
        with self.assertRaises(ValueError):command_line(['--url','bad"quote'])

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
