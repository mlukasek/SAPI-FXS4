#!/usr/bin/env python3
"""Python model of the Fuxoft Soundtrack IV AY player (C359h init, C544h tick).

It follows the Z80 code step by step (same memory, same channel stacks) and
records which song bytes are read and how: this gives the exact layout of the
song data for tools/mkdis.py and an AY register log for every tick.

Channel block (ix = C460h, C474h, C488h for channels A, B, C):
  +0/1 note stream   +2 note counter   +3 mixer bits (8 = tone)   +4/5 envelope pointer
  +6 envelope counter   +7/8 tone period   +9 volume   +10/11 envelope start
  +12/13 pitch effect pointer   +14 flags (0 legato, 1 legato running, 2 new note,
  3 pitch steps in semitones)
  +15 transpose   +16/17 pitch effect start   +18 current note

A song header is 3 words: note streams of AY channels A, B, C (copied to C835h).

Note stream (channel ix+0/1, read at C6BFh):
  00 d          rest, duration d
  01-7F d       note (+ transpose ix+15), duration d
  80 w          jump to w                    81 w   call w (return by 89)
  82 n          loop start, n times           83     loop end
  84 n          noise period (C3F4h)          85 n   mixer bits of the channel (ix+3)
  86 w          pitch effect stream (ix+16)   87 w   volume envelope stream (ix+10)
  88 n          transpose = n                 89     return
  8A / 8B       legato on / off (envelope      8C w   call machine code at w
                not restarted by later notes)
  8D n          noise period += n             8E n   transpose += n
Volume envelope stream (ix+4/5, read at C5C3h): v d (v < 1Eh), v (>= 1Eh: volume
v-32h for one tick), 80 w (jump). Pitch effect stream (ix+12/13, read at C60Fh):
80 w (jump), 82 / 83 (later steps in semitones / in tone period), 84 (swap tone
and noise of the channel), other bytes are signed pitch steps (one per tick).

  player.py log KEY [TICKS]   print the AY registers R0-R13 for every tick of song KEY
  player.py cover [TICKS]     play all songs, report conflicts in the data layout
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AYREG = 0xC3E6      # shadow of R0-R13
NOISE = 0xC3F4
TABLE = 0xC49C      # tone periods, note 1 = table[0]
CMD_TABLE = 0xC752
CHANNELS = (0xC460, 0xC474, 0xC488)
STACKS = (0xC420, 0xC440, 0xC460)
NOISE_MASK = 0xC81C   # operand of 'and 1Fh' in command 8Dh, set per song
NOTE_ARGS = {0x80: 'w', 0x81: 'w', 0x82: 'b', 0x83: '', 0x84: 'b', 0x85: 'b', 0x86: 'w', 0x87: 'w',
             0x88: 'b', 0x89: '', 0x8A: '', 0x8B: '', 0x8C: 'w', 0x8D: 'b', 0x8E: 'b'}
# Start of the Spectrum ROM (48K ROM = 128K ROM 1 up to 004Ah). A channel without command 86h
# has its pitch effect pointer at 0000h (cleared by init_song), so songs E, F and R read
# 0000h-0026h as pitch steps.
ROM_HEAD = bytes.fromhex(
    'F3AF11FFFFC3CB112A5D5C225F5C1843C3F215FFFFFFFFFF2A5D5C7ECD7D00D0'
    'CD740018F7FFFFFFC35B33FFFFFFFFFFC52A615CE5C39E16F5E52A785C232278')
CODE_STUBS = {0x86AA, 0x86AE}   # 8Ch targets: ld (0000h),a with A = 2 / 1 (no effect on the Spectrum)


class Player:
    def __init__(self, mem):
        self.m = bytearray(mem)
        self.m[0:len(ROM_HEAD)] = ROM_HEAD
        self.kind = {}       # byte addr -> 'note' | 'env' | 'fx' | 'hdr'
        self.items = {}      # item start -> (kind, length)
        self.words = {}      # address of a pointer operand -> target
        self.starts = {}     # stream start -> kind
        self.code = set()
        self.errors = []

    # ---- memory
    def w16(self, a):
        return self.m[a] | self.m[(a + 1) & 0xFFFF] << 8

    def put16(self, a, v):
        self.m[a] = v & 0xFF
        self.m[(a + 1) & 0xFFFF] = v >> 8 & 0xFF

    def item(self, a, n, kind):
        for b in range(a, a + n):
            k = self.kind.get(b)
            if k is not None and k != kind:
                self.errors.append('%04X: %s over %s' % (b, kind, k))
            self.kind[b] = kind
        old = self.items.get(a)
        if old is not None and old != (kind, n):
            self.errors.append('%04X: item %s/%d over %s/%d' % (a, kind, n, old[0], old[1]))
        self.items[a] = (kind, n)

    def ptr(self, a, kind):
        t = self.w16(a)
        self.words[a] = t
        if kind:
            k = self.starts.get(t)
            if k is not None and k != kind:
                self.errors.append('%04X: start %s and %s' % (t, kind, k))
            self.starts[t] = kind
        return t

    def reg(self, r, v):
        self.m[AYREG + r] = v & 0xFF

    # ---- channel stack (the player runs each channel with SP = its stack)
    def push(self, v):
        self.sp = (self.sp - 2) & 0xFFFF
        self.put16(self.sp, v)

    def pop(self):
        v = self.w16(self.sp)
        self.sp = (self.sp + 2) & 0xFFFF
        return v

    # ---- C359h
    def start(self, key, header):
        self.item(header, 6, 'hdr')
        self.m[NOISE_MASK] = 0x0F if key in 'ABCDEFGHIJK' else 0x1F
        for k in range(3):
            self.put16(0xC835 + 2 * k, self.ptr(header + 2 * k, 'note'))
        for k, ix in enumerate(CHANNELS):
            self.put16(ix, self.w16(0xC835 + 2 * k))
            self.m[ix + 2] = 1
            self.m[ix + 3] = 8
            self.put16(ix + 14, 0)
            self.put16(ix + 16, 0)
            self.put16(0xC3FA + 2 * k, STACKS[k])
        self.m[NOISE] = 0

    # ---- C544h
    def tick(self):
        for k, ix in enumerate(CHANNELS):
            self.sp = self.w16(0xC3FA + 2 * k)
            self.channel(ix, k + 1)
            self.put16(0xC3FA + 2 * k, self.sp)
        m = self.m
        mix = (((m[0xC48B] << 1 | m[0xC48B] >> 7) & 0xFF) | m[0xC477]) & 0xFF
        mix = ((mix << 1 | mix >> 7) & 0xFF) | m[0xC463]
        self.reg(7, mix)
        return list(m[AYREG:AYREG + 14])

    # ---- C5B0h
    def channel(self, ix, ch):
        m = self.m
        m[ix + 2] = (m[ix + 2] - 1) & 0xFF
        if m[ix + 2] == 0:
            if self.new_note(ix):
                self.envelope(ix)
                self.pitch(ix)
        else:
            self.envelope(ix)
            self.pitch(ix)
        self.out(ix, ch)

    def envelope(self, ix):          # C5BEh
        m = self.m
        m[ix + 6] = (m[ix + 6] - 1) & 0xFF
        if m[ix + 6]:
            return
        hl = self.w16(ix + 4)
        while True:
            a = m[hl]
            if a == 0x80:
                self.item(hl, 3, 'env')
                hl = self.ptr(hl + 1, 'env')
                continue
            if a >= 0x1E:
                self.item(hl, 1, 'env')
                m[ix + 9] = (a - 0x32) & 0xFF
                m[ix + 6] = 1
                hl += 1
            else:
                self.item(hl, 2, 'env')
                m[ix + 9] = a
                m[ix + 6] = m[hl + 1]
                hl += 2
            break
        self.put16(ix + 4, hl)

    def pitch(self, ix):             # C5F9h
        m = self.m
        if self.w16(ix + 7) == 0 or m[ix + 14] & 4:
            return
        hl = self.w16(ix + 12)
        while True:
            a = m[hl]
            if a == 0x80:
                self.item(hl, 3, 'fx')
                t = self.ptr(hl + 1, 'fx')
                self.put16(ix + 12, (hl + 1) & 0xFFFF)
                hl = t
                continue
            self.item(hl, 1, 'fx')
            hl += 1
            self.put16(ix + 12, hl)
            if a == 0x82:
                m[ix + 14] |= 8
            elif a == 0x83:
                m[ix + 14] &= ~8 & 0xFF
            elif a == 0x84:
                m[ix + 3] ^= 9
            elif m[ix + 14] & 8:
                n = (m[ix + 18] + a) & 0xFF
                m[ix + 18] = n
                self.put16(ix + 7, self.w16(TABLE + ((2 * (n - 1)) & 0xFF)))
                return
            else:
                d = a - 256 if a & 0x80 else a
                self.put16(ix + 7, (self.w16(ix + 7) + d) & 0xFFFF)
                return

    def out(self, ix, ch):           # C682h
        m = self.m
        self.reg(6, m[NOISE])
        m[ix + 14] &= ~4 & 0xFF
        self.reg(ch + 7, m[ix + 9] if self.w16(ix + 7) else 0)
        self.reg(2 * (ch - 1), m[ix + 7])
        self.reg(2 * (ch - 1) + 1, m[ix + 8])

    def new_note(self, ix):
        """C6BFh. Returns True when the envelope and the pitch run in this tick (jp C5BEh)."""
        m = self.m
        while True:
            hl = self.w16(ix)
            a = m[hl]
            if a & 0x80:
                self.command(ix, hl, a)
                continue
            self.item(hl, 2, 'note')
            if a:
                n = (a + m[ix + 15]) & 0xFF
                m[ix + 18] = n
                m[ix + 14] &= ~8 & 0xFF
                de = self.w16(TABLE + ((2 * (n - 1)) & 0xFF))
            else:
                de = 0
            m[ix + 2] = m[hl + 1]
            self.put16(ix, hl + 2)
            self.put16(ix + 7, de)
            self.put16(ix + 12, self.w16(ix + 16))
            m[ix + 14] |= 4
            if m[ix + 14] & 2:
                return True
            if m[ix + 14] & 1:
                m[ix + 14] |= 2
            bc = self.w16(ix + 10)
            self.item(bc, 2, 'env')
            m[ix + 9] = m[bc]
            m[ix + 6] = m[bc + 1]
            self.put16(ix + 4, bc + 2)
            return False

    def command(self, ix, hl, a):    # C73Ch and the handlers C770h-C834h
        m = self.m
        c = a & 0x7F
        p = hl + 1
        if c in (0, 1, 6, 7, 0xC):
            self.item(hl, 3, 'note')
            t = self.ptr(p, {0: 'note', 1: 'note', 6: 'fx', 7: 'env', 0xC: None}[c])
            if c == 0:
                self.put16(ix, t)
            elif c == 1:
                self.put16(ix, t)
                self.push(hl + 3)
            elif c == 6:
                self.put16(ix + 16, t)
                self.put16(ix, hl + 3)
            elif c == 7:
                self.put16(ix + 10, t)
                self.put16(ix, hl + 3)
            else:
                self.code.add(t)
                if t not in CODE_STUBS:
                    self.errors.append('%04X: call to unknown code %04X' % (hl, t))
                self.put16(ix, hl + 3)
        elif c in (2, 4, 5, 8, 0xD, 0xE):
            self.item(hl, 2, 'note')
            n = m[p]
            self.put16(ix, hl + 2)
            if c == 2:
                self.push(n << 8 | (self.sp_c() & 0xFF))    # push bc: B = count, C = what it was
                self.push(hl + 2)
            elif c == 4:
                m[NOISE] = n
            elif c == 5:
                m[ix + 3] = n
            elif c == 8:
                m[ix + 15] = n
            elif c == 0xD:
                m[NOISE] = (m[NOISE] + n) & m[NOISE_MASK]
            else:
                m[ix + 15] = (m[ix + 15] + n) & 0xFF
        elif c in (3, 9, 0xA, 0xB):
            self.item(hl, 1, 'note')
            self.put16(ix, hl + 1)
            if c == 3:
                de = self.pop()
                bc = self.pop()
                b = (bc >> 8) - 1 & 0xFF
                if b:
                    self.push(b << 8 | bc & 0xFF)
                    self.push(de)
                    self.put16(ix, de)
            elif c == 9:
                self.put16(ix, self.pop())
            elif c == 0xA:
                m[ix + 14] = (m[ix + 14] | 1) & ~2 & 0xFF
            else:
                m[ix + 14] &= ~3 & 0xFF
        else:
            self.errors.append('%04X: bad command %02X' % (hl, a))
            raise RuntimeError(self.errors[-1])

    def sp_c(self):
        # value of C at 'push bc' in command 82h: C still holds the low byte of the
        # pointer the dispatcher loaded (it does not matter, 83h only uses B)
        return 0


def run_song(p, key, header, ticks):
    p.start(key, header)
    return [p.tick() for _ in range(ticks)]


def coverage(mem, songs, ticks=30000):
    """Play every song from a fresh image and merge the song data layouts."""
    total = Player(mem)
    for key, h in songs:
        p = Player(mem)
        p.kind, p.items, p.words, p.starts, p.code, p.errors = \
            total.kind, total.items, total.words, total.starts, total.code, total.errors
        run_song(p, key, h, ticks)
    return total


if __name__ == '__main__':
    import mkdis, annot
    mem = mkdis.load_image()
    if sys.argv[1] == 'log':
        key = sys.argv[2].upper()
        h = dict(annot.SONGS)[key]
        p = Player(mem)
        for t, r in enumerate(run_song(p, key, h, int(sys.argv[3]) if len(sys.argv) > 3 else 500)):
            print('%5d ' % t + ' '.join('%02X' % v for v in r))
    elif sys.argv[1] == 'cover':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30000
        c = coverage(mem, annot.SONGS, n)
        print('errors:', len(c.errors))
        for e in c.errors[:30]:
            print('  ' + e)
        print('bytes:', len(c.kind), 'streams:', {k: sum(1 for v in c.starts.values() if v == k)
                                                    for k in ('note', 'env', 'fx')})
        print('code:', ' '.join('%04X' % a for a in sorted(c.code)))
