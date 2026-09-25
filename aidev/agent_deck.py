"""Developer desk with native tools, local apps, search, media and AI workflows.

Home launches the whole workstation. Agent workflows live inside AI; scripted
keys use the small PowerShell dispatcher, never the Python control panel.
"""
import json
import re
from pathlib import Path
from .deck_layout import DeckBuilder, FEATURED_DEV, Grid, Key, Page, wrap

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
INTENT_ICONS = {'ask': 'prompt', 'fix': 'bug', 'review': 'review', 'commit': 'commit',
                'explain': 'document', 'test': 'check', 'plan': 'plan', 'pr': 'branch', 'handoff': 'handoff'}
INTENT_TITLES = {'ask': ('ASK', 'DEMANDER'), 'fix': ('FIX', 'CORRIGER'),
                 'review': ('REVIEW', 'REVUE'), 'commit': ('COMMIT', 'COMMIT'),
                 'explain': ('EXPLAIN', 'EXPLIQUER'), 'test': ('TEST + FIX', 'TEST + FIX'),
                 'plan': ('PLAN', 'PLAN'), 'pr': ('PR DRAFT', 'BROUILLON PR'),
                 'handoff': ('HANDOFF', 'RELAIS')}
# Match agentdeck/terminal.ps1: Ctrl+Alt+F13..F23 are handled by PSReadLine
# in the active PowerShell prompt, whose current directory supplies the context.
GIT_HOTKEYS = {action: (124 + index, 16777276 + index) for index, action in enumerate(
    ('status', 'diff', 'log', 'fetch', 'pull', 'push', 'stage', 'switch', 'branch', 'stash', 'unstash'))}


def load_intents(path=None):
    return json.loads(Path(path or ROOT / 'agentdeck/intents.json').read_text('utf-8-sig'))


