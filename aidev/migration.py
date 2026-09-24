"""Explicit, repeatable copy migration. Keep the legacy directory as a backup."""
import os
from pathlib import Path
import shutil
from .storage import data_dir, read_json, save_json


def migrate_legacy():
    if os.environ.get('AI_DEV_DATA_DIR'):
        return {'status':'custom_directory'}
    target = data_dir().resolve()
    source = target.with_name('AI Dev')
    if not source.is_dir():
        return {'status':'no_legacy_data'}
    marker = target/'migration.json'
    if marker.exists():
        return read_json(marker)
    # Constrain both paths to sibling directories under the same app-data root.
    if source.resolve().parent != target.parent or source.is_symlink() or (hasattr(source,'is_junction') and source.is_junction()):
        raise ValueError('Unexpected legacy data location; migration stopped.')
    target.mkdir(parents=True, exist_ok=True)
    lock = target/'.migration-lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    copied = 0
    try:
        for path in source.rglob('*'):
            if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
                raise ValueError('Migration does not follow linked files or directories.')
            relative = path.relative_to(source)
            if relative.parts[0] == 'stream-deck' and relative.parts[1:2] != ('selections',):
                continue  # Generated shortcuts/archives must be rebuilt for the new path.
            destination = target/relative
            if not path.is_file() or destination.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == '.json' and (relative.name in ('settings.json','elgato-mcp.json') or relative.parts[0]=='missions'):
                value = read_json(path)
                def rewrite(item):
                    if isinstance(item, str) and (item == str(source) or item.startswith(str(source)+os.sep)):
                        return str(target)+item[len(str(source)):]
                    if isinstance(item, list):return [rewrite(v) for v in item]
                    if isinstance(item, dict):return {k:(v if k in ('objective','prompt') else rewrite(v)) for k,v in item.items()}
                    return item
                save_json(destination,rewrite(value))
            else:
                shutil.copy2(path,destination)
            copied += 1
        result = {'status':'copied','files':copied,'source':str(source),'target':str(target),'legacy_retained':True}
        save_json(marker,result)
        return result
    finally:
        os.close(descriptor)
        lock.unlink()
