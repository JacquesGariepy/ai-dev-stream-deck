"""Read-only workstation and Git diagnostics for engineering workflows."""
import os
from pathlib import Path
import platform
import sys
import tempfile
from .discovery import discover, powershell
from .runtime import git_read, now
from .storage import data_dir, settings


def health():
    result={'generated':now(),'python':sys.version.split()[0], 'platform':platform.platform(),
            'data_dir':str(data_dir()), 'writable':False, 'entries':[], 'issues':[]}
    try:
        data_dir().mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryFile(dir=data_dir()):pass
        result['writable']=True
    except OSError as error:result['issues'].append(str(error))
    try:
        result['powershell']=powershell()
        result['entries']=discover()['entries']
    except Exception as error:result['issues'].append(str(error))
    config=settings().get('elgato_mcp',{})
    result['bridge_configured']=bool(config)
    result['bridge_files_present']=bool(config and Path(config.get('command','')).is_file() and
                                         config.get('args') and Path(config['args'][0]).is_file())
    return result


def git_status(project):
    project=Path(project).expanduser().resolve(strict=True)
    return {'project':str(project), 'generated':now(),
            'status':git_read(project,'status','--short','--branch'),
            'diff':git_read(project,'diff','--stat'),
            'staged':git_read(project,'diff','--cached','--stat'),
            'worktrees':git_read(project,'worktree','list'),
            'limits':'Local Git metadata; no fetch, no provider calls, no test results inferred.'}


def open_logs():
    directory=data_dir()/'logs'
    directory.mkdir(parents=True,exist_ok=True)
    os.startfile(str(directory))


class EngineeringUI:
    def render_engineering(self, frame):
        from tkinter import ttk
        import tkinter as tk
        ttk.Label(frame,text=self.text('engineering_note'),wraplength=840).pack(anchor='w',pady=8)
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        self.health_button=ttk.Button(row,text=self.text('health'),command=self.refresh_health)
        self.health_button.pack(side='left')
        self.git_button=ttk.Button(row,text=self.text('git_state'),command=self.refresh_git)
        self.git_button.pack(side='left',padx=8)
        ttk.Button(row,text=self.text('logs'),command=self.show_logs).pack(side='left')
        self.engineering_details=tk.Text(frame,wrap='word',state='disabled')
        self.engineering_details.pack(fill='both',expand=True)
        self.engineering_generation=getattr(self,'engineering_generation',0)+1
        self.set_text(self.engineering_details,self.text('engineering_note'))

    def show_logs(self):
        try:open_logs()
        except OSError as error:self.error(error)

    def refresh_health(self):
        generation=self.engineering_generation
        self.health_button.configure(state='disabled')
        self.set_text(self.engineering_details,self.text('loading'))
        def completed(ok,result):
            if generation!=self.engineering_generation:return
            self.health_button.configure(state='normal')
            if not ok:
                self.set_text(self.engineering_details,str(result));return
            lines=[result['generated'],f"Python: {result['python']}",f"PowerShell: {result.get('powershell') or '—'}",
                   f"{self.text('data_folder')}: {result['data_dir']}",
                   self.text('data_writable' if result['writable'] else 'data_denied'),
                   self.text('bridge_present' if result['bridge_files_present'] else 'bridge_missing'),'',self.text('harness')]
            for entry in result['entries']:
                lines.append(f"{entry['tool']} / {entry['profile']}: {self.text('available' if entry['available'] else 'unavailable')}")
                lines.append('  '+entry['command'])
            lines.extend(['',self.text('auth_not_checked'),*result['issues']])
            self.set_text(self.engineering_details,'\n'.join(lines))
        self.background(health,completed)

    def refresh_git(self):
        generation=self.engineering_generation
        project=self.project.get()
        self.git_button.configure(state='disabled')
        self.set_text(self.engineering_details,self.text('loading'))
        def completed(ok,result):
            if generation!=self.engineering_generation:return
            self.git_button.configure(state='normal')
            if not ok:self.set_text(self.engineering_details,str(result));return
            lines=[result['project'],result['generated']]
            for key in ('status','diff','staged','worktrees'):
                lines.extend(['',self.text('git_'+key),result[key]['output'] or self.text('no_changes')])
            lines.extend(['',self.text('git_limits')])
            self.set_text(self.engineering_details,'\n'.join(lines))
        self.background(lambda:git_status(project),completed)
