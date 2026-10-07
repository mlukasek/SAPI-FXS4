#!/usr/bin/env python3
"""Record which addresses of the original execute in zx84 -> build/exec_zx84.txt (read by tools/mkdis.py).

Scenario: load and start (BASIC 9000-9215 with the line animation), ENTER (music, line 20 loop),
every song key A-Z, ENTER held (3 ticks per frame). Traced in chunks of 25 frames ('trace full'
writes a file into ..\\zx84\\mcp\\.cache, deleted after reading).
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from zx84 import ZX84
import boot as B

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
PC = re.compile(r'^([0-9A-F]{4})  ', re.M)


def traced(zx, xs, frames, chunk=25):
    while frames > 0:
        n = min(chunk, frames)
        zx.call('trace', mode='full')
        zx.call('run', frames=n)
        r = zx.call('stop_trace')
        m = re.search(r'written to (.+\.txt)', r)
        if m:
            txt = open(m.group(1)).read()
            os.remove(m.group(1))
        else:
            txt = r
        xs.update(int(a, 16) for a in PC.findall(txt))
        frames -= n


def traced_key(zx, xs, name, after):
    zx.call('trace', mode='full')
    zx.call('key', name=name, frames=5)
    r = zx.call('stop_trace')
    m = re.search(r'written to (.+\.txt)', r)
    txt = open(m.group(1)).read() if m else r
    if m:
        os.remove(m.group(1))
    xs.update(int(a, 16) for a in PC.findall(txt))
    traced(zx, xs, after)


def main():
    xs = set()
    with ZX84() as zx:
        zx.call('model', target='128k')
        zx.call('load', file=B.make_boot_tap())
        B.run_until(zx, '48 BASIC', 400)
        for _ in range(3):
            B.key(zx, 'down')
        B.key(zx, 'enter')
        B.run_until(zx, '1982', 400, 10)
        for k in ('j', 'sym+p', 'sym+p'):
            B.key(zx, k)
        traced_key(zx, xs, 'enter', 700)         # loading, RUN, 9200: stop, animation
        traced_key(zx, xs, 'enter', 200)         # 9500: music, line 20
        for k in 'abcdefghijklmnopqrstuvwxyz':
            traced_key(zx, xs, k, 30)
        traced_key(zx, xs, 'enter', 50)
        zx.call('trace', mode='full')
        zx.call('key', name='enter', frames=60)  # held: 3 ticks per frame
        r = zx.call('stop_trace')
        m = re.search(r'written to (.+\.txt)', r)
        if m:
            xs.update(int(a, 16) for a in PC.findall(open(m.group(1)).read()))
            os.remove(m.group(1))
    code = sorted(a for a in xs if a >= 0x744A)
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    with open(os.path.join(ROOT, 'build', 'exec_zx84.txt'), 'w') as f:
        f.write(''.join('%04X\n' % a for a in code))
    print('%d addresses in 744A-FFFF executed' % len(code))


if __name__ == '__main__':
    main()
