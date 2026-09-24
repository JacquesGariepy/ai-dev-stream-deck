"""Direct Git keys for the Stream Deck.

Every command runs visibly in a new terminal in the selected project, with the
exact argument list shown first. Nothing is evaluated by a shell. Push asks for
confirmation with the branch and destination; branch names are validated by Git.
"""
import shutil
from pathlib import Path
from .runtime import git_read
from .storage import settings

# name -> fixed arguments. Interactive commands (add -p, commit) keep Git's own prompts/editor.
COMMANDS = {
    'status': ['status', '--short', '--branch'],
    'diff': ['diff'],
    'log': ['--no-pager', 'log', '--oneline', '--graph', '--decorate', '-n', '40'],
    'fetch': ['fetch', '--all', '--prune'],
    'pull': ['pull', '--ff-only'],
    'stage': ['add', '--patch'],
    'commit': ['commit', '--verbose'],
    'stash': ['stash', 'push', '--include-untracked'],
    'unstash': ['stash', 'pop'],
}
INTERACTIVE = {'push', 'branch', 'switch'}
ACTIONS = tuple(COMMANDS) + tuple(sorted(INTERACTIVE))


def project():
    value = settings().get('project')
    if not value:
        raise ValueError('Choose a project folder first.')
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError('Project must be a directory.')
    if not git_read(path, 'rev-parse', '--is-inside-work-tree')['ok']:
        raise ValueError('The selected project is not a Git working tree: ' + str(path))
    return path


def git_executable():
    executable = shutil.which('git')
    if not executable:
        raise FileNotFoundError('Git was not found on PATH.')
    return executable


def task(name, arguments, folder):
    return {'name': 'git ' + ' '.join(arguments), 'executable': git_executable(), 'arguments': list(arguments),
            'project': str(folder), 'category': 'git', 'id': 'git-' + name}


def push_plan(folder):
    """Arguments and a human description for pushing the current branch."""
    branch = git_read(folder, 'branch', '--show-current')
    if not branch['ok'] or not branch['output']:
        raise ValueError('Detached HEAD: switch to a branch before pushing.')
    upstream = git_read(folder, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    if upstream['ok'] and upstream['output']:
        ahead = git_read(folder, 'rev-list', '--count', '@{upstream}..HEAD')
        count = ahead['output'] if ahead['ok'] else '?'
        return ['push'], branch['output'], upstream['output'], count
    remotes = git_read(folder, 'remote')['output'].split()
    if 'origin' not in remotes:
        raise ValueError('No upstream and no "origin" remote. Configure a remote first.')
    return ['push', '--set-upstream', 'origin', 'HEAD'], branch['output'], 'origin/' + branch['output'] + ' (new)', '?'


def valid_branch(folder, name):
    name = (name or '').strip()
    if not name or name.startswith('-'):
        return None
    result = git_read(folder, 'check-ref-format', '--branch', name)
    return result['output'] if result['ok'] else None


def local_branches(folder):
    result = git_read(folder, 'for-each-ref', '--format=%(refname:short)', 'refs/heads')
    return [line for line in result['output'].splitlines() if line.strip()] if result['ok'] else []


def run(name):
    from .project_tasks import launch
    if name not in ACTIONS:
        raise ValueError('Unknown Git action.')
    folder = project()
    if name in COMMANDS:
        return launch(task(name, COMMANDS[name], folder))
    return _interactive(name, folder, launch)


def _interactive(name, folder, launch):
    import tkinter as tk
    from tkinter import messagebox, simpledialog
    from .i18n import resolve_language, tr
    language = resolve_language(settings().get('language', 'auto'))
    text = lambda key: tr(key, language)
    root = tk.Tk(); root.withdraw()
    try:
        if name == 'push':
            arguments, branch, destination, ahead = push_plan(folder)
            if messagebox.askokcancel('AI Dev — Git push', text('git_push_confirm').format(
                    branch=branch, destination=destination, ahead=ahead, project=folder), parent=root):
                launch(task(name, arguments, folder))
        elif name == 'branch':
            value = simpledialog.askstring('AI Dev — Git', text('git_branch_name'), parent=root)
            if value is None:
                return
            branch = valid_branch(folder, value)
            if not branch:
                raise ValueError(text('git_branch_invalid'))
            launch(task(name, ['switch', '--create', branch], folder))
        else:
            branches = local_branches(folder)
            current = git_read(folder, 'branch', '--show-current')['output']
            choice = _choose(root, text('git_switch_title'), [b for b in branches if b != current])
            if choice:
                launch(task(name, ['switch', choice], folder))
    finally:
        root.destroy()


def _choose(root, title, values):
    import tkinter as tk
    from tkinter import ttk
    if not values:
        return None
    window = tk.Toplevel(root); window.title('AI Dev — ' + title); window.geometry('420x380')
    window.attributes('-topmost', True)
    result = {}
    frame = ttk.Frame(window, padding=14); frame.pack(fill='both', expand=True)
    ttk.Label(frame, text=title, font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 8))
    listbox = tk.Listbox(frame, font=('Consolas', 11), activestyle='dotbox')
    for value in values:
        listbox.insert('end', value)
    listbox.selection_set(0); listbox.pack(fill='both', expand=True); listbox.focus_set()

    def accept(_=None):
        selection = listbox.curselection()
        if selection:
            result['value'] = values[selection[0]]
        window.destroy()
    listbox.bind('<Double-1>', accept); listbox.bind('<Return>', accept); window.bind('<Escape>', lambda _: window.destroy())
    ttk.Button(frame, text='OK', command=accept).pack(anchor='e', pady=(8, 0))
    window.grab_set(); root.wait_window(window)
    return result.get('value')
