import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aidev.activity import receipts
from aidev.migration import migrate_legacy
from aidev.storage import data_dir,save_json


class ResilienceTests(unittest.TestCase):
    def test_default_directory_has_no_spaces_and_migration_preserves_data(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'LOCALAPPDATA':folder,'AI_DEV_DATA_DIR':''}):
            old=Path(folder)/'AI Dev'
            save_json(old/'settings.json',{'language':'fr','elgato_mcp':{'args':[str(old/'bridge/index.js')]}})
            save_json(old/'missions/one.json',{'id':'one','context':str(old/'context/one.json'),'objective':str(old/'keep-literal')})
            save_json(old/'stream-deck/selections/one.json',{'tool':'codex'})
            (old/'bridge').mkdir();(old/'bridge/index.js').write_text('fixture')
            (old/'stream-deck/old.lnk').write_text('old paths')
            result=migrate_legacy()
            self.assertEqual(data_dir().name,'AIDev')
            self.assertEqual(result['status'],'copied')
            config=json.loads((data_dir()/'settings.json').read_text())
            self.assertEqual(config['language'],'fr')
            self.assertEqual(config['elgato_mcp']['args'],[str(data_dir()/'bridge/index.js')])
            self.assertTrue((old/'settings.json').exists())
            self.assertFalse((data_dir()/'stream-deck/old.lnk').exists())
            receipt=json.loads((data_dir()/'missions/one.json').read_text())
            self.assertEqual(receipt['objective'],str(old/'keep-literal'))
            self.assertEqual(receipt['context'],str(data_dir()/'context/one.json'))
            save_json(data_dir()/'settings.json',{'language':'en'})
            migrate_legacy()
            self.assertEqual(json.loads((data_dir()/'settings.json').read_text())['language'],'en')

    def test_unreadable_directory_produces_a_warning_not_a_crash(self):
        issues=[]
        with patch('pathlib.Path.iterdir',side_effect=PermissionError('access denied')):
            self.assertEqual(receipts(issues=issues),[])
        self.assertIn('access denied',issues[0])

    def test_corrupt_receipt_does_not_hide_valid_receipts(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}):
            save_json(data_dir()/'missions/good.json',{'id':'good','status':'exited'})
            (data_dir()/'missions/bad.json').write_text('{broken')
            issues=[]
            self.assertEqual([r['id'] for r in receipts(issues=issues)],['good'])
            self.assertIn('bad.json',issues[0])

    @unittest.skipUnless(os.name=='nt','Windows Tk')
    def test_sessions_opens_without_powershell_or_harness_discovery(self):
        from aidev.ui import Panel
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}), patch('aidev.ui.discover',side_effect=RuntimeError('discovery must not run')) as discovery:
            panel=Panel(initial_tab='activity')
            try:
                panel.root.withdraw();panel.root.update()
                self.assertEqual(panel.notebook.select(),str(panel.activity_frame))
                discovery.assert_not_called()
            finally:panel.root.destroy()

    def test_failed_terminal_spawn_records_actionable_error(self):
        from aidev.runtime import spawn_terminal
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}):
            path=data_dir()/'missions/test.json'
            save_json(path,{'tool':'codex','profile':'work','project':folder,'status':'prepared'})
            with patch('aidev.runtime.subprocess.Popen',side_effect=PermissionError('access denied')):
                with self.assertRaises(PermissionError):spawn_terminal(path)
            receipt=json.loads(path.read_text())
            self.assertEqual(receipt['status'],'launch_error')
            self.assertIn('access denied',receipt['error'])


if __name__=='__main__':unittest.main()
