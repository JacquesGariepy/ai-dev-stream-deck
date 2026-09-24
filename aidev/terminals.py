"""Discover local shells and terminal applications without starting a shell profile."""
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading

from .discovery import NO_WINDOW
from .storage import settings, save_settings


def installed_terminals():
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    programs = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
    windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
    entries, seen, issues = [], set(), []

    def add(label, kind, candidates, distro=None):
        for candidate in candidates:
            if not candidate or not Path(candidate).is_file():
                continue
            executable = str(Path(candidate).resolve())
            identity = (os.path.normcase(executable), distro)
            if identity in seen:
                continue
            seen.add(identity)
            entries.append({'id': executable + ('::' + distro if distro else ''),
                            'label': label, 'kind': kind, 'executable': executable, 'distro': distro})

    add('CMD', 'cmd', [shutil.which('cmd'), windows/'System32/cmd.exe'])
    add('Windows PowerShell 5.1', 'powershell', [shutil.which('powershell'), windows/'System32/WindowsPowerShell/v1.0/powershell.exe'])
    add('PowerShell 7+', 'powershell', [shutil.which('pwsh')])
    for root in (programs/'PowerShell', local/'Microsoft/PowerShell'):
        if root.is_dir():
            for executable in sorted(root.glob('*/pwsh.exe')):
                add('PowerShell ' + executable.parent.name, 'powershell', [executable])
    git = shutil.which('git')
    git_roots = [programs/'Git', local/'Programs/Git']
    if git:
        git_roots.insert(0, Path(git).resolve().parent.parent)
    add('Git Bash', 'bash', [root/'bin/bash.exe' for root in git_roots])
    add('Windows Terminal', 'wt', [shutil.which('wt'), local/'Microsoft/WindowsApps/wt.exe'])
    add('Windows Terminal Preview', 'wt', [shutil.which('wt-preview')])
    optional = [
        ('Nushell', 'nu', 'shell', [programs/'nu/bin/nu.exe']),
        ('PowerShell ISE', 'powershell_ise', 'app', [windows/'System32/WindowsPowerShell/v1.0/powershell_ise.exe']),
        ('WezTerm', 'wezterm', 'wezterm', [programs/'WezTerm/wezterm.exe']),
        ('Alacritty', 'alacritty', 'alacritty', [programs/'Alacritty/alacritty.exe']),
        ('Tabby', 'tabby', 'app', [local/'Programs/Tabby/Tabby.exe']),
        ('Hyper', 'hyper', 'app', [local/'Programs/Hyper/Hyper.exe']),
        ('ConEmu', 'ConEmu64', 'app', [programs/'ConEmu/ConEmu64.exe']),
        ('Cmder', 'cmder', 'app', [programs/'Cmder/Cmder.exe']),
        ('Cygwin Bash', None, 'bash', [Path('C:/cygwin64/bin/bash.exe'), Path('C:/cygwin/bin/bash.exe')]),
        ('MSYS2 Bash', None, 'bash', [Path('C:/msys64/usr/bin/bash.exe')]),
    ]
    for label, command, kind, extra in optional:
        add(label, kind, [shutil.which(command) if command else None, *extra])
    wsl = shutil.which('wsl')
    if wsl:
        try:
            result = subprocess.run([wsl, '--list', '--quiet'], capture_output=True, timeout=8, creationflags=NO_WINDOW)
            output = result.stdout.decode('utf-16-le' if b'\x00' in result.stdout else 'utf-8', errors='replace')
            if result.returncode == 0:
                for distro in output.replace('\ufeff', '').splitlines():
                    if distro.strip():
                        add('WSL — ' + distro.strip(), 'wsl', [wsl], distro.strip())
            else:
                issues.append('WSL: ' + output.strip())
        except (OSError, subprocess.TimeoutExpired) as error:
            issues.append('WSL: ' + str(error))
    for executable in settings().get('terminal_custom', []):
        add(Path(executable).stem, 'app', [executable])
    return entries, issues


def terminal_command(entry, project):
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be a directory.')
    executable = entry['executable']
    if not Path(executable).is_file():
        raise FileNotFoundError(executable)
    args = [executable]
    kind = entry['kind']
    if kind == 'powershell': args += ['-NoLogo']
    elif kind == 'bash': args += ['--login', '-i']
    elif kind == 'wsl': args += ['--distribution', entry['distro'], '--cd', str(project)]
    elif kind == 'wt': args += ['-w', 'new', 'new-tab', '-d', str(project)]
    elif kind == 'wezterm': args += ['start', '--cwd', str(project)]
    elif kind == 'alacritty': args += ['--working-directory', str(project)]
    return args, str(project)


