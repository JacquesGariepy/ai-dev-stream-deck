"""Declarative expert layout for Stream Deck, independent of the device size.

Pages are described once as ordered keys. The exporter (deck_export) turns them
into native pages for the actual grid: BACK is always the top-left key of a
subpage, MORE is always the bottom-right key of an overflowing page, and every
key carries a functional colour zone so the deck reads at a glance.
"""
from dataclasses import dataclass, field
import re
import textwrap
from .agents import TEXT_PROMPTS

# Keypad grids by Stream Deck model identifier (manifest "Device.Model").
# Only the MK.2 is verified on hardware by this project; the others follow the
# published key grids and can be overridden with --grid COLSxROWS.
MODELS = {
    '20GAA9901': ('Stream Deck', 5, 3), '20GAA9902': ('Stream Deck', 5, 3),
    '20GBA9901': ('Stream Deck MK.2', 5, 3),
    '20GAI9901': ('Stream Deck Mini', 3, 2), '20GAI9902': ('Stream Deck Mini', 3, 2),
    '20GBI9901': ('Stream Deck Mini', 3, 2),
    '20GAT9901': ('Stream Deck XL', 8, 4), '20GAT9902': ('Stream Deck XL', 8, 4), '20GBT9901': ('Stream Deck XL', 8, 4),
    '20GBD9901': ('Stream Deck +', 4, 2),
    '20GBJ9901': ('Stream Deck Neo', 4, 2), '10GBJ9901': ('Stream Deck Neo', 4, 2),
}
VERIFIED_MODELS = {'20GBA9901'}


@dataclass(frozen=True)
class Grid:
    cols: int = 5
    rows: int = 3

    @property
    def capacity(self):
        return self.cols * self.rows

    @classmethod
    def parse(cls, value):
        match = re.fullmatch(r'\s*(\d{1,2})\s*[xX×]\s*(\d{1,2})\s*', value or '')
        if not match:
            raise ValueError('Grid must look like 5x3 (columns x rows).')
        cols, rows = int(match.group(1)), int(match.group(2))
        if not (2 <= cols <= 16 and 1 <= rows <= 8) or cols * rows < 4:
            raise ValueError('Unsupported grid size.')
        return cls(cols, rows)

    @classmethod
    def for_device(cls, device, override=None):
        if override:
            return override if isinstance(override, Grid) else cls.parse(override)
        model = MODELS.get((device or {}).get('Model', ''))
        return cls(model[1], model[2]) if model else cls()


@dataclass
class Key:
    title: str
    kind: str                 # open | folder | back | hotkey | text
    zone: str = 'nav'
    icon: str = 'document'
    target: object = None     # shortcut name | page id | hotkey dict | pasted text
    description: str = ''
    name: str = ''
    warn: bool = False

    def __post_init__(self):
        if not self.name:
            self.name = self.title.replace('\n', ' ')


@dataclass
class Page:
    name: str
    keys: list                # Key or None (an intentional empty key on fixed pages)
    header: list = field(default_factory=list)   # repeated after BACK on each MORE page
    fixed: bool = True        # False: a list that paginates without gaps


WEBSITES = {
    'chatgpt': 'https://chatgpt.com/', 'claude': 'https://claude.ai/', 'gemini': 'https://gemini.google.com/',
    'perplexity': 'https://www.perplexity.ai/', 'github': 'https://github.com/',
    'github-pr': 'https://github.com/pulls', 'github-issues': 'https://github.com/issues',
}
LEGACY_ACTIONS = ('mission', 'codex', 'claude', 'agy', 'context', 'status', 'files', 'terminal', 'guide', 'browser',
                  'browser-open', 'spotify', 'windows-settings', 'applications', 'mcp', 'project-tasks', 'web-work',
                  'web-personal', 'factory', 'factory-status', 'cursor', 'vscode', 'orca', 'monitor', 'resources',
                  'performance', 'system-info', 'capture', 'health', 'git', 'logs')
WINDOWS_UTILITIES = ('display', 'sound', 'network', 'bluetooth', 'storage', 'apps', 'downloads', 'documents',
                     'pictures', 'recycle-bin', 'calculator', 'notepad', 'event-viewer', 'services')
SAFE_ARGUMENT = re.compile(r'[A-Za-z0-9_.:/=-]+')
PROMPT_ICONS = {'implement': 'code', 'plan': 'plan', 'debug': 'bug', 'review': 'review', 'test': 'test', 'handoff': 'handoff',
                'refactor': 'format', 'explain': 'document', 'performance': 'chart', 'security': 'lock', 'docs': 'document',
                'context': 'context', 'usage': 'chart', 'pr_draft': 'branch'}
