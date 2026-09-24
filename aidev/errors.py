"""Visible startup/callback failures with private, bounded local logs."""
from datetime import datetime
from pathlib import Path
import traceback
from .storage import data_dir


def record(error):
    path = data_dir()/'logs/aidev.log'
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and path.stat().st_size > 1_000_000:
            path.replace(path.with_suffix('.previous.log'))
        with path.open('a',encoding='utf-8') as stream:
            stream.write('\n'+datetime.now().astimezone().isoformat()+'\n')
            stream.write(''.join(traceback.format_exception(type(error),error,error.__traceback__)))
        return path
    except OSError:
        return None


def report(error, parent=None):
    from tkinter import Tk, messagebox
    path = record(error)
    root = parent or Tk()
    if parent is None:root.withdraw()
    try:
        messagebox.showerror('AI Dev',str(error)+('\n\nLog / Journal : '+str(path) if path else ''),parent=root)
    finally:
        if parent is None:root.destroy()


def run(main):
    try:
        main()
    except Exception as error:
        report(error)
