"""Human control surfaces backed by local receipts and canonical Factory status."""
from pathlib import Path
import queue
import subprocess
import sys
import threading
from tkinter import filedialog, ttk
import tkinter as tk
from . import factory
from .activity import receipts
from .storage import settings
from .runtime import now


class Operations:
    def background(self, work, done):
        results = queue.Queue()
        def run():
            try:
                results.put((True, work()))
            except Exception as error:
                results.put((False, error))
        threading.Thread(target=run, daemon=True).start()
        def poll():
            try:
                ok, result = results.get_nowait()
            except queue.Empty:
                self.root.after(100, poll)
                return
            done(ok, result)
        self.root.after(100, poll)

    def render_operations(self, activity, factory_frame):
        ttk.Label(activity, text=self.text('activity_note'), wraplength=740).pack(anchor='w', pady=8)
        self.session_warning=ttk.Label(activity,text='',wraplength=820,foreground='#9a4100')
        self.session_warning.pack(anchor='w')
        self.receipt_tree = ttk.Treeview(activity, columns=('tool', 'profile', 'state', 'created'), show='headings', height=6)
        for key, label in [('tool','harness'),('profile','profile'),('state','state'),('created','created')]:
            self.receipt_tree.heading(key, text=self.text(label))
            self.receipt_tree.column(key, width=150)
        self.receipt_tree.pack(fill='x')
        self.receipt_tree.bind('<<TreeviewSelect>>', lambda _: self.receipt_detail())
        self.receipt_details = tk.Text(activity, height=9, wrap='word', state='disabled')
        self.receipt_details.pack(fill='both', expand=True, pady=10)
        row = ttk.Frame(activity); row.pack(fill='x')
        ttk.Button(row, text=self.text('reload'), command=self.refresh_activity).pack(side='left')
        ttk.Button(row,text=self.text('logs'),command=self.show_logs).pack(side='left',padx=6)
        ttk.Button(row,text=self.text('receipt'),command=lambda:self.open_session_file('receipt_path')).pack(side='left')
        ttk.Button(row,text=self.text('session_context'),command=lambda:self.open_session_file('context')).pack(side='left',padx=6)
        ttk.Button(row,text=self.text('copy_handoff'),command=self.copy_handoff).pack(side='left')
        self.follow_button = ttk.Button(row, text=self.text('next_action'), command=self.follow_receipt, state='disabled')
        self.follow_button.pack(side='right')
        self.refresh_activity()
        ttk.Label(factory_frame, text=self.text('factory_note'), wraplength=740).pack(anchor='w', pady=10)
        self.factory_path = ttk.Label(factory_frame, text=settings().get('factory', {}).get('package', self.text('not_configured')), wraplength=740)
        self.factory_path.pack(anchor='w')
        row = ttk.Frame(factory_frame); row.pack(fill='x', pady=12)
        ttk.Button(row, text=self.text('factory_select'), command=self.select_factory).pack(side='left')
        self.factory_refresh = ttk.Button(row, text=self.text('reload'), command=self.refresh_factory)
        self.factory_refresh.pack(side='left', padx=8)
        self.factory_open = ttk.Button(row, text=self.text('factory_open'), command=self.open_factory)
        self.factory_open.pack(side='right')
        self.factory_details = tk.Text(factory_frame, height=14, wrap='word', state='disabled')
        self.factory_details.pack(fill='both', expand=True)
        self.set_text(self.factory_details, self.text('factory_load'))
        self.factory_generation = getattr(self, 'factory_generation', 0) + 1

    @staticmethod
    def set_text(widget, value):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.configure(state='disabled')

    def refresh_activity(self):
        selection = self.receipt_tree.selection()
        issues=[]
        self.receipt_rows = {row['id']:row for row in receipts(issues=issues)}
        self.session_warning.configure(text=self.text('session_read_error')+'\n'+'\n'.join(issues[:3]) if issues else '')
        self.receipt_tree.delete(*self.receipt_tree.get_children())
        for identifier, row in self.receipt_rows.items():
            state = row['observed_status']
            if state == 'exited' and row.get('exit_code') not in (None, 0):
                state = 'failed'
            if state not in ('prepared','running','exited','interrupted','launch_error','failed','unconfirmed'):
                state = 'unknown'
            self.receipt_tree.insert('', 'end', iid=identifier, values=(row.get('tool'), row.get('profile'), self.text(state), row.get('created')))
        if selection and selection[0] in self.receipt_rows:
            self.receipt_tree.selection_set(selection)
        elif self.receipt_rows:
            self.receipt_tree.selection_set(next(iter(self.receipt_rows)))
        else:
            self.set_text(self.receipt_details, self.text('no_sessions'))
            self.follow_button.configure(state='disabled')

    def receipt_detail(self):
        selected = self.receipt_tree.selection()
        row = self.receipt_rows.get(selected[0]) if selected else None
        if not row:
            self.follow_button.configure(state='disabled')
            return
        lines = [f"{self.text('project')}: {row.get('project')}",
                 f"{self.text('objective')}: {row.get('objective') or '—'}",
                 f"{self.text('exit_code')}: {row.get('exit_code', '—')}",
                 self.text('unverified'), self.text('unmeasured')]
        for key in ('created','started','ended'):
            if row.get(key):lines.append(f'{self.text(key)}: {row[key]}')
        if row.get('error'):
            lines.append(str(row['error']))
        terminal = row['observed_status'] in ('exited','interrupted','launch_error','unconfirmed')
        lines.append('\n' + self.text('next_verify' if terminal and row.get('exit_code') == 0 else 'next_diagnose' if terminal else 'next_prepared' if row['observed_status'] == 'prepared' else 'next_wait'))
        self.set_text(self.receipt_details, '\n'.join(lines))
        self.follow_button.configure(state='normal' if terminal and row.get('project') else 'disabled')

    def selected_receipt(self):
        selection=self.receipt_tree.selection()
        return self.receipt_rows.get(selection[0]) if selection else None

    def open_session_file(self, key):
        import os
        row=self.selected_receipt()
        if not row:return
        try:
            path=Path(row.get(key) or '')
            if not path.is_file():raise FileNotFoundError(self.text('artifact_missing'))
            # Open JSON as text, never execute an arbitrary path recorded in a receipt.
            if path.suffix.lower()!='.json':raise ValueError(self.text('artifact_missing'))
            subprocess.Popen([str(Path(os.environ.get('WINDIR','C:/Windows'))/'System32/notepad.exe'),str(path)])
        except Exception as error:self.error(error)

    def copy_handoff(self):
        row=self.selected_receipt()
        if not row:return
        text=(f"Use English. Inspect actual evidence before continuing.\nProject: {row.get('project','unknown')}\n"
              f"Harness/profile: {row.get('tool','unknown')} / {row.get('profile','unknown')}\n"
              f"Original objective: {row.get('objective') or 'No objective recorded'}\n"
              f"Observed process state: {row.get('observed_status','unknown')}\nExit code: {row.get('exit_code','unknown')}\n"
              f"Receipt: {row.get('receipt_path','unknown')}\nContext: {row.get('context','unknown')}\n"
              "Objective completion is unverified. Provider tokens and cost are unmeasured. Check the snapshot timestamp and current repository state.")
        self.root.clipboard_clear();self.root.clipboard_append(text)
        self.session_warning.configure(text=self.text('handoff_copied'))

    def follow_receipt(self):
        selection = self.receipt_tree.selection()
        if not selection:
            return
        row = self.receipt_rows[selection[0]]
        if not self.catalog['entries']:
            from .discovery import discover
            self.follow_button.configure(state='disabled')
            def detected(ok,result):
                self.follow_button.configure(state='normal')
                if not ok:self.error(result);return
                self.catalog=result
                self.tool_box['values']=sorted({entry['tool'] for entry in result['entries']})
                if not self.catalog['entries']:
                    self.error(ValueError(self.text('none')));return
                self.follow_receipt()
            self.background(discover,detected)
            return
        self.project.set(row['project'])
        self.tool.set(row['tool'])
        self.update_profiles()
        matching = next((label for label, entry in self.profile_rows.items() if entry['command'] == row.get('command')), '')
        self.profile.set(matching)
        self.update_status()
        success_exit = row.get('exit_code') == 0
        self.workflow = 'review' if success_exit else 'debug'
        self.flow_box.set(self.text(self.workflow))
        objective = ('Verify the previous session result against the original objective. Inspect actual changes and run relevant checks. Do not assume success from its exit code.' if success_exit else
                     'Diagnose the unconfirmed, interrupted or failed previous session using available local evidence. Propose the next safe action before changing files.')
        objective += '\nOriginal objective: ' + str(row.get('objective') or '')
        self.objective.delete('1.0', 'end'); self.objective.insert('1.0', objective)
        self.english.set(False)
        self.notebook.select(self.mission_frame)

    def select_factory(self):
        selected = filedialog.askdirectory(parent=self.root)
        if selected:
            try:
                self.factory_path.configure(text=str(factory.configure(selected)))
                self.refresh_factory()
            except Exception as error:
                self.error(error)

    def refresh_factory(self):
        generation = self.factory_generation
        self.factory_refresh.configure(state='disabled')
        self.set_text(self.factory_details, self.text('loading'))
        def completed(ok, result):
            if generation != self.factory_generation:
                return
            self.factory_refresh.configure(state='normal')
            if not ok:
                self.set_text(self.factory_details, self.text('unavailable') + '\n' + str(result))
                return
            decisions = result.get('decisions_pending', [])
            tasks = result.get('tasks', {})
            lines = [str(result.get('project', {}).get('name', 'Factory')), now(), self.text('tasks')]
            lines.extend(f"  {self.text('task_ready' if key == 'ready' else key) if key in ('blocked','captured','closed','executing','ready','review','verification') else key}: {value}" for key,value in tasks.items())
            attempts = result.get('executing_attempts', [])
            lines.extend(['', f"{self.text('active_attempts')}: {len(attempts) if isinstance(attempts,list) else attempts}", '', self.text('decisions')])
            for decision in decisions:
                key = decision.get('kind')
                summary = self.text('budget_pending') if key == 'budget' else self.text('registration_pending') if key == 'registration' else decision.get('summary', str(decision))
                lines.append('• ' + summary)
            lines.extend(['', self.text('factory_next_blocked' if any(d.get('blocks') == 'run' for d in decisions) else 'factory_next')])
            self.set_text(self.factory_details, '\n'.join(lines))
        self.background(factory.brief, completed)

    def open_factory(self):
        self.factory_open.configure(state='disabled')
        def completed(ok, result):
            self.factory_open.configure(state='normal')
            if ok:
                subprocess.Popen([sys.executable, str(Path(__file__).resolve().parent.parent/'launch.py'), '--action', 'web', '--url', result])
            else:
                self.error(result)
        self.background(factory.ensure_workbench, completed)

    def deck_language(self):
        def generate():
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent.parent/'scripts/stream_deck.py'), '--language', self.language, '--import-profile'], check=True)
        self.background(generate, lambda ok, result: None if ok else self.error(result))
