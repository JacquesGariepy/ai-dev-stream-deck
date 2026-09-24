"""Generate an importable expert Stream Deck profile for this workstation only.

Layout: aidev/deck_layout.py (declarative pages). Export and audit:
aidev/deck_export.py. Shortcuts: one generated .lnk per Open key, created by
Create-Shortcuts.ps1 from a validated manifest.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.deck_export import audit_profile, model_name, write_profile  # noqa: E402  (re-exported for tests)
from aidev.deck_layout import DeckBuilder, Grid, MODELS, VERIFIED_MODELS  # noqa: E402
from aidev.i18n import resolve_language  # noqa: E402
from aidev.storage import data_dir, settings  # noqa: E402


def build(language, entries=None, installed_apps=None, desktop_entries=None, mcp_entries=None, grid=None):
    if installed_apps is None:
        from aidev.desktop import installed_tools
        installed_apps = installed_tools()
    return DeckBuilder(language, grid or Grid(), entries, installed_apps, desktop_entries, mcp_entries).build()


def generate(output, device, language, links, entries=None, installed_apps=None, desktop_entries=None, mcp_entries=None, grid=None):
    grid = Grid.for_device(device, grid)
    deck = build(language, entries, installed_apps, desktop_entries, mcp_entries, grid)
    return write_profile(deck, output, device, links, grid)


def select_device(profile_root, identifier=None, allow_unknown=False):
    devices = {}
    for manifest in sorted(Path(profile_root).glob('*.sdProfile/manifest.json')):
        candidate = json.loads(manifest.read_text('utf-8-sig')).get('Device', {})
        if candidate.get('UUID') and (candidate.get('Model') in MODELS or allow_unknown):
            devices[candidate['UUID']] = candidate
    if identifier:
        if identifier not in devices:
            raise ValueError('Selected Stream Deck was not found among supported devices.')
        return devices[identifier]
    if len(devices) == 1:
        return next(iter(devices.values()))
    if not devices:
        raise RuntimeError('Create a profile for your Stream Deck in the Stream Deck app first. '
                           'For an unlisted model, pass --grid COLSxROWS. The desktop app works without a device.')
    raise ValueError('Multiple Stream Decks found. Choose one with --device-id: ' +
                     ', '.join(f'{key} ({model_name(value)})' for key, value in devices.items()))


def main():
    from aidev.migration import migrate_legacy
    migrate_legacy()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', choices=['auto', 'en', 'fr'], default=None)
    parser.add_argument('--import-profile', action='store_true', help='Open the normal Stream Deck import dialog.')
    parser.add_argument('--device-id', help='Choose a device when more than one Stream Deck is configured.')
    parser.add_argument('--grid', help='Override the key grid, e.g. 5x3, 3x2, 8x4 (for unlisted models).')
    args = parser.parse_args()
    from aidev.app_catalog import discover_apps
    from aidev.deck_profiles import save_selections
    from aidev.discovery import discover, powershell
    from aidev.mcp_catalog import discover_mcp
    from aidev.storage import save_json, save_settings

    config = settings()
    grid_override = Grid.parse(args.grid) if args.grid else (Grid.parse(config['stream_deck_grid']) if config.get('stream_deck_grid') else None)
    profile_root = Path(os.environ['APPDATA']) / 'Elgato/StreamDeck/ProfilesV3'
    device = select_device(profile_root, args.device_id or config.get('stream_deck_device'), allow_unknown=bool(grid_override))
    if args.device_id or args.grid:
        config = settings()
        if args.device_id:
            config['stream_deck_device'] = device['UUID']
        if args.grid:
            config['stream_deck_grid'] = '%dx%d' % (grid_override.cols, grid_override.rows)
        save_settings(config)
    grid = Grid.for_device(device, grid_override)
    language = resolve_language(args.language or settings().get('language', 'auto'))

    entries = discover()['entries']
    save_selections(entries)
    save_json(data_dir() / 'harness-locations.json', [{key: e.get(key) for key in ('tool', 'profile', 'directory')} for e in entries])
    desktop_entries = discover_apps(); mcp_entries = discover_mcp()
    deck = build(language, entries, None, desktop_entries, mcp_entries, grid)

    links = data_dir() / 'stream-deck/Launchers'
    manifest = data_dir() / 'stream-deck/shortcuts.json'
    save_json(manifest, deck.shortcut_manifest())
    root = Path(__file__).resolve().parents[1]
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    subprocess.run([powershell(), '-NoProfile', '-File', str(Path(__file__).with_name('Create-Shortcuts.ps1')),
                    '-PythonPath', str(pythonw), '-LauncherPath', str(root / 'launch.py'),
                    '-OutputDirectory', str(links), '-ManifestPath', str(manifest)], check=True)
    output = write_profile(deck, data_dir() / ('stream-deck/AI-Dev-' + language.upper() + '.streamDeckProfile'), device, links, grid)
    audit = audit_profile(output, links, grid)
    verified = '' if device.get('Model') in VERIFIED_MODELS else ' (layout not yet verified on this hardware)'
    print(f'Device: {model_name(device)} — {grid.cols}x{grid.rows} keys{verified}.')
    print(f'Detected {len(desktop_entries)} desktop applications and {len(mcp_entries)} MCP declarations. Connections are not checked.')
    print(f'Detected {len(entries)} profile entries across {len({r["tool"] for r in entries})} harnesses.')
    print(f'Audited {audit["buttons"]} keys across {audit["pages"]} reachable pages; all local shortcuts and icons are present.')
    print('Import this local file in Stream Deck (do not commit it): ' + str(output))
    if args.import_profile:
        os.startfile(output)


if __name__ == '__main__':
    main()