def launch_terminal(entry, project):
    args, project = terminal_command(entry, project)
    environment = os.environ.copy()
    if entry['kind'] == 'bash': environment['CHERE_INVOKING'] = '1'
    process = subprocess.Popen(args, cwd=project, env=environment,
                               creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
    return process


class TerminalPicker:
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        from .i18n import resolve_language, tr
        self.tk, self.messagebox = tk, messagebox
        config = settings()
        self.language = resolve_language(config.get('language', 'auto'))
        self.text = lambda key: tr(key, self.language)
        self.root = tk.Tk()
        self.root.title('AI Dev — ' + self.text('terminals'))
        self.root.geometry('760x510')
        self.root.minsize(600, 420)
        frame = ttk.Frame(self.root, padding=20); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=self.text('terminals'), font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=self.text('terminal_note'), wraplength=700).pack(anchor='w', pady=8)
        self.project = tk.StringVar(value=config.get('project', str(Path.home())))
        row = ttk.Frame(frame); row.pack(fill='x', pady=8)
        ttk.Label(row, text=self.text('project')).pack(side='left', padx=(0, 8))
        ttk.Entry(row, textvariable=self.project).pack(side='left', fill='x', expand=True)
        def browse():
            value = filedialog.askdirectory(parent=self.root, initialdir=self.project.get())
            if value: self.project.set(value)
        ttk.Button(row, text=self.text('browse'), command=browse).pack(side='left', padx=8)
        table = ttk.Frame(frame); table.pack(fill='both', expand=True)
        self.list = ttk.Treeview(table, columns=('name', 'path'), show='headings', selectmode='browse')
        self.list.heading('name', text=self.text('terminal_name')); self.list.heading('path', text=self.text('terminal_path'))
        self.list.column('name', width=220); self.list.column('path', width=430)
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.list.yview)
        scroll.pack(side='right', fill='y')
        self.list.configure(yscrollcommand=scroll.set)
        self.list.pack(side='left', fill='both', expand=True)
        self.list.bind('<Double-1>', lambda _: self.submit())
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status, wraplength=700).pack(anchor='w', pady=8)
        row = ttk.Frame(frame); row.pack(fill='x')
        self.refresh_button = ttk.Button(row, text=self.text('reload'), command=self.refresh)
        self.refresh_button.pack(side='left')
        def custom():
            value = filedialog.askopenfilename(parent=self.root, filetypes=[('Executable', '*.exe')])
            if value:
                config = settings()
                config['terminal_custom'] = list(dict.fromkeys([*config.get('terminal_custom', []), value]))
                save_settings(config)
                self.refresh()
        ttk.Button(row, text=self.text('terminal_add'), command=custom).pack(side='left', padx=8)
        self.open_button = ttk.Button(row, text=self.text('open'), command=self.submit)
        self.open_button.pack(side='right')
        self.entries = []
        self.results = queue.Queue()
        self.refresh()

    def refresh(self):
        if str(self.refresh_button['state']) == 'disabled': return
        self.refresh_button.configure(state='disabled'); self.open_button.configure(state='disabled')
        self.status.set(self.text('loading'))
        def worker():
            try: self.results.put(installed_terminals())
            except Exception as error: self.results.put(([], [str(error)]))
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, self.poll)

    def poll(self):
        try: self.entries, issues = self.results.get_nowait()
        except queue.Empty:
            self.root.after(80, self.poll)
            return
        self.list.delete(*self.list.get_children())
        last = settings().get('terminal_last')
        for index, entry in enumerate(self.entries):
            self.list.insert('', 'end', iid=str(index), values=(entry['label'], entry['executable']))
            if entry['id'] == last: self.list.selection_set(str(index))
        if self.entries and not self.list.selection(): self.list.selection_set('0')
        self.status.set('\n'.join(issues) if issues else self.text('terminal_count').format(count=len(self.entries)))
        self.refresh_button.configure(state='normal')
        self.open_button.configure(state='normal' if self.entries else 'disabled')

    def submit(self):
        selected = self.list.selection()
        if not selected or str(self.open_button['state']) == 'disabled': return
        try:
            entry = self.entries[int(selected[0])]
            launch_terminal(entry, self.project.get())
            config = settings(); config['terminal_last'] = entry['id']; save_settings(config)
            self.root.destroy()
        except Exception as error:
            self.messagebox.showerror(self.text('error'), str(error), parent=self.root)


def terminal_dialog():
    TerminalPicker().root.mainloop()
