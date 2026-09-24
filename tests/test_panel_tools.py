import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Native Windows utility tests')
class PanelToolsTests(unittest.TestCase):
    def run_plan(self, action, query=''):
        shell = shutil.which('powershell')
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, AI_DEV_AGENTDECK_DIR=folder)
            return subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File',
                                   str(ROOT / 'agentdeck/run-tools.ps1'), '-Action', action,
                                   '-Query', query, '-Plan'], capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', env=env, timeout=15)

    def test_search_quotes_and_shell_characters_stay_in_encoded_query(self):
        query = 'code: "a & b" / français\n$(echo unsafe) #'
        result = self.run_plan('search-github', query)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        url = urlsplit(data['url'])
        self.assertEqual(url.netloc, 'github.com')
        self.assertEqual(parse_qs(url.query)['q'], [query.strip()])
        self.assertEqual(parse_qs(url.query)['type'], ['code'])
        self.assertFalse(url.fragment)

    def test_empty_search_and_unknown_destinations_are_refused(self):
        for action, query in [('search-google', ''), ('search-executable', 'x'), ('web-file', '')]:
            with self.subTest(action=action):
                self.assertNotEqual(self.run_plan(action, query).returncode, 0)

    def test_website_routes_to_known_https_destination(self):
        result = self.run_plan('web-mslearn')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['url'], 'https://learn.microsoft.com/')


if __name__ == '__main__':
    unittest.main()
