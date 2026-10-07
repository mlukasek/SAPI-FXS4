#!/usr/bin/env python3
"""Compare the AY registers of the original in zx84 with the player model (tools/player.py).

For each song: press its key (the song restarts while the key is held), then log every AY data
write through a trap on 'out (c),a' in ay_write (C593h: D = register, A = value). A tick is the
14 writes R13..R0; ticks after the last stop_music (C3D7h, called by every restart, it writes
silence first) are compared
with player.run_song() from the TAP image.

  ay_compare.py [TICKS] [KEYS]     default 1500 ticks, all songs A-Z and - (the 27th, no key)
  ay_compare.py 1500 ABC --save    also write build/ay_<key>.txt (one tick per line, R0-R13 hex)
"""
import os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
from zx84 import ZX84
import boot as B
import mkdis, annot, player

LINE = re.compile(r'\[([0-9A-F]{4})\] (\w+)\s+C=..\s+DE=([0-9A-F]{2})..\s+A=([0-9A-F]{2})')


def read_log(zx):
    """All trap log entries as (label, reg, value), then clear the log (it keeps 2000 lines)."""
    head = zx.call('trap_log', **{'from': 0, 'to': 1})
    total = int(re.search(r'(\d+) total', head).group(1)) if 'total' in head else 0
    if total >= 2000:
        raise RuntimeError('trap log overflow (zx84 keeps 2000 lines)')
    txt = zx.call('trap_log', **{'from': 0, 'to': total, 'clear': True}) if total else ''
    return [(m.group(2), int(m.group(3), 16), int(m.group(4), 16)) for m in LINE.finditer(txt)]


def capture(zx, key, ticks):
    zx.call('trap_log', clear=True)
    if key == '-':
        # the 27th song has no key: the operand of 'ld hl,song_Y' (C0EDh) points to it while Y is held
        zx.call('write_memory', address='C0ED', hex_bytes='A6A4')
        zx.call('key', name='y', frames=5)
        zx.call('write_memory', address='C0ED', hex_bytes='D485')
    else:
        zx.call('key', name=key.lower(), frames=5)
    log = []
    while sum(1 for e in log if e[0] == 'ay' and e[1] == 0) < ticks + 20:
        zx.call('run', frames=100)
        log += read_log(zx)
    last_stop = max(i for i, e in enumerate(log) if e[0] == 'stop')
    regs, out = [0] * 14, []
    for lab, r, v in log[last_stop + 1:]:
        if lab != 'ay':
            continue
        regs[r] = v
        if r == 0:
            out.append(list(regs))
    return out[1:ticks + 1]       # the first block is the silence written by stop_music


def main():
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    keys = sys.argv[2].upper() if len(sys.argv) > 2 else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ-'
    save = '--save' in sys.argv
    mem = mkdis.load_image()
    songs = dict(annot.SONGS)
    t0 = time.time()
    bad = 0
    with ZX84() as zx:
        B.boot(zx, log=lambda s: None)
        zx.call('trap', address='C593', action='log', label='ay')
        zx.call('trap', address='C3D7', action='log', label='stop')
        for k in keys:
            real = capture(zx, k, ticks)
            model = player.run_song(player.Player(mem), k, songs[k], ticks)
            diff = [i for i in range(min(len(real), len(model))) if real[i] != model[i]]
            if save:
                with open(os.path.join(mkdis.ROOT, 'build', 'ay_%s.txt' % k), 'w') as f:
                    for r in real:
                        f.write(' '.join('%02X' % v for v in r) + '\n')
            if diff or len(real) < ticks:
                bad += 1
                i = diff[0] if diff else len(real)
                print('%s: %d ticks, %d differ, first %d' % (k, len(real), len(diff), i))
                if diff:
                    print('   zx84  ' + ' '.join('%02X' % v for v in real[i]))
                    print('   model ' + ' '.join('%02X' % v for v in model[i]))
            else:
                print('%s: %d ticks OK' % (k, len(real)))
    print('%d of %d songs differ, %.0f s' % (bad, len(keys), time.time() - t0))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
