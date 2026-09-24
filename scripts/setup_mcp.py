"""Opt-in installation of the official pinned Elgato bridge, outside the repository."""
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.discovery import powershell
from aidev.storage import data_dir, save_settings, settings


def main():
    from aidev.migration import migrate_legacy
    migrate_legacy()
    node = shutil.which('node')
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not node or not npm:
        raise RuntimeError('Install Node.js 18+ with npm and make it available on PATH first.')
    # PowerShell invokes Windows npm.cmd without constructing a command string.
    script = Path(__file__).with_name('Install-Bridge.ps1')
    subprocess.run([powershell(), '-NoProfile', '-File', str(script), '-NpmPath', npm,
                    '-InstallDirectory', str(data_dir() / 'bridge')], check=True)
    config = settings()
    config['elgato_mcp'] = {'command': node, 'args': [str(data_dir() / 'bridge/node_modules/@elgato/mcp-server/bin/index.js')]}
    save_settings(config)
    print('Official Elgato MCP bridge configured locally for Codex and Claude. Enable MCP Deck in Stream Deck.')


if __name__ == '__main__':
    main()
