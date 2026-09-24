"""Discover real project tasks, then launch only the task the user selects."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import tomllib
from .discovery import powershell,SCRIPTS
from .storage import settings,save_settings,data_dir,save_json,read_json


def tasks():
    value=settings().get('project')
    if not value:return []
    project=Path(value).expanduser().resolve(strict=True)
    if not project.is_dir():raise ValueError('Choose a project directory.')
    result=[]
    def add(name,executable,args):
        if not executable:return
        task={'name':name,'executable':str(executable),'arguments':args,'project':str(project),'category':'project'}
        task['id']=hashlib.sha256(json.dumps(task,sort_keys=True).encode()).hexdigest();result.append(task)
    manifest=project/'package.json'
    if manifest.is_file():
        data=json.loads(manifest.read_text('utf-8-sig'))
        manager=next((manager for filename,manager in [('pnpm-lock.yaml','pnpm'),('yarn.lock','yarn'),('bun.lock','bun'),('bun.lockb','bun')] if (project/filename).exists()),'npm')
        for name,script in data.get('scripts',{}).items():
            if isinstance(script,str) and re.fullmatch(r'[A-Za-z0-9_:./-]+',name):add(manager+' run '+name,shutil.which(manager),['run',name])
    if (project/'pyproject.toml').is_file() or (project/'requirements.txt').is_file():
        python=project/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
        python=str(python) if python.is_file() else sys.executable
        add('Python: installed packages',python,['-m','pip','list'])
        pytest_config=(project/'pytest.ini').is_file()
        pyproject=project/'pyproject.toml'
        if pyproject.is_file():
            try:
                parsed=tomllib.loads(pyproject.read_text('utf-8-sig'))
                pytest_config=pytest_config or 'pytest' in parsed.get('tool',{})
            except (OSError,ValueError):pass
        if pytest_config:add('Python: pytest',python,['-m','pytest'])
        elif (project/'tests').is_dir():add('Python: unittest discovery',python,['-m','unittest','discover'])
    if any((project/name).is_file() for name in ('compose.yaml','compose.yml','docker-compose.yml','docker-compose.yaml')):
        add('Docker Compose: status',shutil.which('docker'),['compose','ps'])
        add('Docker Compose: validate configuration',shutil.which('docker'),['compose','config','--quiet'])
    makefile=project/'Makefile'
    if makefile.is_file():
        for line in makefile.read_text('utf-8',errors='replace').splitlines():
            match=re.match(r'^([A-Za-z0-9_-]+):(?:\s|$)',line)
            if match:add('make '+match.group(1),shutil.which('make'),[match.group(1)])
    return sorted({e['id']:e for e in result}.values(),key=lambda e:e['name'])


TASK_KINDS={
    'build':('build','compile','bundle'),
    'test':('test','tests','unit','check:test'),
    'lint':('lint','check','eslint','ruff'),
    'dev':('dev','start','serve','run','watch'),
    'types':('typecheck','type-check','types','tsc','mypy'),
    'format':('format','fmt','prettier'),
}


def script_name(task):
    """Short name of a detected task: npm/make script name, or 'test' for Python test runners."""
    args=task.get('arguments',[])
    if task['name'] in ('Python: pytest','Python: unittest discovery'):return 'test'
    if len(args)==2 and args[0]=='run':return args[1]
    if task['name'].startswith('make ') and len(args)==1:return args[0]
    return ''


def task_for_kind(kind, rows=None):
    """Pick the project task matching a direct deck key (BUILD, TEST, ...). Exact names win over prefixes."""
    if kind not in TASK_KINDS:raise ValueError('Unknown task kind.')
    rows=tasks() if rows is None else rows
    names=[(script_name(row),row) for row in rows]
    for candidate in TASK_KINDS[kind]:
        match=next((row for name,row in names if name==candidate),None)
        if match:return match
    for candidate in TASK_KINDS[kind]:
        match=next((row for name,row in names if name.startswith(candidate+':')),None)
        if match:return match
    return None


def launch_kind(kind):
    """Run the matching task immediately; otherwise open the task list so nothing unexpected runs."""
    task=task_for_kind(kind)
    if task:return launch(task)
    task_dialog(notice=kind)


def launch_task(identifier):
    task=next((e for e in tasks() if e['id']==identifier),None)
    if not task:raise ValueError('The selected project task is no longer available. Refresh the task list.')
    return launch(task)


def launch(task):
    path=data_dir()/'task-requests'/(str(uuid.uuid4())+'.json');save_json(path,task)
    python=str(Path(sys.executable).with_name('python.exe')) if os.name=='nt' else sys.executable
    command=[python,str(Path(__file__).resolve().parents[1]/'launch.py'),'--task-run',str(path.resolve())]
    wt=shutil.which('wt')
    if wt:command=[wt,'-w','new','new-tab','--title','AI Dev: '+task['name'],'-d',task['project'],*command]
    try:subprocess.Popen(command,cwd=task['project'],creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
    except OSError:path.unlink(missing_ok=True);raise


def run_task(path):
    path=Path(path);code=1
    try:
        task=read_json(path)
        if not isinstance(task,dict) or not isinstance(task.get('arguments'),list):raise ValueError('Invalid project task request.')
        if not Path(task['executable']).is_file():raise FileNotFoundError(task['executable'])
        print(task['name']+'\n'+task['project'],flush=True)
        code=subprocess.run([powershell(),'-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(SCRIPTS/'ProjectTask.ps1'),'-RequestPath',str(path.resolve())],cwd=task['project']).returncode
    except Exception as error:print(str(error),file=sys.stderr)
    finally:path.unlink(missing_ok=True)
    print('Exit code:',code)
    if sys.stdin and sys.stdin.isatty():
        try:input('Press Enter to close...')
        except (EOFError,KeyboardInterrupt):pass
    return code


def task_dialog(notice=None):
    from .catalog_ui import CatalogWindow
    from tkinter import ttk,filedialog
    from .i18n import tr,resolve_language
    language=resolve_language(settings().get('language','auto'))
    message=(lambda:tr('task_kind_missing',language).format(kind=notice.upper())) if notice else None
    window=CatalogWindow('project_tasks',tasks,lambda e:e['project']+'\n'+subprocess.list2cmdline([e['executable'],*e['arguments']])+'\n\n'+tr('task_limits',language),launch_task,notice=message)
    window.open_button.configure(text=tr('task_run',language))
    def choose():
        value=filedialog.askdirectory(parent=window.root)
        if value:config=settings();config['project']=value;save_settings(config);window.refresh()
    ttk.Button(window.buttons,text=tr('project',language),command=choose).pack(side='left',padx=8)
    window.run()
