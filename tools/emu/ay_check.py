#!/usr/bin/env python3
"""The AY registers of the port in SAPIemu (ay_regs at each opl_update) against tools/player.py.

The port starts song A; the first opl_update is the silence of stop_music, then one per tick.
A song key is typed on the keyboard of the emulator (the song restarts while the key is held,
see KEY_HOLD in platform.asm): ticks after the last silence are compared.

  ay_check.py [TICKS] [KEYS]     default 300 ticks, song A (from the start) only
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
import sapimcp as sm
import port
import mkdis, annot, player


def snapshots(sym, n):
    """n + a few register snapshots from opl_update on."""
    out = []
    for _ in range(n):
        r = sm.call('run_until', address='%04X' % sym['opl_update'], timeout_ms=1000)
        if r.get('stopped') == 'timeout':
            raise RuntimeError('opl_update not reached: %r' % r)
        out.append(list(port.read(sym['ay_regs'], 14)))
        sm.call('step')
    return out


def ticks_after_silence(snaps):
    last = max(i for i, s in enumerate(snaps) if s[7] == 0xFF)
    return snaps[last + 1:]


def compare(key, real, ticks):
    mem = mkdis.load_image()
    model = player.run_song(player.Player(mem), key, dict(annot.SONGS)[key], len(real))
    diff = [i for i in range(len(real)) if real[i] != model[i]]
    if diff:
        i = diff[0]
        print('%s: %d ticks, %d differ, first %d' % (key, len(real), len(diff), i))
        print('   port  ' + ' '.join('%02X' % v for v in real[i]))
        print('   model ' + ' '.join('%02X' % v for v in model[i]))
        return False
    print('%s: %d ticks OK' % (key, len(real)))
    return True


def main():
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    keys = sys.argv[2].upper() if len(sys.argv) > 2 else 'A'
    sym = port.symbols()
    port.start()
    ok = True
    for k in keys:
        if k != 'A' or keys.index(k) > 0:
            sm.call('type_text', text=k.lower())
            snaps = snapshots(sym, ticks + 40)
        else:
            snaps = snapshots(sym, ticks + 1)
        real = ticks_after_silence(snaps)[:ticks]
        ok &= compare(k, real, ticks)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
