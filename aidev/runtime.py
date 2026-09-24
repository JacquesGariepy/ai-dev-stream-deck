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
from .storage import data_dir, read_json, save_json


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


def spawn_terminal(path):
    mission = read_json(path)
    python = str(Path(sys.executable).with_name('python.exe')) if os.name == 'nt' else sys.executable
    launcher = str(Path(__file__).resolve().parent.parent / 'launch.py')
    runner = [python, launcher, '--run', str(path)]
    wt = shutil.which('wt')
    if wt:
        command = [wt, '-w', 'new', 'new-tab', '--title', f"AI Dev: {mission['tool']} [{mission['profile']}]",
                   '-d', mission['project'], *runner]
        subprocess.Popen(command)
    else:
        subprocess.Popen(runner, cwd=mission['project'], creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))


def run_mission(path):
    path = Path(path)
    mission = read_json(path)
    request = None
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
    except Exception as error:
        mission.update(status='launch_error', ended=now(), error=str(error))
        print(str(error))
    finally:
        save_json(path, mission)
        if request and request.exists():
            request.unlink()
    print('\nSession ended. Exit status does not prove the objective was achieved.')
    input('Press Enter to close...')


def open_sessions():
    target = data_dir() / 'missions'
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(target)
