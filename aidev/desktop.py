"""Launch installed desktop tools using explicit executable paths."""
import os
from pathlib import Path
import subprocess
from .storage import settings


def open_tool(name):
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    programs = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
    locations = {
        'cursor': [local/'Programs/cursor/Cursor.exe', programs/'Cursor/Cursor.exe'],
        'vscode': [local/'Programs/Microsoft VS Code/Code.exe', programs/'Microsoft VS Code/Code.exe'],
        'orca': [local/'Programs/orca/Orca.exe', programs/'Orca/Orca.exe'],
        'monitor': [Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/Taskmgr.exe'],
    }
    executable = next((p for p in locations[name] if p.is_file()), None)
    if not executable:
        raise FileNotFoundError(f'{name}: application not installed in a supported location.')
    args = [str(executable)]
    if name in ('cursor', 'vscode'):
        args.append(settings().get('project', str(Path.home())))
    subprocess.Popen(args)
