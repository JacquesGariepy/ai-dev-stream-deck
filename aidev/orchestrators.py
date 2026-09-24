"""Optional external orchestration; never bundle or install an orchestrator."""
import json
import os
from pathlib import Path
import subprocess
from .storage import settings, save_settings


def selected():
    config = settings()
    if 'orchestrator' in config:
        return config['orchestrator']
    # Preserve explicit legacy configuration, without guessing from a project folder.
    package = config.get('factory', {}).get('package') or os.environ.get('AI_DEV_FACTORY')
    return {'kind': 'factory', 'name': 'Factory', 'package': package} if package else {'kind': 'none', 'name': ''}


def configure(value):
    kind = value.get('kind')
    if kind == 'none':
        result = {'kind': 'none', 'name': ''}
    elif kind == 'factory':
        from .factory import installation
        if not value.get('package'): raise ValueError('Choose the external Factory folder.')
        result = {'kind': kind, 'name': 'Factory', 'package': str(installation(value['package']))}
    elif kind == 'custom':
        name = str(value.get('name', '')).strip()
        if not name: raise ValueError('Enter the orchestrator name.')
        result = {'kind': kind, 'name': name, 'url': str(value.get('url', '')).strip()}
        executable = str(value.get('executable', '')).strip()
        if bool(executable) == bool(result['url']):
            raise ValueError('Choose either an executable or a dashboard URL.')
        if result['url']:
            from .browsers import validate_url
            validate_url(result['url'])
        else:
            executable = Path(executable).expanduser().resolve(strict=True)
            if not executable.is_file() or (os.name == 'nt' and executable.suffix.lower() != '.exe'):
                raise ValueError('Choose an executable (.exe on Windows). For scripts, choose their interpreter.')
            directory = Path(value.get('directory') or executable.parent).expanduser().resolve(strict=True)
            if not directory.is_dir(): raise ValueError('Choose an existing working directory.')
            args = value.get('arguments', [])
            if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                raise ValueError('Arguments must be a JSON array of strings.')
            result.update(executable=str(executable), directory=str(directory), arguments=args)
    else:
        raise ValueError('Unknown orchestrator kind.')
    config = settings()
    config['orchestrator'] = result
    if kind == 'factory': config.setdefault('factory', {})['package'] = result['package']
    save_settings(config)
    return result


def open_selected():
    value = selected()
    if value['kind'] == 'none': raise ValueError('Choose an external orchestrator first.')
    if value['kind'] == 'factory':
        from .factory import ensure_workbench
        return ensure_workbench()
    if value.get('url'): return value['url']
    executable = Path(value['executable'])
    if not executable.is_file(): raise FileNotFoundError(executable)
    subprocess.Popen([str(executable), *value.get('arguments', [])], cwd=value['directory'],
                     creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
    return None


def choose(parent, language, on_save):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from .i18n import tr
    text = lambda key: tr(key, language)
    value = selected()
    dialog = tk.Toplevel(parent); dialog.title(text('factory_select'))
    dialog.geometry('740x530'); dialog.transient(parent)
    frame = ttk.Frame(dialog, padding=18); frame.pack(fill='both', expand=True)
    ttk.Label(frame, text=text('orchestrator_choice_note'), wraplength=680).grid(row=0, column=0, columnspan=3, sticky='w', pady=8)
    kinds = {'none': text('orchestrator_none'), 'factory': text('orchestrator_factory'), 'custom': text('orchestrator_custom')}
    kind = tk.StringVar(value=kinds[value['kind']])
    ttk.Combobox(frame, textvariable=kind, values=list(kinds.values()), state='readonly').grid(row=1, column=0, columnspan=3, sticky='ew', pady=8)
    variables, rows = {}, {}
    for row, (key, label) in enumerate((('name','orchestrator_name'), ('package','orchestrator_package'),
                                       ('url','orchestrator_url'), ('executable','orchestrator_executable'),
                                       ('arguments','orchestrator_arguments'), ('directory','project')), 2):
        ttk.Label(frame, text=text(label)).grid(row=row, column=0, sticky='w', pady=7)
        initial = json.dumps(value.get(key, []), ensure_ascii=False) if key == 'arguments' else value.get(key, '')
        variables[key] = tk.StringVar(value=initial)
        ttk.Entry(frame, textvariable=variables[key]).grid(row=row, column=1, sticky='ew', padx=8)
        if key in ('package', 'directory', 'executable'):
            def browse(field=key):
                path = (filedialog.askopenfilename(parent=dialog, filetypes=[('Executable','*.exe')]) if field == 'executable'
                        else filedialog.askdirectory(parent=dialog))
                if path: variables[field].set(path)
            ttk.Button(frame, text=text('browse'), command=browse).grid(row=row, column=2)
        rows[key] = frame.grid_slaves(row=row)
    frame.columnconfigure(1, weight=1)
    ttk.Label(frame, text=text('orchestrator_args_note'), wraplength=680).grid(row=8, column=0, columnspan=3, sticky='w', pady=12)
    def update_fields(*_):
        selection = next(key for key, label in kinds.items() if label == kind.get())
        visible = {'package'} if selection == 'factory' else set(variables)-{'package'} if selection == 'custom' else set()
        for key, widgets in rows.items():
            for widget in widgets:
                widget.grid() if key in visible else widget.grid_remove()
    kind.trace_add('write', update_fields)
    update_fields()
    def save():
        try:
            selection = next(key for key, label in kinds.items() if label == kind.get())
            payload = {key: var.get() for key, var in variables.items()}
            payload['kind'] = selection
            if selection == 'custom' and not payload['url'].strip(): payload['arguments'] = json.loads(payload['arguments'])
            configure(payload)
            dialog.destroy(); on_save()
        except Exception as error: messagebox.showerror(text('error'), str(error), parent=dialog)
    ttk.Button(frame, text=text('save'), command=save).grid(row=9, column=2, sticky='e')
