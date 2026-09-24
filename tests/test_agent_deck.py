import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from aidev.shelllink import read_link, shell_link
from aidev.agent_deck import AgentDeck
from aidev.deck_export import audit_profile, write_profile
from aidev.deck_layout import Grid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agent_deck_script',ROOT/'scripts/agent_deck.py')
script=importlib.util.module_from_spec(spec);spec.loader.exec_module(script)
SCRIPT='C:\\Tools\\ai-dev\\agentdeck\\ai.ps1'


class AgentDeckTests(unittest.TestCase):
    def test_every_key_is_native_or_an_agent_shortcut_never_the_panel(self):
        with tempfile.TemporaryDirectory() as folder:
            output,audit=script.generate(Path(folder)/'deck.zip',{'Model':'20GBA9901'},SCRIPT,'C:\\Links',Path(folder)/'links',
                                         native_shortcuts=False)
            self.assertGreater(audit['hotkeys'], 30)
            with zipfile.ZipFile(output) as archive:
                pages={json.loads(archive.read(n))['Name']:json.loads(archive.read(n)) for n in archive.namelist() if '/Profiles/' in n and n.endswith('manifest.json')}
            home=pages['home']['Controllers'][0]['Actions']
            self.assertEqual([home[f'{c},0']['Name'] for c in range(5)],
                             ['DEV', 'IA', 'QUOTIDIEN', 'MEDIA', 'RECHERCHE'])
            self.assertEqual(len(home), 15)
            self.assertTrue(all(home[f'{c},0']['UUID'].endswith('profile.openchild') for c in range(5)))
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

    def test_dynamic_local_tools_are_direct_and_profile_ids_are_stable(self):
        apps=[{'name':'Docker Desktop','category':'dev','deck_id':'a'*16,'app_id':'Docker.DockerDesktop'}]
        terminals=[{'label':'PowerShell 7','kind':'powershell','deck_id':'b'*16,
                    'executable':'C:\\Program Files\\PowerShell\\7\\pwsh.exe','distro':None}]
        with tempfile.TemporaryDirectory() as folder:
            first=Path(folder)/'one.zip'; second=Path(folder)/'two.zip'
            args=({'Model':'20GBA9901','UUID':'device'},SCRIPT,'C:\\Links',Path(folder)/'links')
            script.generate(first,*args,native_shortcuts=False,apps=apps,terminals=terminals)
            script.generate(second,*args,native_shortcuts=False,apps=apps,terminals=terminals)
            with zipfile.ZipFile(first) as one, zipfile.ZipFile(second) as two:
                self.assertEqual(set(one.namelist()),set(two.namelist()))
                text='\n'.join(one.read(name).decode('utf-8') for name in one.namelist() if name.endswith('manifest.json'))
            self.assertIn('ai-app-'+'a'*16+'.lnk',text)
            self.assertIn('ai-terminal-'+'b'*16+'.lnk',text)
            self.assertNotIn('launch.py',text)

    def test_empty_workstation_has_useful_home_and_search_uses_browser_choice(self):
        deck = AgentDeck(SCRIPT, language='en', harnesses=[]).build()
        self.assertEqual([key.title for key in deck.pages['home'].keys[:5]],
                         ['DEV', 'AI', 'DAILY', 'MEDIA', 'SEARCH'])
        self.assertTrue(deck.pages['terminals'].keys)
        self.assertEqual(deck.pages['apps'].keys[0].target, 'ai-refresh')
        self.assertEqual({key.target for key in deck.pages['cli'].keys}, {'ai-refresh', 'ai-settings'})
        self.assertFalse(any(target in deck.shortcuts for target in ('ai-claude', 'ai-codex', 'ai-agy')))
        self.assertFalse(any(key.target.startswith('ai-app-') for page in deck.pages.values()
                             for key in page.keys if key.kind == 'open'))
        self.assertEqual(deck.profile_name, 'AI Dev Agentic')
        self.assertEqual(deck.stable_id, 'ai-dev-agentic-v1')
        searches = [key for key in deck.pages['search'].keys if key.kind == 'open'
                    and key.target.startswith('ai-search-')]
        self.assertEqual(len(searches), 7)
        self.assertTrue(all('Review your query' in key.description for key in searches))
        # Native website keys bypass the user's chosen work/personal browser.
        self.assertFalse(any(key.kind == 'website' for page in deck.pages.values() for key in page.keys))

    def test_desktop_ai_and_featured_dev_are_exact_installed_apps(self):
        apps = [dict(name=name, category=category, deck_id=f'{index:016x}') for index, (name, category) in enumerate([
            ('ChatGPT', 'agentic'), ('Claude', 'agentic'), ('Docker Desktop', 'dev'),
            ('GitHub Desktop', 'dev'), ('Spotify', 'daily')])]
        deck = AgentDeck(SCRIPT, apps=apps).build()
        first = deck.pages['ai'].keys[:2]
        self.assertEqual({key.name for key in first}, {'ChatGPT Desktop', 'Claude Desktop'})
        self.assertEqual({key.icon for key in first}, {'chatgpt', 'claude'})
        self.assertTrue(all(key.target.startswith('ai-app-') for key in first))
        self.assertTrue({'Docker Desktop', 'GitHub Desktop'}.issubset(
            {key.name for key in deck.pages['dev'].keys}))
        self.assertIn('Spotify', {key.name for key in deck.pages['media'].keys})
        self.assertNotIn('ai-web-spotify', {key.target for key in deck.pages['media'].keys if key.kind == 'open'})

    def test_large_app_catalog_is_complete_unique_and_has_bounded_navigation(self):
        apps = [dict(name=f'Tool {index:03}', category='daily', deck_id=f'{index:016x}') for index in range(300)]
        for grid in (Grid(5, 3), Grid(3, 2)):
            with self.subTest(grid=grid):
                deck = AgentDeck(SCRIPT, grid, apps=apps + [apps[0]]).build()
                catalog = [page for name, page in deck.pages.items() if name.startswith('catalog-')]
                app_targets = [key.target for page in catalog for key in page.keys if key.kind == 'open']
                self.assertEqual(len(app_targets), len(apps))
                self.assertEqual(set(app_targets), {'ai-app-' + app['deck_id'] for app in apps})
                self.assertTrue(all(len(page.keys) <= grid.capacity - 1 for page in catalog))
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / 'profile.zip'
                    write_profile(deck, output, {'Model': '20GBA9901'}, 'C:\\Links', grid)
                    self.assertGreater(audit_profile(output, grid=grid)['buttons'], 300)

    def test_every_target_resolves_and_windows_shortcuts_cover_common_work(self):
        deck = AgentDeck(SCRIPT, language='en').build()
        seen = set()
        def visit(name):
            if name in seen:
                return
            seen.add(name)
            for key in deck.pages[name].keys:
                if key.kind == 'folder':
                    self.assertIn(key.target, deck.pages)
                    self.assertTrue(deck.pages[key.target].keys)
                    visit(key.target)
                elif key.kind == 'open':
                    self.assertIn(key.target, deck.shortcuts)
                    target, args = deck.shortcuts[key.target]
                    self.assertNotIn('launch.py', args)
                    self.assertTrue(target.endswith('powershell.exe'))
        visit('home')
        self.assertEqual(seen, set(deck.pages))
        specs = [key.target for page in deck.pages.values() for key in page.keys if key.kind == 'hotkey']
        for letter in ('V', 'H', 'P', 'A', 'N', 'Z', 'E', 'R', 'L'):
            self.assertTrue(any(spec['key'] == ord(letter) and spec['win'] for spec in specs), letter)
        self.assertTrue(any(spec['key'] == 83 and spec['win'] and spec['shift'] for spec in specs))
        self.assertTrue(any(spec['key'] == 27 and spec['ctrl'] and spec['shift'] for spec in specs))
        for arrow in (37, 39):
            self.assertTrue(any(spec['key'] == arrow and spec['win'] and spec['shift'] for spec in specs))
            self.assertTrue(any(spec['key'] == arrow and spec['win'] and spec['ctrl'] for spec in specs))
        self.assertEqual(len([key for key in deck.pages['git'].keys if key.kind == 'hotkey']), 11)
        self.assertFalse(any(name.startswith('ai-git-') for name in deck.shortcuts))
        self.assertIn('ai-shell-setup', deck.shortcuts)

    def test_git_keys_use_active_terminal_native_chords_without_launchers(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _ = script.generate(Path(directory) / 'deck.zip', {'Model': '20GBA9901'}, SCRIPT,
                                        'C:\\Links', Path(directory) / 'links', native_shortcuts=False,
                                        language='en')
            with zipfile.ZipFile(output) as archive:
                pages = [json.loads(archive.read(name)) for name in archive.namelist()
                         if '/Profiles/' in name and name.endswith('manifest.json')]
            git_pages = [page for page in pages if page.get('Name') == 'git']
            self.assertTrue(git_pages)
            expected = ['STATUS', 'DIFF', 'LOG', 'FETCH', 'PULL', 'PUSH', 'STAGE', 'SWITCH',
                        'NEW BRANCH', 'STASH', 'APPLY STASH']
            for page in git_pages:
                buttons = page['Controllers'][0]['Actions'].values()
                native = [button for button in buttons if button['UUID'].endswith('system.hotkey')]
                self.assertEqual([button['Name'] for button in native], expected)
                for index, button in enumerate(native):
                    chord = button['Settings']['Hotkeys'][0]
                    self.assertEqual(chord['VKeyCode'], 124 + index)
                    self.assertEqual(chord['QTKeyCode'], 16777276 + index)
                    self.assertTrue(chord['KeyCtrl'])
                    self.assertTrue(chord['KeyOption'])
                    self.assertFalse(chord['KeyShift'])
                    self.assertFalse(chord['KeyCmd'])
                    self.assertIn('Active PowerShell prompt/current folder', button['UserInput'])
            self.assertFalse(list((Path(directory) / 'links').glob('ai-git-*.lnk')))

    def test_all_detected_harnesses_and_exact_profiles_get_direct_buttons(self):
        commands = [('claude', 'personal', 'claude-personal'), ('claude', 'client-team', 'claude-client-team'),
                    ('codex', 'work', 'codex-work'), ('cursor', 'personal', 'cursor-personal'),
                    ('gemini', 'default', 'gemini')]
        entries = [dict(tool=tool, profile=profile, command=command, deck_id=f'{index:016x}')
                   for index, (tool, profile, command) in enumerate(commands)]
        for grid in (Grid(5, 3), Grid(3, 2)):
            deck = AgentDeck(SCRIPT, grid, harnesses=entries).build()
            buttons = [key for name, page in deck.pages.items() if name.startswith('cli-tool-')
                       for key in page.keys if key.kind == 'open']
            self.assertEqual({key.target for key in buttons}, {'ai-cli-' + entry['deck_id'] for entry in entries})
            self.assertEqual({key.name for key in buttons}, {entry['command'] + ' (' + entry['profile'] + ')' for entry in entries})
            self.assertEqual({key.target for key in deck.pages['cli'].keys if key.kind == 'folder'},
                             {'cli-tool-claude', 'cli-tool-codex', 'cli-tool-cursor', 'cli-tool-gemini'})
            for entry in entries:
                self.assertTrue(deck.shortcuts['ai-cli-' + entry['deck_id']][1].endswith('cli-' + entry['deck_id']))
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'profile.zip'
                write_profile(deck, output, {'Model': '20GBA9901'}, 'C:\\Links', grid)
                self.assertGreater(audit_profile(output, grid=grid)['open'], len(entries))

    def test_many_named_profiles_are_grouped_without_long_pagination(self):
        entries = [dict(tool='claude', profile=f'client-{index:03}', command=f'claude-client-{index:03}',
                        deck_id=f'{index:016x}') for index in range(80)]
        grid = Grid(3, 2)
        deck = AgentDeck(SCRIPT, grid, harnesses=entries).build()
        pages = [page for name, page in deck.pages.items() if name.startswith('cli-tool-')]
        self.assertTrue(all(len(page.keys) <= grid.capacity - 1 for page in pages))
        self.assertEqual(sum(key.kind == 'open' for page in pages for key in page.keys), len(entries))

    def test_power_user_diagnostics_are_direct_and_keep_primary_pages_within_grid(self):
        apps = [dict(name=name, category=category, deck_id=f'{index:016x}') for index, (name, category) in enumerate([
            ('Docker Desktop', 'dev'), ('GitHub Desktop', 'dev'), ('Visual Studio Code', 'dev'),
            ('Cursor', 'dev'), ('Postman', 'dev'), ('DevToys', 'dev'), ('PowerToys', 'daily'),
            ('Outlook', 'daily'), ('Teams', 'daily'), ('Slack', 'daily')])]
        for language in ('fr', 'en'):
            deck = AgentDeck(SCRIPT, apps=apps, language=language).build()
            self.assertEqual(deck.pages['home'].keys[6].target, 'power-user')
            for page in ('dev', 'system'):
                self.assertTrue(any(key.kind == 'folder' and key.target == 'power-user'
                                    for key in deck.pages[page].keys))
                self.assertLessEqual(len(deck.pages[page].keys), 14)
            diagnostic_keys = [key for key in deck.pages['power-user'].keys if key.kind == 'open']
            self.assertEqual({key.target for key in diagnostic_keys}, {'ai-diag-' + action for action in
                ('ports', 'processes', 'connection', 'dns', 'routes', 'path', 'disk', 'startup', 'wsl', 'docker', 'longpaths')})
            self.assertLessEqual(len(deck.pages['power-user'].keys), 14)
            self.assertEqual(len(deck.pages['home'].keys), 15)
            for key in diagnostic_keys:
                self.assertTrue(deck.shortcuts[key.target][1].endswith(key.target.removeprefix('ai-')))
                self.assertTrue(key.description)
            self.assertTrue(any(key.target == 'ai-windows-files' for key in deck.pages['dev'].keys if key.kind == 'open'))


if __name__=='__main__':unittest.main()
