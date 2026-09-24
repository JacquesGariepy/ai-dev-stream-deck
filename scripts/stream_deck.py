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
from aidev.deck_icons import icon_png, button_icon


def background():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + (bytes((88,220,197)) if y < 6 else bytes((17,27,42))) * 144 for y in range(144))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B',144,144,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(rows)) + chunk(b'IEND',b'')


def action(title, kind, config, description=''):
    return {'ActionID':str(uuid.uuid4()), 'Name':title.replace('\n',' '), 'UUID':'com.elgato.streamdeck.'+kind,
            'LinkedTitle':True, 'Settings':config, 'State':0, 'UserInput':description,
            'States':[{'Title':title, 'ShowTitle':True, 'TitleAlignment':'bottom', 'TitleColor':'#ffffff', 'FontSize':9, 'Image':'Images/background.png'}]}


def hotkey(title, key, ctrl=False, shift=False, alt=False, win=False, qt=None):
    actual={'KeyCmd':win,'KeyCtrl':ctrl,'KeyShift':shift,'KeyOption':alt,'KeyModifiers':2*ctrl+shift+4*alt+8*win,'NativeCode':key,'QTKeyCode':qt if qt is not None else key,'VKeyCode':key}
    blank={'KeyCmd':False,'KeyCtrl':False,'KeyShift':False,'KeyOption':False,'KeyModifiers':0,'NativeCode':146,'QTKeyCode':33554431,'VKeyCode':-1}
    return action(title,'system.hotkey',{'Coalesce':True,'Hotkeys':[actual,blank,blank,blank]})


def audit_profile(path, shortcuts=None):
    """Inspect every generated key without executing it."""
    with zipfile.ZipFile(path) as archive:
        names=set(archive.namelist())
        manifests=[name for name in names if name.endswith('/manifest.json')]
        roots=[name for name in manifests if '/Profiles/' not in name]
        if len(roots)!=1:raise ValueError('Profile archive must contain one root manifest.')
        root=json.loads(archive.read(roots[0]))
        pages={name.rsplit('/',2)[1].upper():(name,json.loads(archive.read(name)))
               for name in manifests if '/Profiles/' in name}
        current=root['Pages']['Current'].upper();default=root['Pages']['Default'].upper()
        if current not in pages or default not in pages:raise ValueError('Profile root refers to a missing page.')
        supported={'com.elgato.streamdeck.system.open','com.elgato.streamdeck.profile.openchild',
                   'com.elgato.streamdeck.profile.backtoparent','com.elgato.streamdeck.system.hotkey',
                   'com.elgato.streamdeck.system.text'}
        visited=set();action_ids=set();folder_targets=[]
        counts={'pages':0,'buttons':0,'open':0,'folders':0,'hotkeys':0,'text':0}
        def inspect_page(identifier):
            if identifier in visited:return
            visited.add(identifier);name,page=pages[identifier];counts['pages']+=1
            actions=[button for controller in page.get('Controllers',[]) for button in (controller.get('Actions') or {}).values()]
            if len(actions)>15:raise ValueError('A page exceeds the 15-key layout: '+page.get('Name',''))
            for button in actions:
                counts['buttons']+=1
                if button.get('UUID') not in supported:raise ValueError('Unsupported key action: '+str(button.get('UUID')))
                action_id=button.get('ActionID')
                if not action_id or action_id in action_ids:raise ValueError('Missing or duplicate key ActionID.')
                action_ids.add(action_id)
                states=button.get('States') or []
                if not states or not states[0].get('Title'):raise ValueError('A key has no visible label.')
                image_name=name.rsplit('/',1)[0]+'/'+states[0].get('Image','')
                if image_name not in names or not archive.read(image_name).startswith(b'\x89PNG'):
                    raise ValueError('A key icon is missing or invalid.')
                kind=button['UUID'].rsplit('.',1)[-1]
                if kind=='open':
                    counts['open']+=1
                    target=button.get('Settings',{}).get('path','').strip('"')
                    if not target or not button.get('UserInput'):raise ValueError('An Open key is incomplete.')
                    if shortcuts is not None and not Path(target).is_file():raise ValueError('Missing local shortcut: '+Path(target).name)
                elif kind=='openchild':
                    counts['folders']+=1;target=button.get('Settings',{}).get('ProfileUUID','').upper()
                    if target not in pages:raise ValueError('A folder key refers to a missing page.')
                    folder_targets.append(target);inspect_page(target)
                elif kind=='hotkey':
                    counts['hotkeys']+=1
                    if len(button.get('Settings',{}).get('Hotkeys',[]))!=4:raise ValueError('A hotkey is incomplete.')
                elif kind=='text':counts['text']+=1
        inspect_page(current)
        if len(folder_targets)!=len(set(folder_targets)):raise ValueError('A native folder has more than one parent.')
        orphan=set(pages)-visited-{default}
        if orphan:raise ValueError('Unreachable generated pages: '+', '.join(sorted(orphan)))
        return counts