PROMPT_LABELS = {'implement': ('IMPLEMENT', 'REALISER'), 'plan': ('PLAN', 'PLAN'), 'debug': ('DEBUG', 'DEBUG'),
                 'review': ('REVIEW', 'REVUE'), 'test': ('TESTS', 'TESTS'), 'handoff': ('HANDOFF', 'RELAIS'),
                 'refactor': ('REFACTOR', 'REFACTOR'), 'explain': ('EXPLAIN', 'EXPLIQUER'),
                 'performance': ('PERF', 'PERF'), 'security': ('SECURITY', 'SECURITE'), 'docs': ('DOCS', 'DOCS'),
                 'context': ('CONTEXT', 'CONTEXTE'), 'usage': ('USAGE', 'COUTS'), 'pr_draft': ('PR DRAFT', 'PR DRAFT')}
WORKFLOW_KEYS = (('plan', 'plan', ('PLAN', 'PLAN')), ('implement', 'code', ('IMPLEMENT', 'REALISER')),
                 ('review', 'review', ('REVIEW', 'REVUE')), ('debug', 'bug', ('DEBUG', 'DEBUG')),
                 ('test', 'test', ('TEST', 'TEST')), ('handoff', 'handoff', ('HANDOFF', 'RELAIS')))
FEATURED_DEV = ('docker desktop', 'github desktop', 'gitkraken', 'fork', 'visual studio code', 'cursor', 'visual studio',
                'postman', 'insomnia', 'bruno', 'dbeaver', 'datagrip', 'pycharm', 'webstorm', 'rider', 'notepad++', 'devtoys')
MEDIA_KEYS = {173, 174, 175, 176, 177, 179}


def command_line(arguments):
    """Windows command-line for a .lnk; arguments are app-authored, never user text."""
    parts = []
    for argument in arguments:
        if SAFE_ARGUMENT.fullmatch(argument):
            parts.append(argument)
        elif '"' in argument or '\n' in argument:
            raise ValueError('Unsafe shortcut argument.')
        else:
            parts.append('"' + argument + '"')
    return ' '.join(parts)


def wrap(text, width=10, lines=2):
    return '\n'.join(textwrap.wrap(text.upper(), width)[:lines]) or text.upper()[:width]


