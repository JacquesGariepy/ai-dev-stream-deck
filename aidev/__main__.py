import argparse
import json
from pathlib import Path
from .storage import settings


def main():
    parser = argparse.ArgumentParser(description='AI Dev: local AI harness and Stream Deck control panel')
    parser.add_argument('--discover', action='store_true', help='Print local inventory; contains private paths, do not publish it.')
    parser.add_argument('--run', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--tool', help='Preselect a detected harness.')
    parser.add_argument('--action', choices=['mission', 'context', 'status', 'codex', 'claude', 'agy','terminal','files','guide'], default='mission')
    args = parser.parse_args()
    if args.discover:
        from .discovery import discover
        print(json.dumps(discover(), ensure_ascii=False, indent=2))
    elif args.run:
        from .runtime import run_mission
        run_mission(args.run)
    elif args.action == 'context':
        from .runtime import capture_context
        print(capture_context(settings().get('project', str(Path.home()))))
    elif args.action == 'status':
        from .runtime import open_sessions
        open_sessions()
    elif args.action in ('terminal', 'files', 'guide'):
        import os
        import subprocess
        project = settings().get('project', str(Path.home()))
        if args.action == 'terminal':
            from .discovery import powershell
            subprocess.Popen([powershell(), '-NoLogo'], cwd=project, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            os.startfile(str(Path(__file__).parent.parent / 'README.md') if args.action == 'guide' else project)
    else:
        from .ui import Panel
        Panel(args.tool or (args.action if args.action != 'mission' else None)).run()


if __name__ == '__main__':
    main()