def generate(output, device, language, links, entries=None, installed_apps=None, desktop_entries=None, mcp_entries=None):
    if installed_apps is None:
        from aidev.desktop import installed_tools
        installed_apps = installed_tools()
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
            opened(label('PROFILES','PROFILS'),'mission','Inspect detected harnesses and PowerShell profile commands.'),
            opened('ORCH','factory','Open the user-selected external orchestrator, or offer configuration when none is selected. Factory is optional; custom tools use an explicit command or URL.'),
            opened(label('CONTEXT','CONTEXTE'),'context','Capture Git metadata for the selected project. The action starts asynchronously; check the timestamp in the local context/latest.json file.'),
            opened('SESSIONS','status','Open local session receipts. Exited is not proof of a successful objective.'),
            folder(label('EDITOR','EDITEUR'),'editor'),folder('AI WEB','web'),
            folder('PROMPTS','prompts'),opened('TERMINAL','terminal','Choose a detected shell or terminal, including CMD, PowerShell, Git Bash and installed WSL distributions, in the selected project.'),
            folder(label('APPS','OUTILS'),'apps'),opened(label('PROJECT','PROJET'),'mission','Choose the project folder in the control panel.'),
            opened(label('CONTROL','PILOTAGE'),'factory-status','Choose an optional external orchestrator and inspect supported status. Custom tools do not imply status or usage integration.'),
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
    featured = [tool for tool, rows in groups.items() if any(row['available'] for row in rows)][:3]
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
        if tool in featured:
            # Native folders are a tree: importing a child with two parents drops a link.
            home_page = page+'-home'
            paginated(home_page,buttons,opened(label('PANEL','PANNEAU'),tool,'Open the mission panel to choose a harness and profile.'))
            home_folders[tool]=folder(tool.upper(),home_page)
    paginated('profiles',list(tool_folders.values()),opened('MISSION','mission','Open the mission panel to choose a harness and profile.'))
    pages['home'][1]=folder(label('PROFILES','PROFILS'),'profiles')
    # No preferred provider and no empty machine-specific placeholders on a clean install.
    pages['home'] = [pages['home'][0], *[home_folders[tool] for tool in featured], *pages['home'][1:]]
    desktop_actions = {'cursor','vscode','orca','monitor','resources','performance','system-info','capture'}
    for page in ('apps', 'system'):
        pages[page] = [button for button in pages[page]
                       if (Path(button['Settings'].get('path','').strip('"')).stem not in desktop_actions
                           or Path(button['Settings'].get('path','').strip('"')).stem in installed_apps)]
    # Each native folder has one parent. Daily system tools get their own page.
    agent_buttons = [button for button in pages.pop('home')
                     if button['Name'] not in (label('EDITOR','EDITEUR'), 'TERMINAL', label('APPS','OUTILS'), label('PROJECT','PROJET'))]
    orchestrator_buttons=[button for button in agent_buttons
                          if Path(button['Settings'].get('path','').strip('"')).stem in ('factory','factory-status')]
    agent_buttons=[button for button in agent_buttons if button not in orchestrator_buttons]
    pages['orchestrator']=[back,*orchestrator_buttons]
    pages['agentic'] = [back, *agent_buttons,folder('ORCH','orchestrator')]
    pages['dev'] = [back, opened('TERMINAL','terminal','Choose an installed terminal for the selected project.'),
                    folder(label('EDITOR','EDITEUR'),'editor'), folder(label('APPS','OUTILS'),'apps'),
                    opened('GIT','git','Inspect local Git state for the selected project.'),
                    opened(label('PROJECT','PROJET'),'mission','Choose the project in the control panel.'),
                    opened(label('FILES','FICHIERS'),'files','Open the selected project folder.'),
                    opened(label('HEALTH','DIAG'),'health','Inspect locally installed tools and storage.'),
                    opened(label('LOGS','JOURNAUX'),'logs','Open private logs.')]
    pages['system-home'] = list(pages['system'])
    pages['home'] = [folder('DEV','dev'), folder('AGENTIC','agentic'),
                     opened(label('BROWSER','NAVIGATEUR'),'browser-open','Choose an installed browser and open it.'),
                     opened(label('FILES','FICHIERS'),'files','Open the current project or the user home folder.'),
                     opened('SPOTIFY','spotify','Open installed Spotify; otherwise offer its web player in your chosen browser. No playback starts automatically.'),
                     hotkey(label('PREVIOUS','PRECEDENT'),177,qt=0x01000082),
                     hotkey(label('PLAY / PAUSE','LECTURE'),179,qt=0x01000086),
                     hotkey(label('NEXT','SUIVANT'),176,qt=0x01000083),
                     hotkey(label('MUTE','MUET'),173,qt=0x01000071),
                     opened('PHOTO\nVIDEO','capture','Open Snipping Tool to choose photo or video. Recording requires an explicit user action.'),
                     hotkey('VOL -',174,qt=0x01000070),hotkey('VOL +',175,qt=0x01000072),
                     hotkey(label('DESKTOP','BUREAU'),68,win=True),folder('CPU / RAM','system-home'),
                     opened(label('SETTINGS','REGLAGES'),'windows-settings','Open Windows Settings without changing a setting.')]
    if 'capture' not in installed_apps:
        pages['home']=[button for button in pages['home'] if button['Name']!='PHOTO VIDEO']
    desktop_entries=desktop_entries or []
    def application_button(entry):
        aliases={'visual studio code':'VS CODE','docker desktop':'DOCKER\nDESKTOP','github desktop':'GITHUB\nDESKTOP',
                 'chatgpt':'CHATGPT','claude':'CLAUDE','windows terminal':'TERMINAL'}
        title=aliases.get(entry['name'].casefold(),'\n'.join(textwrap.wrap(entry['name'].upper(),10)[:2]))
        button=opened(title,'app-'+entry['id'],'Open this exact detected Windows desktop application.')
        button['Name']=entry['name'];return button
    paginated('daily-apps',[application_button(e) for e in desktop_entries if e['category']=='daily'],opened(label('ALL APPS','TOUTES APPS'),'applications','Search all locally installed Start-menu applications.'))
    dev_entries=[e for e in desktop_entries if e['category']=='dev']
    paginated('dev-apps',[application_button(e) for e in dev_entries],opened(label('ALL APPS','TOUTES APPS'),'applications','Search installed development tools.'))
    ai_entries=[e for e in desktop_entries if e['category']=='agentic']
    paginated('ai-apps',[application_button(e) for e in ai_entries],opened(label('ALL APPS','TOUTES APPS'),'applications','Search installed AI desktop applications.'))
    mcp_buttons=[]
    for entry in mcp_entries or []:
        button=opened('\n'.join(textwrap.wrap(entry['name'].upper(),10)[:2]),'mcp-'+entry['id'],
                      'Inspect this local MCP declaration. Server connection, tools and credentials are not tested or exposed.')
        button['Name']=entry['host']+' / '+entry['name'];mcp_buttons.append(button)
    paginated('mcp',mcp_buttons,opened('MCP','mcp','Refresh known local MCP configurations and add a configuration source. No server is started.'))
    direct_ai=[]
    for wanted in ('claude','chatgpt'):
        entry=next((entry for entry in ai_entries if entry['name'].casefold()==wanted),None)
        if entry:
            button=application_button(entry)
            button['Name']=entry['name']+' Desktop'
            button['States'][0]['Title']=entry['name'].upper()+'\nDESKTOP'
            direct_ai.append(button)
    pages['agentic'] += [folder('MCP','mcp'),folder(label('AI APPS','APPS IA'),'ai-apps'),*direct_ai]
    preferred=('docker desktop','github desktop','gitkraken','visual studio code','cursor','visual studio','postman','insomnia','dbeaver','datagrip','pycharm','webstorm','rider','notepad++','devtoys')
    def dev_rank(entry):
        name=entry['name'].casefold()
        return next((index for index,value in enumerate(preferred) if name==value or name.startswith(value+' ')),len(preferred))
    featured_dev=[e for e in sorted(dev_entries,key=lambda e:(dev_rank(e),e['name'].casefold()))
                  if not any(word in e['name'].casefold() for word in ('installer','blend','powershell','terminal','wsl settings'))][:4]
    # Keep the DEV landing page workstation-first. AI Dev diagnostics remain under AI DEV.
    pages['dev']=[back,opened('TERMINAL','terminal','Choose an installed terminal for the selected project.'),
                  folder(label('EDITOR','EDITEUR'),'editor'),folder(label('DEV APPS','APPS DEV'),'dev-apps'),
                  opened('BUILD\nTEST','project-tasks','Inspect real project scripts and run only the selected task in a terminal.'),
                  folder('DEBUG','debug'),opened('GIT','git','Inspect local Git state for the selected project.'),
                  folder('GIT WEB','git-web'),opened(label('FILES','FICHIERS'),'files','Open the selected project folder.'),
                  opened(label('PROJECT','PROJET'),'mission','Choose the project in the control panel.'),folder('AI DEV','apps'),
                  *[application_button(entry) for entry in featured_dev]]
    pages['debug']=[back,hotkey('START F5',116,qt=16777268),hotkey('STOP',116,shift=True,qt=16777268),
                    hotkey('BREAKPOINT',120,qt=16777272),hotkey('STEP OVER',121,qt=16777273),
                    hotkey('STEP INTO',122,qt=16777274),hotkey('STEP OUT',122,shift=True,qt=16777274),
                    hotkey('BUILD',66,ctrl=True,shift=True)]
    pages['git-web']=[back,website('GITHUB','github'),website('PULL REQ','github-pr'),website('ISSUES','github-issues')]
    pages['media']=[back,*[b for b in pages['home'] if 'Hotkeys' in b['Settings'] and b['Settings']['Hotkeys'][0]['NativeCode'] in (173,174,175,176,177,179)]]
    pages['windows']=[back,opened(label('DISPLAY','AFFICHAGE'),'windows-display','Open Windows display settings.'),
                      opened(label('SOUND','SON'),'windows-sound','Open Windows sound settings.'),
                      opened(label('NETWORK','RESEAU'),'windows-network','Open Windows network status.'),
                      opened('BLUETOOTH','windows-bluetooth','Open Bluetooth settings.'),
                      opened(label('STORAGE','STOCKAGE'),'windows-storage','Open storage settings.'),
                      opened(label('DOWNLOADS','TELECHARG.'),'windows-downloads','Open Downloads.'),
                      opened('DOCUMENTS','windows-documents','Open Documents.'),
                      opened(label('PICTURES','IMAGES'),'windows-pictures','Open Pictures.'),
                      opened(label('RECYCLE','CORBEILLE'),'windows-recycle-bin','Open Recycle Bin without emptying it.'),
                      hotkey(label('SEARCH','RECHERCHE'),83,win=True),hotkey('EMOJI',190,win=True,qt=46),
                      hotkey(label('TASK VIEW','VUE TACHES'),9,win=True,qt=16777217),
                      hotkey(label('LOCK','VERROU'),76,win=True),opened(label('SERVICES','SERVICES'),'windows-services','Inspect Windows services.')]
    pages['desktop']=[back,hotkey(label('SHOW\nDESKTOP','AFFICHER'),68,win=True),
                      hotkey(label('TASK\nVIEW','VUE\nTACHES'),9,win=True,qt=16777217),
                      hotkey(label('DISPLAY\nMODE','MODE\nECRAN'),80,win=True),
                      opened(label('DISPLAY','AFFICHAGE'),'windows-display','Open Windows display settings to identify and arrange monitors.'),
                      hotkey(label('NEW\nDESKTOP','NOUV.\nBUREAU'),68,ctrl=True,win=True),
                      hotkey(label('PREV\nDESKTOP','BUREAU\nPREC.'),37,ctrl=True,win=True,qt=16777234),
                      hotkey(label('NEXT\nDESKTOP','BUREAU\nSUIV.'),39,ctrl=True,win=True,qt=16777236),
                      hotkey(label('CLOSE\nDESKTOP','FERMER\nBUREAU'),115,ctrl=True,win=True,qt=16777267),
                      hotkey(label('MOVE\nLEFT','ECRAN\nGAUCHE'),37,shift=True,win=True,qt=16777234),
                      hotkey(label('MOVE\nRIGHT','ECRAN\nDROIT'),39,shift=True,win=True,qt=16777236),
                      hotkey(label('MINIMIZE','MINIMISER'),77,win=True),
                      hotkey(label('RESTORE','RESTAURER'),77,shift=True,win=True)]
    # Daily home is generic; media applications are in the detected app catalog.
    pages['home']=[folder('DEV','dev'),folder('AGENTIC','agentic'),folder(label('APPS','APPS'),'daily-apps'),folder('WINDOWS','windows'),
                    opened(label('BROWSER','NAVIGATEUR'),'browser-open','Choose a browser.'),opened(label('FILES','FICHIERS'),'files','Open project files or the home directory.'),
                    opened('PHOTO\nVIDEO','capture','Open Snipping Tool; recording starts only by user action.'),folder(label('MEDIA','MEDIA'),'media'),
                    hotkey(label('CLIPBOARD','PRESSE-PAP.'),86,win=True),opened(label('CALCULATOR','CALC'),'windows-calculator','Open Windows Calculator.'),
                    opened(label('NOTEPAD','BLOC-NOTES'),'windows-notepad','Open Notepad.'),folder('CPU / RAM','system-home'),
                    folder(label('DESKTOP','BUREAU'),'desktop'),opened(label('SETTINGS','REGLAGES'),'windows-settings','Open Windows Settings.'),
                    opened(label('REFRESH','ACTUALISER'),'deck-refresh-'+language,'Rescan this workstation and open the regenerated profile for import.')]
    if 'capture' not in installed_apps:pages['home']=[b for b in pages['home'] if b['Name']!='PHOTO VIDEO']
    prefix=ids['profile'].upper()+'.sdProfile'
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        def write(path,data):archive.writestr(prefix+'/'+path,json.dumps(data,ensure_ascii=False))
        write('manifest.json',{'Name':'AI Dev '+language.upper(),'Version':'3.0','Device':device,'Pages':{'Current':ids['home'],'Default':ids['pinned'],'Pages':[ids['home']]}})
        for page,actions in pages.items():
            path='Profiles/'+ids.setdefault(page,str(uuid.uuid4())).upper()
            icons={}
            for button in actions:
                kind=button_icon(button)
                theme='music' if kind=='music' else 'daily' if page in ('home','system-home') else 'dev' if page in ('dev','apps','editor','system') else 'agent'
                filename=kind+'-'+theme+'.png'
                # Copies avoid shared state changing icons on another page.
                button['States']=[dict(state,Image='Images/'+filename) for state in button['States']]
                icons[filename]=icon_png(kind,theme)
            write(path+'/manifest.json',{'Name':page,'Icon':'','Controllers':[{'Type':'Keypad','Actions':{f'{i%5},{i//5}':dict(a,ActionID=str(uuid.uuid4())) for i,a in enumerate(actions)}}]})
            for filename,content in icons.items():archive.writestr(prefix+'/'+path+'/Images/'+filename,content)
        write('Profiles/'+ids['pinned'].upper()+'/manifest.json',{'Name':'','Icon':'','Controllers':[{'Type':'Keypad','Actions':None}]})
    audit_profile(output)
    return output