class DeckBuilder:
    def __init__(self, language, grid=None, entries=None, installed_apps=None, desktop_entries=None, mcp_entries=None):
        self.language = language
        self.grid = grid or Grid()
        self.entries = entries or []
        self.installed = set(installed_apps or ())
        self.apps = desktop_entries or []
        self.mcp = mcp_entries or []
        self.shortcuts = {}
        self.pages = {}

    # ---- key factories -------------------------------------------------
    def L(self, en, fr):
        return fr if self.language == 'fr' else en

    def shortcut(self, name, arguments):
        line = command_line(arguments)
        if self.shortcuts.get(name, line) != line:
            raise ValueError('Conflicting shortcut definition: ' + name)
        self.shortcuts[name] = line
        return name

    def open(self, title, name, arguments, icon, zone, description, key_name=''):
        return Key(title, 'open', zone, icon, self.shortcut(name, arguments), description, key_name)

    def action(self, title, action, icon, zone, description, key_name=''):
        return self.open(title, action, ['--action', action], icon, zone, description, key_name)

    def folder(self, title, page, icon='folder', zone='nav'):
        return Key(title, 'folder', zone, icon, page)

    def hotkey(self, title, key, icon='keyboard', zone='dev', ctrl=False, shift=False, alt=False, win=False, qt=None):
        return Key(title, 'hotkey', zone, icon, {'key': key, 'ctrl': ctrl, 'shift': shift, 'alt': alt, 'win': win,
                                                 'qt': key if qt is None else qt})

    def text(self, title, pasted, icon='prompt'):
        return Key(title, 'text', 'agent', icon, pasted)

    def windows(self, title, utility, icon, description):
        return self.open(title, 'windows-' + utility, ['--windows-action', utility], icon, 'system', description)

    def website(self, title, site, zone='web'):
        icon = {'chatgpt': 'chatgpt', 'claude': 'claude', 'github': 'git', 'github-pr': 'branch', 'github-issues': 'warning'}.get(site, 'web')
        return self.open(title, 'web-' + site, ['--action', 'web', '--url', WEBSITES[site]], icon, zone,
                         'Open the website with the user-selected browser and work/personal context.')

    def refresh(self):
        return self.open(self.L('REFRESH', 'ACTUALISER'), 'deck-refresh-' + self.language,
                         ['--action', 'deck-refresh', '--deck-language', self.language], 'refresh', 'nav',
                         'Rescan harnesses, profiles, apps and MCP declarations, then open the regenerated profile for import.')

    def workflow(self, workflow, icon, labels):
        return self.open(self.L(*labels), 'mission-' + workflow, ['--action', 'mission', '--workflow', workflow], icon, 'agent',
                         'Open the mission panel with the ' + workflow + ' workflow preselected. Nothing starts until you launch.')

    def git(self, title, action, icon, description):
        return self.open(title, 'git-' + action, ['--git', action], icon, 'git', description)

    def task(self, title, kind, icon, description):
        return self.open(title, 'task-' + kind, ['--task-kind', kind], icon, 'run', description)

    def app(self, entry, zone='system'):
        aliases = {'visual studio code': 'VS CODE', 'docker desktop': 'DOCKER\nDESKTOP', 'github desktop': 'GITHUB\nDESKTOP',
                   'chatgpt': 'CHATGPT\nDESKTOP', 'claude': 'CLAUDE\nDESKTOP', 'windows terminal': 'TERMINAL'}
        lowered = entry['name'].casefold()
        icon = {'claude': 'claude', 'chatgpt': 'chatgpt'}.get(lowered, 'apps')
        name = entry['name'] + (' Desktop' if lowered in ('claude', 'chatgpt') else '')
        return self.open(aliases.get(lowered, wrap(entry['name'])), 'app-' + entry['id'], ['--app-id', entry['id']], icon, zone,
                         'Open this exact detected Windows desktop application.', name)

    # ---- pages ---------------------------------------------------------
    def build(self):
        from .deck_profiles import selection_id
        L = self.L
        k = {}
        # Agentic
        k['mission'] = self.action('MISSION', 'mission', 'mission', 'agent',
                                   'Open the mission panel: project, harness, exact profile and English objective.')
        for workflow, icon, labels in WORKFLOW_KEYS:
            k['wf-' + workflow] = self.workflow(workflow, icon, labels)
        k['sessions'] = self.action('SESSIONS', 'status', 'sessions', 'agent',
                                    'Live session receipts, errors and the suggested next mission. Exited is not proof of success.')
        k['context'] = self.action(L('CONTEXT', 'CONTEXTE'), 'context', 'context', 'agent',
                                   'Capture Git metadata of the selected project for the next mission.')
        k['profiles'] = self.folder(L('PROFILES', 'PROFILS'), 'profiles', 'profile', 'agent')
        k['prompts'] = self.folder('PROMPTS', 'prompts', 'prompt', 'agent')
        k['ai-web'] = self.folder('AI WEB', 'web', 'web', 'web')
        k['mcp'] = self.folder('MCP', 'mcp', 'mcp', 'agent')
        k['ai-apps'] = self.folder(L('AI APPS', 'APPS IA'), 'ai-apps', 'apps', 'agent')
        k['orch'] = self.folder('ORCH', 'orchestrator', 'hub', 'agent')
        k['agentic'] = self.folder('AGENTIC', 'agentic', 'agent', 'agent')
        # Dev
        k['terminal'] = self.action('TERMINAL', 'terminal', 'terminal', 'dev',
                                    'Choose a detected shell or terminal (CMD, PowerShell, Git Bash, WSL...) in the selected project.')
        k['editor'] = self.folder(L('EDITOR', 'EDITEUR'), 'editor', 'keyboard', 'dev')
        k['git'] = self.folder('GIT', 'git-ops', 'git', 'git')
        k['run'] = self.folder(L('BUILD\nTEST', 'BUILD\nTEST'), 'run', 'run', 'run')
        k['debug'] = self.folder('DEBUG', 'debug', 'bug', 'run')
        k['project'] = self.action(L('PROJECT', 'PROJET'), 'mission', 'folder', 'dev', 'Choose the project folder in the control panel.',
                                   L('PROJECT', 'PROJET'))
        k['files'] = self.action(L('FILES', 'FICHIERS'), 'files', 'folder', 'dev', 'Open the selected project folder.')
        k['diag'] = self.action(L('HEALTH', 'DIAG'), 'health', 'chart', 'dev',
                                'Tool availability, storage access and MCP bridge files. Authentication is not verified.')
        k['logs'] = self.action(L('LOGS', 'JOURNAUX'), 'logs', 'document', 'dev', 'Open the private application log folder.')
        k['dev'] = self.folder('DEV', 'dev', 'code', 'dev')
        k['dev-apps'] = self.folder(L('DEV APPS', 'APPS DEV'), 'dev-apps', 'apps', 'dev')
        # Git one-press actions
        git_text = 'Runs visibly in a terminal in the selected project; nothing is evaluated by a shell.'
        k['g-status'] = self.git('STATUS', 'status', 'git', 'git status --short --branch. ' + git_text)
        k['g-diff'] = self.git('DIFF', 'diff', 'diff', 'git diff with the pager. ' + git_text)
        k['g-log'] = self.git('LOG', 'log', 'log', 'Last 40 commits as a graph. ' + git_text)
        k['g-fetch'] = self.git('FETCH', 'fetch', 'fetch', 'git fetch --all --prune. ' + git_text)
        k['g-pull'] = self.git('PULL', 'pull', 'pull', 'git pull --ff-only: never creates a merge commit. ' + git_text)
        k['g-push'] = self.git('PUSH', 'push', 'push', 'Confirms branch and destination, then pushes. ' + git_text)
        k['g-stage'] = self.git(L('ADD -P', 'AJOUT -P'), 'stage', 'stage', 'git add --patch: review each hunk. ' + git_text)
        k['g-commit'] = self.git('COMMIT', 'commit', 'commit', 'git commit --verbose with your configured editor. ' + git_text)
        k['g-branch'] = self.git(L('NEW\nBRANCH', 'NOUV.\nBRANCHE'), 'branch', 'branch', 'Asks a name validated by Git, then git switch --create. ' + git_text)
        k['g-switch'] = self.git(L('SWITCH', 'BASCULER'), 'switch', 'switch', 'Choose a local branch, then git switch. ' + git_text)
        k['g-stash'] = self.git('STASH', 'stash', 'stash', 'git stash push --include-untracked. ' + git_text)
        k['g-pop'] = self.git('STASH\nPOP', 'unstash', 'unstash', 'git stash pop. ' + git_text)
        k['g-panel'] = self.action(L('GIT\nPANEL', 'PANNEAU\nGIT'), 'git', 'chart', 'git',
                                   'Read branch, changes and worktrees without modifying the repository or fetching.')
        k['git-web'] = self.folder('GIT WEB', 'git-web', 'web', 'git')
        # Direct project tasks
        task_text = 'Runs the matching script of the selected project (package.json, pyproject, Makefile); opens the task list when none matches.'
        k['t-build'] = self.task('BUILD', 'build', 'build', task_text)
        k['t-test'] = self.task('TEST', 'test', 'check', task_text)
        k['t-lint'] = self.task('LINT', 'lint', 'lint', task_text)
        k['t-dev'] = self.task(L('DEV\nSERVER', 'SERVEUR\nDEV'), 'dev', 'run', task_text)
        k['t-types'] = self.task('TYPES', 'types', 'types', task_text)
        k['t-format'] = self.task(L('FORMAT', 'FORMATER'), 'format', 'format', task_text)
        k['t-all'] = self.action(L('ALL\nTASKS', 'TOUTES\nTACHES'), 'project-tasks', 'tasks', 'run',
                                 'List real project scripts and run only the selected one.')
        # System
        k['system'] = self.folder(L('SYSTEM', 'SYSTEME'), 'system', 'windows', 'system')
        k['media'] = self.folder('MEDIA', 'media', 'music', 'media')
        k['refresh'] = self.refresh()

        harness_keys, harness_folders = self.harnesses(selection_id)
        self.pages['profiles'] = Page('profiles', harness_folders, fixed=False,
                                      header=[self.action('MISSION', 'mission', 'mission', 'agent', 'Open the mission panel.'), self.refresh()])
        self.home(k, harness_keys)
        self.pages['agentic'] = Page('agentic', [k['wf-plan'], k['wf-implement'], k['wf-review'], k['wf-debug'],
                                                 k['wf-test'], k['wf-handoff'], k['sessions'], k['context'], k['profiles'],
                                                 k['prompts'], k['ai-web'], k['mcp'], k['ai-apps'], k['orch']])
        self.pages['git-ops'] = Page('git-ops', [k['g-status'], k['g-diff'], k['g-log'], k['g-fetch'],
                                                 k['g-stage'], k['g-commit'], k['g-pull'], k['g-push'], k['g-branch'],
                                                 k['g-switch'], k['g-stash'], k['g-pop'], k['g-panel'], k['git-web']])
        self.pages['run'] = Page('run', [k['t-build'], k['t-test'], k['t-lint'], k['t-dev'], k['t-types'], k['t-format'],
                                         k['t-all'], k['debug'], k['terminal']])
        self.dev_pages(k)
        self.agent_pages()
        self.system_pages(k)
        self.catalog_pages()
        return self

    def harnesses(self, selection_id):
        L = self.L
        groups = {}
        unique = {(r['tool'], r['profile'], r['command']): r for r in self.entries}
        for row in sorted(unique.values(), key=lambda r: (r['tool'], r['profile'], r['command'])):
            groups.setdefault(row['tool'], []).append(row)
        featured, folders = [], []
        for index, (tool, rows) in enumerate(groups.items()):
            page = 'harness-' + str(index)
            buttons = []
            for row in rows:
                display = L('DEFAULT', 'DEFAUT') if row.get('kind') == 'application' else row['profile'].upper()
                title = tool.upper() + '\n' + '\n'.join(textwrap.wrap(display, 9)[:1])
                key = self.open(('! ' if not row['available'] else '') + title, 'profile-' + selection_id(row),
                                ['--profile-id', selection_id(row)], 'claude' if tool == 'claude' else 'agent', 'agent' if row['available'] else 'alert',
                                'Open the mission panel with this exact harness, profile and command. Never falls back to another account.',
                                tool + ' / ' + row['profile'] + ' / ' + (row['command'] if row.get('kind') != 'application' else 'default'))
                key.warn = not row['available']
                buttons.append(key)
            panel = self.action(L('PANEL', 'PANNEAU'), tool if tool in ('codex', 'claude', 'agy') else 'mission', 'mission', 'agent',
                                'Open the mission panel for this harness.', L('PANEL', 'PANNEAU'))
            self.pages[page] = Page(page, buttons, header=[panel, self.refresh()], fixed=False)
            available = [b for b, r in zip(buttons, rows) if r['available']]
            folder = self.folder(('! ' if not available else '') + tool.upper(), page, 'claude' if tool == 'claude' else 'agent', 'agent' if available else 'alert')
            folder.warn = not available
            folders.append(folder)
            if available:
                # One exact account: the home key opens it directly (one press to the mission panel).
                if len(rows) == 1:
                    featured.append(Key(buttons[0].title, 'open', 'agent', buttons[0].icon, buttons[0].target, buttons[0].description, buttons[0].name))
                else:
                    featured.append(self.folder(tool.upper(), page, folder.icon, 'agent'))
        return featured, folders

    def home(self, k, harness):
        capacity = self.grid.capacity
        if capacity >= 32:
            fallback = [k['ai-web'], k['mcp'], k['orch'], k['ai-apps']]
            slots = (harness + fallback)[:4]
            layout = [k['mission'], *slots, k['sessions'], k['context'], k['profiles'],
                      k['wf-plan'], k['wf-implement'], k['wf-review'], k['wf-debug'], k['wf-test'], k['wf-handoff'], k['prompts'], k['agentic'],
                      k['terminal'], k['editor'], k['project'], k['files'], k['t-build'], k['t-test'], k['t-lint'], k['run'],
                      k['g-status'], k['g-pull'], k['g-commit'], k['g-push'], k['git'], k['system'], k['media'], k['refresh']]
            layout += [k['dev']] if capacity > 32 else []
            self.pages['home'] = Page('home', layout)
            return
        fallback = [k['profiles'], k['context'], k['ai-web']]
        h = (harness + fallback)[:3]
        if capacity >= 15:
            self.pages['home'] = Page('home', [k['mission'], h[0], h[1], h[2], k['sessions'],
                                               k['terminal'], k['editor'], k['git'], k['run'], k['prompts'],
                                               k['agentic'], k['dev'], k['system'], k['media'], k['refresh']])
        else:
            self.pages['home'] = Page('home', [k['mission'], h[0], k['terminal'], k['git'], k['sessions'], k['run'],
                                               k['prompts'], k['editor'], k['agentic'], k['dev'], k['system'],
                                               h[1], h[2], k['media'], k['refresh']], fixed=False)

    def dev_pages(self, k):
        L = self.L
        dev_entries = [e for e in self.apps if e.get('category') == 'dev']

        def rank(entry):
            name = entry['name'].casefold()
            return next((i for i, v in enumerate(FEATURED_DEV) if name == v or name.startswith(v + ' ')), len(FEATURED_DEV))
        featured = []
        for tool, label in (('cursor', 'CURSOR'), ('vscode', 'VS CODE'), ('orca', 'ORCA')):
            if tool in self.installed:
                featured.append(self.action(label, tool, 'code', 'dev', 'Open the selected project in ' + label.title() + '.'))
        skip = ('installer', 'blend', 'powershell', 'terminal', 'wsl settings', 'uninstall')
        covered = {'cursor' if 'cursor' in self.installed else None, 'visual studio code' if 'vscode' in self.installed else None}
        for entry in sorted(dev_entries, key=lambda e: (rank(e), e['name'].casefold())):
            if not any(word in entry['name'].casefold() for word in skip) and entry['name'].casefold() not in covered:
                featured.append(self.app(entry, 'dev'))
        self.pages['dev'] = Page('dev', [k['terminal'], k['editor'], k['run'], k['debug'], k['git'], k['project'], k['files'],
                                         k['diag'], k['logs'], k['dev-apps'], *featured[:4]])
        H = self.hotkey
        self.pages['editor'] = Page('editor', [
            H(L('COMMANDS', 'COMMANDES'), 80, 'keyboard', ctrl=True, shift=True), H(L('FIND FILE', 'FICHIER'), 80, 'search', ctrl=True),
            H(L('SEARCH', 'RECHERCHE'), 70, 'search', ctrl=True, shift=True), H(L('SAVE', 'SAUVER'), 83, 'document', ctrl=True),
            H(L('FORMAT', 'FORMATER'), 70, 'format', shift=True, alt=True), H(L('COPY', 'COPIER'), 67, 'clipboard', ctrl=True),
            H(L('PASTE', 'COLLER'), 86, 'clipboard', ctrl=True), H(L('PANEL', 'PANNEAU'), 74, 'terminal', ctrl=True),
            H(L('PROBLEMS', 'PROBLEMES'), 77, 'warning', ctrl=True, shift=True), H(L('RENAME', 'RENOMMER'), 113, 'keyboard', qt=16777265),
            H(L('DEFINITION', 'DEFINITION'), 123, 'code', qt=16777275), H(L('UNDO', 'ANNULER'), 90, 'keyboard', ctrl=True),
            H(L('REDO', 'RETABLIR'), 89, 'keyboard', ctrl=True), H(L('ESCAPE', 'ECHAP'), 27, 'keyboard', qt=16777216)])
        self.pages['debug'] = Page('debug', [
            H(L('START\nF5', 'DEMARRER\nF5'), 116, 'run', 'run', qt=16777268), H('STOP', 116, 'stop', 'run', shift=True, qt=16777268),
            H(L('RESTART', 'RELANCER'), 116, 'refresh', 'run', ctrl=True, shift=True, qt=16777268),
            H(L('BREAK\nPOINT', 'POINT\nARRET'), 120, 'breakpoint', 'run', qt=16777272),
            H(L('STEP\nOVER', 'PAS A\nPAS'), 121, 'step-over', 'run', qt=16777273),
            H(L('STEP\nINTO', 'ENTRER'), 122, 'step-into', 'run', qt=16777274),
            H(L('STEP\nOUT', 'SORTIR'), 122, 'step-out', 'run', shift=True, qt=16777274),
            H('BUILD', 66, 'build', 'run', ctrl=True, shift=True)])
        self.pages['git-web'] = Page('git-web', [self.website('GITHUB', 'github', 'git'), self.website('PULL REQ', 'github-pr', 'git'),
                                                 self.website('ISSUES', 'github-issues', 'git')])

    def agent_pages(self):
        L = self.L
        self.pages['prompts'] = Page('prompts', [self.text(L(*PROMPT_LABELS[key]), 'Communicate in English. ' + text, PROMPT_ICONS.get(key, 'prompt'))
                                                 for key, text in TEXT_PROMPTS.items()], fixed=False)
        self.pages['web'] = Page('web', [
            self.action(L('BROWSER', 'NAVIGATEUR'), 'browser', 'settings', 'web', 'Choose Chrome, Edge, Firefox or Brave and preferences.'),
            self.action(L('WORK', 'TRAVAIL'), 'web-work', 'web', 'web', 'Select the work web context. Does not change CLI profiles.'),
            self.action(L('PERSONAL', 'PERSO'), 'web-personal', 'web', 'web', 'Select the personal web context. Does not change CLI profiles.'),
            self.website('CHATGPT', 'chatgpt'), self.website('CLAUDE', 'claude'), self.website('GEMINI', 'gemini'),
            self.website('PERPLEXITY', 'perplexity'), self.website('GITHUB', 'github'), self.website('GITHUB PR', 'github-pr'),
            self.website('ISSUES', 'github-issues')])
        self.pages['orchestrator'] = Page('orchestrator', [
            self.action('ORCH', 'factory', 'hub', 'agent', 'Open the user-selected external orchestrator, or offer configuration.'),
            self.action(L('CONTROL', 'PILOTAGE'), 'factory-status', 'settings', 'agent',
                        'Choose an optional orchestrator and inspect supported status.')])

    def system_pages(self, k):
        L = self.L
        H = self.hotkey
        capture = self.action(L('PHOTO\nVIDEO', 'PHOTO\nVIDEO'), 'capture', 'camera', 'system',
                              'Open Snipping Tool: choose screenshot or recording. Recording starts only by user action.') if 'capture' in self.installed else None
        self.pages['aidev'] = Page('aidev', [
            self.action(L('SETTINGS', 'REGLAGES'), 'mission', 'settings', 'nav', 'Panel language and Stream Deck profile update.', L('SETTINGS', 'REGLAGES')),
            k['diag'], k['logs'], self.action('GUIDE', 'guide', 'document', 'nav', 'Open the local README.'), k['refresh']])
        self.pages['system'] = Page('system', [
            self.folder('APPS', 'daily-apps', 'apps', 'system'), self.folder('WINDOWS', 'windows', 'windows', 'system'),
            self.folder(L('DESKTOP', 'BUREAU'), 'desktop', 'desktop', 'system'), self.folder('CPU / RAM', 'cpu', 'chart', 'system'),
            self.action(L('BROWSER', 'NAVIGATEUR'), 'browser-open', 'web', 'system', 'Choose an installed browser and open it.'),
            self.action(L('FILES', 'FICHIERS'), 'files', 'folder', 'system', 'Open the project folder or home directory.'),
            capture, H(L('CLIPBOARD', 'PRESSE-PAP.'), 86, 'clipboard', 'system', win=True),
            self.windows(L('CALCULATOR', 'CALC'), 'calculator', 'calc', 'Open Windows Calculator.'),
            self.windows(L('NOTEPAD', 'BLOC-NOTES'), 'notepad', 'document', 'Open Notepad.'),
            H(L('SEARCH', 'RECHERCHE'), 83, 'search', 'system', win=True), H(L('LOCK', 'VERROU'), 76, 'lock', 'alert', win=True),
            self.action(L('SETTINGS', 'REGLAGES'), 'windows-settings', 'settings', 'system', 'Open Windows Settings.'),
            self.folder('AI DEV', 'aidev', 'settings', 'nav')])
        media = [H(L('PREVIOUS', 'PRECEDENT'), 177, 'track-prev', 'media', qt=0x01000082),
                 H(L('PLAY / PAUSE', 'LECTURE'), 179, 'playpause', 'media', qt=0x01000086),
                 H(L('NEXT', 'SUIVANT'), 176, 'track-next', 'media', qt=0x01000083),
                 H(L('MUTE', 'MUET'), 173, 'mute', 'media', qt=0x01000071),
                 H('VOL -', 174, 'volume-down', 'media', qt=0x01000070), H('VOL +', 175, 'volume', 'media', qt=0x01000072)]
        if 'spotify' in self.installed:
            media.append(self.action('SPOTIFY', 'spotify', 'music', 'media', 'Open installed Spotify. No playback starts automatically.'))
        self.pages['media'] = Page('media', media)
        W = self.windows
        self.pages['windows'] = Page('windows', [
            W(L('DISPLAY', 'AFFICHAGE'), 'display', 'screen', 'Open Windows display settings.'),
            W(L('SOUND', 'SON'), 'sound', 'volume', 'Open Windows sound settings.'),
            W(L('NETWORK', 'RESEAU'), 'network', 'web', 'Open Windows network status.'),
            W('BLUETOOTH', 'bluetooth', 'settings', 'Open Bluetooth settings.'),
            W(L('STORAGE', 'STOCKAGE'), 'storage', 'chart', 'Open storage settings.'),
            W(L('DOWNLOADS', 'TELECHARG.'), 'downloads', 'pull', 'Open Downloads.'),
            W('DOCUMENTS', 'documents', 'folder', 'Open Documents.'), W(L('PICTURES', 'IMAGES'), 'pictures', 'camera', 'Open Pictures.'),
            W(L('RECYCLE', 'CORBEILLE'), 'recycle-bin', 'folder', 'Open Recycle Bin without emptying it.'),
            H('EMOJI', 190, 'keyboard', 'system', win=True, qt=46),
            H(L('TASK VIEW', 'VUE TACHES'), 9, 'desktop', 'system', win=True, qt=16777217),
            W(L('SERVICES', 'SERVICES'), 'services', 'settings', 'Inspect Windows services.'),
            W(L('EVENTS', 'EVENEMENTS'), 'event-viewer', 'log', 'Open Event Viewer.')])
        self.pages['desktop'] = Page('desktop', [
            H(L('SHOW\nDESKTOP', 'AFFICHER'), 68, 'desktop', 'system', win=True),
            H(L('TASK\nVIEW', 'VUE\nTACHES'), 9, 'desktop', 'system', win=True, qt=16777217),
            H(L('DISPLAY\nMODE', 'MODE\nECRAN'), 80, 'screen', 'system', win=True),
            W(L('DISPLAY', 'AFFICHAGE'), 'display', 'screen', 'Open display settings to identify and arrange monitors.'),
            H(L('SNIP', 'CAPTURE'), 83, 'camera', 'system', shift=True, win=True),
            H(L('NEW\nDESKTOP', 'NOUV.\nBUREAU'), 68, 'desktop', 'system', ctrl=True, win=True),
            H(L('PREV\nDESKTOP', 'BUREAU\nPREC.'), 37, 'track-prev', 'system', ctrl=True, win=True, qt=16777234),
            H(L('NEXT\nDESKTOP', 'BUREAU\nSUIV.'), 39, 'track-next', 'system', ctrl=True, win=True, qt=16777236),
            H(L('CLOSE\nDESKTOP', 'FERMER\nBUREAU'), 115, 'stop', 'alert', ctrl=True, win=True, qt=16777267),
            H(L('MOVE\nLEFT', 'ECRAN\nGAUCHE'), 37, 'back', 'system', shift=True, win=True, qt=16777234),
            H(L('MOVE\nRIGHT', 'ECRAN\nDROIT'), 39, 'switch', 'system', shift=True, win=True, qt=16777236),
            H(L('MINIMIZE', 'MINIMISER'), 77, 'pull', 'system', win=True),
            H(L('RESTORE', 'RESTAURER'), 77, 'push', 'system', shift=True, win=True)])
        cpu = [self.action(L('TASKS', 'TACHES'), 'monitor', 'chart', 'system', 'Open Task Manager.'),
               self.action(L('RESOURCES', 'RESSOURCES'), 'resources', 'chart', 'system', 'Open Resource Monitor.'),
               self.action('PERFMON', 'performance', 'chart', 'system', 'Open Performance Monitor.'),
               self.action(L('SYSTEM\nINFO', 'INFOS\nSYSTEME'), 'system-info', 'document', 'system', 'Open System Information.')]
        self.pages['cpu'] = Page('cpu', [key for key in cpu if key.target in self.installed])

    def catalog_pages(self):
        L = self.L
        all_apps = lambda text: self.action(L('ALL APPS', 'TOUTES APPS'), 'applications', 'search', 'system', text, L('ALL APPS', 'TOUTES APPS'))
        daily = [self.app(e) for e in self.apps if e.get('category') == 'daily']
        dev = [self.app(e, 'dev') for e in self.apps if e.get('category') == 'dev']
        ai_entries = sorted((e for e in self.apps if e.get('category') == 'agentic'),
                            key=lambda e: (e['name'].casefold() not in ('claude', 'chatgpt'), e['name'].casefold()))
        ai = [self.app(e, 'agent') for e in ai_entries]
        self.pages['daily-apps'] = Page('daily-apps', daily, [all_apps('Search all installed Start-menu applications.'), self.refresh()], False)
        self.pages['dev-apps'] = Page('dev-apps', dev, [all_apps('Search installed development tools.'), self.refresh()], False)
        self.pages['ai-apps'] = Page('ai-apps', ai, [all_apps('Search installed AI desktop applications.'), self.refresh()], False)
        mcp = []
        for entry in self.mcp:
            key = self.open(wrap(entry['name']), 'mcp-' + entry['id'], ['--mcp-id', entry['id']], 'mcp', 'agent',
                            'Inspect this local MCP declaration. Connection, tools and credentials are not tested or exposed.',
                            entry['host'] + ' / ' + entry['name'])
            mcp.append(key)
        self.pages['mcp'] = Page('mcp', mcp, [self.action('MCP', 'mcp', 'mcp', 'agent',
                                                          'Refresh known local MCP configurations. No server is started.'), self.refresh()], False)

    def shortcut_manifest(self):
        """Every shortcut the deck references, plus legacy names kept for previously imported profiles."""
        rows = dict(self.shortcuts)
        for action in LEGACY_ACTIONS:
            rows.setdefault(action, command_line(['--action', action]))
        for utility in WINDOWS_UTILITIES:
            rows.setdefault('windows-' + utility, command_line(['--windows-action', utility]))
        for site, url in WEBSITES.items():
            rows.setdefault('web-' + site, command_line(['--action', 'web', '--url', url]))
        for language in ('en', 'fr'):
            rows.setdefault('deck-refresh-' + language, command_line(['--action', 'deck-refresh', '--deck-language', language]))
        return [{'name': name, 'arguments': arguments} for name, arguments in sorted(rows.items())]
