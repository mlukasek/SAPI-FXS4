#!/usr/bin/env python3
"""Disassemble Fuxoft Soundtrack IV (ZX Spectrum) into pasmo source.

The memory image is the CODE block of Demos/FXSOUND4.TAP at 744Ah-FFFFh.
Code is found by recursive descent from known entry points (tools/annot.py)
plus every address listed in build/exec*.txt (executed PCs, one hex address
per line, from an emulator trace when one is available). The song data layout
comes from playing every song in the player model (tools/player.py); jumps
'80 w' that the songs never reach are added when w is a known stream start.

  mkdis.py report      code/data map, conflicts, immediate operands to review
  mkdis.py map         ranges of code and data
  mkdis.py asm OUT     write the source (assembles to the same image)
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80dis import decode
import annot
import player

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TAP = os.path.join(ROOT, 'Demos', 'FXSOUND4.TAP')
CODE_START = 0x744A


def tap_blocks(path=TAP):
    """List of TAP blocks (flag byte + data, without the length and the checksum)."""
    d = open(path, 'rb').read()
    out, i = [], 0
    while i < len(d):
        n = d[i] | d[i + 1] << 8
        out.append(d[i + 2:i + 1 + n])
        i += 2 + n
    return out


def load_image():
    """64 KB memory with the CODE block at 744Ah (the state before RUN)."""
    blocks = tap_blocks()
    code = blocks[3][1:]
    m = bytearray(65536)
    m[CODE_START:CODE_START + len(code)] = code
    return m


SEGS = annot.SEGMENTS   # list of (start, end_exclusive, name)


def in_seg(a):
    for s, e, n in SEGS:
        if s <= a < e:
            return True
    return False


def exec_set():
    xs = set()
    for f in glob.glob(os.path.join(ROOT, 'build', 'exec*.txt')):
        for line in open(f):
            line = line.strip()
            if line:
                xs.add(int(line, 16))
    return xs


def data_kind(a):
    for t in annot.DATA_RANGES:
        if t[0] <= a < t[1]:
            return t
    return None


class Dis:
    def __init__(self):
        self.mem = load_image()
        self.ins = {}          # addr -> Ins
        self.owner = {}        # byte addr -> instruction start
        self.inline = {}       # addr -> length of inline data after rst 08h / rst 28h
        self.conflicts = []
        self.xs = exec_set()
        self.names = dict(annot.NAMES)
        self.song = player.coverage(self.mem, annot.SONGS)
        self.static_items = set()

    def song_names(self):
        """Parse the song bytes the player never reads (tails of streams, unused envelopes)."""
        s, m = self.song, self.mem
        for s_, e_ in annot.SONG_RANGES:
            a = s_
            while a < e_:
                if a in s.kind or a in self.owner:
                    a += 1
                    continue
                b = a
                while b < e_ and b not in s.kind and b not in self.owner:
                    b += 1
                prev = s.kind.get(a - 1)
                items = None
                if any(m[k] for k in range(a, b)):
                    for kind in [prev] + [k for k in ('env', 'fx', 'note') if k != prev]:
                        if kind in ('note', 'env', 'fx'):
                            items = parse_static(m, kind, a, b, s.items)
                            if items:
                                break
                if items:
                    for p, n, wa in items:
                        for k in range(p, p + n):
                            s.kind[k] = kind
                        s.items[p] = (kind, n)
                        self.static_items.add(p)
                        if wa is not None:
                            t = m[wa] | m[wa + 1] << 8
                            s.words[wa] = t
                            if t not in s.starts and t not in s.code:
                                s.starts[t] = s.kind.get(t, kind)
                a = b
        prefix = {'note': 'nt', 'env': 'env', 'fx': 'fx'}
        for a, k in s.starts.items():
            self.names.setdefault(a, '%s_%04X' % (prefix[k], a))
        for key, a in annot.SONGS:
            self.names.setdefault(a, 'song_' + key if key != '-' else 'song_nokey')

    def descend(self, seeds):
        todo = list(seeds)
        while todo:
            a = todo.pop()
            while True:
                if a in self.ins or not in_seg(a):
                    break
                if a in annot.DATA_FORCE or data_kind(a) or a in self.song.kind:
                    self.conflicts.append((a, 'descent into data'))
                    break
                i = decode(self.mem, a)
                clash = [b for b in range(a, a + i.length) if b in self.owner]
                if clash:
                    self.conflicts.append((a, 'overlaps instruction at %04X' % self.owner[clash[0]]))
                    break
                self.ins[a] = i
                for b in range(a, a + i.length):
                    self.owner[b] = a
                if i.target is not None and i.flow in ('jump', 'cjump', 'call', 'ccall'):
                    todo.append(i.target)
                if i.flow in ('jump', 'ret', 'stop'):
                    break
                if a in annot.NORETURN_AFTER:
                    break
                if i.flow in ('call', 'ccall') and i.target in annot.NORETURN:
                    if i.flow == 'call':
                        break
                if i.flow == 'rst' and i.target == 0x08:
                    # ROM error restart: one byte of error code follows, no return
                    self.inline[a + 1] = 1
                    self.owner[a + 1] = a + 1
                    break
                if i.flow == 'rst' and i.target == 0x28:
                    # ROM calculator: literal bytes up to and including 38h (end-calc)
                    n = 0
                    while self.mem[a + 1 + n] != 0x38:
                        n += 1
                    self.inline[a + 1] = n + 1
                    for b in range(a + 1, a + 2 + n):
                        self.owner[b] = a + 1
                    a += 1 + n + 1
                    continue
                a += i.length

    def run(self):
        self.run_code()
        self.song_names()

    def run_code(self):
        seeds = list(annot.ENTRIES)
        prev = False
        for a in range(65536):
            x = a in self.xs
            if x and not prev and in_seg(a) and a not in annot.DATA_FORCE:
                seeds.append(a)
            prev = x
        self.descend(seeds)
        self.uncovered = sorted(a for a in self.xs if in_seg(a) and a not in self.owner
                                and a not in annot.DATA_FORCE)

    # ---- labels
    def refs(self):
        """address -> set of kinds that reference it"""
        refs = {}
        for a, i in self.ins.items():
            if i.target is not None and i.flow != 'rst':
                refs.setdefault(i.target, set()).add(i.flow)
            if i.nn is not None and i.nn_kind == 'mem':
                refs.setdefault(i.nn, set()).add('mem')
            if i.nn is not None and i.nn_kind == 'imm' and self.imm_is_addr(a, i):
                refs.setdefault(i.nn, set()).add('imm')
        for t in annot.DATA_RANGES:
            s, e, kind = t[0], t[1], t[2]
            if kind == 'dw':
                for p in range(s, e, 2):
                    v = self.mem[p] | self.mem[p + 1] << 8
                    if self.dw_is_addr(v):
                        refs.setdefault(v, set()).add('dw')
        for a, v in self.song.words.items():
            refs.setdefault(v, set()).add('dw')
        for key, a in annot.SONGS:
            refs.setdefault(a, set()).add('song')
        for a in annot.NAMES:
            refs.setdefault(a, set()).add('name')
        return refs

    def dw_is_addr(self, v):
        return in_seg(v) or v in annot.EQU

    def imm_is_addr(self, a, i):
        if a in annot.IMM_NUM:
            return False
        if a in annot.IMM_ADDR:
            return True
        return any(s <= i.nn < e for s, e in annot.IMM_RANGES) or i.nn in annot.EQU

    def label(self, v):
        if v in self.names:
            return self.names[v]
        if v in annot.EQU:
            return annot.EQU[v]
        return 'L%04X' % v


def parse_static(m, kind, a, end, items):
    """Items [(addr, length, word operand addr)] covering a..end exactly, or None.
    Zero bytes after a final jump or return are padding and stay outside.
    A word operand must point to an item start or to a machine code stub."""
    while end > a and m[end - 1] == 0:
        end -= 1
    out, p = [], a
    while p < end:
        c = m[p]
        if kind == 'note':
            if c < 0x80:
                n, wa = 2, None
            elif c in player.NOTE_ARGS:
                n = {'w': 3, 'b': 2, '': 1}[player.NOTE_ARGS[c]]
                wa = p + 1 if n == 3 else None
            else:
                return None
        elif c == 0x80:
            n, wa = 3, p + 1
        else:
            n, wa = (2 if kind == 'env' and c < 0x1E else 1), None
        out.append((p, n, wa))
        p += n
    if p == end:
        pass
    elif p == end + 1 and m[end] == 0:      # the last item ends with a zero byte
        pass
    else:
        return None
    if not out:
        return None
    starts = {q for q, _, _ in out}
    for q, n, wa in out:
        if wa is not None:
            t = m[wa] | m[wa + 1] << 8
            if t not in items and t not in starts and t not in player.CODE_STUBS:
                return None
    return out


def hx(v, w=2):
    s = ('%0' + str(w) + 'X') % v
    return ('0' + s if s[0] in 'ABCDEF' else s) + 'h'


def code_map(d):
    """[(start, end_exclusive, 'code'|'data')] over the segments."""
    out = []
    for s, e, _ in SEGS:
        a = s
        while a < e:
            c = a in d.owner and a not in d.inline and d.owner[a] in d.ins
            b = a + 1
            while b < e and (b in d.owner and d.owner[b] in d.ins and b not in d.inline) == c:
                b += 1
            out.append((a, b, 'code' if c else 'data'))
            a = b
    return out


def report(d):
    print('conflicts:')
    for a, why in d.conflicts:
        print('  %04X %s' % (a, why))
    print('executed but not decoded:', ' '.join('%04X' % a for a in d.uncovered[:200]))
    code = sorted(d.ins)
    print('instructions:', len(code), ' not executed:', sum(1 for a in code if a not in d.xs))
    print('immediates treated as addresses:')
    for a in sorted(d.ins):
        i = d.ins[a]
        if i.nn is not None and i.nn_kind == 'imm' and d.imm_is_addr(a, i) and a not in annot.IMM_ADDR:
            print('  %04X  %s' % (a, i.render()))
    print('immediates treated as numbers (16-bit, >= 0100h):')
    for a in sorted(d.ins):
        i = d.ins[a]
        if i.nn is not None and i.nn_kind == 'imm' and not d.imm_is_addr(a, i) and i.nn >= 0x100:
            print('  %04X  %s' % (a, i.render()))


CMD = {0x80: 'jump', 0x81: 'call', 0x82: 'loop', 0x83: 'end loop', 0x84: 'noise', 0x85: 'mixer',
       0x86: 'pitch effect', 0x87: 'envelope', 0x88: 'transpose', 0x89: 'return', 0x8A: 'legato on',
       0x8B: 'legato off', 0x8C: 'machine code', 0x8D: 'noise +', 0x8E: 'transpose +'}


def write_song_item(d, refs, w, a, lab):
    """Write one song data item (or a run of short ones), return the next address."""
    mem, s = d.mem, d.song
    kind, n = s.items[a]
    pfx = (lab + ':') if lab else ''
    if kind == 'hdr':
        key = [k for k, h in annot.SONGS if h == a][0]
        key = key if key != '-' else '27 (no key selects it)'
        w('%-40s; %04X  song %s: channels A, B, C' % (
            '%s\tdefw %s' % (pfx, ','.join(d.label(s.words[a + 2 * k]) for k in range(3))), a, key))
        return a + 6
    if n == 3:
        c = mem[a]
        what = 'jump' if kind != 'note' else CMD[c]
        if a in d.static_items:
            what += ' (never reached)'
        w('%-40s; %04X  %s' % ('%s\tdefb %s' % (pfx, hx(c)), a, what))
        w('%-40s; %04X' % ('\tdefw %s' % d.label(s.words[a + 1]), a + 1))
        return a + 3
    if kind == 'note' and mem[a] >= 0x80:
        c = mem[a]
        what = CMD[c] + (' %d' % mem[a + 1] if n == 2 else '')
        w('%-40s; %04X  %s' % ('%s\tdefb %s' % (pfx, ','.join(hx(mem[k]) for k in range(a, a + n))), a, what))
        return a + n
    # run of notes / envelope steps / pitch steps
    b = a + n
    while b - a < 16 and b in s.items and s.items[b][0] == kind and s.items[b][1] < 3 and b not in refs \
            and b not in annot.COMMENTS and not (kind == 'note' and mem[b] >= 0x80) \
            and b + s.items[b][1] - a <= 16:
        b += s.items[b][1]
    w('%-40s; %04X' % ('%s\tdefb %s' % (pfx, ','.join(hx(mem[k]) for k in range(a, b))), a))
    return b


def write_asm(d, path):
    refs = d.refs()
    mem = d.mem
    out = []
    w = out.append
    w('; Fuxoft Soundtrack IV (Frantisek Fuka), ZX Spectrum - disassembly generated by tools/mkdis.py')
    w('; CODE block of Demos/FXSOUND4.TAP, 744Ah-FFFFh. Assembles with pasmo 0.5.3.')
    w('; Edit tools/annot.py and regenerate, do not edit this file.')
    w('')
    used_equ = sorted(v for v in refs if not in_seg(v))
    for v in used_equ:
        w('%-16s equ %s' % (d.label(v), hx(v, 4)))
    w('')
    for s, e, segname in SEGS:
        w('; ' + '=' * 70)
        w('; %s %04X-%04X' % (segname, s, e - 1))
        w('')
        w('\torg %s' % hx(s, 4))
        a = s
        while a < e:
            if a in annot.COMMENTS:
                for c in annot.COMMENTS[a].split('\n'):
                    w('; ' + c if c else ';')
            lab = d.label(a) if a in refs else None
            if a in d.ins:
                i = d.ins[a]
                nn = None
                if i.nn is not None:
                    use = (i.nn_kind in ('jump', 'call', 'mem')) or (i.nn_kind == 'imm' and d.imm_is_addr(a, i))
                    if use and i.nn in refs:
                        nn = d.label(i.nn)
                e_ = d.label(i.e) if i.e is not None else None
                text = i.render(nn, e_)
                if i.undoc and not text.startswith('defb'):
                    text = 'defb ' + ','.join(hx(b) for b in i.bytes) + '\t; ' + text
                cmt = annot.LINE_CMT.get(a, '')
                line = '%s\t%s' % ((lab + ':') if lab else '', text)
                w('%-40s; %04X%s' % (line, a, ('  ' + cmt) if cmt else ''))
                for k in range(1, i.length):
                    if a + k in refs:
                        w('%-16s equ $-%d' % (d.label(a + k), i.length - k))
                a += i.length
                continue
            if a in d.inline:
                n = d.inline[a]
                w('%-40s; %04X' % ('%s\tdefb %s' % ((lab + ':') if lab else '',
                                                    ','.join(hx(mem[k]) for k in range(a, a + n))), a))
                a += n
                continue
            if a in d.song.items:
                a = write_song_item(d, refs, w, a, lab)
                continue
            rng = data_kind(a)
            kind = rng[2] if rng else 'db'
            if kind in ('dw', 'dwn') and (a - rng[0]) % 2 == 0 and a + 1 < rng[1]:
                v = mem[a] | mem[a + 1] << 8
                txt = d.label(v) if (kind == 'dw' and v in refs and d.dw_is_addr(v)) else hx(v, 4)
                w('%-40s; %04X' % ('%s\tdefw %s' % ((lab + ':') if lab else '', txt), a))
                if a + 1 in refs:
                    w('%-16s equ $-1' % d.label(a + 1))
                a += 2
                continue

            def stop(b):
                return b >= e or b in refs or b in d.ins or b in d.inline or b in annot.COMMENTS \
                    or data_kind(b) is not rng

            if kind == 'text' and 0x20 <= mem[a] < 0x7F and mem[a] not in b'"\\':
                b = a + 1
                while not stop(b) and b - a < 64 and 0x20 <= mem[b] < 0x7F and mem[b] not in b'"\\':
                    b += 1
                w('%-40s; %04X' % ('%s\tdefm "%s"' % ((lab + ':') if lab else '',
                                                    bytes(mem[a:b]).decode('latin1')), a))
                a = b
                continue
            if kind == 'font' and (a - rng[0]) % 8 == 0:
                w('%-40s; %04X  %r' % ('%s\tdefb %s' % ((lab + ':') if lab else '',
                                                        ','.join(hx(mem[k]) for k in range(a, a + 8))),
                                       a, chr(0x20 + (a - rng[0]) // 8)))
                a += 8
                continue
            b = a + 1
            while not stop(b) and b - a < 16 and b not in d.song.items:
                b += 1
            if b - a == 16 and all(mem[k] == 0 for k in range(a, b)):
                z = a + 1
                while not stop(z) and mem[z] == 0:
                    z += 1
                w('%-40s; %04X' % ('%s\tdefs %d' % ((lab + ':') if lab else '', z - a), a))
                a = z
                continue
            w('%-40s; %04X' % ('%s\tdefb %s' % ((lab + ':') if lab else '',
                                                ','.join(hx(mem[k]) for k in range(a, b))), a))
            a = b
        w('')
    w('\tend')
    open(path, 'w', newline='\n').write('\n'.join(out) + '\n')


def main():
    d = Dis()
    d.run()
    if sys.argv[1] == 'report':
        report(d)
    elif sys.argv[1] == 'map':
        for s, e, k in code_map(d):
            print('%04X-%04X %-4s %d' % (s, e - 1, k, e - s))
    elif sys.argv[1] == 'asm':
        write_asm(d, sys.argv[2])


if __name__ == '__main__':
    main()
