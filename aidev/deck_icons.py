"""Original, dependency-free Stream Deck pictograms (no external icon license).

Icons are drawn at 2x on a coverage mask, then downsampled for anti-aliased
strokes. Each key gets a dark tile tinted by its functional zone, an accent bar
and a bright pictogram in the upper area; Stream Deck draws the title below.
"""
from functools import lru_cache
import math
import struct
import zlib

SIZE = 144
SCALE = 2
BASE = (13, 18, 28)
ZONES = {
    'agent': (170, 136, 255),   # missions, harnesses, prompts
    'dev': (56, 214, 170),      # terminal, editor, project
    'git': (255, 146, 72),      # version control
    'run': (250, 204, 21),      # build / test / debug
    'system': (84, 170, 250),   # Windows, apps, desktop
    'media': (60, 214, 128),    # playback and volume
    'web': (56, 196, 240),      # browser contexts and sites
    'nav': (150, 164, 186),     # back, more, refresh
    'alert': (255, 120, 96),    # unavailable or destructive-looking actions
}
# Legacy theme names from earlier generated decks.
ZONES.update(daily=ZONES['system'], music=ZONES['media'])


def _disc(radius):
    r = max(1, int(round(radius * SCALE)))
    return r, [(dx, dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dx * dx + dy * dy <= r * r]


class _Mask:
    def __init__(self):
        self.n = SIZE * SCALE
        self.data = bytearray(self.n * self.n)
        self.discs = {}

    def dot(self, x, y, r=2.6):
        key = round(r, 1)
        if key not in self.discs:
            self.discs[key] = _disc(key)
        _, offsets = self.discs[key]
        cx, cy, n, data = int(x * SCALE), int(y * SCALE), self.n, self.data
        for dx, dy in offsets:
            px, py = cx + dx, cy + dy
            if 0 <= px < n and 0 <= py < n:
                data[py * n + px] = 1

    def line(self, x1, y1, x2, y2, w=2.6):
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) * SCALE / max(1.0, w * SCALE / 2)))
        for i in range(steps + 1):
            t = i / steps
            self.dot(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, w)

    def poly(self, points, close=False, w=2.6):
        for a, b in zip(points, points[1:]):
            self.line(*a, *b, w=w)
        if close:
            self.line(*points[-1], *points[0], w=w)

    def box(self, x, y, w, h, stroke=2.6):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True, stroke)

    def arc(self, x, y, r, start, end, w=2.6):
        steps = max(8, int(abs(end - start) * r * SCALE / 2))
        points = [(x + r * math.cos(start + (end - start) * i / steps), y + r * math.sin(start + (end - start) * i / steps))
                  for i in range(steps + 1)]
        self.poly(points, w=w)

    def circle(self, x, y, r, w=2.6):
        self.arc(x, y, r, 0, math.tau, w)

    def fill(self, points):
        n, data = self.n, self.data
        pts = [(px * SCALE, py * SCALE) for px, py in points]
        top = max(0, int(min(p[1] for p in pts)))
        bottom = min(n - 1, int(max(p[1] for p in pts)) + 1)
        for row in range(top, bottom + 1):
            yy = row + 0.5
            xs = []
            for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
                if (ay <= yy < by) or (by <= yy < ay):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for left, right in zip(xs[::2], xs[1::2]):
                for col in range(max(0, int(left + 0.5)), min(n, int(right + 0.5))):
                    data[row * n + col] = 1

    def disc(self, x, y, r):
        self.fill([(x + r * math.cos(a * math.tau / 48), y + r * math.sin(a * math.tau / 48)) for a in range(48)])

    def arrow(self, x1, y1, x2, y2, head=11, w=3):
        self.line(x1, y1, x2, y2, w)
        angle = math.atan2(y2 - y1, x2 - x1)
        left = (x2 - head * math.cos(angle - 0.6), y2 - head * math.sin(angle - 0.6))
        right = (x2 - head * math.cos(angle + 0.6), y2 - head * math.sin(angle + 0.6))
        self.fill([(x2 + 2 * math.cos(angle), y2 + 2 * math.sin(angle)), left, right])


