"""Read canonical Factory state and start its existing loopback workbench."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from .discovery import NO_WINDOW
from .storage import data_dir, settings, save_settings


def installation(value=None):
    value = value or os.environ.get('AI_DEV_FACTORY') or settings().get('factory', {}).get('package')
    if not value:
        candidate = Path(settings().get('project', '.'))
        if (candidate / 'automation/control_server.py').is_file():
            value = str(candidate)
    if not value:
        raise ValueError('Select the Factory installation folder first.')
    package = Path(value).expanduser().resolve(strict=True)
    for name in ('automation/control_server.py', 'automation/autopilot.py', 'factory.py'):
        if not (package / name).is_file():
            raise ValueError('This folder is not a Factory installation.')
    return package


def configure(value):
    package = installation(value)
    config = settings()
    config.setdefault('factory', {})['package'] = str(package)
    save_settings(config)
    return package


def interpreter(package):
    local = package / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
    return str(local) if local.is_file() else sys.executable


def brief():
    package = installation()
    # This shortcut targets the Factory repository itself, independently of the mission folder.
    result = subprocess.run([interpreter(package), str(package/'automation/autopilot.py'),
                             '--root', str(package), 'status', '--brief'],
                            cwd=package, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=45, creationflags=NO_WINDOW)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(result.stderr.strip() or 'Factory returned no JSON status.') from error
    if result.returncode or not data.get('ok'):
        raise RuntimeError(data.get('error') or result.stderr.strip() or 'Factory status failed.')
    return data


def workbench_identity(port, package):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/projects', timeout=1) as response:
            data = json.load(response)
        return (data.get('ok') is True and isinstance(data.get('projects'), list)
                and bool(data.get('package')) and Path(data['package']).resolve() == package.resolve())
    except (OSError, ValueError, TypeError):
        return False


def port_available(port):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def ensure_workbench():
    package = installation()
    config = settings().get('factory', {})
    preferred = int(config.get('port', 8765))
    ports = list(dict.fromkeys([preferred, *range(8765, 8776)]))
    for port in ports:
        if not 1024 <= port <= 65535:
            continue
        if workbench_identity(port, package):
            return f'http://127.0.0.1:{port}/'
        if not port_available(port):
            continue
        log = data_dir() / 'factory/workbench.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('ab') as output:
            child = subprocess.Popen([interpreter(package), str(package/'automation/control_server.py'),
                                      '--root', str(package), '--host', '127.0.0.1', '--port', str(port)],
                                     cwd=package, stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                                     creationflags=NO_WINDOW)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if workbench_identity(port, package):
                latest = settings()
                latest.setdefault('factory', {}).update(package=str(package), port=port)
                save_settings(latest)
                return f'http://127.0.0.1:{port}/'
            if child.poll() is not None:
                break
            time.sleep(.25)
        # Only our own failed child may be stopped; never touch an existing service.
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        raise RuntimeError(f'Factory workbench did not start. See {log}')
    raise RuntimeError('No local port available for the Factory workbench.')
