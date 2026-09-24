"""Generate the AI-first Stream Deck profile and its shortcuts.

    python scripts/agent_deck.py            (on Windows: writes shortcuts + profile, opens the import)
    python scripts/agent_deck.py --no-import

Shortcuts go to %LOCALAPPDATA%\\AIDev\\agentdeck\\Launchers. Directory handles resolve
the physical path so Windows sees the same files when generation runs in a packaged app.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.agent_deck import AgentDeck  # noqa: E402
from aidev.deck_export import audit_profile, write_profile  # noqa: E402
from aidev.deck_layout import Grid, MODELS  # noqa: E402
from aidev.shelllink import shell_link  # noqa: E402
from aidev.app_catalog import discover_apps  # noqa: E402
from aidev.terminals import installed_terminals  # noqa: E402
from aidev.browsers import installed_browsers  # noqa: E402
from aidev.discovery import discover  # noqa: E402


def write_shortcuts(deck, output, working, native=None):
    output.mkdir(parents=True, exist_ok=True)
    if native is None:
        native = os.name == 'nt'
    if native:
        manifest = output / 'shortcuts.json'
        manifest.write_text(json.dumps([
            {'name': name, 'target': target, 'arguments': arguments, 'workingDirectory': working}
            for name, (target, arguments) in deck.shortcuts.items()
        ], indent=2), encoding='utf-8')
        creator = Path(__file__).with_name('Create-AgentShortcuts.ps1')
        subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile',
                        '-ExecutionPolicy', 'Bypass', '-File', str(creator), '-ManifestPath', str(manifest),
                        '-OutputDirectory', str(output)], check=True)
    else:
        for name, (target, arguments) in deck.shortcuts.items():
            (output / (name + '.lnk')).write_bytes(shell_link(target, arguments, working))


def generate(output, device, script_windows_path, links_windows_path, links_local_path, grid=None,
             native_shortcuts=None, apps=None, terminals=None, intents=None, language=None, harnesses=None):
    grid = grid or Grid.for_device(device)
    deck = AgentDeck(script_windows_path, grid, apps=apps, terminals=terminals,
                     intents=intents, language=language, harnesses=harnesses).build()
    local = Path(links_local_path)
    working = str(PureWindowsPath(script_windows_path).parent)
    write_shortcuts(deck, local, working, native_shortcuts)
    write_profile(deck, output, device, links_windows_path, grid)
    audit = audit_profile(output, local, grid)
    return output, audit


def physical_directory(path):
    """Resolve the directory handle so non-packaged Windows apps see the same files."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        return path.resolve()
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path.resolve()), 0, 7, None, 3, 0x02000000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        if not kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        value = buffer.value
        if value.startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\'):
            value = value[4:]
        return Path(value)
    finally:
        kernel.CloseHandle(handle)


