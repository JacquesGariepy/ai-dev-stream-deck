import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aidev import orchestrators, factory
from aidev.storage import save_settings, settings


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'AI_DEV_DATA_DIR': str(self.root/'private'), 'AI_DEV_FACTORY': ''})
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_no_default_or_project_autodetection(self):
        (self.root/'automation').mkdir()
        (self.root/'automation/control_server.py').touch()
        save_settings({'project': str(self.root)})
        self.assertEqual(orchestrators.selected()['kind'], 'none')
        with self.assertRaises(ValueError): factory.installation()
        with patch('aidev.orchestrators.subprocess.Popen') as launch:
            with self.assertRaises(ValueError): orchestrators.open_selected()
            launch.assert_not_called()

    def test_legacy_factory_preserved_and_none_overrides_environment(self):
        save_settings({'factory': {'package': str(self.root)}, 'language':'fr', 'web': {'context':'work'}})
        self.assertEqual(orchestrators.selected()['kind'], 'factory')
        with patch.dict(os.environ, {'AI_DEV_FACTORY':str(self.root)}):
            orchestrators.configure({'kind':'none'})
            self.assertEqual(orchestrators.selected()['kind'], 'none')
        self.assertEqual(settings()['language'], 'fr')
        self.assertEqual(settings()['web'], {'context':'work'})
        self.assertEqual(settings()['factory']['package'], str(self.root))

    def test_custom_url_never_calls_factory(self):
        orchestrators.configure({'kind':'custom', 'name':'OpenClaw', 'url':'http://localhost:1234/'})
        with patch('aidev.factory.ensure_workbench') as factory_open:
            self.assertEqual(orchestrators.open_selected(), 'http://localhost:1234/')
            factory_open.assert_not_called()

    def test_custom_command_preserves_arguments_without_shell(self):
        executable = self.root/'test tool.exe'; executable.touch()
        args=['dashboard', 'quoted " value', '$literal;not-a-shell-command']
        with patch('aidev.orchestrators.subprocess.Popen') as launch:
            orchestrators.configure({'kind':'custom','name':'AX','executable':str(executable), 'directory':str(self.root), 'arguments':args})
            launch.assert_not_called()
            self.assertIsNone(orchestrators.open_selected())
        self.assertEqual(launch.call_args.args[0], [str(executable.resolve()), *args])
        self.assertNotIn('shell', launch.call_args.kwargs)

    def test_reject_ambiguous_custom_and_invalid_url(self):
        for payload in ({'url':'file:///local'}, {'url':'https://example.com','executable':'any.exe'}, {}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                orchestrators.configure({'kind':'custom','name':'Other', **payload})
        self.assertNotIn('orchestrator', settings())

    @unittest.skipUnless(os.name == 'nt', 'Windows Tk')
    def test_none_and_custom_ui_never_query_factory(self):
        from aidev.ui import Panel
        for selection in ({'kind':'none'}, {'kind':'custom','name':'Other','url':'https://example.com'}):
            orchestrators.configure(selection)
            with patch('aidev.factory.brief', side_effect=AssertionError('Factory must not run')) as brief:
                panel=Panel(initial_tab='factory')
                try:
                    panel.root.withdraw(); panel.root.update()
                    brief.assert_not_called()
                    self.assertEqual(panel.notebook.tab(panel.factory_frame, 'text'), panel.text('factory_tab'))
                finally: panel.root.destroy()


if __name__ == '__main__': unittest.main()
