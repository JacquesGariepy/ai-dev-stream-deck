"""Local context capture, mission receipts, and interactive terminal launch."""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from .agents import arguments_for
from .discovery import NO_WINDOW, SCRIPTS, discover, find_entry
from .storage import data_dir, save_json


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def git_read(project, *args):
    try:
        result = subprocess.run(['git', '-C', str(project), *args], capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=20,
                                creationflags=NO_WINDOW)
        return {'ok': result.returncode == 0, 'output': (result.stdout if result.returncode == 0 else result.stderr).strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'ok': False, 'output': str(error)}


def capture_context(project, identifier=None):
    if not str(project).strip():raise ValueError('Choose a project folder first.')
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be a directory.')
    result = {'project': str(project), 'generated': now(),
              'branch': git_read(project, 'branch', '--show-current'),
              'status': git_read(project, 'status', '--short', '--branch'),
              'diff_stat': git_read(project, 'diff', '--stat'),
              'staged_stat': git_read(project, 'diff', '--cached', '--stat'),
              'recent_commits': git_read(project, 'log', '-5', '--format=%h %s'),
              'limits': 'Git metadata only. No file contents read, no tests run, no cost or token measurements.'}
    path = data_dir() / 'context' / ((identifier or 'latest') + '.json')
    save_json(path, result)
    if identifier:
        save_json(data_dir() / 'context/latest.json', result)
    return path


def prepare(entry, project, workflow, objective='', english_confirmed=False):
    if not str(project).strip():raise ValueError('Choose a project folder first.')
    if not entry or not entry['available']:
        raise ValueError('Choose an available harness and profile.')
    identifier = str(uuid.uuid4())
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be a directory.')
    mission = {'id': identifier, 'created': now(), 'tool': entry['tool'], 'profile': entry['profile'],
               'command': entry['command'], 'project': str(project), 'workflow': workflow,
               'objective': objective, 'english_confirmed': english_confirmed, 'agent_language': 'en',
               'context': str(data_dir() / 'context' / (identifier + '.json')),
               'status': 'prepared', 'outcome': 'unverified', 'tokens': None, 'cost': None}
    arguments_for(entry, mission)
    capture_context(project, identifier)
    path = data_dir() / 'missions' / (identifier + '.json')
    save_json(path, mission)
    return path


def load_mission(path):
    """Reject missing/invalid receipts without overwriting the original evidence."""
    path = Path(path).expanduser().resolve()
    try:
        mission = json.loads(path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError as error:
        raise ValueError(f'Mission file not found: {path}. Reopen AI Dev and launch a new session.') from error
    except (OSError, ValueError) as error:
        raise ValueError(f'Cannot read mission file: {path}: {error}') from error
    if not isinstance(mission, dict):
        raise ValueError(f'Invalid mission file (expected a JSON object): {path}')
    for field in ('tool', 'profile', 'command', 'project'):
        if not isinstance(mission.get(field), str) or not mission[field].strip():
            raise ValueError(f'Invalid mission field "{field}": {path}')
    return path, mission


def console_error(error):
    from .errors import record
    log = record(error)
    print(f'AI Dev: {error}', file=sys.stderr)
    if log:
        print(f'Log: {log}', file=sys.stderr)


def spawn_terminal(path):
    path, mission = load_mission(path)
    python = str(Path(sys.executable).with_name('python.exe')) if os.name == 'nt' else sys.executable
    launcher = str(Path(__file__).resolve().parent.parent / 'launch.py')
    runner = [python, launcher, '--run', str(path)]
    wt = shutil.which('wt')
    try:
        if wt:
            command = [wt, '-w', 'new', 'new-tab', '--title', f"AI Dev: {mission['tool']} [{mission['profile']}]",
                       '-d', mission['project'], *runner]
            subprocess.Popen(command)
        else:
            subprocess.Popen(runner, cwd=mission['project'], creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
    except OSError as error:
        mission.update(status='launch_error',ended=now(),error=str(error))
        try:
            save_json(path,mission)
        except OSError as save_error:
            console_error(save_error)
        raise


def run_mission(path):
    try:
        path, mission = load_mission(path)
    except ValueError as error:
        console_error(error)
        return 1
    request = None
    exit_code = 1
    try:
        catalog = discover()
        entry = find_entry(catalog, mission['tool'], mission['profile'], mission['command'])
        if not entry or not entry['available']:
            raise RuntimeError('The selected profile or executable is no longer available.')
        if int(catalog['psVersion'].split('.')[0]) < 7 and mission.get('objective'):
            raise RuntimeError('Mission launch requires PowerShell 7 to preserve native arguments. Set AI_DEV_POWERSHELL.')
        request = path.with_suffix('.launch.json')
        save_json(request, {'tool': mission['tool'], 'profile': mission['profile'], 'command': entry['command'],
                            'project': mission['project'], 'arguments': arguments_for(entry, mission)})
        mission.update(status='running', started=now(), runner_pid=os.getpid())
        save_json(path, mission)
        child = subprocess.run([catalog['powershell'], '-NoLogo', '-ExecutionPolicy', 'Bypass',
                                '-File', str(SCRIPTS / 'Launch.ps1'), '-RequestPath', str(request)], cwd=mission['project'])
        mission.update(status='exited', ended=now(), exit_code=child.returncode)
        exit_code = child.returncode
    except Exception as error:
        mission.update(status='launch_error', ended=now(), error=str(error))
        console_error(error)
    finally:
        try:
            save_json(path, mission)
        except OSError as error:
            console_error(error)
            exit_code = 1
        if request:
            try:
                request.unlink(missing_ok=True)
            except OSError as error:
                console_error(error)
                exit_code = 1
    print('\nSession ended. Exit status does not prove the objective was achieved.')
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input('Press Enter to close...')
        except (EOFError, KeyboardInterrupt):
            pass
    return exit_code


def open_sessions():
    target = data_dir() / 'missions'
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(target)
