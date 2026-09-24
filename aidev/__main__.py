import argparse
import json
from pathlib import Path
from .storage import settings


def main():
    from .migration import migrate_legacy
    migrate_legacy()
    parser = argparse.ArgumentParser(description='AI Dev: local AI harness and Stream Deck control panel')
    parser.add_argument('--discover', action='store_true', help='Print local inventory; contains private paths, do not publish it.')
    parser.add_argument('--run', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--tool', help='Preselect a detected harness.')
    parser.add_argument('--profile-id', help='Exact locally generated Stream Deck profile selection.')
    parser.add_argument('--deck-language', choices=['en','fr'], help='Language of the Stream Deck profile to refresh.')
    parser.add_argument('--url', help='HTTP(S) URL for an explicit browser launch.')
    parser.add_argument('--web-context', choices=['work','personal'])
    parser.add_argument('--action', choices=['mission', 'context', 'status', 'codex', 'claude', 'agy','terminal','files','guide','browser','web','web-work','web-personal','factory','factory-status','cursor','vscode','orca','monitor','resources','performance','system-info','capture','deck-refresh','health','git','logs'], default='mission')
    args = parser.parse_args()
    if args.profile_id or args.action == 'deck-refresh':
        try:
            if args.profile_id:
                from .deck_profiles import load_selection
                from .ui import Panel
                Panel(initial_selection=load_selection(args.profile_id)).run()
            else:
                import subprocess
                import sys
                command = [sys.executable, str(Path(__file__).resolve().parent.parent/'scripts/stream_deck.py'), '--import-profile']
                if args.deck_language:
                    command += ['--language',args.deck_language]
                subprocess.run(command, check=True)
        except Exception as error:
            from .errors import report
            report(error)
    elif args.action in ('browser','web','web-work','web-personal'):
        from .browsers import browser_dialog, open_website, select_context, validate_url
        if args.action == 'web':
            if not args.url: parser.error('--action web requires --url')
            validate_url(args.url)
            if settings().get('web',{}).get('ask_each_time',True):
                browser_dialog(args.url,args.web_context)
            else:
                try:
                    open_website(args.url,args.web_context)
                except (ValueError,OSError):
                    browser_dialog(args.url,args.web_context)
        elif args.action in ('web-work','web-personal'):
            context=args.action.removeprefix('web-')
            if not select_context(context):browser_dialog(context=context)
        else:
            browser_dialog(context=args.web_context)
    elif args.discover:
        from .discovery import discover
        print(json.dumps(discover(), ensure_ascii=False, indent=2))
    elif args.run:
        from .runtime import run_mission
        raise SystemExit(run_mission(args.run))
    elif args.action == 'context':
        from .runtime import capture_context
        print(capture_context(settings().get('project', str(Path.home()))))
    elif args.action == 'status':
        from .ui import Panel
        Panel(initial_tab='activity').run()
    elif args.action in ('health','git'):
        from .ui import Panel
        panel=Panel(initial_tab='engineering')
        panel.root.after(100,panel.refresh_health if args.action=='health' else panel.refresh_git)
        panel.run()
    elif args.action == 'logs':
        from .engineering import open_logs
        open_logs()
    elif args.action == 'factory-status':
        from .ui import Panel
        Panel(initial_tab='factory').run()
    elif args.action == 'factory':
        from .ui import Panel
        panel = Panel(initial_tab='factory')
        panel.root.after(100, panel.open_factory)
        panel.run()
    elif args.action in ('cursor','vscode','orca','monitor','resources','performance','system-info','capture'):
        from .desktop import open_tool
        try:
            open_tool(args.action)
        except Exception as error:
            from tkinter import Tk, messagebox
            from .i18n import tr, resolve_language
            root = Tk(); root.withdraw()
            messagebox.showerror(tr('error',resolve_language(settings().get('language','auto'))), str(error), parent=root)
            root.destroy()
    elif args.action in ('terminal', 'files', 'guide'):
        import os
        import subprocess
        project = settings().get('project', str(Path.home()))
        if args.action == 'terminal':
            from .terminals import terminal_dialog
            terminal_dialog()
        else:
            os.startfile(str(Path(__file__).parent.parent / 'README.md') if args.action == 'guide' else project)
    else:
        from .ui import Panel
        Panel(args.tool or (args.action if args.action != 'mission' else None)).run()


if __name__ == '__main__':
    from .errors import run
    run(main)
