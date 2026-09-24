"""Exercise real Tk widget transitions with isolated state and no provider launch."""
import gc
import os
from pathlib import Path
import tempfile
import unittest
import time
from unittest.mock import patch
from aidev.storage import data_dir, save_json


@unittest.skipUnless(os.name == 'nt', 'Windows Tk interface')
class PanelTests(unittest.TestCase):
    def setUp(self):
        # Prior Tk roots contain reference cycles. Collect them on the UI thread
        # before discovery workers start, so Tcl finalizers never run there.
        gc.collect()

    def tearDown(self):
        gc.collect()

    def test_agentic_test_explains_direct_project_test_difference(self):
        from aidev.ui import Panel
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}), patch('aidev.ui.discover',return_value={'entries':[]}):
            panel=Panel(initial_workflow='test')
            try:
                panel.root.withdraw();panel.root.update()
                def labels(widget):
                    values=[]
                    for child in widget.winfo_children():
                        try:values.append(str(child.cget('text')))
                        except Exception:pass
                        values.extend(labels(child))
                    return values
                self.assertTrue(any(panel.text('workflow_test_note') in value for value in labels(panel.root)))
            finally:panel.root.destroy()

    def test_empty_catalog_shows_an_actionable_state(self):
        from aidev.catalog_ui import CatalogWindow
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}):
            window=CatalogWindow('applications',lambda:[],lambda _: '')
            try:
                window.root.withdraw()
                deadline=time.monotonic()+2
                while window.busy and time.monotonic()<deadline:
                    window.root.update();time.sleep(.02)
                rows=window.tree.get_children()
                self.assertEqual(len(rows),1)
                self.assertIn(window.text('catalog_empty'),window.tree.item(rows[0],'values'))
                self.assertIn('0',window.status.get())
            finally:window.close()

    def test_window_is_ready_while_profile_discovery_is_blocked(self):
        import threading
        from aidev.ui import Panel
        gate=threading.Event()
        entry={'tool':'claude','profile':'personal','command':'claude-personal','kind':'powershell','available':True,'initialized':True}
        def slow_discovery():
            gate.wait(4)
            return {'entries':[entry]}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AI_DEV_DATA_DIR':folder}), patch('aidev.ui.discover',side_effect=slow_discovery):
            panel=Panel(initial_selection=entry)
            try:
                panel.root.withdraw();panel.root.update()
                self.assertTrue(panel.detecting)
                self.assertIn('claude / personal',panel.root.title())
                self.assertEqual(panel.status['text'],panel.text('detecting_profiles'))
                self.assertEqual(str(panel.open_button['state']),'disabled')
                gate.set()
                deadline=time.monotonic()+3
                while panel.detecting and time.monotonic()<deadline:
                    panel.root.update();time.sleep(.02)
                self.assertFalse(panel.detecting, 'Profile discovery did not finish')
                self.assertEqual(panel.profile.get(),'claude-personal')
                self.assertEqual(str(panel.open_button['state']),'normal')
            finally:gate.set();panel.root.destroy()

    def test_language_followup_and_launch_keep_control_panel_open(self):
        from aidev.ui import Panel
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR':folder}):
            entry={'tool':'codex','profile':'work','command':'codex-work','kind':'powershell','available':True,'initialized':True}
            save_json(data_dir()/'settings.json', {'language':'fr','project':folder,'profiles':{'codex':'codex-work'}})
            save_json(data_dir()/'missions/previous.json', {'id':'previous','tool':'codex','profile':'work','command':'codex-work','project':folder,'objective':'Fix the parser.','status':'exited','exit_code':0})
            with patch('aidev.ui.discover', return_value={'entries':[entry]}):
                panel=Panel()
                deadline=time.monotonic()+3
                while panel.detecting and time.monotonic()<deadline:
                    panel.root.update();time.sleep(.02)
            try:
                panel.root.withdraw()
                panel.root.update()
                panel.follow_receipt()
                self.assertEqual(panel.workflow,'review')
                self.assertEqual(panel.profile.get(),'codex-work')
                self.assertIn('Verify the previous session',panel.objective.get('1.0','end'))
                self.assertFalse(panel.english.get())
                panel.language='en';panel.preference='en';panel.render()
                self.assertIn('Verify the previous session',panel.objective.get('1.0','end'))
                self.assertEqual(panel.root.title(),'AI Dev — Control Panel')
                panel.english.set(True)
                with patch('aidev.ui.prepare', return_value=Path(folder)/'next.json') as prepare, patch('aidev.ui.spawn_terminal') as spawn:
                    panel.submit(True)
                    prepare.assert_called_once()
                    spawn.assert_called_once()
                self.assertTrue(panel.root.winfo_exists())
                self.assertEqual(panel.notebook.select(),str(panel.activity_frame))
            finally:
                panel.root.destroy()


if __name__ == '__main__': unittest.main()
