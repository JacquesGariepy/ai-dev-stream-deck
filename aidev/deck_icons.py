"""Original, dependency-free Stream Deck pictograms (no external icon license)."""
from functools import lru_cache
import math
import struct
import zlib


@lru_cache(maxsize=64)
def icon_png(kind, theme='daily'):
    colors={'daily':(77,190,237),'dev':(78,220,180),'agent':(177,145,255),'music':(58,214,129)}
    ink=colors.get(theme,colors['daily'])
    size=144
    pixels=bytearray(bytes((14,22,35))*size*size)
    def dot(x,y,color=ink,r=2):
        for yy in range(max(0,int(y-r)),min(size,int(y+r)+1)):
            for xx in range(max(0,int(x-r)),min(size,int(x+r)+1)):
                if (xx-x)**2+(yy-y)**2<=r*r:
                    offset=(yy*size+xx)*3;pixels[offset:offset+3]=bytes(color)
    def line(x1,y1,x2,y2,width=2):
        steps=max(abs(x2-x1),abs(y2-y1),1)*2
        for i in range(int(steps)+1):
            t=i/steps;dot(x1+(x2-x1)*t,y1+(y2-y1)*t,r=width)
    def poly(points,close=False):
        for a,b in zip(points,points[1:]):line(*a,*b)
        if close:line(*points[-1],*points[0])
    def box(x,y,w,h):poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],True)
    def circle(x,y,r):
        for i in range(241):
            a=i*math.tau/240;dot(x+r*math.cos(a),y+r*math.sin(a),r=1.8)
    line(24,9,120,9,1)
    if kind=='code':
        poly([(52,35),(34,54),(52,73)]);poly([(92,35),(110,54),(92,73)]);line(79,30,65,79)
    elif kind=='agent':
        box(42,33,60,43);line(72,33,72,22);dot(72,20,r=4)
        dot(57,49,r=4);dot(87,49,r=4);line(59,64,85,64)
    elif kind=='music':
        circle(72,54,32)
        for offset in (0,12,24):poly([(49,42+offset),(64,39+offset),(82,40+offset),(96,45+offset)])
    elif kind in ('play','next','prev'):
        points=[(53,32),(84,54),(53,76)]
        if kind=='prev':points=[(144-x,y) for x,y in points]
        poly(points,True)
        if kind=='play':line(94,36,94,72);line(105,36,105,72)
        else:line(99 if kind=='next' else 45,32,99 if kind=='next' else 45,76)
    elif kind in ('volume','mute'):
        poly([(37,44),(51,44),(70,29),(70,79),(51,64),(37,64)],True)
        if kind=='mute':line(85,43,106,66);line(106,43,85,66)
        else:poly([(83,40),(91,54),(83,68)]);poly([(97,29),(111,54),(97,79)])
    elif kind=='camera':
        box(36,35,72,43);box(48,26,25,9);circle(72,56,14)
    elif kind=='web':
        circle(72,54,31);line(41,54,103,54)
        for scale in (-1,1):poly([(72,23),(72+scale*14,38),(72+scale*18,54),(72+scale*14,70),(72,85)])
    elif kind in ('screen','terminal'):
        box(34,26,76,52);line(72,78,72,87);line(53,88,91,88)
        if kind=='terminal':poly([(47,40),(58,49),(47,59)]);line(68,60,88,60)
    elif kind=='folder':
        poly([(33,77),(33,33),(61,33),(70,42),(111,42),(111,77)],True)
    elif kind=='back':poly([(64,29),(39,54),(64,79)]);line(39,54,105,54)
    elif kind=='git':
        line(53,29,53,80);poly([(91,30),(91,51),(53,68)])
        for x,y in ((53,27),(53,82),(91,28)):circle(x,y,6)
    elif kind=='chart':
        poly([(33,27),(33,83),(111,83)]);poly([(43,68),(60,52),(77,62),(102,34)])
    elif kind=='settings':
        for y,x in ((34,56),(55,87),(76,64)):
            line(36,y,108,y);dot(x,y,color=(14,22,35),r=7);circle(x,y,6)
    elif kind=='keyboard':
        box(30,31,84,47)
        for y in (43,55):
            for x in range(41,107,13):dot(x,y,r=2.5)
        line(50,67,94,67)
    else:
        box(46,24,53,60);line(57,40,86,40);line(57,52,86,52);line(57,64,77,64)
    def chunk(name,data):return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
    rows=b''.join(b'\0'+pixels[y*size*3:(y+1)*size*3] for y in range(size))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')


def button_icon(button):
    title=button['Name'].upper()
    path=button['Settings'].get('path','').lower()
    media=button['Settings'].get('Hotkeys',[{}])[0].get('NativeCode')
    if media in (173,174,175,176,177,179):return {173:'mute',174:'volume',175:'volume',176:'next',177:'prev',179:'play'}[media]
    if 'SPOTIFY' in title:return 'music'
    if title=='DEV':return 'code'
    if title=='AGENTIC' or 'profile-' in path or title=='MISSION':return 'agent'
    if 'terminal' in path:return 'terminal'
    if 'capture' in path or 'PHOTO' in title or title=='CAPTURE':return 'camera'
    if 'browser' in path or 'web-' in path or 'WEB' in title:return 'web'
    if 'git.lnk' in path:return 'git'
    if 'BACK'==title or 'RETOUR'==title:return 'back'
    if 'SETTINGS' in title or 'REGLAGES' in title or 'CONTROL' in title or 'PILOTAGE' in title:return 'settings'
    if 'CPU' in title or any(k in path for k in ('monitor','resources','performance','health')):return 'chart'
    if 'DESKTOP' in title or 'BUREAU' in title:return 'screen'
    if 'EDITOR' in title or 'EDITEUR' in title or media:return 'keyboard'
    if button['UUID'].endswith('openchild') or 'files' in path:return 'folder'
    return 'document'
