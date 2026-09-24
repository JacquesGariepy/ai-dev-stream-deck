import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aidev.browsers import browser_command, open_website, save_browser_choices, select_context, validate_url
from aidev.storage import settings, save_settings
from aidev.__main__ import main


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'AI_DEV_DATA_DIR':self.temp.name});self.env.start()
        self.installed=patch('aidev.browsers.installed_browsers',return_value={'edge':'edge.exe','chrome':'chrome.exe'});self.installed.start()

    def tearDown(self):
        self.installed.stop();self.env.stop();self.temp.cleanup()

    def test_default_is_ask_without_forcing_a_browser(self):
        with patch('sys.argv',['ai-dev','--action','web','--url','https://example.com']), patch('aidev.browsers.browser_dialog') as dialog, patch('aidev.browsers.open_website') as launch:
            main();dialog.assert_called_once_with('https://example.com',None);launch.assert_not_called()

    def test_work_and_personal_can_use_either_browser(self):
        save_browser_choices('work',{'work':'chrome','personal':'edge'},False)
        self.assertEqual(browser_command('https://example.com'),['chrome.exe','https://example.com'])
        self.assertTrue(select_context('personal'))
        self.assertEqual(browser_command('https://example.com'),['edge.exe','https://example.com'])
        save_browser_choices('work',{'work':'edge','personal':'chrome'},False)
        self.assertEqual(browser_command('https://example.com'),['edge.exe','https://example.com'])

    def test_saved_route_is_explicit_and_does_not_use_os_default(self):
        save_browser_choices('personal',{'personal':'chrome'},False)
        with patch('aidev.browsers.subprocess.Popen') as popen:
            command=open_website('https://example.com/a?q=test&lang=en')
            popen.assert_called_once_with(['chrome.exe','https://example.com/a?q=test&lang=en'])
            self.assertEqual(command[0],'chrome.exe')

    def test_explicit_context_does_not_switch_saved_context(self):
        save_browser_choices('work',{'work':'edge','personal':'chrome'},False)
        self.assertEqual(browser_command('https://example.com','personal')[0],'chrome.exe')
        self.assertEqual(settings()['web']['context'],'work')

    def test_missing_browser_does_not_silently_fall_back(self):
        save_browser_choices('work',{'work':'edge'},False)
        with patch('aidev.browsers.installed_browsers',return_value={'chrome':'chrome.exe'}):
            with self.assertRaises(ValueError):browser_command('https://example.com')
            self.assertFalse(select_context('work'))

    def test_only_website_urls_are_accepted(self):
        for value in ('file:///local','javascript:alert(1)','--incognito','https://','https://example.com\nargument'):
            with self.assertRaises(ValueError):validate_url(value)

    def test_browser_preferences_preserve_other_settings(self):
        save_settings({'language':'fr','project':'project','profiles':{'codex':'codex-work'}})
        save_browser_choices('personal',{'personal':'edge'})
        config=settings()
        self.assertTrue(config['web']['ask_each_time'])
        self.assertEqual(config['language'],'fr')
        self.assertEqual(config['profiles']['codex'],'codex-work')

    def test_missing_saved_mapping_reopens_choice(self):
        save_settings({'web':{'context':'work','ask_each_time':False}})
        with patch('sys.argv',['ai-dev','--action','web','--url','https://example.com']), patch('aidev.browsers.browser_dialog') as dialog:
            main();dialog.assert_called_once_with('https://example.com',None)


if __name__=='__main__':unittest.main()
