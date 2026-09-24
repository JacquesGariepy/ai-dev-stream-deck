"""Explicit Windows convenience actions; no shell command evaluation."""
import os
from pathlib import Path
import subprocess

URIS={'display':'ms-settings:display','sound':'ms-settings:sound','network':'ms-settings:network-status',
      'bluetooth':'ms-settings:bluetooth','storage':'ms-settings:storagesense','apps':'ms-settings:appsfeatures'}
FOLDERS={'downloads':'shell:Downloads','documents':'shell:Personal','pictures':'shell:My Pictures','recycle-bin':'shell:RecycleBinFolder'}
EXECUTABLES={'calculator':'calc.exe','notepad':'notepad.exe','event-viewer':'eventvwr.exe','services':'services.msc'}


def open_windows_action(name):
    system=Path(os.environ.get('WINDIR','C:/Windows'))/'System32'
    if name in URIS:os.startfile(URIS[name])
    elif name in FOLDERS:subprocess.Popen([str(system/'explorer.exe') if (system/'explorer.exe').exists() else str(system.parent/'explorer.exe'),FOLDERS[name]])
    elif name in EXECUTABLES:
        executable=system/EXECUTABLES[name]
        if executable.suffix=='.msc':subprocess.Popen([str(system/'mmc.exe'),str(executable)])
        else:subprocess.Popen([str(executable)])
    else:raise ValueError('Unknown Windows action.')
