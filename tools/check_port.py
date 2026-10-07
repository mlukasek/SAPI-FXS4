#!/usr/bin/env python3
"""After build.cmd: the program must end below the Spectrum screen buffer (zx_screen); print the size."""
import os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def symbols(path):
    s = {}
    for line in open(path):
        m = re.match(r'^(\S+)\s+EQU\s+0?([0-9A-F]+)H', line.strip(), re.I)
        if m:
            s[m.group(1)] = int(m.group(2), 16)
    return s


def main():
    sym = symbols(os.path.join(ROOT, 'build', 'fxs4.sym'))
    size = os.path.getsize(os.path.join(ROOT, 'build', 'fxs4.com'))
    end = sym['program_end']
    limit = sym['zx_screen']
    print('build\\fxs4.com: %d bytes (0100-%04X), free up to %04X: %d bytes, in CP/M: SAVE %d FXS4.COM'
          % (size, 0x100 + size - 1, limit - 1, limit - end, (size + 255) // 256))
    if end > limit:
        print('ERROR: the program ends at %04X, in the screen buffer' % end)
        return False
    return True


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