def install_runtime(source, base):
    for file in source.glob('*.ps1'):
        shutil.copy2(file, base / file.name)
    template = json.loads((source / 'intents.json').read_text('utf-8-sig'))
    config_path = base / 'intents.json'
    config = json.loads(config_path.read_text('utf-8-sig')) if config_path.exists() else template
    if config.get('schemaVersion', 1) < template.get('schemaVersion', 1):
        shutil.copy2(config_path, base / 'intents.before-upgrade.json')
        # Keep workstation choices; upgrade shipped unsafe/obsolete task defaults.
        template['defaults'].update(config.get('defaults', {}))
        for name, intent in config.get('intents', {}).items():
            if name not in template['intents']:
                template['intents'][name] = intent
            elif intent.get('harness'):
                template['intents'][name]['harness'] = intent['harness']
        config = template
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--no-import', action='store_true')
    parser.add_argument('--device-id')
    parser.add_argument('--install', action='store_true', help='Replace this generated profile with a backup and restart Stream Deck.')
    parser.add_argument('--enable-shell', action='store_true', help='Install the PowerShell integration for Git in the active terminal.')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--language', choices=('auto', 'fr', 'en'))
    args = parser.parse_args()
    root = physical_directory(Path(os.environ['APPDATA']) / 'Elgato/StreamDeck/ProfilesV3')
    devices = {}
    for manifest in root.glob('*.sdProfile/manifest.json'):
        try:
            device = json.loads(manifest.read_text('utf-8-sig')).get('Device', {})
        except (OSError, ValueError):
            continue
        if device.get('Model') in MODELS and device.get('UUID'):
            devices[device['UUID']] = device
    if args.device_id:
        device = devices[args.device_id]
    elif len(devices) == 1:
        device = next(iter(devices.values()))
    else:
        raise SystemExit('Choose a device with --device-id: ' + ', '.join(devices))
    base = physical_directory(args.data_dir or os.environ.get('AI_DEV_AGENTDECK_DIR') or
                              Path(os.environ['LOCALAPPDATA']) / 'AIDev' / 'agentdeck')
    source = Path(__file__).resolve().parents[1] / 'agentdeck'
    legacy = Path(os.environ['LOCALAPPDATA']) / 'AI Dev' / 'agentdeck'
    for name in ('state.json', 'intents.json'):
        if not (base / name).exists() and (legacy / name).is_file():
            shutil.copy2(legacy / name, base / name)
    config = install_runtime(source, base)
    state_path = base / 'state.json'
    state = json.loads(state_path.read_text('utf-8-sig')) if state_path.exists() else {}
    language = args.language or state.get('language', 'auto')
    if args.language:
        state['language'] = args.language
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    apps = discover_apps()
    terminals, terminal_issues = installed_terminals()
    app_rows = [{**entry, 'deck_id': entry['id'][:16]} for entry in apps]
    terminal_rows = []
    for entry in terminals:
        deck_id = hashlib.sha256(entry['id'].encode('utf-8')).hexdigest()[:16]
        terminal_rows.append({**entry, 'deck_id': deck_id})
    try:
        catalog = discover()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        catalog = {'entries': [], 'discovery_error': str(error)}
    tools = {'apps': app_rows, 'terminals': terminal_rows, 'terminal_issues': terminal_issues,
             'browsers': installed_browsers(), 'powershell': catalog.get('powershell'),
             'harnesses': [{k: e[k] for k in ('tool', 'profile', 'command') if k in e}
                           for e in catalog.get('entries', [])]}
    for entry in tools['harnesses']:
        entry['deck_id'] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    if language == 'auto':
        language = 'fr' if catalog.get('uiCulture', '').startswith('fr') else 'en'
    (base / 'tools.json').write_text(json.dumps(tools, ensure_ascii=False, indent=2), encoding='utf-8')
    output, audit = generate(base / 'AI Dev Agentic.streamDeckProfile', device,
                             base / 'ai.ps1', base / 'Launchers', base / 'Launchers',
                             apps=app_rows, terminals=terminal_rows, intents=config, language=language,
                             harnesses=tools['harnesses'])
    (base / 'installation.json').write_text(json.dumps({'source': str(source.parent), 'python': sys.executable,
                                                        'device_id': device['UUID'], 'profile': str(output)},
                                                       indent=2), encoding='utf-8')
    print('Audited', audit['buttons'], 'keys on', audit['pages'], 'pages:', output)
    if args.enable_shell:
        shells = {r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', tools.get('powershell')}
        for shell in sorted(s for s in shells if s and Path(s).is_file()):
            subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                            str(base / 'install-terminal.ps1'), '-RuntimePath', str(base)], check=True)
    if args.install:
        subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile',
                        '-ExecutionPolicy', 'Bypass', '-File', str(Path(__file__).with_name('Install-AgentProfile.ps1')),
                        '-ProfilePath', str(output), '-ProfilesRoot', str(root), '-BackupRoot', str(base / 'backups')],
                       check=True)
    elif not args.no_import:
        os.startfile(output)


if __name__ == '__main__':
    main()
