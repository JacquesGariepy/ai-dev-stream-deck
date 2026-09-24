"""Discover launchable Start-menu apps; keep their identities local."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from .discovery import powershell, NO_WINDOW
from .storage import data_dir, save_json


def category(name):
    if re.search(r'^(ChatGPT|Claude|Codex|LM Studio|AnythingLLM|Ollama|Antigravity|Orca|Copilot)\b',name,re.I):return 'agentic'
    if re.search(r'Visual Studio|Cursor|Windsurf|Docker|Postman|Insomnia|GitHub|GitKraken|DBeaver|DataGrip|JetBrains|IntelliJ|PyCharm|Rider|WebStorm|Android Studio|Notepad\+\+|Windows Terminal|^Terminal$|PowerShell|WSL|Ubuntu|Debian|DevToys|WinMerge|Meld|Sublime|Neovim|^Git |^Python |^IDLE|Dev Home|Developer Command|Google Cloud SDK|Hyper-V|ODBC',name,re.I):return 'dev'
    return 'daily'


def discover_apps():
    shell=powershell()
    if not shell:raise RuntimeError('PowerShell is required to enumerate Windows applications.')
    result=subprocess.run([shell,'-NoProfile','-NonInteractive','-Command',
                           '[Console]::OutputEncoding = [Text.UTF8Encoding]::new(); @(Get-StartApps | Select-Object Name,AppID) | ConvertTo-Json -Compress'],
                          capture_output=True,text=True,encoding='utf-8-sig',errors='replace',timeout=20,creationflags=NO_WINDOW)
    if result.returncode:raise RuntimeError('Cannot enumerate installed Start-menu apps.')
    values=json.loads(result.stdout or '[]')
    if isinstance(values,dict):values=[values]
    entries=[]
    for value in values:
        if not value.get('Name') or not value.get('AppID'):continue
        appid=value['AppID']
        entries.append({'id':hashlib.sha256(appid.encode()).hexdigest(),'name':value['Name'],'app_id':appid,'category':category(value['Name'])})
    entries=sorted({e['id']:e for e in entries}.values(),key=lambda e:e['name'].casefold())
    save_json(data_dir()/'desktop-apps.json',entries)
    return entries


def open_app(identifier):
    if not re.fullmatch('[a-f0-9]{64}',identifier):raise ValueError('Invalid application selection.')
    entry=next((e for e in discover_apps() if e['id']==identifier),None)
    if not entry:raise ValueError('This application is no longer installed. Refresh the deck.')
    subprocess.Popen([str(Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'),'shell:AppsFolder\\'+entry['app_id']])


def app_dialog():
    from .catalog_ui import CatalogWindow
    window=CatalogWindow('applications',discover_apps,
                         lambda e: e['name']+'\n'+e['category'],open_app)
    window.run()