def select_device(profile_root, identifier=None):
    devices = {}
    for manifest in sorted(profile_root.glob('*.sdProfile/manifest.json')):
        candidate=json.loads(manifest.read_text('utf-8-sig')).get('Device',{})
        # This layout is qualified for the 15-key device family only.
        if candidate.get('Model')=='20GBA9901' and candidate.get('UUID'):
            devices[candidate['UUID']] = candidate
    if identifier:
        if identifier not in devices:raise ValueError('Selected compatible Stream Deck was not found.')
        return devices[identifier]
    if len(devices) == 1:return next(iter(devices.values()))
    if not devices:
        raise RuntimeError('Create a profile for a supported 15-key Stream Deck in Stream Deck first. Other layouts are not yet supported; the desktop app works without a device.')
    raise ValueError('Multiple compatible devices found. Choose one with --device-id: '+', '.join(devices))


def main():
    from aidev.migration import migrate_legacy
    migrate_legacy()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',choices=['auto','en','fr'],default=None)
    parser.add_argument('--import-profile', action='store_true', help='Open the normal Stream Deck import dialog.')
    parser.add_argument('--device-id', help='Choose a detected device when more than one compatible Stream Deck is configured.')
    args=parser.parse_args()
    links=data_dir()/'stream-deck/Launchers'
    root=Path(__file__).resolve().parents[1]
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    entries = discover()['entries']
    selections = save_selections(entries)
    from aidev.app_catalog import discover_apps
    from aidev.mcp_catalog import discover_mcp
    from aidev.storage import save_json
    save_json(data_dir()/'harness-locations.json',[{key:e.get(key) for key in ('tool','profile','directory')} for e in entries])
    desktop_entries=discover_apps();mcp_entries=discover_mcp()
    catalog_path=data_dir()/'stream-deck/catalog-shortcuts.json'
    save_json(catalog_path,[{'kind':kind,'id':e['id']} for kind,rows in [('app',desktop_entries),('mcp',mcp_entries)] for e in rows])
    subprocess.run([powershell(),'-NoProfile','-File',str(Path(__file__).with_name('Create-Shortcuts.ps1')),
                    '-PythonPath',str(pythonw),'-LauncherPath',str(root/'launch.py'),'-OutputDirectory',str(links),'-ProfilesPath',str(selections),'-CatalogPath',str(catalog_path)],check=True)
    profile_root=Path(os.environ['APPDATA'])/'Elgato/StreamDeck/ProfilesV3'
    device=select_device(profile_root,args.device_id or settings().get('stream_deck_device'))
    if args.device_id:
        from aidev.storage import save_settings
        config=settings();config['stream_deck_device']=device['UUID'];save_settings(config)
    language = resolve_language(args.language or settings().get('language','auto'))
    output=generate(data_dir()/('stream-deck/AI-Dev-'+language.upper()+'.streamDeckProfile'),device,language,links,entries,desktop_entries=desktop_entries,mcp_entries=mcp_entries)
    audit=audit_profile(output,links)
    print(f'Detected {len(desktop_entries)} desktop applications and {len(mcp_entries)} MCP declarations. Connections are not checked.')
    print(f'Detected {len(entries)} profile entries across {len({r["tool"] for r in entries})} harnesses.')
    print(f'Audited {audit["buttons"]} keys across {audit["pages"]} reachable pages; all local shortcuts and icons are present.')
    print('Import this local file in Stream Deck (do not commit it): '+str(output))
    if args.import_profile:
        os.startfile(output)


if __name__=='__main__':main()
