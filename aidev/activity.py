"""Receipt observations, not invented agent progress or successful outcomes."""
import os
from datetime import datetime
from .storage import data_dir, read_json


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        api.OpenProcess.restype = wintypes.HANDLE
        api.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        api.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = api.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = wintypes.DWORD()
            return code.value == 259 if api.GetExitCodeProcess(handle, ctypes.byref(code)) else None
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


def receipts(limit=50, issues=None):
    issues = issues if issues is not None else []
    directory = data_dir()/'missions'
    paths = []
    try:
        candidates = list(directory.iterdir())
    except FileNotFoundError:
        return []
    except OSError as error:
        issues.append(str(error))
        return []
    for path in candidates:
        if path.suffix != '.json' or path.name.endswith('.launch.json'):
            continue
        try:paths.append((path.stat().st_mtime,path))
        except OSError as error:issues.append(f'{path.name}: {error}')
    paths.sort(key=lambda item:item[0],reverse=True)
    rows = []
    for _, path in paths:
        try:
            row = read_json(path)
            if not isinstance(row, dict) or not isinstance(row.get('id'),str) or not row['id']:
                issues.append(f'{path.name}: invalid session receipt')
                continue
        except (ValueError, OSError) as error:
            issues.append(f'{path.name}: {error}')
            continue
        row['receipt_path'] = str(path)
        row['observed_status'] = row.get('status', 'unknown')
        if row['observed_status'] == 'running' and process_alive(row.get('runner_pid')) is False:
            row['observed_status'] = 'interrupted'
        if row['observed_status'] == 'prepared':
            try:
                created = datetime.fromisoformat(row['created'])
                if (datetime.now().astimezone() - created).total_seconds() > 30:
                    row['observed_status'] = 'unconfirmed'
            except (ValueError, KeyError, TypeError):
                pass
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows
