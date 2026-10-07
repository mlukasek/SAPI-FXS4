#!/usr/bin/env python3
"""Start the port in SAPIemu (sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592,
run from ..\\SAPIemu-release; another URL: SAPIEMU_MCP).

  port.py [MS] [PNG]    boot CP/M (state 'cpm' in the emulator), load build\\fxs4.com at 0100h,
                        run MS ms (default 3000) and save the CGA-1V screen (default build\\port.png)
"""
import base64, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sapimcp as sm

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
COM = os.path.join(ROOT, 'build', 'fxs4.com')


def boot_cpm():
    """CP/M prompt, from the saved state 'cpm' if there is one."""
    sm.call('pause')
    try:
        sm.call('load_state', name='cpm')
    except RuntimeError:
        sm.call('power', state='cycle')
        sm.call('resume')
        sm.call('run_until', screen_text='Zadej 0-3', timeout_ms=20000)
        sm.call('type_text', text='1')
        sm.call('run_until', screen_text='A>', timeout_ms=30000)
        sm.call('pause')
        sm.call('save_state', name='cpm')
    sm.call('pause')


def start(path=COM):
    boot_cpm()
    sm.call('load_binary', address='0100', path=path)
    sm.call('set_registers', pc='0100')


def read(a, n):
    out = b''
    while len(out) < n:
        k = min(4096, n - len(out))
        h = sm.call('read_memory', address='%04X' % (a + len(out)), length=k, format='hex')
        b = bytes.fromhex(re.sub(r'[^0-9A-Fa-f]', '', h))
        assert len(b) == k
        out += b
    return out


def screenshot(path):
    """Save the CGA-1V screen as PNG (the tool returns the image)."""
    r = sm.call('screenshot', display='CGA-1V')
    for c in r if isinstance(r, list) else [r]:
        if isinstance(c, dict) and 'data' in c:
            open(path, 'wb').write(base64.b64decode(c['data']))
            return path
    raise RuntimeError('no image: %r' % (r,)[:200])


def symbols():
    s = {}
    for line in open(os.path.join(ROOT, 'build', 'fxs4.sym')):
        m = re.match(r'^(\S+)\s+EQU\s+0?([0-9A-F]+)H', line.strip(), re.I)
        if m:
            s[m.group(1)] = int(m.group(2), 16)
    return s


if __name__ == '__main__':
    ms = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    png = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'build', 'port.png')
    start()
    r = sm.call('run_for', ms=ms)
    print(r.get('registers', {}).get('pc'), r.get('stopped'))
    print(screenshot(png))
