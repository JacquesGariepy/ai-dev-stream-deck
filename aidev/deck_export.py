"""Turn a declarative deck into an importable .streamDeckProfile and audit it."""
import json
import re
from pathlib import Path
import uuid
import zipfile
from .deck_icons import icon_png
from .deck_layout import Grid, Key, MODELS

ACTION_UUID = {'open': 'system.open', 'folder': 'profile.openchild', 'back': 'profile.backtoparent',
               'hotkey': 'system.hotkey', 'text': 'system.text', 'website': 'system.website'}
SUPPORTED = {'com.elgato.streamdeck.' + value for value in ACTION_UUID.values()}
MAX_DEPTH = 8


def _hotkey_settings(spec):
    ctrl, shift, alt, win = (bool(spec.get(name)) for name in ('ctrl', 'shift', 'alt', 'win'))
    actual = {'KeyCmd': win, 'KeyCtrl': ctrl, 'KeyShift': shift, 'KeyOption': alt,
              'KeyModifiers': 2 * ctrl + shift + 4 * alt + 8 * win,
              'NativeCode': spec['key'], 'QTKeyCode': spec['qt'], 'VKeyCode': spec['key']}
    blank = {'KeyCmd': False, 'KeyCtrl': False, 'KeyShift': False, 'KeyOption': False, 'KeyModifiers': 0,
             'NativeCode': 146, 'QTKeyCode': 33554431, 'VKeyCode': -1}
    return {'Coalesce': True, 'Hotkeys': [actual, blank, blank, blank]}


class _Expander:
    """Expand pages into a native folder tree: one parent per folder, pagination by grid."""

    def __init__(self, deck, grid, language):
        self.deck, self.grid, self.language = deck, grid, language
        self.instances = []   # (uuid, name, [Key|None ...] with folder targets resolved to uuids)

    def back(self):
        return Key('BACK' if self.language != 'fr' else 'RETOUR', 'back', 'nav', 'back')

    def more(self, target):
        return Key('MORE' if self.language != 'fr' else 'SUITE', 'folder', 'nav', 'more', target)

    def expand(self, page_id, stack=()):
        if page_id in stack or len(stack) > MAX_DEPTH:
            raise ValueError('Folder cycle or excessive depth at page: ' + page_id)
        page = self.deck.pages[page_id]
        capacity = self.grid.capacity
        nav = [] if not stack else [self.back()]
        keys = list(page.keys)
        while keys and keys[-1] is None:
            keys.pop()
        if len(nav) + len(page.header) + len(keys) <= capacity:
            chunks = [(nav, keys)]
        else:
            # Every page after the first is a child of the previous one, so it gets BACK too.
            content, chunks = [key for key in keys if key is not None], []
            while content:
                lead = nav if not chunks else [self.back()]
                room = capacity - len(lead) - len(page.header)
                if room < 2:
                    raise ValueError('Grid too small for page: ' + page_id)
                take = content if len(content) <= room else content[:room - 1]
                chunks.append((lead, take))
                content = content[len(take):]
        identifiers = [str(uuid.uuid4()) for _ in chunks]
        for index, (identifier, (lead, chunk)) in enumerate(zip(identifiers, chunks)):
            name = page.name if index == 0 else page.name + '-' + str(index)
            slots = [*lead, *page.header, *chunk]
            if index + 1 < len(chunks):
                slots += [None] * (capacity - 1 - len(slots))
                slots.append(self.more(identifiers[index + 1]))
            resolved = []
            for key in slots:
                if key is not None and key.kind == 'folder' and key.target in self.deck.pages:
                    target = self.deck.pages[key.target]
                    if not any(target.keys) and not target.header:
                        resolved.append(None)   # nothing detected for this folder on this workstation
                        continue
                    # A fresh instance per reference keeps the native tree single-parent.
                    child = self.expand(key.target, (*stack, page_id))
                    key = Key(key.title, 'folder', key.zone, key.icon, child, key.description, key.name, key.warn)
                resolved.append(key)
            self.instances.append((identifier, name, resolved))
        return identifiers[0]


def _action(key, links):
    kind = key.kind
    if kind == 'open':
        folder = str(links).rstrip('\\/')
        separator = '\\' if '\\' in folder or re.match(r'^[A-Za-z]:', folder) else '/'
        settings = {'path': '"' + folder + separator + key.target + '.lnk"'}
    elif kind == 'folder':
        settings = {'ProfileUUID': key.target}
    elif kind == 'hotkey':
        settings = _hotkey_settings(key.target)
    elif kind == 'text':
        settings = {'isSendingEnter': False, 'pastedText': key.target}
    elif kind == 'website':
        settings = {'openInBrowser': True, 'path': key.target}
    else:
        settings = {}
    return {'ActionID': str(uuid.uuid4()), 'Name': key.name, 'UUID': 'com.elgato.streamdeck.' + ACTION_UUID[kind],
            'LinkedTitle': True, 'Settings': settings, 'State': 0, 'UserInput': key.description,
            'States': [{'Title': key.title, 'ShowTitle': True, 'TitleAlignment': 'bottom',
                        'TitleColor': '#ffbd66' if key.warn else '#ffffff', 'FontSize': 9}]}