def _draw(kind, m):
    """Pictograms live in the 144px frame, centred near (72, 54)."""
    if kind == 'code':
        m.poly([(54, 34), (34, 54), (54, 74)], w=3.2); m.poly([(90, 34), (110, 54), (90, 74)], w=3.2); m.line(80, 30, 64, 78, 3)
    elif kind == 'agent':
        m.box(42, 34, 60, 42, 3); m.line(72, 34, 72, 24, 3); m.disc(72, 21, 4.5)
        m.disc(58, 52, 5); m.disc(86, 52, 5); m.line(60, 66, 84, 66, 3)
    elif kind == 'mission':
        m.circle(72, 54, 32, 3); m.circle(72, 54, 19, 3); m.disc(72, 54, 7)
        m.arrow(112, 16, 78, 49, 13, 3.4)
    elif kind == 'chatgpt':
        m.circle(72, 54, 10)
        for i in range(6):
            a = i * math.tau / 6 - math.pi / 2
            x, y = 72 + 28 * math.cos(a), 54 + 28 * math.sin(a)
            m.circle(x, y, 8); m.line(72 + 10 * math.cos(a), 54 + 10 * math.sin(a), x - 8 * math.cos(a), y - 8 * math.sin(a))
    elif kind == 'claude':
        m.circle(72, 54, 12); m.disc(72, 54, 5)
        for i in range(8):
            a = i * math.tau / 8
            m.line(72 + 18 * math.cos(a), 54 + 18 * math.sin(a), 72 + 33 * math.cos(a), 54 + 33 * math.sin(a), 3.4)
    elif kind == 'profile':
        m.circle(72, 42, 12, 3); m.arc(72, 86, 26, math.pi * 1.1, math.pi * 1.9, 3)
    elif kind == 'plan':
        for i, y in enumerate((36, 54, 72)):
            m.box(38, y - 6, 12, 12, 2.6)
            if i < 2:
                m.poly([(40, y), (44, y + 4), (50, y - 5)], w=2.6)
            m.line(60, y, 106, y, 3)
    elif kind == 'review':
        m.arc(72, 76, 38, math.pi * 1.18, math.pi * 1.82, 3); m.arc(72, 32, 38, math.pi * 0.18, math.pi * 0.82, 3)
        m.circle(72, 54, 11, 3); m.disc(72, 54, 5)
    elif kind == 'bug':
        m.fill([(72 + 16 * math.cos(a * math.tau / 40), 58 + 22 * math.sin(a * math.tau / 40)) for a in range(40)])
        m.disc(72, 32, 9)
        for y, dx in ((46, 30), (58, 32), (70, 30)):
            m.line(72 - 16, y, 72 - dx, y - 6, 2.6); m.line(72 + 16, y, 72 + dx, y - 6, 2.6)
        m.line(66, 26, 60, 18, 2.4); m.line(78, 26, 84, 18, 2.4)
    elif kind in ('check', 'test'):
        if kind == 'test':
            m.poly([(60, 26), (60, 46), (40, 80), (104, 80), (84, 46), (84, 26)], w=3); m.line(54, 26, 90, 26, 3)
            m.poly([(56, 64), (66, 72), (88, 52)], w=3.6)
        else:
            m.circle(72, 54, 32, 3); m.poly([(56, 55), (67, 66), (90, 42)], w=4)
    elif kind == 'handoff':
        m.box(32, 36, 38, 38, 3); m.arrow(78, 55, 112, 55, 12, 3.4); m.line(40, 48, 62, 48, 2.6); m.line(40, 60, 56, 60, 2.6)
    elif kind == 'next':
        m.fill([(40, 34), (70, 54), (40, 74)]); m.fill([(72, 34), (102, 54), (72, 74)]); m.line(108, 34, 108, 74, 3.6)
    elif kind == 'sessions':
        for i, y in enumerate((30, 48, 66)):
            m.box(36, y, 72, 14, 2.6); m.disc(46, y + 7, 3.2 if i else 4)
    elif kind == 'context':
        m.poly([(72, 28), (108, 44), (72, 60), (36, 44)], True, 3)
        m.poly([(36, 56), (72, 72), (108, 56)], w=3); m.poly([(36, 68), (72, 84), (108, 68)], w=3)
    elif kind == 'prompt':
        m.poly([(34, 30), (110, 30), (110, 70), (62, 70), (46, 84), (48, 70), (34, 70)], True, 3)
        m.line(46, 44, 98, 44, 2.6); m.line(46, 56, 84, 56, 2.6)
    elif kind == 'mcp':
        m.box(52, 38, 40, 26, 3); m.line(62, 26, 62, 38, 3.4); m.line(82, 26, 82, 38, 3.4); m.line(72, 64, 72, 84, 3.4)
    elif kind == 'hub':
        m.circle(72, 54, 10, 3)
        for a in range(5):
            ang = a * math.tau / 5 - math.pi / 2
            x, y = 72 + 32 * math.cos(ang), 54 + 30 * math.sin(ang)
            m.disc(x, y, 6); m.line(72 + 10 * math.cos(ang), 54 + 10 * math.sin(ang), x, y, 2.4)
    elif kind == 'music':
        m.circle(72, 54, 32)
        for off in (0, 12, 24):
            m.poly([(49, 42 + off), (64, 39 + off), (82, 40 + off), (96, 45 + off)])
    elif kind == 'playpause':
        m.fill([(40, 32), (70, 54), (40, 76)]); m.fill([(82, 34), (92, 34), (92, 74), (82, 74)]); m.fill([(98, 34), (108, 34), (108, 74), (98, 74)])
    elif kind in ('track-next', 'track-prev'):
        pts = [(50, 32), (86, 54), (50, 76)]
        bar = 92
        if kind == 'track-prev':
            pts = [(144 - x, y) for x, y in pts]; bar = 144 - bar - 6
        m.fill(pts); m.fill([(bar, 32), (bar + 6, 32), (bar + 6, 76), (bar, 76)])
    elif kind in ('volume', 'volume-down', 'mute'):
        m.fill([(34, 44), (50, 44), (70, 28), (70, 80), (50, 64), (34, 64)])
        if kind == 'mute':
            m.line(84, 42, 108, 66, 3.4); m.line(108, 42, 84, 66, 3.4)
        else:
            m.arc(72, 54, 18, -0.9, 0.9, 3)
            if kind == 'volume':
                m.arc(72, 54, 32, -0.9, 0.9, 3)
    elif kind == 'camera':
        m.box(34, 36, 76, 44, 3); m.box(50, 26, 24, 10, 3); m.circle(72, 58, 14, 3)
    elif kind == 'web':
        m.circle(72, 54, 32, 3); m.line(40, 54, 104, 54, 2.6)
        for s in (-1, 1):
            m.poly([(72, 22), (72 + s * 14, 38), (72 + s * 17, 54), (72 + s * 14, 70), (72, 86)], w=2.6)
    elif kind in ('screen', 'terminal'):
        m.box(32, 26, 80, 52, 3); m.line(72, 78, 72, 88, 3); m.line(52, 89, 92, 89, 3)
        if kind == 'terminal':
            m.poly([(46, 40), (58, 50), (46, 60)], w=3.2); m.line(66, 62, 90, 62, 3.2)
    elif kind == 'folder':
        m.poly([(32, 78), (32, 32), (60, 32), (70, 42), (112, 42), (112, 78)], True, 3)
    elif kind == 'back':
        m.arrow(106, 54, 36, 54, 24, 5)
    elif kind == 'more':
        for x in (48, 72, 96):
            m.disc(x, 54, 7)
    elif kind == 'refresh':
        m.arc(72, 54, 28, math.pi * 0.15, math.pi * 1.1, 3.4); m.arc(72, 54, 28, math.pi * 1.15, math.pi * 2.1, 3.4)
        for a in (math.pi * 1.1, math.pi * 2.1):
            x, y = 72 + 28 * math.cos(a), 54 + 28 * math.sin(a)
            t = a + math.pi / 2
            m.fill([(x + 9 * math.cos(t), y + 9 * math.sin(t)), (x + 9 * math.cos(t - 2.3), y + 9 * math.sin(t - 2.3)),
                    (x + 9 * math.cos(t + 2.3), y + 9 * math.sin(t + 2.3))])
    elif kind == 'git':
        m.line(52, 30, 52, 80, 3.2); m.poly([(92, 36), (92, 50), (52, 68)], w=3.2)
        for x, y in ((52, 26), (52, 84), (92, 30)):
            m.circle(x, y, 6, 3)
    elif kind == 'push':
        m.arrow(72, 84, 72, 28, 22, 4.4); m.line(40, 88, 104, 88, 3)
    elif kind == 'pull':
        m.arrow(72, 24, 72, 80, 22, 4.4); m.line(40, 88, 104, 88, 3)
    elif kind == 'fetch':
        m.arc(72, 54, 28, math.pi * 0.2, math.pi * 1.8, 3.4)
        m.arrow(72, 38, 72, 70, 12, 3.2)
    elif kind == 'commit':
        m.line(28, 54, 54, 54, 3.4); m.line(90, 54, 116, 54, 3.4); m.circle(72, 54, 16, 3.4)
    elif kind == 'branch':
        m.line(52, 26, 52, 84, 3.2); m.poly([(52, 64), (92, 50), (92, 30)], w=3.2)
        m.circle(92, 26, 6, 3); m.fill([(92, 70), (100, 70), (100, 62), (108, 62), (108, 70), (116, 70), (116, 78), (108, 78), (108, 86), (100, 86), (100, 78), (92, 78)])
    elif kind == 'switch':
        m.arrow(36, 42, 104, 42, 12, 3.4); m.arrow(108, 68, 40, 68, 12, 3.4)
    elif kind == 'stash':
        m.box(36, 50, 72, 32, 3); m.line(36, 62, 108, 62, 2.6); m.arrow(72, 20, 72, 46, 12, 3.4)
    elif kind == 'unstash':
        m.box(36, 50, 72, 32, 3); m.line(36, 62, 108, 62, 2.6); m.arrow(72, 46, 72, 18, 12, 3.4)
    elif kind == 'diff':
        m.line(38, 40, 62, 40, 4); m.line(50, 28, 50, 52, 4); m.line(82, 40, 106, 40, 4)
        m.line(36, 70, 108, 70, 2.6); m.line(36, 82, 90, 82, 2.6)
    elif kind == 'log':
        m.line(44, 26, 44, 84, 3)
        for y in (30, 54, 78):
            m.disc(44, y, 6); m.line(58, y, 108, y, 3)
    elif kind == 'stage':
        m.box(38, 30, 68, 48, 3); m.line(72, 42, 72, 66, 4); m.line(60, 54, 84, 54, 4)
    elif kind == 'build':
        m.poly([(72, 26), (104, 42), (104, 72), (72, 88), (40, 72), (40, 42)], True, 3)
        m.poly([(40, 42), (72, 58), (104, 42)], w=3); m.line(72, 58, 72, 88, 3)
    elif kind == 'lint':
        m.fill([(72, 24), (78, 48), (102, 54), (78, 60), (72, 84), (66, 60), (42, 54), (66, 48)])
        m.fill([(100, 24), (103, 32), (111, 35), (103, 38), (100, 46), (97, 38), (89, 35), (97, 32)])
    elif kind == 'run':
        m.circle(72, 54, 32, 3); m.fill([(62, 38), (90, 54), (62, 70)])
    elif kind == 'format':
        for y, w in ((32, 72), (46, 52), (60, 72), (74, 52)):
            m.line(36, y, 36 + w, y, 3.4)
    elif kind == 'types':
        m.line(40, 32, 80, 32, 4); m.line(60, 32, 60, 80, 4); m.poly([(92, 44), (86, 54), (92, 64)], w=3); m.poly([(100, 44), (106, 54), (100, 64)], w=3)
    elif kind == 'tasks':
        for y in (32, 54, 76):
            m.poly([(38, y), (44, y + 5), (52, y - 5)], w=3); m.line(62, y, 106, y, 3)
    elif kind == 'chart':
        m.poly([(32, 26), (32, 84), (112, 84)], w=3); m.poly([(42, 68), (60, 50), (78, 60), (104, 32)], w=3.4)
    elif kind == 'settings':
        for y, x in ((34, 56), (55, 88), (76, 64)):
            m.line(34, y, 110, y, 3); m.disc(x, y, 8)
    elif kind == 'keyboard':
        m.box(28, 32, 88, 46, 3)
        for y in (44, 56):
            for x in range(40, 108, 13):
                m.disc(x, y, 3)
        m.line(50, 68, 94, 68, 3)
    elif kind == 'apps':
        for y in (30, 50, 70):
            for x in (46, 66, 86):
                m.fill([(x, y), (x + 12, y), (x + 12, y + 12), (x, y + 12)])
    elif kind == 'windows':
        for x, y in ((36, 26), (74, 26), (36, 58), (74, 58)):
            m.fill([(x, y), (x + 34, y), (x + 34, y + 28), (x, y + 28)])
    elif kind == 'lock':
        m.box(44, 50, 56, 36, 3); m.arc(72, 50, 16, math.pi, math.tau, 3.4); m.disc(72, 66, 5)
    elif kind == 'calc':
        m.box(44, 24, 56, 64, 3); m.box(52, 32, 40, 12, 2.4)
        for y in (54, 66, 78):
            for x in (56, 72, 88):
                m.disc(x, y, 3.2)
    elif kind == 'clipboard':
        m.box(42, 30, 60, 58, 3); m.box(58, 24, 28, 12, 3); m.line(54, 52, 90, 52, 2.6); m.line(54, 66, 82, 66, 2.6)
    elif kind == 'search':
        m.circle(64, 48, 20, 3.4); m.line(78, 62, 102, 86, 4.4)
    elif kind == 'home':
        m.poly([(34, 54), (72, 24), (110, 54)], w=3.4); m.poly([(44, 48), (44, 84), (100, 84), (100, 48)], w=3); m.box(64, 62, 16, 22, 2.6)
    elif kind == 'warning':
        m.poly([(72, 24), (108, 84), (36, 84)], True, 3.4); m.line(72, 44, 72, 66, 4); m.disc(72, 75, 3.6)
    elif kind == 'desktop':
        m.box(28, 30, 60, 40, 3); m.box(56, 44, 60, 40, 3)
    elif kind == 'stop':
        m.fill([(46, 30), (98, 30), (98, 80), (46, 80)])
    elif kind == 'breakpoint':
        m.disc(72, 54, 20)
    elif kind in ('step-over', 'step-into', 'step-out'):
        if kind == 'step-over':
            m.arc(72, 60, 28, math.pi * 1.05, math.pi * 1.95, 3.4); m.arrow(97, 50, 99, 58, 12, 3); m.disc(72, 84, 5)
        elif kind == 'step-into':
            m.arrow(72, 24, 72, 70, 14, 3.6); m.disc(72, 84, 5)
        else:
            m.arrow(72, 76, 72, 30, 14, 3.6); m.disc(72, 86, 5)
    elif kind == 'document':
        m.poly([(46, 24), (86, 24), (100, 38), (100, 84), (46, 84)], True, 3); m.line(56, 44, 88, 44, 2.6); m.line(56, 56, 88, 56, 2.6); m.line(56, 68, 78, 68, 2.6)
    else:
        m.poly([(46, 24), (86, 24), (100, 38), (100, 84), (46, 84)], True, 3)


