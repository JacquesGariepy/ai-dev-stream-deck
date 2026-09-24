import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from aidev import factory
from aidev.activity import receipts
from aidev.storage import data_dir, save_json, settings


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'AI_DEV_DATA_DIR': str(self.root/'private'), 'AI_DEV_FACTORY':''})
        self.env.start()
        self.package = self.root/'Factory with spaces'
        for name in ('automation/control_server.py','automation/autopilot.py','factory.py'):
            file = self.package/name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('')

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_factory_configuration_preserves_browser_and_language(self):
        save_json(data_dir()/'settings.json', {'language':'fr', 'web':{'ask_each_time':True}})
        factory.configure(self.package)
        self.assertEqual(settings()['language'], 'fr')
        self.assertTrue(settings()['web']['ask_each_time'])
        self.assertEqual(factory.installation(), self.package.resolve())

    def test_invalid_factory_is_not_saved(self):
        with self.assertRaises(ValueError):
            factory.configure(self.root)
        self.assertNotIn('factory', settings())

    def test_brief_reads_canonical_status_without_starting_a_run(self):
        factory.configure(self.package)
        response = MagicMock(returncode=0, stdout=json.dumps({'ok':True,'decisions_pending':[{'kind':'budget','blocks':'run'}]}))
        with patch('aidev.factory.subprocess.run', return_value=response) as call:
            self.assertEqual(factory.brief()['decisions_pending'][0]['blocks'], 'run')
        args = call.call_args.args[0]
        self.assertEqual(args[-2:], ['status','--brief'])
        self.assertEqual(Path(args[args.index('--root')+1]).resolve(), self.package.resolve())

    def test_existing_workbench_reused_without_launch(self):
        factory.configure(self.package)
        with patch('aidev.factory.workbench_identity', return_value=True), patch('aidev.factory.subprocess.Popen') as launch:
            self.assertEqual(factory.ensure_workbench(),'http://127.0.0.1:8765/')
            launch.assert_not_called()

    def test_unrelated_service_is_not_reused_or_stopped(self):
        factory.configure(self.package)
        with patch('aidev.factory.workbench_identity', return_value=False), patch('aidev.factory.port_available', return_value=False), patch('aidev.factory.subprocess.Popen') as launch:
            with self.assertRaises(RuntimeError): factory.ensure_workbench()
            launch.assert_not_called()

    def test_identity_requires_matching_package(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'ok':True,'projects':[], 'package':str(self.root/'unrelated')})
        with patch('aidev.factory.urlopen', return_value=response):
            self.assertFalse(factory.workbench_identity(8765, self.package))

    def test_interrupted_receipt_is_observed_without_rewriting_evidence(self):
        path=data_dir()/'missions/one.json'
        save_json(path, {'id':'one','status':'running','runner_pid':123,'outcome':'unverified','tokens':None})
        save_json(path.with_name('one.launch.json'), {'tool':'codex'})
        with patch('aidev.activity.process_alive', return_value=False):
            rows=receipts()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['observed_status'],'interrupted')
        self.assertEqual(rows[0]['outcome'],'unverified')
        self.assertIsNone(rows[0]['tokens'])
        self.assertEqual(json.loads(path.read_text())['status'],'running')

    def test_old_prepared_receipt_does_not_claim_an_active_terminal(self):
        save_json(data_dir()/'missions/unconfirmed.json', {'id':'unconfirmed','status':'prepared','created':'2000-01-01T00:00:00+00:00'})
        self.assertEqual(receipts()[0]['observed_status'],'unconfirmed')


if __name__ == '__main__': unittest.main()
