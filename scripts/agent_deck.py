"""Generate the AI-first Stream Deck profile and its shortcuts.

    python scripts/agent_deck.py            (on Windows: writes shortcuts + profile, opens the import)
    python scripts/agent_deck.py --no-import

Shortcuts go to %LOCALAPPDATA%\\AI Dev\\agentdeck\\Launchers (a real folder, also when started
from a packaged app). Intents and prompts live in agentdeck/intents.json.
"""
import argparse
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


def write_shortcuts(deck, output, working):
    output.mkdir(parents=True, exist_ok=True)
    # This directory is owned by the generated Agentic profile. Remove links
    # for intents that disappeared so upgrades cannot leave dead deck actions.
    for link in output.glob('ai-*.lnk'):
        link.unlink()
    if os.name == 'nt':
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


def generate(output, device, script_windows_path, links_windows_path, links_local_path, grid=None):
    grid = grid or Grid.for_device(device)
    deck = AgentDeck(script_windows_path, grid).build()
    local = Path(links_local_path)
    working = str(PureWindowsPath(script_windows_path).parent)
    write_shortcuts(deck, local, working)
    write_profile(deck, output, device, links_windows_path, grid)
    audit = audit_profile(output, local, grid)
    return output, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--no-import', action='store_true')
    parser.add_argument('--device-id')
    args = parser.parse_args()
    root = Path(os.environ['APPDATA']) / 'Elgato/StreamDeck/ProfilesV3'
    devices = {}
    for manifest in root.glob('*.sdProfile/manifest.json'):
        device = json.loads(manifest.read_text('utf-8-sig')).get('Device', {})
        if device.get('Model') in MODELS and device.get('UUID'):
            devices[device['UUID']] = device
    if args.device_id:
        device = devices[args.device_id]
    elif len(devices) == 1:
        device = next(iter(devices.values()))
    else:
        raise SystemExit('Choose a device with --device-id: ' + ', '.join(devices))
    base = Path(os.environ['LOCALAPPDATA']) / 'AI Dev' / 'agentdeck'
    source = Path(__file__).resolve().parents[1] / 'agentdeck'
    base.mkdir(parents=True, exist_ok=True)
    for name in ('ai.ps1', 'run-agent.ps1', 'run-git.ps1'):
        shutil.copy2(source / name, base / name)
    if not (base / 'intents.json').exists():
        shutil.copy2(source / 'intents.json', base / 'intents.json')
    output, audit = generate(base / 'AI Dev Agentic.streamDeckProfile', device,
                             base / 'ai.ps1', base / 'Launchers', base / 'Launchers')
    print('Audited', audit['buttons'], 'keys on', audit['pages'], 'pages:', output)
    if not args.no_import:
        os.startfile(output)


if __name__ == '__main__':
    main()
