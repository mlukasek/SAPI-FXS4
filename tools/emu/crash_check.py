#!/usr/bin/env python3
"""Play every song of the port in SAPIemu for a while and watch for a crash (PC outside the program).

  crash_check.py [SECONDS] [KEYS]    default 20 s each, keys a-z and - (the 27th song)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sapimcp as sm
import port


def main():
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    keys = sys.argv[2].lower() if len(sys.argv) > 2 else 'abcdefghijklmnopqrstuvwxyz-'
    sym = port.symbols()
    port.start()
    sm.call('run_for', ms=1000)
    bad = []
    for k in keys:
        sm.call('type_text', text=k, run_ms=200)
        for s in range(secs):
            pc = int(sm.call('run_for', ms=1000)['registers']['pc'], 16)
            if not 0x100 <= pc < sym['program_end']:
                bad.append(k)
                print('%s: crash after %d s, PC %04X' % (k, s, pc))
                port.start()
                sm.call('run_for', ms=1000)
                break
    print('crashes: %s' % (' '.join(bad) or 'none'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
