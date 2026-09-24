"""Small bilingual Windows launcher. Discovery never starts an AI session."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .agents import MISSION_ADAPTERS, WORKFLOWS
from .discovery import discover, find_entry
from .i18n import resolve_language, tr, windows_locale
from .runtime import capture_context, open_sessions, prepare, spawn_terminal
from .storage import save_settings, settings
from .operations import Operations
from .engineering import EngineeringUI


class Panel(Operations, EngineeringUI):
    def __init__(self, initial_tool=None, initial_tab='mission', initial_selection=None):
        self.preferences = settings()
        self.preference = self.preferences.get('language', 'auto')
        self.language = resolve_language(self.preference)
        self.catalog_error = None
        self.catalog = {'entries':[]}
        self.initial_selection = initial_selection
        self.discovery_attempted = False
        if initial_selection: initial_tool = initial_selection['tool']
        self.root = tk.Tk()
        self.root.bind('<Destroy>', self.cancel_callbacks, add='+')
        self.root.report_callback_exception = lambda kind, value, trace: self.error(value.with_traceback(trace))
        self.root.geometry('980x800')
        self.root.minsize(920, 760)
        self.project = tk.StringVar(value=self.preferences.get('project', str(Path.home())))
        self.tool = tk.StringVar(value=initial_tool or self.preferences.get('last_tool', 'codex'))
        self.profile = tk.StringVar()
        self.workflow = 'implement'
        self.objective_value = ''
        self.render()
        self.notebook.select({'mission':self.mission_frame, 'activity':self.activity_frame, 'factory':self.factory_frame,'engineering':self.engineering_frame}[initial_tab])
        if initial_tab == 'factory':
            self.refresh_factory()
        elif initial_tab == 'mission':
            self.refresh()
        self.root.after(4000, self.tick)

    def tick(self):
        try:self.refresh_activity()
        finally:self.root.after(4000, self.tick)

    def cancel_callbacks(self, event):
        if event.widget is not self.root:return
        for identifier in self.root.tk.call('after', 'info'):
            try:self.root.after_cancel(identifier)
            except tk.TclError:pass

    def text(self, key):
        return tr(key, self.language)

    def render(self):
        if hasattr(self, 'objective'):
            self.objective_value = self.objective.get('1.0', 'end').strip()
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.text('title'))
        if self.initial_selection:
            self.root.title(self.text('title')+' — '+self.initial_selection['tool']+' / '+self.initial_selection['profile'])
        frame = ttk.Frame(self.root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=self.text('heading'), font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        top = ttk.Frame(frame); top.pack(fill='x', pady=12)
        ttk.Label(top, text=self.text('language')).pack(side='left')
        language = ttk.Combobox(top, state='readonly', values=['Auto', 'Français', 'English'], width=15)
        language.set({'auto': 'Auto', 'fr': 'Français', 'en': 'English'}[self.preference])
        language.pack(side='left', padx=8)
        def change_language(_):
            self.preference = {'Auto': 'auto', 'Français': 'fr', 'English': 'en'}[language.get()]
            self.language = resolve_language(self.preference)
            self.preferences['language'] = self.preference
            latest = settings()
            latest['language'] = self.preference
            save_settings(latest)
            self.render()
        language.bind('<<ComboboxSelected>>', change_language)
        ttk.Label(top, text=windows_locale()).pack(side='left')
        ttk.Button(top, text=self.text('refresh'), command=self.refresh).pack(side='right')
        ttk.Button(top, text=self.text('browsers'), command=self.browsers).pack(side='right', padx=8)
        deck = ttk.Frame(frame); deck.pack(fill='x', pady=(0,8))
        ttk.Button(deck, text=self.text('deck_language'), command=self.deck_language).pack(side='left')
        ttk.Label(deck, text=self.text('deck_note')).pack(side='left', padx=10)
        self.notebook = ttk.Notebook(frame); self.notebook.pack(fill='both', expand=True)
        self.mission_frame = ttk.Frame(self.notebook, padding=12)
        self.activity_frame = ttk.Frame(self.notebook, padding=12)
        self.factory_frame = ttk.Frame(self.notebook, padding=12)
        self.engineering_frame = ttk.Frame(self.notebook, padding=12)
        for tab, key in ((self.mission_frame,'mission_tab'),(self.activity_frame,'activity_tab'),(self.factory_frame,'factory_tab'),(self.engineering_frame,'engineering_tab')):
            self.notebook.add(tab, text=self.text(key))
        self.render_operations(self.activity_frame, self.factory_frame)
        self.render_engineering(self.engineering_frame)
        frame = self.mission_frame
        ttk.Label(frame, text=self.text('project')).pack(anchor='w')
        project_row = ttk.Frame(frame); project_row.pack(fill='x', pady=(4, 15))
        ttk.Entry(project_row, textvariable=self.project).pack(side='left', fill='x', expand=True)
        ttk.Button(project_row, text=self.text('browse'), command=self.browse).pack(side='right', padx=(8, 0))
        choices = ttk.Frame(frame); choices.pack(fill='x')
        tools = sorted({entry['tool'] for entry in self.catalog['entries']})
        if tools and self.tool.get() not in tools:
            self.tool.set(tools[0] if tools else '')
        columns = [(self.text('harness'), self.tool), (self.text('profile'), self.profile)]
        boxes = []
        for title, variable in columns:
            column = ttk.Frame(choices); column.pack(side='left', fill='x', expand=True, padx=(0, 12))
            ttk.Label(column, text=title).pack(anchor='w')
            box = ttk.Combobox(column, state='readonly', textvariable=variable, width=23)
            box.pack(fill='x', pady=4); boxes.append(box)
        self.tool_box, self.profile_box = boxes
        self.tool_box['values'] = tools
        def manual_selection(_):
            self.initial_selection = None
            self.catalog_error = None
            self.update_profiles()
        self.tool_box.bind('<<ComboboxSelected>>', manual_selection)
        self.profile_box.bind('<<ComboboxSelected>>', manual_selection)
        flow_column = ttk.Frame(choices); flow_column.pack(side='left')
        ttk.Label(flow_column, text=self.text('workflow')).pack(anchor='w')
        self.flow_box = ttk.Combobox(flow_column, state='readonly', values=[self.text(key) for key in WORKFLOWS], width=19)
        self.flow_box.set(self.text(self.workflow)); self.flow_box.pack(pady=4)
        self.flow_box.bind('<<ComboboxSelected>>', lambda _: setattr(self, 'workflow', list(WORKFLOWS)[self.flow_box.current()]))
        self.status = ttk.Label(frame, wraplength=795)
        self.status.pack(anchor='w', pady=(8, 10))
        ttk.Label(frame, text=self.text('objective')).pack(anchor='w')
        self.objective = tk.Text(frame, height=9, wrap='word', font=('Segoe UI', 11))
        self.objective.pack(fill='both', expand=True, pady=6)
        self.objective.insert('1.0', self.objective_value)
        self.english = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, variable=self.english, text=self.text('english_confirm')).pack(anchor='w', pady=5)
        ttk.Label(frame, text=self.text('note'), wraplength=795).pack(anchor='w', pady=10)
        bottom = ttk.Frame(frame); bottom.pack(fill='x', pady=6)
        ttk.Button(bottom, text=self.text('sessions'), command=lambda: self.notebook.select(self.activity_frame)).pack(side='left')
        ttk.Button(bottom, text=self.text('context'), command=self.context).pack(side='left', padx=8)
        self.open_button = ttk.Button(bottom, text=self.text('open'), command=lambda: self.submit(False))
        self.open_button.pack(side='right')
        self.launch_button = ttk.Button(bottom, text=self.text('launch'), command=lambda: self.submit(True))
        self.launch_button.pack(side='right', padx=8)
        self.update_profiles()
        self.notebook.bind('<<NotebookTabChanged>>',self.tab_changed)

    def tab_changed(self, _):
        if self.notebook.select()==str(self.mission_frame) and not self.discovery_attempted and not getattr(self,'detecting',False):
            self.refresh()

    def rows(self):
        return [row for row in self.catalog['entries'] if row['tool'] == self.tool.get()]

    def update_profiles(self):
        self.profile_rows = {}
        for row in self.rows():
            label = self.text('default') if row['kind'] == 'application' else row['command']
            self.profile_rows[label] = row
        self.profile_box['values'] = list(self.profile_rows)
        old = self.profile.get()
        remembered = self.preferences.get('profiles', {}).get(self.tool.get())
        matching = next((label for label, row in self.profile_rows.items() if row['command'] == remembered), '')
        self.profile.set(old if old in self.profile_rows else matching)
        self.update_status()

    def update_status(self):
        row = self.profile_rows.get(self.profile.get())
        key = 'select' if self.catalog['entries'] else 'none'
        if row:
            key = 'missing' if not row['available'] else ('uninitialized' if row['initialized'] is False else 'ready')
        value = self.text(key)
        if getattr(self,'detecting',False): value = self.text('detecting_profiles')
        if self.catalog_error:value += '\n'+self.catalog_error
        adapter = self.tool.get() in MISSION_ADAPTERS
        if not adapter and self.tool.get():
            value += '\n' + self.text('unknown_adapter')
        self.status.configure(text=value)
        ready = row and row['available'] and not getattr(self,'detecting',False) and not self.catalog_error
        self.launch_button.configure(state='normal' if ready and adapter else 'disabled')
        self.open_button.configure(state='normal' if ready else 'disabled')
        for box in (self.tool_box, self.profile_box):
            box.configure(state='disabled' if getattr(self,'detecting',False) else 'readonly')

    def refresh(self):
        if getattr(self,'detecting',False):return
        self.detecting=True
        self.discovery_attempted=True
        self.update_status()
        def completed(ok,result):
            self.detecting=False
            if ok:
                self.catalog=result
                self.catalog_error=None
                tab=self.notebook.index(self.notebook.select())
                self.render()
                if self.initial_selection:
                    wanted=self.initial_selection
                    row=find_entry(self.catalog,wanted['tool'],wanted['profile'],wanted['command'])
                    self.tool.set(wanted['tool'])
                    self.update_profiles()
                    self.profile.set(next((label for label, entry in self.profile_rows.items() if entry == row), ''))
                    if row is None:self.catalog_error=self.text('profile_removed')
                    self.update_status()
                self.notebook.select(tab)
            else:
                self.catalog_error=str(result)
                self.update_status()
                self.error(result)
        self.background(discover,completed)

    def browsers(self):
        import subprocess
        import sys
        subprocess.Popen([sys.executable, str(Path(__file__).resolve().parent.parent/'launch.py'), '--action','browser'])

    def browse(self):
        selected = filedialog.askdirectory(initialdir=self.project.get(), parent=self.root)
        if selected:
            self.project.set(selected)

    def context(self):
        try:
            capture_context(self.project.get())
            messagebox.showinfo(self.text('title'), self.text('saved_context'), parent=self.root)
        except Exception as error:
            self.error(error)

    def submit(self, with_objective):
        try:
            if getattr(self,'detecting',False) or self.catalog_error:
                raise ValueError(self.catalog_error or self.text('detecting_profiles'))
            row = self.profile_rows.get(self.profile.get())
            if not row or not row['available']:
                raise ValueError(self.text('select'))
            objective = self.objective.get('1.0', 'end').strip() if with_objective else ''
            if with_objective and (not objective or not self.english.get()):
                raise ValueError(self.text('english_required'))
            path = prepare(row, self.project.get(), self.workflow, objective, self.english.get())
            spawn_terminal(path)
            self.preferences.update(project=self.project.get(), last_tool=self.tool.get())
            self.preferences.setdefault('profiles', {})[self.tool.get()] = row['command']
            latest = settings()
            latest.update({key:self.preferences[key] for key in ('project','last_tool','profiles')})
            save_settings(latest)
            self.refresh_activity()
            self.notebook.select(self.activity_frame)
        except Exception as error:
            self.error(error)

    def error(self, error):
        from .errors import report
        report(error,parent=self.root)

    def run(self):
        self.root.mainloop()
