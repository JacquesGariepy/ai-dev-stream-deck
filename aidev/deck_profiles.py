"""Exact profile selections for locally generated Stream Deck shortcuts."""
import hashlib
import json
import re
from .storage import data_dir, read_json, save_json


def identity(entry):
    return {key: entry[key] for key in ('tool', 'profile', 'command')}


def selection_id(entry):
    payload = json.dumps(identity(entry), ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def save_selections(entries):
    selections = []
    for entry in entries:
        identifier = selection_id(entry)
        save_json(data_dir()/'stream-deck/selections'/f'{identifier}.json', identity(entry))
        selections.append({'id': identifier})
    manifest = data_dir()/'stream-deck/profile-shortcuts.json'
    save_json(manifest, selections)
    return manifest


def load_selection(identifier):
    if not re.fullmatch(r'[a-f0-9]{64}', identifier):
        raise ValueError('Invalid Stream Deck profile identifier.')
    value = read_json(data_dir()/'stream-deck/selections'/f'{identifier}.json')
    if not isinstance(value, dict) or any(not isinstance(value.get(key), str) or not value[key] for key in ('tool','profile','command')):
        raise ValueError('This profile shortcut is no longer configured. Refresh the Stream Deck profiles.')
    return identity(value)