class AgentDeck:
    def __init__(self, script_path, grid=None, intents=None, apps=None, terminals=None, language=None, harnesses=None):
        self.script = str(script_path)
        self.grid = grid or Grid()
        self.intents = intents if intents is not None else load_intents()
        self.apps = sorted({entry['deck_id']: entry for entry in (apps or [])}.values(),
                           key=lambda entry: (entry['name'].casefold(), entry['deck_id']))
        self.terminals = terminals or []
        self.harnesses = harnesses
        requested = language or self.intents.get('defaults', {}).get('language', 'fr')
        self.language = 'fr' if str(requested).lower().startswith('fr') else 'en'
        self.profile_name = 'AI Dev Agentic'
        self.stable_id = 'ai-dev-agentic-v1'
        self.shortcuts, self.pages = {}, {}

    def L(self, en, fr):
        return fr if self.language == 'fr' else en

    def agent(self, title, intent, icon, zone='agent', description=''):
        if not re.fullmatch(r'[a-z0-9-]+', intent):
            raise ValueError('Invalid deck action: ' + intent)
        self.shortcuts['ai-' + intent] = (POWERSHELL,
            '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%s" %s' % (self.script, intent))
        return Key(title, 'open', zone, icon, 'ai-' + intent, description or 'Run deck action: ' + intent)

    def folder(self, title, page, icon, zone='nav'):
        return Key(title, 'folder', zone, icon, page)

    def app(self, entry):
        lowered = entry['name'].casefold()
        aliases = {'visual studio code': 'VS CODE', 'docker desktop': 'DOCKER\nDESKTOP',
                   'github desktop': 'GITHUB\nDESKTOP', 'chatgpt': 'CHATGPT\nDESKTOP',
                   'claude': 'CLAUDE\nDESKTOP', 'windows terminal': 'TERMINAL'}
        zone = {'agentic': 'agent', 'dev': 'dev'}.get(entry.get('category'), 'system')
        icon = ('claude' if lowered in ('claude', 'claude desktop') else
                'chatgpt' if lowered in ('chatgpt', 'chatgpt desktop') else
                'music' if any(part in lowered for part in ('spotify', 'music', 'vlc')) else
                'git' if any(part in lowered for part in ('github desktop', 'gitkraken')) else
                'code' if zone == 'dev' else 'agent' if zone == 'agent' else 'apps')
        key = self.agent(aliases.get(lowered, wrap(entry['name'])), 'app-' + entry['deck_id'], icon,
                         zone, 'Open this installed application: ' + entry['name'])
        key.name = entry['name'] + (' Desktop' if lowered in ('claude', 'chatgpt') else '')
        return key

    def _featured(self, names, limit):
        def rank(entry):
            lowered = entry['name'].casefold()
            return next((i for i, name in enumerate(names)
                         if lowered == name or lowered.startswith(name + ' ')), len(names))
        entries = [entry for entry in self.apps if rank(entry) < len(names)
                   and not any(word in entry['name'].casefold()
                               for word in ('uninstall', 'installer', 'release notes'))]
        return sorted(entries, key=lambda entry: (rank(entry), entry['name'].casefold()))[:limit]

    def _catalog(self):
        """One app tree with short alphabetic groups instead of a long MORE chain."""
        categories = [('dev', self.L('DEV APPS', 'APPS DEV'), 'code', 'dev'),
                      ('agentic', self.L('AI APPS', 'APPS IA'), 'agent', 'agent'),
                      ('daily', self.L('DAILY APPS', 'APPS USUELLES'), 'apps', 'system')]
        roots, width = [], self.grid.capacity - 1

        def tree(page_id, entries, zone, icon):
            if len(entries) <= width:
                self.pages[page_id] = Page(page_id, [self.app(entry) for entry in entries], fixed=False)
                return
            size = width
            while (len(entries) + size - 1) // size > width:
                size *= width
            keys = []
            for index, start in enumerate(range(0, len(entries), size)):
                group, child = entries[start:start + size], page_id + '-' + str(index + 1)
                tree(child, group, zone, icon)
                first, last = group[0]['name'], group[-1]['name']
                key = self.folder(first[:7].upper() + '\n' + last[:7].upper(), child, icon, zone)
                key.name = first + ' — ' + last
                key.description = 'Installed applications, alphabetically: ' + key.name
                keys.append(key)
            self.pages[page_id] = Page(page_id, keys, fixed=False)

        for category, title, icon, zone in categories:
            entries = [entry for entry in self.apps if
                (entry.get('category') if entry.get('category') in ('dev', 'agentic') else 'daily') == category]
            if entries:
                page_id = 'catalog-' + category
                tree(page_id, entries, zone, icon)
                roots.append(self.folder(title, page_id, icon, zone))
        roots.append(self.agent(self.L('RESCAN', 'ACTUALISER'), 'refresh', 'refresh', 'nav',
                                'Detect installed tools again and regenerate the Stream Deck profile.'))
        self.pages['apps'] = Page('apps', roots)

    def _cli_pages(self):
        L, a, F = self.L, self.agent, self.folder
        settings = a(L('PROFILES', 'PROFILS'), 'settings', 'settings', 'agent',
                     'Choose the harness and exact account profile.')
        if self.harnesses is None:
            # Compatibility for callers that have not supplied a discovery result.
            keys = [a('CLAUDE\nCLI', 'claude', 'claude', 'agent', 'Open Claude Code with the active account profile.'),
                    a('CODEX\nCLI', 'codex', 'code', 'agent', 'Open Codex with the active account profile.'),
                    a('AGY\nCLI', 'agy', 'agent', 'agent', 'Open AGY with the active account profile.'),
                    a('WORK /\nPERSO', 'profile', 'profile', 'agent', 'Switch the active account context.'), settings]
        elif not self.harnesses:
            keys = [a(L('RESCAN', 'ACTUALISER'), 'refresh', 'refresh', 'nav',
                      'No CLI harness was detected. Rescan installed tools and PowerShell profiles.'), settings]
        else:
            groups, width = {}, self.grid.capacity - 1
            entries = sorted({entry['deck_id']: entry for entry in self.harnesses}.values(),
                             key=lambda entry: (entry['tool'].casefold(), entry.get('profile', 'default').casefold(),
                                                entry['command'].casefold()))
            for entry in entries:
                if not re.fullmatch('[a-f0-9]{16}', entry['deck_id']):
                    raise ValueError('Invalid CLI selection identifier.')
                groups.setdefault(entry['tool'], []).append(entry)

            def label(value, width=10):
                return value.upper() if len(value) <= width else value[:width - 4].upper() + '~' + value[-3:].upper()

            def key(entry):
                tool, profile = entry['tool'], entry.get('profile') or 'default'
                icon = {'claude': 'claude', 'codex': 'code', 'cursor': 'code'}.get(tool, 'agent')
                result = a(label(tool) + '\n' + label(profile), 'cli-' + entry['deck_id'], icon, 'agent',
                           'Open this exact detected command in the selected project: ' + entry['command'] +
                           '. Interactive launch; automatic task prompts require an implemented adapter.')
                result.name = entry['command'] + ' (' + profile + ')'
                return result

            def tree(page_id, entries, icon):
                if len(entries) <= width:
                    self.pages[page_id] = Page(page_id, [key(entry) for entry in entries], fixed=False)
                    return
                size = width
                while (len(entries) + size - 1) // size > width:
                    size *= width
                folders = []
                for index, start in enumerate(range(0, len(entries), size)):
                    chunk, child = entries[start:start + size], page_id + '-' + str(index + 1)
                    tree(child, chunk, icon)
                    first, last = chunk[0].get('profile', 'default'), chunk[-1].get('profile', 'default')
                    folder = F(label(first) + '\n' + label(last), child, icon, 'agent')
                    folder.name = first + ' — ' + last
                    folders.append(folder)
                self.pages[page_id] = Page(page_id, folders, fixed=False)

            keys = []
            for tool, entries in groups.items():
                page_id = 'cli-tool-' + tool
                icon = {'claude': 'claude', 'codex': 'code', 'cursor': 'code'}.get(tool, 'agent')
                tree(page_id, entries, icon)
                keys.append(F(wrap(tool), page_id, icon, 'agent'))
            keys += [settings, a(L('RESCAN', 'ACTUALISER'), 'refresh', 'refresh', 'nav',
                                 'Refresh installed CLI tools and exact PowerShell profile commands.')]
        self.pages['cli'] = Page('cli', keys)

    def build(self):
        L, a, F = self.L, self.agent, self.folder
        classic = DeckBuilder(self.language, Grid(), [], set()).build()
        H = classic.hotkey
        native = lambda page: [key for key in classic.pages[page].keys if key is not None and key.kind == 'hotkey']
        W = lambda en, fr, action, icon: a(L(en, fr), 'windows-' + action, icon, 'system', 'Open Windows ' + action + '.')
        web = lambda title, target, icon='web', zone='web': a(title, 'web-' + target, icon, zone,
            'Open this website using the selected browser for the active work/personal context.')
        self._catalog()
        self.pages['home'] = Page('home', [
            F('DEV', 'dev', 'code', 'dev'), F(L('AI', 'IA'), 'ai', 'agent', 'agent'),
            F(L('DAILY', 'QUOTIDIEN'), 'system', 'windows', 'system'), F('MEDIA', 'media', 'music', 'media'),
            F(L('SEARCH', 'RECHERCHE'), 'search', 'search', 'web'),
            F(L('TERMINALS', 'TERMINAUX'), 'terminals', 'terminal', 'dev'),
            F('POWER USER', 'power-user', 'terminal', 'system'),
            F('GIT', 'git', 'git', 'git'), F('APPS', 'apps', 'apps', 'system'), W('PHOTO\nVIDEO', 'PHOTO\nVIDEO', 'capture', 'camera'),
            H(L('CLIPBOARD', 'PRESSE-PAP.'), 86, 'clipboard', 'system', win=True),
            H(L('DICTATION', 'DICTEE'), 72, 'prompt', 'system', win=True),
            F(L('DESKTOP', 'BUREAU'), 'desktop', 'desktop', 'system'),
            a(L('PROJECT', 'PROJET'), 'project', 'folder', 'dev', 'Choose the working project.'),
            F(L('SETTINGS', 'REGLAGES'), 'settings', 'settings')], fixed=self.grid.capacity >= 15)
        self.pages['settings'] = Page('settings', [
            a('PREFERENCES', 'settings', 'settings', 'nav', 'Choose the project, language, harness, account profile and browsers.'),
            a(L('BROWSER', 'NAVIGATEUR'), 'browser', 'web', 'web', 'Choose a browser for each account context.'),
            a(L('TERMINAL\nSETUP', 'CONFIG\nTERMINAL'), 'shell-setup', 'terminal', 'dev',
              'Install or activate AIDevTerminal in PowerShell so Git keys use the active prompt and its current folder.'),
            a('WORK /\nPERSO', 'profile', 'profile', 'agent', 'Switch between work and personal account contexts.'),
            a(L('RESCAN', 'ACTUALISER'), 'refresh', 'refresh', 'nav', 'Detect local tools and regenerate the deck.'),
            a('GUIDE', 'help', 'document', 'nav', 'Open the local deck guide.')])

        desktop_ai = self._featured(('claude', 'chatgpt', 'claude desktop', 'chatgpt desktop'), 2)
        ai_keys = [self.app(entry) for entry in desktop_ai + self._featured(('orca',), 1)]
        for name, icon in (('chatgpt', 'chatgpt'), ('claude', 'claude')):
            if not any(entry['name'].casefold() in (name, name + ' desktop') for entry in desktop_ai):
                ai_keys.append(web(name.upper() + '\nWEB', name, icon, 'agent'))
        ai_keys += [F(L('WORKFLOWS', 'MISSIONS'), 'workflows', 'mission', 'agent'),
                    F(L('CLI /\nPROFILES', 'CLI /\nPROFILS'), 'cli', 'terminal', 'agent'),
                    a(L('CONTINUE', 'REPRENDRE'), 'continue', 'next', 'agent', 'Resume the last agent session in this project.'),
                    a('WORK /\nPERSO', 'profile', 'profile', 'agent', 'Switch the active account context.'),
                    a(L('AI SETTINGS', 'REGLAGES IA'), 'settings', 'settings', 'agent', 'Choose the default harness and exact profile.'),
                    web('CHATGPT\nWEB', 'chatgpt', 'chatgpt'), web('CLAUDE\nWEB', 'claude', 'claude'), web('GEMINI', 'gemini'),
                    a('PERPLEXITY', 'search-perplexity', 'search', 'web', 'Review a search query before opening Perplexity.')]
        self.pages['ai'] = Page('ai', list({key.target: key for key in ai_keys}.values()))
        self.pages['workflows'] = Page('workflows', [
            a(L(*INTENT_TITLES.get(name, (value['title'], value['title']))), name, INTENT_ICONS.get(name, 'agent'), 'agent',
              'Run ' + name + ' with the selected project, harness, profile and reviewed context.')
            for name, value in self.intents.get('intents', {}).items()])
        self._cli_pages()
        self.pages['terminals'] = Page('terminals', [
            a(wrap(entry['label']), 'terminal-' + entry['deck_id'], 'terminal', 'dev',
              'Open ' + entry['label'] + ' in the selected project.') for entry in self.terminals] or [
            a(L('RESCAN', 'ACTUALISER'), 'refresh', 'refresh', 'nav', 'No terminal detected. Rescan local tools.')])
        self.pages['tasks'] = Page('tasks', [
            a(L(en, fr), 'task-' + kind, icon, 'run', 'Run the detected ' + kind + ' task in the selected project.')
            for en, fr, kind, icon in [('BUILD', 'BUILD', 'build', 'build'), ('TEST', 'TEST', 'test', 'check'),
                ('LINT', 'LINT', 'lint', 'lint'), ('DEV SERVER', 'SERVEUR DEV', 'dev', 'run'),
                ('TYPES', 'TYPES', 'types', 'types'), ('FORMAT', 'FORMATER', 'format', 'format')]])
        git_keys = []
        for en, fr, action, icon, description in [
                ('STATUS', 'STATUS', 'status', 'git', 'Show branch and working-tree changes.'),
                ('DIFF', 'DIFF', 'diff', 'diff', 'Show the current unstaged diff.'),
                ('LOG', 'LOG', 'log', 'log', 'Show the recent commit graph.'),
                ('FETCH', 'FETCH', 'fetch', 'fetch', 'Fetch remote branches and prune obsolete remote references.'),
                ('PULL', 'PULL', 'pull', 'pull', 'Pull with fast-forward only.'),
                ('PUSH', 'PUSH', 'push', 'push', 'Confirm the branch and destination before pushing.'),
                ('STAGE', 'INDEXER', 'stage', 'stage', 'Review changes and confirm before staging all changes.'),
                ('SWITCH', 'CHANGER', 'switch', 'switch', 'Choose an existing branch.'),
                ('NEW BRANCH', 'NOUV. BRANCHE', 'branch', 'branch', 'Enter and validate a new branch name.'),
                ('STASH', 'REMISER', 'stash', 'stash', 'Confirm before storing the working changes in a stash.'),
                ('APPLY STASH', 'APPL. REMISE', 'unstash', 'unstash', 'Apply a chosen stash while retaining the stash.')]:
            virtual_key, qt_key = GIT_HOTKEYS[action]
            key = H(L(en, fr), virtual_key, icon, 'git', ctrl=True, alt=True, qt=qt_key)
            key.description = description + " Active PowerShell prompt/current folder; requires AIDevTerminal."
            git_keys.append(key)
        self.pages['git'] = Page('git', git_keys + [
            web('GITHUB', 'github', 'git', 'git'), web('PULL REQ', 'github-pr', 'branch', 'git'),
            web('ISSUES', 'github-issues', 'warning', 'git')])
        self.pages['editor'] = Page('editor', native('editor'))
        self.pages['debug'] = Page('debug', native('debug'))
        self.pages['dev'] = Page('dev', [
            F('BUILD / TEST', 'tasks', 'build', 'run'), F('GIT', 'git', 'git', 'git'),
            F(L('EDITOR', 'EDITEUR'), 'editor', 'keyboard', 'dev'), F('DEBUG', 'debug', 'bug', 'run'),
            F(L('TERMINALS', 'TERMINAUX'), 'terminals', 'terminal', 'dev'),
            a(L('PROJECT', 'PROJET'), 'project', 'folder', 'dev', 'Choose the working project.'),
            W('FILES', 'FICHIERS', 'files', 'folder'), F('DOCS', 'docs', 'document', 'web'),
            F('POWER USER', 'power-user', 'terminal', 'system'),
            *[self.app(entry) for entry in self._featured(('orca',) + FEATURED_DEV, 5)]])

        self.pages['clipboard'] = Page('clipboard', [
            H(L('COPY', 'COPIER'), 67, 'clipboard', 'system', ctrl=True), H(L('PASTE', 'COLLER'), 86, 'clipboard', 'system', ctrl=True),
            H(L('CUT', 'COUPER'), 88, 'clipboard', 'system', ctrl=True),
            H(L('PASTE TEXT', 'COLLER TEXTE'), 86, 'document', 'system', ctrl=True, shift=True),
            H(L('HISTORY', 'HISTORIQUE'), 86, 'clipboard', 'system', win=True),
            H(L('SELECT ALL', 'TOUT CHOISIR'), 65, 'keyboard', 'system', ctrl=True),
            H(L('UNDO', 'ANNULER'), 90, 'back', 'system', ctrl=True), H(L('REDO', 'RETABLIR'), 89, 'refresh', 'system', ctrl=True),
            H(L('DICTATION', 'DICTEE'), 72, 'prompt', 'system', win=True), H('EMOJI', 190, 'keyboard', 'system', win=True, qt=46)])
        daily_featured = self._featured(('powertoys', 'microsoft outlook', 'outlook', 'microsoft teams',
                                         'teams', 'slack', 'discord', 'onenote', 'obsidian', 'notion', 'whatsapp'), 3)
        self.pages['system'] = Page('system', [
            F('WINDOWS', 'windows', 'windows', 'system'), F('CPU / RAM', 'cpu', 'chart', 'system'),
            F('POWER USER', 'power-user', 'terminal', 'system'),
            F(L('CLIPBOARD', 'PRESSE-PAP.'), 'clipboard', 'clipboard', 'system'),
            W('CALCULATOR', 'CALC', 'calculator', 'calc'), W('NOTEPAD', 'BLOC-NOTES', 'notepad', 'document'),
            H(L('EXPLORER', 'EXPLORATEUR'), 69, 'folder', 'system', win=True),
            H(L('RUN', 'EXECUTER'), 82, 'run', 'system', win=True), H(L('PC SEARCH', 'RECHERCHE PC'), 83, 'search', 'system', win=True),
            H(L('LOCK', 'VERROUILLER'), 76, 'lock', 'system', win=True), W('SETTINGS', 'PARAMETRES', 'settings', 'settings'),
            *[self.app(entry) for entry in daily_featured]])
        self.pages['power-user'] = Page('power-user', [
            a(L(en, fr), 'diag-' + action, icon, 'system', description)
            for en, fr, action, icon, description in [
                ('PORTS', 'PORTS', 'ports', 'web', 'Inspect listening network ports and their owning processes.'),
                ('PROCESSES', 'PROCESSUS', 'processes', 'tasks', 'Inspect running processes and resource usage.'),
                ('CONNECTION', 'CONNEXION', 'connection', 'web', 'Diagnose network connectivity.'),
                ('DNS', 'DNS', 'dns', 'search', 'Inspect DNS configuration and name resolution.'),
                ('ROUTES', 'ROUTES', 'routes', 'branch', 'Inspect the Windows network route table.'),
                ('PATH / ENV', 'PATH / ENV', 'path', 'terminal', 'Inspect executable search paths and command resolution.'),
                ('DISK SPACE', 'ESPACE\nDISQUE', 'disk', 'chart', 'Inspect available disk space and storage volumes.'),
                ('STARTUP', 'DEMARRAGE', 'startup', 'run', 'Inspect applications configured to start with Windows.'),
                ('WSL', 'WSL', 'wsl', 'terminal', 'Inspect installed WSL distributions and their status.'),
                ('DOCKER', 'DOCKER', 'docker', 'apps', 'Inspect Docker availability and local container status.'),
                ('LONG PATHS', 'CHEMINS\nLONGS', 'longpaths', 'folder', 'Inspect Windows support for long file paths.')]] + [
            H(L('TASK\nMANAGER', 'GESTION\nTACHES'), 27, 'chart', 'system', ctrl=True, shift=True, qt=16777216),
            H(L('CLIPBOARD', 'PRESSE-PAP.'), 86, 'clipboard', 'system', win=True)])
        self.pages['windows'] = Page('windows', [W(en, fr, action, icon) for en, fr, action, icon in [
            ('DISPLAY', 'AFFICHAGE', 'display', 'screen'), ('SOUND', 'SON', 'sound', 'volume'), ('NETWORK', 'RESEAU', 'network', 'web'),
            ('BLUETOOTH', 'BLUETOOTH', 'bluetooth', 'settings'), ('STORAGE', 'STOCKAGE', 'storage', 'chart'),
            ('DOWNLOADS', 'TELECHARG.', 'downloads', 'pull'), ('DOCUMENTS', 'DOCUMENTS', 'documents', 'folder'),
            ('PICTURES', 'IMAGES', 'pictures', 'camera'), ('RECYCLE BIN', 'CORBEILLE', 'recycle-bin', 'folder'),
            ('SERVICES', 'SERVICES', 'services', 'settings'), ('EVENTS', 'EVENEMENTS', 'event-viewer', 'log')]] + [
            H(L('QUICK\nSETTINGS', 'REGLAGES\nRAPIDES'), 65, 'settings', 'system', win=True),
            H('NOTIFICATIONS', 78, 'warning', 'system', win=True)])
        self.pages['cpu'] = Page('cpu', [
            H(L('TASK\nMANAGER', 'GESTION\nTACHES'), 27, 'chart', 'system', ctrl=True, shift=True, qt=16777216),
            W('RESOURCES', 'RESSOURCES', 'resource-monitor', 'chart'), W('PERFMON', 'PERFMON', 'performance', 'chart'),
            W('SYSTEM\nINFO', 'INFOS\nSYSTEME', 'system-info', 'document')])
        self.pages['desktop'] = Page('desktop', native('desktop') + [
            H(L('SNAP\nLAYOUTS', 'DISPOSITION'), 90, 'screen', 'system', win=True), W('DISPLAY', 'AFFICHAGE', 'display', 'screen')])
        media_apps = self._featured(('spotify', 'vlc', 'obs studio', 'audacity', 'clipchamp'), 3)
        self.pages['media'] = Page('media', [*native('media'), W('PHOTO\nVIDEO', 'PHOTO\nVIDEO', 'capture', 'camera'),
            W('SOUND', 'SON', 'sound', 'volume'), web('YOUTUBE', 'youtube', 'playpause', 'media'),
            *[self.app(entry) for entry in media_apps]])
        if not any(entry['name'].casefold().startswith('spotify') for entry in media_apps):
            self.pages['media'].keys.append(web('SPOTIFY\nWEB', 'spotify', 'music', 'media'))
        self.pages['search'] = Page('search', [
            a(title, 'search-' + engine, icon, 'web',
              'Review your query before searching ' + title + ' in the selected browser. No clipboard text is sent automatically.')
            for title, engine, icon in [('GOOGLE', 'google', 'search'), ('BING', 'bing', 'search'),
                ('DUCKDUCKGO', 'duckduckgo', 'search'), ('GITHUB', 'github', 'git'),
                ('STACK\nOVERFLOW', 'stackoverflow', 'code'), ('YOUTUBE', 'youtube', 'playpause'), ('PERPLEXITY', 'perplexity', 'agent')]] + [
            F('DOCS', 'docs', 'document', 'web'), a(L('BROWSER', 'NAVIGATEUR'), 'browser', 'settings', 'web',
            'Choose the browser for this context.'), web('GITHUB PR', 'github-pr', 'branch'), web('ISSUES', 'github-issues', 'warning')])
        self.pages['docs'] = Page('docs', [web(title, site, 'document') for title, site in
            [('MDN', 'mdn'), ('MS LEARN', 'mslearn'), ('NPM', 'npm'), ('PYPI', 'pypi')]])
        return self
