"""Discover installed CLI harnesses and profile commands without launching agents."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .storage import read_json

SCRIPTS = Path(__file__).parent / 'scripts'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def powershell():
    override = os.environ.get('AI_DEV_POWERSHELL')
    if override:
        if not Path(override).is_file():
            raise FileNotFoundError('AI_DEV_POWERSHELL does not point to an executable.')
        return override
    candidates = [shutil.which('pwsh'), str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'PowerShell/7/pwsh.exe'), shutil.which('powershell')]
    return next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)


def discover():
    shell = powershell()
    if not shell:
        raise RuntimeError('PowerShell was not found. Set AI_DEV_POWERSHELL to its executable.')
    with tempfile.TemporaryDirectory(prefix='ai-dev-discovery-') as temp:
        output = Path(temp) / 'catalog.json'
        result = subprocess.run([shell, '-NoLogo', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(SCRIPTS / 'Discover.ps1'), '-OutputPath', str(output)],
                                capture_output=True, encoding='utf-8', errors='replace', timeout=40,
                                creationflags=NO_WINDOW)
        if result.returncode or not output.is_file():
            raise RuntimeError('PowerShell discovery failed. Check your PowerShell startup profile.\n' + result.stderr[-2000:])
        catalog = read_json(output)
        catalog['powershell'] = shell
        return catalog


def find_entry(catalog, harness, profile='default', command=None):
    return next((row for row in catalog['entries'] if row['tool'] == harness and row['profile'] == profile
                 and (command is None or row['command'] == command)), None)