def _png(pixels):
    def chunk(name, data):
        return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name + data) & 0xffffffff)
    rows = b''.join(b'\0' + bytes(pixels[y * SIZE * 3:(y + 1) * SIZE * 3]) for y in range(SIZE))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', SIZE, SIZE, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def _tile(zone_color):
    """Rounded, tinted tile with a top accent bar. Computed once per zone."""
    pixels = bytearray(SIZE * SIZE * 3)
    radius, inset = 18, 5
    tint = tuple(int(BASE[i] * 0.84 + zone_color[i] * 0.16) for i in range(3))
    for y in range(SIZE):
        for x in range(SIZE):
            # Distance outside the rounded rectangle, used for a soft edge.
            dx = max(inset + radius - x, 0, x - (SIZE - 1 - inset - radius))
            dy = max(inset + radius - y, 0, y - (SIZE - 1 - inset - radius))
            outside = math.hypot(dx, dy) - radius
            cover = min(1.0, max(0.0, 0.5 - outside))
            shade = 1.0 - 0.18 * (y / SIZE)
            color = tuple(int(tint[i] * shade) for i in range(3))
            if inset + 10 <= x <= SIZE - inset - 10 and inset + 3 <= y <= inset + 6:
                color = zone_color
            o = (y * SIZE + x) * 3
            for i in range(3):
                pixels[o + i] = int(BASE[i] * (1 - cover) * 0.6 + color[i] * cover)
    return pixels


@lru_cache(maxsize=16)
def _cached_tile(zone):
    return bytes(_tile(ZONES.get(zone, ZONES['nav'])))


@lru_cache(maxsize=256)
def icon_png(kind, zone='system'):
    zone = zone if zone in ZONES else 'nav'
    color = ZONES[zone]
    mask = _Mask()
    _draw(kind, mask)
    pixels = bytearray(_cached_tile(zone))
    n, data = mask.n, mask.data
    for y in range(SIZE):
        row0, row1 = (2 * y) * n, (2 * y + 1) * n
        for x in range(SIZE):
            c = data[row0 + 2 * x] + data[row0 + 2 * x + 1] + data[row1 + 2 * x] + data[row1 + 2 * x + 1]
            if c:
                a = c / 4
                o = (y * SIZE + x) * 3
                for i in range(3):
                    pixels[o + i] = int(pixels[o + i] * (1 - a) + color[i] * a)
    return _png(pixels)


def blank_png():
    return _png(bytearray(_cached_tile('nav')))
