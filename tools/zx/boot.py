#!/usr/bin/env python3
"""Boot the original in zx84: 128K in 48 BASIC mode, LOAD "", ENTER at the menu -> music plays.

zx84's 'load' resets the machine and starts the tape at once, so build/fxs4_boot.tap has a dummy
CODE block (1500 bytes) in front of Demos/FXSOUND4.TAP: the tape does not reach the original before
the 128K boot, the menu and typing LOAD "" are done (the ROM skips the dummy as 'Bytes: wait').

  boot.py [PNG]     boot and save a screenshot (zx84 writes it into its own directory)
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zx84 import ZX84, ZX84_DIR

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TAP = os.path.join(ROOT, 'Demos', 'FXSOUND4.TAP')
BOOT_TAP = os.path.join(ROOT, 'build', 'fxs4_boot.tap')


def tap_block(flag, data):
    body = bytes([flag]) + data
    x = 0
    for b in body:
        x ^= b
    body += bytes([x])
    return bytes([len(body) & 0xFF, len(body) >> 8]) + body


def make_boot_tap(dummy=1500):
    hdr = bytes([3]) + b'wait      ' + bytes([dummy & 0xFF, dummy >> 8, 0, 0x80, 0, 0x80])
    os.makedirs(os.path.dirname(BOOT_TAP), exist_ok=True)
    open(BOOT_TAP, 'wb').write(tap_block(0, hdr) + tap_block(0xFF, bytes(dummy)) + open(TAP, 'rb').read())
    return BOOT_TAP


def key(zx, name, after=5):
    zx.call('key', name=name, frames=5)
    zx.call('run', frames=after)


def ocr(zx):
    return zx.call('ocr')


def run_until(zx, text, max_frames, step=50):
    n = 0
    while n < max_frames:
        zx.call('run', frames=step)
        n += step
        if text in ocr(zx):
            return n
    raise RuntimeError('"%s" not on screen after %d frames' % (text, max_frames))


def boot(zx, log=print):
    """From any state to the music playing (song A) and the line animation running."""
    zx.call('model', target='128k')
    log(zx.call('load', file=make_boot_tap()))
    run_until(zx, '48 BASIC', 400)
    for _ in range(3):
        key(zx, 'down')
    key(zx, 'enter')
    run_until(zx, '1982', 400, 10)    # 48 BASIC ready
    key(zx, 'j')                      # LOAD
    key(zx, 'sym+p')
    key(zx, 'sym+p')
    key(zx, 'enter')
    n = run_until(zx, 'enter.', 8000, 250)      # copy prompt of BASIC line 9210
    log('loaded after %d frames' % n)
    key(zx, 'enter', 50)              # -> GO TO 2: start the music, animation loop
    log('BANKM (5B5Ch): ' + zx.call('read_memory', address='5B5C', length=1).split('\n')[0])


if __name__ == '__main__':
    t = time.time()
    with ZX84() as zx:
        boot(zx)
        zx.call('run', frames=100)
        print(ocr(zx))
        if len(sys.argv) > 1:
            print(zx.call('screenshot', file=sys.argv[1]))
    print('%.1f s' % (time.time() - t))
