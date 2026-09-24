"""Exercise real Tk widget transitions with isolated state and no provider launch."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aidev.storage import data_dir, save_json


@unittest.skipUnless(os.name == 'nt', 'Windows Tk interface')
class PanelTests(unittest.TestCase):
    def test_language_followup_and_launch_keep_control_panel_open(self):
        from aidev.ui import Panel
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AI_DEV_DATA_DIR':folder}):
            entry={'tool':'codex','profile':'work','command':'codex-work','kind':'powershell','available':True,'initialized':True}
            save_json(data_dir()/'settings.json', {'language':'fr','project':folder,'profiles':{'codex':'codex-work'}})
            save_json(data_dir()/'missions/previous.json', {'id':'previous','tool':'codex','profile':'work','command':'codex-work','project':folder,'objective':'Fix the parser.','status':'exited','exit_code':0})
            with patch('aidev.ui.discover', return_value={'entries':[entry]}):
                panel=Panel()
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
