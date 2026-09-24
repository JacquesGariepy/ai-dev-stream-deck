"""Launch installed desktop tools using explicit executable paths."""
import os
import shutil
from pathlib import Path
import subprocess
from .storage import settings


def installed_tools():
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    programs = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
    locations = {
        'spotify': [Path(shutil.which('Spotify') or local/'Microsoft/WindowsApps/Spotify.exe'),
                    Path(os.environ.get('APPDATA',Path.home()))/'Spotify/Spotify.exe'],
        'cursor': [local/'Programs/cursor/Cursor.exe', programs/'Cursor/Cursor.exe'],
        'vscode': [local/'Programs/Microsoft VS Code/Code.exe', programs/'Microsoft VS Code/Code.exe'],
        'orca': [local/'Programs/orca/Orca.exe', programs/'Orca/Orca.exe'],
        'monitor': [Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/Taskmgr.exe'],
        'resources': [Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/resmon.exe'],
        'performance': [Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/perfmon.exe'],
        'system-info': [Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/msinfo32.exe'],
        'capture': [Path(shutil.which('SnippingTool') or local/'Microsoft/WindowsApps/SnippingTool.exe'),
                    Path(os.environ.get('WINDIR', 'C:/Windows'))/'System32/SnippingTool.exe'],
    }
    return {name: str(executable) for name, paths in locations.items()
            if (executable := next((p for p in paths if p.is_file()), None))}


def open_tool(name):
    executable = installed_tools().get(name)
    if not executable:
        raise FileNotFoundError(f'{name}: application not installed in a supported location.')
    args = [str(executable)]
    if name in ('cursor', 'vscode'):
        args.append(settings().get('project', str(Path.home())))
    subprocess.Popen(args)
