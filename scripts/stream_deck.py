"""Generate an importable 15-key Stream Deck profile for this workstation only."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import textwrap
import uuid
import zipfile
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.agents import TEXT_PROMPTS
from aidev.discovery import powershell, discover
from aidev.deck_profiles import save_selections, selection_id
from aidev.i18n import resolve_language
from aidev.storage import data_dir, settings


def background():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + (bytes((88,220,197)) if y < 6 else bytes((17,27,42))) * 144 for y in range(144))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B',144,144,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(rows)) + chunk(b'IEND',b'')


def action(title, kind, config, description=''):
    return {'ActionID':str(uuid.uuid4()), 'Name':title.replace('\n',' '), 'UUID':'com.elgato.streamdeck.'+kind,
            'LinkedTitle':True, 'Settings':config, 'State':0, 'UserInput':description,
            'States':[{'Title':title, 'ShowTitle':True, 'TitleAlignment':'middle', 'TitleColor':'#ffffff', 'FontSize':10, 'Image':'Images/background.png'}]}


def hotkey(title, key, ctrl=False, shift=False, alt=False, win=False, qt=None):
    actual={'KeyCmd':win,'KeyCtrl':ctrl,'KeyShift':shift,'KeyOption':alt,'KeyModifiers':2*ctrl+shift+4*alt+8*win,'NativeCode':key,'QTKeyCode':qt if qt is not None else key,'VKeyCode':key}
    blank={'KeyCmd':False,'KeyCtrl':False,'KeyShift':False,'KeyOption':False,'KeyModifiers':0,'NativeCode':146,'QTKeyCode':33554431,'VKeyCode':-1}
    return action(title,'system.hotkey',{'Coalesce':True,'Hotkeys':[actual,blank,blank,blank]})


def generate(output, device, language, links, entries=None):
    ids={name:str(uuid.uuid4()) for name in ('profile','home','prompts','editor','web','apps','pinned')}
    label=lambda en,fr:fr if language=='fr' else en
    def opened(title, name, description):
        return action(title,'system.open',{'path':'"'+str(links/(name+'.lnk'))+'"'},description)
    def folder(title,name):
        return action(title,'profile.openchild',{'ProfileUUID':ids.setdefault(name,str(uuid.uuid4()))})
    def website(title,site):
        return opened(title,'web-'+site,'Open the website with the user-selected browser and work/personal context. Ask first unless the user saved a browser preference.')
    back=action(label('BACK','RETOUR'),'profile.backtoparent',{})
    prompt_labels = {'implement':('IMPLEMENT','REALISER'), 'plan':('PLAN','PLAN'), 'debug':('DEBUG','DEBUG'),
                     'review':('REVIEW','REVUE'), 'test':('TESTS','TESTS'), 'handoff':('HANDOFF','RELAIS'),
                     'refactor':('REFACTOR','REFACTOR'), 'explain':('EXPLAIN','EXPLIQUER'),
                     'performance':('PERF','PERF'), 'security':('SECURITY','SECURITE'), 'docs':('DOCS','DOCS'),
                     'context':('CONTEXT','CONTEXTE'), 'usage':('USAGE','COUTS'), 'pr_draft':('PR DRAFT','PR DRAFT')}
    pages={
        'home':[
            opened('MISSION','mission','Open the AI Dev control panel to select an installed harness, PowerShell profile and English objective.'),
            opened('CODEX','codex','Open the control panel with Codex selected.'),
            opened('CLAUDE','claude','Open the control panel with Claude selected.'),
            opened('AGY','agy','Open the control panel with AGY selected.'),
            opened(label('PROFILES','PROFILS'),'mission','Inspect detected harnesses and PowerShell profile commands.'),
            opened('FACTORY','factory','Start or reuse the installed Factory workbench and open it in the selected browser. Autonomous execution still requires Factory readiness and budget decisions.'),
            opened(label('CONTEXT','CONTEXTE'),'context','Capture Git metadata for the selected project. The action starts asynchronously; check the timestamp in the local context/latest.json file.'),
            opened('SESSIONS','status','Open local session receipts. Exited is not proof of a successful objective.'),
            folder(label('EDITOR','EDITEUR'),'editor'),folder('AI WEB','web'),
            folder('PROMPTS','prompts'),opened('TERMINAL','terminal','Choose a detected shell or terminal, including CMD, PowerShell, Git Bash and installed WSL distributions, in the selected project.'),
            folder(label('APPS','OUTILS'),'apps'),opened(label('PROJECT','PROJET'),'mission','Choose the project folder in the control panel.'),
            opened(label('CONTROL','PILOTAGE'),'factory-status','Read canonical Factory task states and pending decisions.'),
        ],
        'prompts':[back]+[action(label(*prompt_labels[key]),'system.text',{'isSendingEnter':False,'pastedText':'Communicate in English. '+text}) for key,text in TEXT_PROMPTS.items()],
        'editor':[back,hotkey(label('COMMANDS','COMMANDES'),80,ctrl=True,shift=True),hotkey(label('FIND FILE','FICHIER'),80,ctrl=True),hotkey(label('SEARCH','RECHERCHE'),70,ctrl=True,shift=True),hotkey(label('SAVE','SAUVER'),83,ctrl=True),hotkey(label('FORMAT','FORMATER'),70,shift=True,alt=True),hotkey(label('COPY','COPIER'),67,ctrl=True),hotkey(label('PASTE','COLLER'),86,ctrl=True),
                  hotkey(label('PANEL','PANNEAU'),74,ctrl=True),hotkey(label('PROBLEMS','PROBLEMES'),77,ctrl=True,shift=True),
                  hotkey(label('RENAME','RENOMMER'),113,qt=16777265),hotkey(label('DEFINITION','DEFINITION'),123,qt=16777275),
                  hotkey(label('UNDO','ANNULER'),90,ctrl=True),hotkey(label('REDO','RETABLIR'),89,ctrl=True),hotkey(label('ESCAPE','ECHAP'),27,qt=16777216)],
        'apps':[back,opened('CURSOR','cursor','Open the selected project in the installed Cursor desktop editor.'),
                opened('VS CODE','vscode','Open the selected project in the installed Visual Studio Code editor.'),
                opened('ORCA','orca','Open the installed Orca application.'),folder('CPU / RAM','system'),
                hotkey(label('CAPTURE','CAPTURE'),83,win=True,shift=True),opened(label('FILES','FICHIERS'),'files','Open the selected project folder.'),
                opened('GUIDE','guide','Open the local README.'),opened(label('SETTINGS','REGLAGES'),'mission','Open the control panel to select French or English and apply the language to Stream Deck.'),
                opened(label('HEALTH','DIAG'),'health','Inspect current tool availability, local storage access and MCP bridge files. Authentication is not verified.'),
                opened('GIT','git','Read current branch, changed files and Git worktrees without modifying the repository or fetching remotes.'),
                opened(label('LOGS','JOURNAUX'),'logs','Open the private application error log folder. No logs are uploaded.'),
                opened('PHOTO\nVIDEO','capture','Open Windows Snipping Tool to choose screenshot or screen recording. Recording starts only when the user chooses an area and starts it.')],
        'system':[back,
                  opened(label('TASKS','TACHES'),'monitor','Open Task Manager for processes and CPU, memory, disk, network and GPU performance.'),
                  opened(label('RESOURCES','RESSOURCES'),'resources','Open Resource Monitor for detailed per-process CPU, memory, disk activity and network connections.'),
                  opened('PERFMON','performance','Open Performance Monitor for Windows performance counters.'),
                  opened(label('SYSTEM\nINFO','INFOS\nSYSTEME'),'system-info','Open Windows System Information for hardware and software configuration.')],
        'web':[back,opened(label('BROWSER','NAVIGATEUR'),'browser','Choose Chrome or Edge and optional preferences for work and personal.'),
               opened(label('WORK','TRAVAIL'),'web-work','Select the work web context. Does not change CLI account profiles.'),
               opened(label('PERSONAL','PERSO'),'web-personal','Select the personal web context. Does not change CLI account profiles.'),
               website('CHATGPT','chatgpt'),website('CLAUDE','claude'),website('GEMINI','gemini'),
               website('PERPLEXITY','perplexity'),website('GITHUB','github'),website('GITHUB PR','github-pr'),website('ISSUES','github-issues')],
    }
    refresh = opened(label('REFRESH','ACTUALISER'),'deck-refresh-'+language,
                     'Detect installed harnesses and exact PowerShell profiles again, then open the standard Stream Deck import dialog. Install the generated profile to update hardware buttons.')
    def paginated(name, buttons, panel_action):
        # Back + panel + refresh + 11 entries + optional next folder fit 15 keys.
        chunks = [buttons[i:i+11] for i in range(0,len(buttons),11)] or [[]]
        for index, chunk in enumerate(chunks):
            page = name if index == 0 else name+'-'+str(index)
            ids.setdefault(page,str(uuid.uuid4()))
            pages[page] = [back, panel_action, refresh, *chunk]
            if index + 1 < len(chunks):
                pages[page].append(folder(label('MORE','SUITE'),name+'-'+str(index+1)))
    groups = {}
    unique = {(row['tool'],row['profile'],row['command']):row for row in (entries or [])}
    for row in sorted(unique.values(),key=lambda r:(r['tool'],r['profile'],r['command'])):
        groups.setdefault(row['tool'],[]).append(row)
    tool_folders = {}
    home_folders = {}
    for index, (tool, rows) in enumerate(groups.items()):
        page = 'harness-'+str(index)
        buttons = []
        for row in rows:
            display = label('DEFAULT','DEFAUT') if row['kind']=='application' else row['profile'].upper()
            title = tool.upper()+'\n'+'\n'.join(textwrap.wrap(display,9)[:2])
            if not row['available']:
                title = '! '+title
            button = opened(title,'profile-'+selection_id(row),
                            'Open the AI Dev mission panel with this exact detected harness, profile and command selected. Recheck availability; never fall back to another account.')
            button['Name'] = tool+' / '+row['profile']+' / '+(row['command'] if row['kind']!='application' else 'default')
            if not row['available']:
                button['States'][0]['TitleColor'] = '#ffbd66'
            buttons.append(button)
        paginated(page,buttons,opened(label('PANEL','PANNEAU'),tool if tool in ('codex','claude','agy') else 'mission','Open the mission panel to choose a harness and profile.'))
        tool_folders[tool]=folder(('! ' if not any(row['available'] for row in rows) else '')+tool.upper(),page)
        if tool in ('codex','claude','agy'):
            # Native folders are a tree: importing a child with two parents drops a link.
            home_page = page+'-home'
            paginated(home_page,buttons,opened(label('PANEL','PANNEAU'),tool,'Open the mission panel to choose a harness and profile.'))
            home_folders[tool]=folder(tool.upper(),home_page)
    paginated('profiles',list(tool_folders.values()),opened('MISSION','mission','Open the mission panel to choose a harness and profile.'))
    pages['home'][4]=folder(label('PROFILES','PROFILS'),'profiles')
    for position, tool in ((1,'codex'),(2,'claude'),(3,'agy')):
        if tool in home_folders:
            pages['home'][position]=home_folders[tool]
    prefix=ids['profile'].upper()+'.sdProfile'
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        def write(path,data):archive.writestr(prefix+'/'+path,json.dumps(data,ensure_ascii=False))
        write('manifest.json',{'Name':'AI Dev '+language.upper(),'Version':'3.0','Device':device,'Pages':{'Current':ids['home'],'Default':ids['pinned'],'Pages':[ids['home']]}})
        for page,actions in pages.items():
            path='Profiles/'+ids[page].upper()
            write(path+'/manifest.json',{'Name':page,'Icon':'','Controllers':[{'Type':'Keypad','Actions':{f'{i%5},{i//5}':dict(a,ActionID=str(uuid.uuid4())) for i,a in enumerate(actions)}}]})
            archive.writestr(prefix+'/'+path+'/Images/background.png',background())
        write('Profiles/'+ids['pinned'].upper()+'/manifest.json',{'Name':'','Icon':'','Controllers':[{'Type':'Keypad','Actions':None}]})
    return output


def main():
    from aidev.migration import migrate_legacy
    migrate_legacy()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',choices=['auto','en','fr'],default=None)
    parser.add_argument('--import-profile', action='store_true', help='Open the normal Stream Deck import dialog.')
    args=parser.parse_args()
    links=data_dir()/'stream-deck/Launchers'
    root=Path(__file__).resolve().parents[1]
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    entries = discover()['entries']
    selections = save_selections(entries)
    subprocess.run([powershell(),'-NoProfile','-File',str(Path(__file__).with_name('Create-Shortcuts.ps1')),
                    '-PythonPath',str(pythonw),'-LauncherPath',str(root/'launch.py'),'-OutputDirectory',str(links),'-ProfilesPath',str(selections)],check=True)
    profile_root=Path(os.environ['APPDATA'])/'Elgato/StreamDeck/ProfilesV3'
    device=None
    for manifest in sorted(profile_root.glob('*.sdProfile/manifest.json')):
        candidate=json.loads(manifest.read_text('utf-8-sig')).get('Device',{})
        if candidate.get('Model')=='20GBA9901':
            device=candidate;break
    if not device:
        raise RuntimeError('Connect a 15-key Stream Deck and create a profile in Stream Deck first. Other models need a layout adapter.')
    language = resolve_language(args.language or settings().get('language','auto'))
    output=generate(data_dir()/('stream-deck/AI-Dev-'+language.upper()+'.streamDeckProfile'),device,language,links,entries)
    print(f'Detected {len(entries)} profile entries across {len({r["tool"] for r in entries})} harnesses.')
    print('Import this local file in Stream Deck (do not commit it): '+str(output))
    if args.import_profile:
        os.startfile(output)


if __name__=='__main__':main()