def write_profile(deck, output, device, links, grid=None):
    grid = grid or Grid.for_device(device)
    expander = _Expander(deck, grid, deck.language)
    home = expander.expand('home')
    pinned = str(uuid.uuid4())
    prefix = str(uuid.uuid4()).upper() + '.sdProfile'
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        def write(path, data):
            archive.writestr(prefix + '/' + path, json.dumps(data, ensure_ascii=False))
        write('manifest.json', {'Name': getattr(deck, 'profile_name', 'AI Dev ' + deck.language.upper()), 'Version': '3.0', 'Device': device,
                                'Pages': {'Current': home, 'Default': pinned, 'Pages': [home]}})
        for identifier, name, slots in expander.instances:
            folder = 'Profiles/' + identifier.upper()
            actions, images = {}, {}
            for index, key in enumerate(slots):
                if key is None:
                    continue
                action = _action(key, links)
                filename = key.icon + '-' + key.zone + '.png'
                action['States'][0]['Image'] = 'Images/' + filename
                images[filename] = icon_png(key.icon, key.zone)
                actions[f'{index % grid.cols},{index // grid.cols}'] = action
            write(folder + '/manifest.json', {'Name': name, 'Icon': '', 'Controllers': [{'Type': 'Keypad', 'Actions': actions}]})
            for filename, content in images.items():
                archive.writestr(prefix + '/' + folder + '/Images/' + filename, content)
        write('Profiles/' + pinned.upper() + '/manifest.json', {'Name': '', 'Icon': '', 'Controllers': [{'Type': 'Keypad', 'Actions': None}]})
    audit_profile(output, grid=grid)
    return output


def audit_profile(path, shortcuts=None, grid=None):
    """Inspect every generated key without executing it."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        manifests = [name for name in names if name.endswith('/manifest.json')]
        roots = [name for name in manifests if '/Profiles/' not in name]
        if len(roots) != 1:
            raise ValueError('Profile archive must contain one root manifest.')
        root = json.loads(archive.read(roots[0]))
        if grid is None:
            grid = Grid.for_device(root.get('Device'))
        pages = {name.rsplit('/', 2)[1].upper(): (name, json.loads(archive.read(name)))
                 for name in manifests if '/Profiles/' in name}
        current = root['Pages']['Current'].upper(); default = root['Pages']['Default'].upper()
        if current not in pages or default not in pages:
            raise ValueError('Profile root refers to a missing page.')
        visited, action_ids, folder_targets = set(), set(), []
        counts = {'pages': 0, 'buttons': 0, 'open': 0, 'folders': 0, 'hotkeys': 0, 'text': 0, 'back': 0}

        def inspect_page(identifier, depth):
            if identifier in visited:
                return
            visited.add(identifier)
            name, page = pages[identifier]
            counts['pages'] += 1
            layout = {}
            for controller in page.get('Controllers', []):
                layout.update(controller.get('Actions') or {})
            if len(layout) > grid.capacity:
                raise ValueError('A page exceeds the %dx%d layout: %s' % (grid.cols, grid.rows, page.get('Name', '')))
            for position, button in layout.items():
                col, row = (int(value) for value in position.split(','))
                if not (0 <= col < grid.cols and 0 <= row < grid.rows):
                    raise ValueError('A key is outside the device grid: ' + position)
                counts['buttons'] += 1
                if button.get('UUID') not in SUPPORTED:
                    raise ValueError('Unsupported key action: ' + str(button.get('UUID')))
                action_id = button.get('ActionID')
                if not action_id or action_id in action_ids:
                    raise ValueError('Missing or duplicate key ActionID.')
                action_ids.add(action_id)
                states = button.get('States') or []
                if not states or not states[0].get('Title'):
                    raise ValueError('A key has no visible label.')
                image_name = name.rsplit('/', 1)[0] + '/' + states[0].get('Image', '')
                if image_name not in names or not archive.read(image_name).startswith(b'\x89PNG'):
                    raise ValueError('A key icon is missing or invalid.')
                kind = button['UUID'].rsplit('.', 1)[-1]
                if kind == 'backtoparent':
                    counts['back'] += 1
                    if depth == 0:
                        raise ValueError('The home page cannot have a Back key.')
                    if position != '0,0':
                        raise ValueError('Back must be the top-left key: ' + page.get('Name', ''))
                elif kind == 'open':
                    counts['open'] += 1
                    target = button.get('Settings', {}).get('path', '').strip('"')
                    if not target or not button.get('UserInput'):
                        raise ValueError('An Open key is incomplete.')
                    if shortcuts is not None and not (Path(shortcuts) / re.split(r'[\\/]', target)[-1]).is_file():
                        raise ValueError('Missing local shortcut: ' + re.split(r'[\\/]', target)[-1])
                elif kind == 'openchild':
                    counts['folders'] += 1
                    target = button.get('Settings', {}).get('ProfileUUID', '').upper()
                    if target not in pages:
                        raise ValueError('A folder key refers to a missing page.')
                    folder_targets.append(target)
                    inspect_page(target, depth + 1)
                elif kind == 'hotkey':
                    counts['hotkeys'] += 1
                    if len(button.get('Settings', {}).get('Hotkeys', [])) != 4:
                        raise ValueError('A hotkey is incomplete.')
                elif kind == 'text':
                    counts['text'] += 1
                elif kind == 'website':
                    counts['website'] = counts.get('website', 0) + 1
                    if not str(button.get('Settings', {}).get('path', '')).startswith('https://'):
                        raise ValueError('A website key must use https.')
            if depth and not any(b.get('UUID', '').endswith('backtoparent') for b in layout.values()):
                raise ValueError('A subpage has no Back key: ' + page.get('Name', ''))
        inspect_page(current, 0)
        if len(folder_targets) != len(set(folder_targets)):
            raise ValueError('A native folder has more than one parent.')
        orphan = set(pages) - visited - {default}
        if orphan:
            raise ValueError('Unreachable generated pages: ' + ', '.join(sorted(orphan)))
        return counts


def model_name(device):
    model = MODELS.get((device or {}).get('Model', ''))
    return model[0] if model else 'Stream Deck (%s)' % (device or {}).get('Model', 'unknown')
