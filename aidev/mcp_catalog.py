"""Read known local MCP declarations; never execute servers or retain secrets."""
import hashlib
import json
import os
from pathlib import Path
import re
import tomllib
from .storage import data_dir,settings,save_json,read_json,save_settings


def _jsonc(text):
    """Remove JSONC comments/trailing commas without touching quoted secrets."""
    output=[];index=0;quoted=False;escaped=False
    while index < len(text):
        char=text[index]
        if quoted:
            output.append(char)
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
            index+=1;continue
        if char=='"':quoted=True;output.append(char);index+=1;continue
        if text.startswith('//',index):
            end=text.find('\n',index);index=len(text) if end<0 else end;continue
        if text.startswith('/*',index):
            end=text.find('*/',index+2)
            if end<0:raise ValueError('Unterminated JSONC comment')
            index=end+2;continue
        output.append(char);index+=1
    cleaned=''.join(output);output=[];index=0;quoted=False;escaped=False
    while index < len(cleaned):
        char=cleaned[index]
        if quoted:
            output.append(char)
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
            index+=1;continue
        if char=='"':quoted=True;output.append(char);index+=1;continue
        if char==',':
            look=index+1
            while look<len(cleaned) and cleaned[look].isspace():look+=1
            if look<len(cleaned) and cleaned[look] in '}]':index+=1;continue
        output.append(char);index+=1
    return ''.join(output)


def sources():
    home=Path.home();appdata=Path(os.environ.get('APPDATA',home))
    rows=[('Codex',Path(os.environ.get('CODEX_HOME',home/'.codex'))/'config.toml'),
          ('Claude Desktop',appdata/'Claude/claude_desktop_config.json'),
          ('Claude Code',home/'.claude.json'),('Cursor',home/'.cursor/mcp.json'),
          ('VS Code',appdata/'Code/User/mcp.json'),('Windsurf',home/'.codeium/windsurf/mcp_config.json'),
          ('AI Dev',data_dir()/'elgato-mcp.json')]
    project=settings().get('project')
    if project:
        rows += [('Project',Path(project)/p) for p in ('.mcp.json','.vscode/mcp.json','.cursor/mcp.json','.codex/config.toml')]
    rows += [('Custom',Path(path)) for path in settings().get('mcp_config_files',[])]
    harnesses=read_json(data_dir()/'harness-locations.json',[])
    if not isinstance(harnesses,list):harnesses=[]
    for entry in harnesses:
        if not isinstance(entry,dict):continue
        directory=entry.get('directory')
        if directory:
            host=str(entry.get('tool','Harness'))+' / '+str(entry.get('profile','default'))
            rows += [(host,Path(directory)/filename)
                     for filename in ('config.toml','.mcp.json','mcp.json','mcp_config.json','claude_desktop_config.json')]
    return list(dict.fromkeys(rows))


def read_entries(host,path):
    # Do not log parser exceptions: their text may contain credentials from the file.
    text=path.read_text('utf-8-sig')
    data=tomllib.loads(text) if path.suffix=='.toml' else json.loads(_jsonc(text))
    if not isinstance(data,dict):raise ValueError('MCP configuration must be an object')
    tables=[data.get(key,{}) for key in ('mcpServers','mcp_servers','servers')]
    if host=='Claude Code':
        project=settings().get('project')
        if project:
            scoped=data.get('projects',{}).get(project,{})
            tables.append(scoped.get('mcpServers',{}))
    result=[]
    for table in tables:
        if not isinstance(table,dict):continue
        for name,value in table.items():
            if not isinstance(value,dict):continue
            source=str(path.resolve())
            identifier=hashlib.sha256((source+'\0'+name).encode()).hexdigest()
            state='disabled' if value.get('disabled') is True or value.get('enabled') is False else 'enabled' if value.get('enabled') is True else 'unspecified'
            result.append({'id':identifier,'name':name,'host':host,'source':source,
                           'transport':'stdio' if value.get('command') else 'remote' if value.get('url') else 'unspecified',
                           'enabled':state,
                           'status':'configured; connection and tools not checked'})
    return result


def discover_mcp():
    entries=[];issues=[]
    for host,path in sources():
        if not path.is_file():continue
        try:entries.extend(read_entries(host,path))
        except (OSError,ValueError,TypeError,AttributeError):issues.append({'host':host,'source':str(path),'issue':'Cannot read this configuration (JSON/TOML required).'})
    entries=sorted({e['id']:e for e in entries}.values(),key=lambda e:(e['host'],e['name']))
    save_json(data_dir()/'mcp-inventory.json',{'entries':entries,'issues':issues})
    return entries


def mcp_dialog(identifier=None):
    if identifier and not re.fullmatch('[a-f0-9]{64}',identifier):raise ValueError('Invalid MCP selection.')
    from .catalog_ui import CatalogWindow
    from .i18n import resolve_language,tr
    language=resolve_language(settings().get('language','auto'))
    def details(entry):
        return (entry['name']+'\n'+entry['host']+'\n'+entry['source']+'\n'+entry['transport']+'\n'+
                tr('mcp_'+entry['enabled'],language)+'\n\n'+tr('mcp_limits',language))
    def open_source_folder(value):
        entry=next((e for e in discover_mcp() if e['id']==value),None)
        if not entry:raise ValueError(tr('catalog_removed',language))
        os.startfile(str(Path(entry['source']).parent))
    def notice():
        issues=read_json(data_dir()/'mcp-inventory.json',{}).get('issues',[])
        return tr('mcp_limits',language)+(' '+tr('mcp_read_issues',language).format(count=len(issues)) if issues else '')
    window=CatalogWindow('mcp_inventory',discover_mcp,details,open_source_folder,identifier,notice)
    window.open_button.configure(text=tr('mcp_source_folder',language))
    from tkinter import filedialog,ttk
    def add_source():
        value=filedialog.askopenfilename(parent=window.root,filetypes=[('MCP configuration','*.json *.toml')])
        if value:
            config=settings();config['mcp_config_files']=list(dict.fromkeys([*config.get('mcp_config_files',[]),value]));save_settings(config);window.refresh()
    ttk.Button(window.buttons,text=tr('mcp_add_source',language),command=add_source).pack(side='left',padx=8)
    window.run()
