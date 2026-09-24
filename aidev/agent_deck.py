"""AI-first Stream Deck: every key either acts natively or starts an agent already at work.

No AI Dev window is opened. Agent keys run agentdeck/ai.ps1 hidden, which captures
context (editor project, selection, clipboard, Git) and opens a terminal where the
chosen harness is working on the task. Other keys are native Stream Deck hotkeys
and websites.
"""
import json
from pathlib import Path
from .deck_layout import DeckBuilder, Grid, Key, Page

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
INTENT_ICONS = {'ask': 'prompt', 'fix': 'bug', 'review': 'review', 'commit': 'commit', 'explain': 'document',
                'test': 'check', 'plan': 'plan', 'pr': 'branch', 'handoff': 'handoff'}
WEB = (('CHATGPT', 'https://chatgpt.com/', 'chatgpt'), ('CLAUDE', 'https://claude.ai/', 'claude'),
       ('GEMINI', 'https://gemini.google.com/', 'web'), ('PERPLEXITY', 'https://www.perplexity.ai/', 'web'),
       ('GITHUB', 'https://github.com/', 'git'), ('PULL REQ', 'https://github.com/pulls', 'branch'),
       ('ISSUES', 'https://github.com/issues', 'warning'))


def load_intents(path=None):
    return json.loads(Path(path or ROOT / 'agentdeck/intents.json').read_text('utf-8'))


class AgentDeck:
    def __init__(self, script_path, grid=None, intents=None):
        self.script = str(script_path)          # Windows path of agentdeck\ai.ps1
        self.grid = grid or Grid()
        self.intents = intents or load_intents()
        self.language = 'fr'
        self.profile_name = 'AI Dev Agentic'
        self.shortcuts = {}                     # name -> (target, arguments)
        self.pages = {}

    def agent(self, title, intent, icon, zone='agent', description=''):
        self.shortcuts['ai-' + intent] = (POWERSHELL, '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%s" %s' % (self.script, intent))
        return Key(title, 'open', zone, icon, 'ai-' + intent, description or 'Agent deck: ' + intent)

    def build(self):
        a = self.agent
        spec = self.intents['intents']
        intent_keys = {name: a(value['title'], name, INTENT_ICONS.get(name, 'agent'), 'agent',
                               '%s (%s, %s): starts the agent on this task with the current context.' % (value['title'], value['harness'], value['mode']))
                       for name, value in spec.items()}
        home = [intent_keys.get(n) for n in ('ask', 'fix', 'review', 'commit', 'explain', 'test', 'plan', 'pr', 'handoff')]
        home = [k for k in home if k]
        home.append(a('CONTINUE', 'continue', 'next', 'agent', 'Resume the last agent session in this project.'))
        home += [a('CLAUDE', 'claude', 'claude', 'dev', 'Open Claude Code with the active profile in the current project.'),
                 a('CODEX', 'codex', 'code', 'dev', 'Open Codex with the active profile in the current project.'),
                 a('AGY', 'agy', 'agent', 'dev', 'Open AGY with the active profile in the current project.'),
                 a('WORK /\nPERSO', 'profile', 'profile', 'nav', 'Toggle the active account profile (work / personal).'),
                 Key('PLUS', 'folder', 'nav', 'more', 'more')]
        self.pages['home'] = Page('home', home, fixed=self.grid.capacity >= 15)

        # Native tools reused from the classic layout (hotkeys only, no app windows).
        classic = DeckBuilder('fr', Grid(), [], set()).build().pages
        native = lambda name: [k for k in classic[name].keys if k is not None and k.kind == 'hotkey']
        for name in ('editor', 'debug', 'media', 'desktop', 'windows'):
            self.pages[name] = Page(name, native(name))
        self.pages['web'] = Page('web', [Key(t, 'website', 'web', i, u, 'Open ' + u) for t, u, i in WEB])
        self.pages['more'] = Page('more', [
            a('PROJET', 'project', 'folder', 'dev', 'Choose the working project (defaults to the folder open in the editor).'),
            a('STATUS', 'git-status', 'git', 'git'), a('DIFF', 'git-diff', 'diff', 'git'), a('LOG', 'git-log', 'log', 'git'),
            a('PULL', 'git-pull', 'pull', 'git'), a('PUSH', 'git-push', 'push', 'git', 'Push after confirmation in the terminal.'),
            a('FETCH', 'git-fetch', 'fetch', 'git'),
            Key('EDITEUR', 'folder', 'dev', 'keyboard', 'editor'), Key('DEBUG', 'folder', 'run', 'bug', 'debug'),
            Key('MEDIA', 'folder', 'media', 'music', 'media'), Key('BUREAU', 'folder', 'system', 'desktop', 'desktop'),
            Key('WINDOWS', 'folder', 'system', 'windows', 'windows'), Key('WEB', 'folder', 'web', 'web', 'web')])
        return self
