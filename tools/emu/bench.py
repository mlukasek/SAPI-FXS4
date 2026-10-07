#!/usr/bin/env python3
"""Time of the work of a frame of the port in SAPIemu, by parts, at 4 and 2 MHz.

  bench.py [FRAMES]     default 20 frames each
Prints the parts of one frame (in 4 MHz cycles, as the MCP counts them), the frame work in ms
(budget 20 ms) and the frames that came while the last one still ran (frames_lost) in 10 s.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sapimcp as sm
import port

PARTS = ['isr_work', 'vu_cga', 'scroller', 'frame', 'tick', 'opl_update', 'zx_flush_frame', 'zff_end']


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    sym = port.symbols()
    for turbo in (True, False):
        port.start()
        sm.call('cpu_turbo', on=turbo)
        sm.call('run_for', ms=500)
        total = []
        for k in range(n):
            prev = first = None
            parts = []
            for name in PARTS:
                c = sm.call('run_until', address='%04X' % sym[name], timeout_ms=1000)['cycles']
                if first is None:
                    first = c
                if prev is not None:
                    parts.append('%s %d' % (name, c - prev))
                prev = c
            total.append((prev - first) / 4000.0)
            if k == 0:
                print('  ' + ' | '.join(parts))
        lost0 = port.read(sym['frames_lost'], 1)[0]
        sm.call('run_for', ms=10000)
        lost = (port.read(sym['frames_lost'], 1)[0] - lost0) & 0xFF
        print('%d MHz: frame work %.1f ms average, %.1f ms longest; late frames in 10 s: %d'
              % (4 if turbo else 2, sum(total) / n, max(total), lost))
    sm.call('cpu_turbo', on=True)


if __name__ == '__main__':
    main()
