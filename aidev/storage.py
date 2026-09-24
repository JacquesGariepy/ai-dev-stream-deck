"""Private runtime data is kept outside the source repository."""
import json
import os
from pathlib import Path
import tempfile


def data_dir():
    override = os.environ.get('AI_DEV_DATA_DIR')
    return Path(override) if override else Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'AI Dev'


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text('utf-8-sig'))
    except FileNotFoundError:
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if Path(temp).exists():
            Path(temp).unlink()


def settings():
    return read_json(data_dir() / 'settings.json', {})


def save_settings(value):
    save_json(data_dir() / 'settings.json', value)
