#!/usr/bin/env python3
"""Save the Spectrum screen of the original at the start of the music -> build/zx_start_screen.bin.

In zx84 the BASIC (lines 10, 9500) has drawn the frame and the texts when it calls USR 49500
(start_music, C15Ch); the line animation has not started yet. tools/make_screen.py makes the
data of the port from this file (6912 bytes: pixels 4000h-57FFh, attributes 5800h-5AFFh).
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from zx84 import ZX84
import boot as B

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))


def read_mem(zx, a, n):
    out = bytearray()
    while n > 0:
        k = min(n, 1024)
        for line in zx.call('read_memory', address='%04X' % a, length=k).split('\n'):
            m = re.match(r'^([0-9A-F]{4})\s+((?:[0-9A-F]{2} ?)+)', line)
            if m:
                out += bytes.fromhex(m.group(2).replace(' ', ''))
        a += k
        n -= k
    return bytes(out)


def main():
    with ZX84() as zx:
        zx.call('model', target='128k')
        zx.call('load', file=B.make_boot_tap())
        B.run_until(zx, '48 BASIC', 400)
        for _ in range(3):
            B.key(zx, 'down')
        B.key(zx, 'enter')
        B.run_until(zx, '1982', 400, 10)
        for k in ('j', 'sym+p', 'sym+p', 'enter'):
            B.key(zx, k)
        B.run_until(zx, 'enter.', 8000, 250)
        zx.call('breakpoint', address='C15C')
        zx.call('key', name='enter', frames=5)
        r = zx.call('continue', max_frames=500)
        regs = zx.call('registers')
        if 'PC  C15C' not in regs:
            raise RuntimeError('no stop at C15C: %s\n%s' % (r, regs))
        scr = read_mem(zx, 0x4000, 6912)
    assert len(scr) == 6912
    path = os.path.join(ROOT, 'build', 'zx_start_screen.bin')
    open(path, 'wb').write(scr)
    print('saved', path)


if __name__ == '__main__':
    main()
