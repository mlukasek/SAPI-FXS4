#!/usr/bin/env python3
"""Check that orig/fxs4.asm assembles to the CODE block of the original (Demos/FXSOUND4.TAP)."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkdis import load_image, ROOT, CODE_START

PASMO = os.environ.get('PASMO', r'E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe')
out = os.path.join(ROOT, 'build')
os.makedirs(out, exist_ok=True)
binf, symf = os.path.join(out, 'orig.bin'), os.path.join(out, 'orig.sym')
subprocess.check_call([PASMO, '--bin', os.path.join(ROOT, 'orig', 'fxs4.asm'), binf, symf])
b = open(binf, 'rb').read()
m = load_image()[CODE_START:]
d = [CODE_START + i for i in range(max(len(b), len(m))) if i >= len(b) or i >= len(m) or b[i] != m[i]]
print('%04X-FFFF: %s' % (CODE_START, 'OK' if not d else '%d bytes differ, first %04X (length %d, expected %d)'
                         % (len(d), d[0], len(b), len(m))))
sys.exit(1 if d else 0)
