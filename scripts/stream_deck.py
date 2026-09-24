"""Generate an importable 15-key Stream Deck profile for this workstation only."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import zipfile
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.agents import TEXT_PROMPTS
from aidev.discovery import powershell
from aidev.i18n import resolve_language, tr
from aidev.storage import data_dir, settings


def background():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + (bytes((88,220,197)) if y < 6 else bytes((17,27,42))) * 144 for y in range(144))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B',144,144,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(rows)) + chunk(b'IEND',b'')


def action(title, kind, config, description=''):
    return {'ActionID':str(uuid.uuid4()), 'Name':title.replace('\n',' '), 'UUID':'com.elgato.streamdeck.'+kind,
            'LinkedTitle':True, 'Settings':config, 'State':0, 'UserInput':description,
            'States':[{'Title':title, 'ShowTitle':True, 'TitleAlignment':'middle', 'TitleColor':'#ffffff', 'FontSize':13, 'Image':'Images/background.png'}]}


def hotkey(title, key, ctrl=False, shift=False, alt=False):
    actual={'KeyCmd':False,'KeyCtrl':ctrl,'KeyShift':shift,'KeyOption':alt,'KeyModifiers':2*ctrl+shift+4*alt,'NativeCode':key,'QTKeyCode':key,'VKeyCode':key}
    blank={'KeyCmd':False,'KeyCtrl':False,'KeyShift':False,'KeyOption':False,'KeyModifiers':0,'NativeCode':146,'QTKeyCode':33554431,'VKeyCode':-1}
    return action(title,'system.hotkey',{'Coalesce':True,'Hotkeys':[actual,blank,blank,blank]})


def generate(output, device, language, links):
    ids={name:str(uuid.uuid4()) for name in ('profile','home','prompts','editor','web','pinned')}
    label=lambda en,fr:fr if language=='fr' else en
    def opened(title, name, description):
        return action(title,'system.open',{'path':'"'+str(links/(name+'.lnk'))+'"'},description)
    def folder(title,name):
        return action(title,'profile.openchild',{'ProfileUUID':ids[name]})
    def website(title,url):
        return action(title,'system.website',{'path':url,'openInBrowser':True})
    back=action(label('BACK','RETOUR'),'profile.backtoparent',{})
    pages={
        'home':[
            opened('MISSION','mission','Open the AI Dev control panel to select an installed harness, PowerShell profile and English objective.'),
            opened('CODEX','codex','Open the control panel with Codex selected.'),
            opened('CLAUDE','claude','Open the control panel with Claude selected.'),
            opened('AGY','agy','Open the control panel with AGY selected.'),
            opened(label('PROFILES','PROFILS'),'mission','Inspect detected harnesses and PowerShell profile commands.'),
            opened(label('PROJECT','PROJET'),'mission','Choose the project folder in the control panel.'),
            opened(label('CONTEXT','CONTEXTE'),'context','Capture Git metadata for the selected project. The action starts asynchronously; check the timestamp in the local context/latest.json file.'),
            opened('SESSIONS','status','Open local session receipts. Exited is not proof of a successful objective.'),
            folder(label('EDITOR','EDITEUR'),'editor'),folder('AI WEB','web'),
            folder('PROMPTS','prompts'),opened('TERMINAL','terminal','Open PowerShell in the selected project.'),
            opened(label('FILES','FICHIERS'),'files','Open the selected project folder.'),opened('GUIDE','guide','Open the local README.'),
        ],
        'prompts':[back]+[action(tr(key,language),'system.text',{'isSendingEnter':False,'pastedText':'Communicate in English. '+text}) for key,text in TEXT_PROMPTS.items()],
        'editor':[back,hotkey(label('COMMANDS','COMMANDES'),80,ctrl=True,shift=True),hotkey(label('FIND FILE','FICHIER'),80,ctrl=True),hotkey(label('SEARCH','RECHERCHE'),70,ctrl=True,shift=True),hotkey(label('SAVE','SAUVER'),83,ctrl=True),hotkey(label('FORMAT','FORMATER'),70,shift=True,alt=True),hotkey(label('COPY','COPIER'),67,ctrl=True),hotkey(label('PASTE','COLLER'),86,ctrl=True)],
        'web':[back,website('CHATGPT','https://chatgpt.com/'),website('CLAUDE','https://claude.ai/'),website('GEMINI','https://gemini.google.com/'),website('GITHUB','https://github.com/')],
    }
    prefix=ids['profile'].upper()+'.sdProfile'
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        def write(path,data):archive.writestr(prefix+'/'+path,json.dumps(data,ensure_ascii=False))
        write('manifest.json',{'Name':'AI Dev','Version':'3.0','Device':device,'Pages':{'Current':ids['home'],'Default':ids['pinned'],'Pages':[ids['home']]}})
        for page,actions in pages.items():
            path='Profiles/'+ids[page].upper()
            write(path+'/manifest.json',{'Name':page,'Icon':'','Controllers':[{'Type':'Keypad','Actions':{f'{i%5},{i//5}':a for i,a in enumerate(actions)}}]})
            archive.writestr(prefix+'/'+path+'/Images/background.png',background())
        write('Profiles/'+ids['pinned'].upper()+'/manifest.json',{'Name':'','Icon':'','Controllers':[{'Type':'Keypad','Actions':None}]})
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',choices=['auto','en','fr'],default=None)
    args=parser.parse_args()
    links=data_dir()/'stream-deck/Launchers'
    root=Path(__file__).resolve().parents[1]
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    subprocess.run([powershell(),'-NoProfile','-File',str(Path(__file__).with_name('Create-Shortcuts.ps1')),
                    '-PythonPath',str(pythonw),'-LauncherPath',str(root/'launch.py'),'-OutputDirectory',str(links)],check=True)
    profile_root=Path(os.environ['APPDATA'])/'Elgato/StreamDeck/ProfilesV3'
    device=None
    for manifest in sorted(profile_root.glob('*.sdProfile/manifest.json')):
        candidate=json.loads(manifest.read_text('utf-8-sig')).get('Device',{})
        if candidate.get('Model')=='20GBA9901':
            device=candidate;break
    if not device:
        raise RuntimeError('Connect a 15-key Stream Deck and create a profile in Stream Deck first. Other models need a layout adapter.')
    output=generate(data_dir()/'stream-deck/AI-Dev.streamDeckProfile',device,
                    resolve_language(args.language or settings().get('language','auto')),links)
    print('Import this local file in Stream Deck (do not commit it): '+str(output))


if __name__=='__main__':main()
