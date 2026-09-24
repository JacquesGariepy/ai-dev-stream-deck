"""Render an actual Stream Deck archive as a standalone, non-executing HTML preview.

    python scripts/render_agent_deck_preview.py profile.streamDeckProfile preview.html --page home

Only visible key titles, embedded PNG icons and navigation are exported. Runtime
commands, shortcut paths, device identifiers and private action metadata stay out.
This is a generated-profile preview, not a screenshot of the Stream Deck software.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aidev.deck_layout import Grid  # noqa: E402


def profile_data(archive_path, page_name='home', grid=None):
    with zipfile.ZipFile(archive_path) as archive:
        roots = [name for name in archive.namelist() if name.endswith('/manifest.json') and '/Profiles/' not in name]
        if len(roots) != 1:
            raise ValueError('Expected one Stream Deck profile in the archive.')
        root = json.loads(archive.read(roots[0]))
        grid = grid or Grid.for_device(root.get('Device'))
        pages = {}
        for name in archive.namelist():
            if '/Profiles/' in name and name.endswith('/manifest.json'):
                pages[name.rsplit('/', 2)[1].upper()] = (name, json.loads(archive.read(name)))
        current = root['Pages']['Current'].upper()
        seen, result, selectors, icons = {}, [], {}, {}

        def visit(identifier, trail, parent=None):
            if identifier in seen:
                return seen[identifier]
            archive_name, manifest = pages[identifier]
            public_id = 'page-' + str(len(result))
            seen[identifier] = public_id
            selectors.setdefault(manifest.get('Name', ''), public_id)
            public = {'id': public_id, 'title': trail[-1], 'trail': trail, 'parent': parent, 'keys': []}
            result.append(public)
            slots = {}
            for controller in manifest.get('Controllers', []):
                if controller.get('Type') == 'Keypad':
                    slots.update(controller.get('Actions') or {})
            for position, action in sorted(slots.items(), key=lambda item: tuple(reversed([int(n) for n in item[0].split(',')]))):
                column, row = (int(number) for number in position.split(','))
                if not (0 <= column < grid.cols and 0 <= row < grid.rows):
                    raise ValueError('A button lies outside the selected grid.')
                states = action.get('States') or []
                if not states:
                    continue
                state_index = min(max(0, int(action.get('State', 0))), len(states) - 1)
                state = states[state_index]
                kind = action['UUID'].rsplit('.', 1)[-1]
                label = state.get('Title', '')
                button = {'column': column, 'row': row, 'title': label, 'kind': kind}
                image_name = archive_name.rsplit('/', 1)[0] + '/' + state.get('Image', '')
                if image_name in archive.namelist():
                    image = archive.read(image_name)
                    if not image.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('Preview icons must be PNG images.')
                    encoded = base64.b64encode(image).decode('ascii')
                    image_id = next((key for key, value in icons.items() if value == encoded), None)
                    if image_id is None:
                        image_id = 'icon-' + str(len(icons))
                        icons[image_id] = encoded
                    button['icon'] = image_id
                if kind == 'openchild':
                    child = action['Settings']['ProfileUUID'].upper()
                    button['destination'] = visit(child, trail + [label.replace('\n', ' ')], public_id)
                elif kind == 'backtoparent':
                    button['destination'] = parent
                public['keys'].append(button)
            return public_id

        home = visit(current, ['Home'])
        if page_name not in selectors:
            raise ValueError('Unknown archive page: ' + page_name + '. Available: ' + ', '.join(selectors))
        return {'profile': root.get('Name', 'Developer control desk'), 'columns': grid.cols, 'rows': grid.rows,
                'home': home, 'initial': selectors[page_name], 'pages': result, 'icons': icons}


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Dev · Generated profile preview</title>
<style>
:root{color-scheme:dark;font-family:Inter,"Segoe UI",sans-serif;background:#080c13;color:#f1f5fc}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 15% 5%,#172338 0,transparent 48%),radial-gradient(ellipse at 92% 80%,#172436 0,transparent 43%),#080c13}
main{max-width:1260px;margin:auto;padding:46px 54px 30px}.eyebrow{color:#58d6b0;font-size:12px;font-weight:700;letter-spacing:2.5px;display:flex;align-items:center;gap:10px}.eyebrow:before{content:"";height:8px;width:8px;background:#58d6b0;border-radius:3px}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:30px}h1{font-size:42px;letter-spacing:-1.5px;line-height:1.12;margin:16px 0 12px;font-weight:650}header p{font-size:14px;color:#a4b2c8;margin:0;line-height:1.7}.tag{border:1px solid #364254;background:#18212f;border-radius:30px;font-size:12px;color:#c2cddd;padding:9px 14px;white-space:nowrap;margin-bottom:4px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:34px 0 19px}.path{font-size:14px;font-weight:500;color:#aab8cd;overflow-wrap:anywhere}.path strong{color:#f0f5ff}select{font:12px "Segoe UI",sans-serif;max-width:420px;min-width:210px;padding:10px 36px 10px 13px;border:1px solid #344056;border-radius:9px;color:#d0dcf0;background:#111a28}
.deck-frame{border:1px solid #2a3548;border-radius:25px;background:linear-gradient(135deg,#192333,#101722);box-shadow:0 25px 75px #0008,inset 0 1px 0 #45536960;padding:27px}.deck{display:grid;gap:17px;max-width:930px;margin:auto;grid-template-columns:repeat(var(--columns),minmax(0,1fr));grid-template-rows:repeat(var(--rows),auto)}
.key{aspect-ratio:1;min-width:0;position:relative;padding:0;border:1px solid #39475a;border-radius:15px;background:#0d121c;overflow:hidden;color:white;box-shadow:0 5px 8px #0005;cursor:default}.key img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}.key .label{position:absolute;left:3px;right:3px;bottom:11%;font-family:"Segoe UI",sans-serif;font-size:clamp(10px,1.08vw,15px);font-weight:600;line-height:1.15;text-align:center;white-space:pre-line;letter-spacing:.25px;text-shadow:0 2px 3px #000b}.key.folder,.key.back{cursor:pointer}.key.folder:hover,.key.back:hover{border-color:#94b3df;box-shadow:0 0 0 2px #5a82b830,0 5px 8px #0005}.key.folder:after{content:"›";position:absolute;right:11px;top:7px;font-size:20px;color:#a4b3cc}.empty{border-color:#1d2939;background:#0c111a;box-shadow:inset 0 0 0 1px #090e15}
footer{display:flex;justify-content:space-between;align-items:center;gap:18px;color:#8d9fb9;font-size:12px;line-height:1.7;margin-top:21px}footer .hint{color:#becbe0}#status{min-height:20px;margin:12px 0 0;font-size:12px;text-align:center;color:#8eabc9}
@media(max-width:800px){main{padding:25px 20px}h1{font-size:30px}.tag{display:none}.toolbar{align-items:flex-start;flex-direction:column}.deck-frame{padding:14px;border-radius:18px}.deck{gap:9px}.key{border-radius:9px}.key .label{font-size:10px}footer{align-items:flex-start;flex-direction:column;gap:4px}select{max-width:100%;width:100%}}
</style></head><body><main>
<header><div><div class="eyebrow">AI DEV / STREAM DECK</div><h1>Your developer control desk.</h1><p>AI agents, development, everyday tools, media and search.</p></div><span class="tag">Generated profile preview</span></header>
<div class="toolbar"><div class="path" id="path"></div><select id="pages" aria-label="Profile page"></select></div>
<div class="deck-frame"><div class="deck" id="deck" aria-label="Generated Stream Deck buttons"></div></div>
<footer><span id="facts"></span><span class="hint">Explore folders · Preview only, no actions are executed</span></footer><div id="status" role="status"></div>
</main><script id="profile-data" type="application/json">__PROFILE_DATA__</script><script>
const data=JSON.parse(document.getElementById('profile-data').textContent),pages=new Map(data.pages.map(p=>[p.id,p])),selector=document.getElementById('pages'),deck=document.getElementById('deck');
deck.style.setProperty('--columns',data.columns);deck.style.setProperty('--rows',data.rows);
data.pages.forEach(page=>{const option=document.createElement('option');option.value=page.id;option.textContent=page.trail.join(' / ');selector.append(option)});
function show(id){const page=pages.get(id)||pages.get(data.initial);selector.value=page.id;deck.replaceChildren();document.getElementById('status').textContent='';const trail=document.getElementById('path');trail.replaceChildren();page.trail.forEach((label,index)=>{if(index)trail.append(' / ');const text=document.createElement(index===page.trail.length-1?'strong':'span');text.textContent=label;trail.append(text)});
for(let row=0;row<data.rows;row++)for(let column=0;column<data.columns;column++){const item=page.keys.find(k=>k.row===row&&k.column===column);const button=document.createElement('button');button.type='button';button.className='key';if(!item){button.classList.add('empty');button.disabled=true;button.setAttribute('aria-label','Empty key')}else{button.setAttribute('aria-label',item.title.replaceAll('\n',' '));if(item.icon){const image=document.createElement('img');image.src='data:image/png;base64,'+data.icons[item.icon];image.alt='';button.append(image)}const label=document.createElement('span');label.className='label';label.textContent=item.title;button.append(label);if(item.kind==='openchild')button.classList.add('folder');if(item.kind==='backtoparent')button.classList.add('back');button.addEventListener('click',()=>{if(item.destination){location.hash=item.destination;show(item.destination)}else{document.getElementById('status').textContent='Preview: '+item.title.replaceAll('\n',' ')+'. This page never launches tools or sends keystrokes.'}})}deck.append(button)}
document.getElementById('facts').textContent=data.profile+' · '+data.columns+' × '+data.rows+' keys · Actual exported icons and labels';}
selector.addEventListener('change',()=>{location.hash=selector.value;show(selector.value)});window.addEventListener('hashchange',()=>show(location.hash.slice(1)));show(location.hash.slice(1)||data.initial);
</script></body></html>'''


def render(archive_path, output, page_name='home', grid=None):
    data = profile_data(archive_path, page_name, grid)
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(TEMPLATE.replace('__PROFILE_DATA__', serialized), encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--page', default='home', help='An original page name from the archive, such as home, ai or dev.')
    parser.add_argument('--grid', help='Override the key grid, such as 5x3.')
    args = parser.parse_args()
    data = render(args.archive, args.output, args.page, Grid.parse(args.grid) if args.grid else None)
    print('Rendered', len(data['pages']), 'actual profile pages to', args.output)


if __name__ == '__main__':
    main()
