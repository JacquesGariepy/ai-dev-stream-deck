"""Minimal Windows .lnk writer (MS-SHLLINK) so shortcuts can be produced without COM.

Only what Stream Deck needs: an absolute local target, arguments, working
directory and show command. Unicode strings, no ID list.
"""
import struct

CLSID = bytes.fromhex('0114020000000000c000000000000046')
HAS_LINK_INFO, HAS_WORKING_DIR, HAS_ARGUMENTS, IS_UNICODE = 0x02, 0x10, 0x20, 0x80
SW_SHOWNORMAL, SW_SHOWMINNOACTIVE = 1, 7


def _string(value):
    data = value.encode('utf-16le')
    if len(value) > 0xFFFF:
        raise ValueError('String too long for a shortcut.')
    return struct.pack('<H', len(value)) + data


def shell_link(target, arguments='', working_dir='', show=SW_SHOWMINNOACTIVE):
    if len(target) < 3 or target[1:3] != ':\\':
        raise ValueError('Target must be an absolute local Windows path.')
    flags = HAS_LINK_INFO | IS_UNICODE | (HAS_WORKING_DIR if working_dir else 0) | (HAS_ARGUMENTS if arguments else 0)
    header = struct.pack('<I16sII', 0x4C, CLSID, flags, 0x20) + b'\0' * 24 + struct.pack('<IiIH', 0, 0, show, 0) + b'\0' * 10
    assert len(header) == 0x4C
    volume = struct.pack('<IIII', 0x11, 3, 0, 0x10) + b'\0'           # fixed drive, empty label
    base = target.encode('ascii') + b'\0'      # ASCII local path (validated by encode)
    suffix = b'\0'
    header_size = 0x1C
    volume_offset = header_size
    base_offset = volume_offset + len(volume)
    suffix_offset = base_offset + len(base)
    size = suffix_offset + len(suffix)
    link_info = struct.pack('<IIIIIII', size, header_size, 1, volume_offset, base_offset, 0, suffix_offset) + volume + base + suffix
    strings = (_string(working_dir) if working_dir else b'') + (_string(arguments) if arguments else b'')
    return header + link_info + strings + b'\0\0\0\0'


def read_link(data):
    """Parse the fields written above (used by tests and audits)."""
    flags = struct.unpack_from('<I', data, 20)[0]
    show = struct.unpack_from('<I', data, 60)[0]
    offset = 0x4C
    target = None
    if flags & 0x01:
        offset += 2 + struct.unpack_from('<H', data, offset)[0]
    if flags & HAS_LINK_INFO:
        size = struct.unpack_from('<I', data, offset)[0]
        info = data[offset:offset + size]
        base = struct.unpack_from('<I', info, 16)[0]
        target = info[base:info.index(b'\0', base)].decode('latin1')
        offset += size
    result = {'target': target, 'show': show}
    for bit, name in ((0x04, 'name'), (0x08, 'relative'), (HAS_WORKING_DIR, 'working_dir'), (HAS_ARGUMENTS, 'arguments'), (0x40, 'icon')):
        if flags & bit:
            count = struct.unpack_from('<H', data, offset)[0]
            width = 2 if flags & IS_UNICODE else 1
            raw = data[offset + 2:offset + 2 + count * width]
            result[name] = raw.decode('utf-16le' if width == 2 else 'latin1')
            offset += 2 + count * width
    return result
