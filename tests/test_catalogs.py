import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from aidev import app_catalog,mcp_catalog,project_tasks


class CatalogTests(unittest.TestCase):
    def test_mcp_jsonc_is_sanitized_and_activation_is_tristate(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}):
            config=Path(folder)/'mcp.json'
            config.write_text('''{// a comment\n"mcpServers": {"alpha": {"command":"secret-command","note":"literal ,}","env":{"TOKEN":"secret-token"},},"beta":{"url":"https://example.invalid/key","enabled":false}}}''',encoding='utf-8')
            with patch('aidev.mcp_catalog.sources',return_value=[('VS Code',config)]):
                entries=mcp_catalog.discover_mcp()
            self.assertEqual([e['enabled'] for e in entries],['unspecified','disabled'])
            serialized=json.dumps(entries)
            self.assertNotIn('secret-command',serialized);self.assertNotIn('secret-token',serialized);self.assertNotIn('/key',serialized)
            inventory=(Path(folder)/'mcp-inventory.json').read_text('utf-8')
            self.assertNotIn('secret-command',inventory);self.assertNotIn('secret-token',inventory)

    def test_application_identity_is_exact_and_categories_cover_ai_and_dev(self):
        raw=json.dumps([{'Name':'ChatGPT','AppID':'chat.exact!App'},{'Name':'Visual Studio Code','AppID':'code.exact'},{'Name':'Word','AppID':'word.exact'}])
        completed=type('Result',(),{'returncode':0,'stdout':raw})()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}), \
             patch('aidev.app_catalog.powershell',return_value='pwsh.exe'),patch('aidev.app_catalog.subprocess.run',return_value=completed):
            entries=app_catalog.discover_apps()
        self.assertEqual({e['category'] for e in entries},{'agentic','dev','daily'})
        self.assertEqual(next(e for e in entries if e['name']=='ChatGPT')['app_id'],'chat.exact!App')

    def test_project_scripts_are_discovered_without_execution(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}):
            root=Path(folder)/'project';root.mkdir();(root/'tests').mkdir()
            (root/'package.json').write_text('{"scripts":{"build":"do anything","bad name":"ignored"}}',encoding='utf-8')
            (root/'pyproject.toml').write_text('[project]\nname="fixture"',encoding='utf-8')
            from aidev.storage import save_settings
            save_settings({'project':str(root)})
            with patch('aidev.project_tasks.shutil.which',side_effect=lambda x:'C:/tools/'+x+'.exe'):
                rows=project_tasks.tasks()
            names={row['name'] for row in rows}
            self.assertIn('npm run build',names);self.assertNotIn('npm run bad name',names)
            self.assertIn('Python: unittest discovery',names);self.assertNotIn('Python: pytest',names)

    def test_dynamic_deck_reaches_every_app_and_mcp_button(self):
        import importlib.util
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('catalog_deck',root/'scripts/stream_deck.py')
        deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
        apps=[{'id':f'{n:064x}','name':'App '+str(n),'category':('agentic' if n<2 else 'dev' if n<17 else 'daily')} for n in range(45)]
        mcps=[{'id':f'{100+n:064x}','name':'Server '+str(n),'host':'Host'} for n in range(15)]
        with tempfile.TemporaryDirectory() as folder:
            output=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'en',Path(folder)/'links',[],installed_apps={'capture'},desktop_entries=apps,mcp_entries=mcps)
            with zipfile.ZipFile(output) as archive:
                pages=[json.loads(archive.read(name)) for name in archive.namelist() if '/Profiles/' in name and name.endswith('manifest.json')]
        actions=[a for page in pages for a in (page['Controllers'][0]['Actions'] or {}).values()]
        paths=[a['Settings'].get('path','') for a in actions]
        for entry in apps:self.assertTrue(any(('app-'+entry['id']+'.lnk') in path for path in paths))
        for entry in mcps:self.assertTrue(any(('mcp-'+entry['id']+'.lnk') in path for path in paths))
        self.assertTrue(any(page['Name']=='daily-apps-2' for page in pages))
        self.assertTrue(all(len(page['Controllers'][0]['Actions'] or {})<=15 for page in pages))

    def test_dev_home_features_installed_workstation_tools(self):
        import importlib.util
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('featured_deck',root/'scripts/stream_deck.py')
        deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
        names=['PowerShell','Docker Desktop','GitHub Desktop','Visual Studio Code','Postman','Notepad++']
        apps=[{'id':f'{200+n:064x}','name':name,'category':'dev'} for n,name in enumerate(names)]
        with tempfile.TemporaryDirectory() as folder:
            output=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'en',Path(folder)/'links',[],installed_apps=set(),desktop_entries=apps)
            with zipfile.ZipFile(output) as archive:
                pages=[json.loads(archive.read(name)) for name in archive.namelist() if '/Profiles/' in name and name.endswith('manifest.json')]
        dev=next(page for page in pages if page['Name']=='dev')
        actions=list(dev['Controllers'][0]['Actions'].values())
        visible={action['Name'] for action in actions}
        self.assertTrue({'Docker Desktop','GitHub Desktop','Visual Studio Code','Postman'}.issubset(visible))
        vscode=next(action for action in actions if action['Name']=='Visual Studio Code')
        self.assertEqual(vscode['States'][0]['Title'],'VS CODE')
        self.assertNotIn('PowerShell',visible)
        self.assertEqual(len(actions),15)

    def test_agentic_home_features_installed_ai_desktop_apps_with_icons(self):
        import importlib.util
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('agentic_deck',root/'scripts/stream_deck.py')
        deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
        apps=[{'id':f'{300+n:064x}','name':name,'category':'agentic'} for n,name in enumerate(('Claude','ChatGPT','LM Studio'))]
        with tempfile.TemporaryDirectory() as folder:
            output=deck.generate(Path(folder)/'deck.zip',{'Model':'test'},'fr',Path(folder)/'links',[],installed_apps=set(),desktop_entries=apps)
            with zipfile.ZipFile(output) as archive:
                manifests=[(name,json.loads(archive.read(name))) for name in archive.namelist() if '/Profiles/' in name and name.endswith('manifest.json')]
                name,page=next(row for row in manifests if row[1]['Name']=='agentic')
                actions=list(page['Controllers'][0]['Actions'].values())
                self.assertLessEqual(len(actions),15)
                visible={action['Name']:action for action in actions}
                self.assertIn('Claude Desktop',visible);self.assertIn('ChatGPT Desktop',visible)
                self.assertIn('APPS IA',visible);self.assertIn('ORCH',visible)
                base=name.rsplit('/',1)[0]+'/'
                for app,icon in (('Claude Desktop','claude-agent.png'),('ChatGPT Desktop','chatgpt-agent.png')):
                    self.assertTrue(visible[app]['States'][0]['Image'].endswith(icon))
                    self.assertTrue(archive.read(base+visible[app]['States'][0]['Image']).startswith(b'\x89PNG'))


if __name__=='__main__':unittest.main()
