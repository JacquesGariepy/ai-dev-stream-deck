"""Explicit browser routing for work and personal web sessions."""
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit
from .storage import settings, save_settings

CONTEXTS = ('work', 'personal')


def installed_browsers():
    programs = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
    programs86 = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    candidates = {
        'chrome': [shutil.which('chrome'), programs/'Google/Chrome/Application/chrome.exe',
                   programs86/'Google/Chrome/Application/chrome.exe', local/'Google/Chrome/Application/chrome.exe'],
        'edge': [shutil.which('msedge'), programs86/'Microsoft/Edge/Application/msedge.exe',
                 programs/'Microsoft/Edge/Application/msedge.exe', local/'Microsoft/Edge/Application/msedge.exe'],
    }
    return {name: str(found) for name, paths in candidates.items()
            if (found := next((path for path in paths if path and Path(path).is_file()), None))}


def validate_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.hostname or any(ord(char) < 32 for char in url):
        raise ValueError('Only HTTP and HTTPS website URLs are supported.')
    return url


def save_browser_choices(context, mapping, ask_each_time=True):
    if context not in CONTEXTS:
        raise ValueError('Choose work or personal.')
    installed = installed_browsers()
    if mapping.get(context) not in installed or any(value and value not in installed for value in mapping.values()):
        raise ValueError('Choose an installed browser for the active context.')
    config = settings()
    config['web'] = {'context': context, 'browsers': {key: mapping[key] for key in CONTEXTS if mapping.get(key)}, 'ask_each_time': bool(ask_each_time)}
    save_settings(config)


def browser_command(url, context=None):
    validate_url(url)
    config = settings().get('web', {})
    context = context or config.get('context')
    if context not in CONTEXTS:
        raise ValueError('Choose a web context in Browser settings first.')
    name = config.get('browsers', {}).get(context)
    executable = installed_browsers().get(name)
    if not executable:
        raise ValueError('The browser for this context is not configured or no longer installed.')
    return [executable, url]


def open_website(url, context=None):
    command = browser_command(url, context)
    subprocess.Popen(command)
    return command


def select_context(context):
    config = settings()
    web = config.get('web', {})
    if context not in CONTEXTS or web.get('browsers', {}).get(context) not in installed_browsers():
        return False
    web['context'] = context
    config['web'] = web
    save_settings(config)
    return True


def browser_dialog(url=None, context=None):
    import tkinter as tk
    from tkinter import ttk, messagebox
    from .i18n import resolve_language, tr
    config = settings()
    language = resolve_language(config.get('language','auto'))
    text = lambda key: tr(key, language)
    app = tk.Tk()
    app.title('AI Dev — ' + text('browsers'))
    app.geometry('600x390')
    app.minsize(580, 375)
    panel = ttk.Frame(app, padding=22); panel.pack(fill='both',expand=True)
    ttk.Label(panel,text=text('browsers'),font=('Segoe UI',18,'bold')).pack(anchor='w')
    ttk.Label(panel,text=text('browser_note'),wraplength=530).pack(anchor='w',pady=12)
    installed=installed_browsers()
    labels={'edge':'Edge','chrome':'Chrome'}
    existing=config.get('web',{})
    variables={}
    for key in CONTEXTS:
        row=ttk.Frame(panel);row.pack(fill='x',pady=5)
        ttk.Label(row,text='Work' if key=='work' else 'Personal',width=14).pack(side='left')
        var=tk.StringVar(value=labels.get(existing.get('browsers',{}).get(key),''))
        variables[key]=var
        ttk.Combobox(row,textvariable=var,values=[labels[name] for name in installed],state='readonly').pack(side='left',fill='x',expand=True)
    selected=tk.StringVar(value=context or existing.get('context','work'))
    row=ttk.Frame(panel);row.pack(fill='x',pady=12)
    ttk.Label(row,text=text('web_context'),width=14).pack(side='left')
    for key in CONTEXTS:
        ttk.Radiobutton(row,text=key.capitalize(),value=key,variable=selected).pack(side='left',padx=8)
    ask=tk.BooleanVar(value=existing.get('ask_each_time',True))
    ttk.Checkbutton(panel,text=text('ask_browser'),variable=ask).pack(anchor='w',pady=5)
    def submit():
        try:
            mapping={key:next((name for name,label in labels.items() if label==var.get()),None) for key,var in variables.items()}
            save_browser_choices(selected.get(),mapping,ask.get())
            if url:open_website(url,selected.get())
            app.destroy()
        except Exception as error:messagebox.showerror(text('error'),str(error),parent=app)
    ttk.Button(panel,text=text('save_open' if url else 'save'),command=submit).pack(anchor='e',pady=8)
    app.mainloop()
