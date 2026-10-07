#!/usr/bin/env python3
"""Table driven Z80 disassembler (documented + common undocumented opcodes).

decode(mem, addr) -> Ins with length, text template and operand info.
The template uses {nn} for a 16-bit operand (immediate, memory address or
jump/call target), {n} for an 8-bit immediate, {d} for an index displacement
and {e} for a relative jump target. Output syntax is pasmo compatible.
"""

R = ['b', 'c', 'd', 'e', 'h', 'l', '(hl)', 'a']
RP = ['bc', 'de', 'hl', 'sp']
RP2 = ['bc', 'de', 'hl', 'af']
CC = ['nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm']
ALU = ['add a,', 'adc a,', 'sub ', 'sbc a,', 'and ', 'xor ', 'or ', 'cp ']
ROT = ['rlc', 'rrc', 'rl', 'rr', 'sla', 'sra', 'sll', 'srl']
IM = ['0', '0', '1', '2', '0', '0', '1', '2']
BLI = {(4, 0): 'ldi', (4, 1): 'cpi', (4, 2): 'ini', (4, 3): 'outi',
       (5, 0): 'ldd', (5, 1): 'cpd', (5, 2): 'ind', (5, 3): 'outd',
       (6, 0): 'ldir', (6, 1): 'cpir', (6, 2): 'inir', (6, 3): 'otir',
       (7, 0): 'lddr', (7, 1): 'cpdr', (7, 2): 'indr', (7, 3): 'otdr'}


class Ins:
    __slots__ = ('addr', 'length', 'text', 'nn', 'nn_kind', 'n', 'd', 'e',
                 'flow', 'target', 'bytes', 'undoc')

    def __init__(self, addr):
        self.addr = addr
        self.length = 1
        self.text = ''
        self.nn = None        # 16-bit operand value
        self.nn_kind = None   # 'imm', 'mem', 'jump', 'call'
        self.n = None
        self.d = None
        self.e = None         # relative target (absolute address)
        self.flow = 'next'    # next, jump, cjump, call, ccall, ret, cret, stop, rst
        self.target = None
        self.undoc = False

    def render(self, nn=None, e=None):
        def hx(v, w):
            s = ('%0' + str(w) + 'X') % v
            return ('0' + s if s[0] in 'ABCDEF' else s) + 'h'
        t = self.text
        if '{nn}' in t:
            t = t.replace('{nn}', nn if nn is not None else hx(self.nn, 4))
        if '{n}' in t:
            t = t.replace('{n}', hx(self.n, 2))
        if '{d}' in t:
            d = self.d
            t = t.replace('{d}', ('+%d' % d) if d >= 0 else ('-%d' % -d))
        if '{e}' in t:
            t = t.replace('{e}', e if e is not None else hx(self.e, 4))
        return t


def _s8(v):
    return v - 256 if v >= 128 else v


def decode(mem, addr):
    ins = Ins(addr)
    p = addr
    rd = lambda i: mem[(p + i) & 0xFFFF]
    op = rd(0)
    idx = None
    if op in (0xDD, 0xFD):
        idx = 'ix' if op == 0xDD else 'iy'
        nxt = rd(1)
        if nxt in (0xDD, 0xFD, 0xED):
            ins.text = 'defb %s' % ('0DDh' if op == 0xDD else '0FDh')
            ins.length = 1
            ins.undoc = True
            ins.bytes = [op]
            return ins
        p += 1
        op = rd(0)
    # p points at the opcode byte
    pos = 1  # bytes consumed after p

    def r_(i, allow_idx=True):
        nonlocal pos
        if i == 6 and idx:
            ins.d = _s8(rd(pos))
            pos += 1
            return '(%s{d})' % idx
        if idx and allow_idx and i in (4, 5):
            ins.undoc = True
            return idx + ('h' if i == 4 else 'l')
        return R[i]

    def rp_(i, tbl=RP):
        if i == 2 and idx:
            return idx
        return tbl[i]

    def nn_():
        nonlocal pos
        v = rd(pos) | (rd(pos + 1) << 8)
        pos += 2
        ins.nn = v
        return '{nn}'

    def n_():
        nonlocal pos
        ins.n = rd(pos)
        pos += 1
        return '{n}'

    def e_():
        nonlocal pos
        ins.e = (p + pos + 1 + _s8(rd(pos))) & 0xFFFF
        pos += 1
        return '{e}'

    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    pp, q = y >> 1, y & 1
    t = None
    if op == 0xCB:
        if idx:
            ins.d = _s8(rd(1))
            op2 = rd(2)
            pos = 3
            x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
            m = '(%s{d})' % idx
            if z != 6:
                ins.undoc = True
                m2 = ',' + R[z] if x != 1 else ''
            else:
                m2 = ''
            if x == 0:
                t = '%s %s%s' % (ROT[y], m, m2)
            elif x == 1:
                t = 'bit %d,%s' % (y, m)
            else:
                t = '%s %d,%s%s' % ('res' if x == 2 else 'set', y, m, m2)
            if x == 0 and y == 6:
                ins.undoc = True
        else:
            op2 = rd(1)
            pos = 2
            x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
            if x == 0:
                t = '%s %s' % (ROT[y], R[z])
                if y == 6:
                    ins.undoc = True
            elif x == 1:
                t = 'bit %d,%s' % (y, R[z])
            else:
                t = '%s %d,%s' % ('res' if x == 2 else 'set', y, R[z])
    elif op == 0xED:
        if idx:
            t = None
        op2 = rd(1)
        pos = 2
        x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
        pp, q = y >> 1, y & 1
        if x == 1:
            if z == 0:
                t = 'in %s,(c)' % R[y] if y != 6 else 'in f,(c)'
                if y == 6:
                    ins.undoc = True
            elif z == 1:
                t = 'out (c),%s' % R[y] if y != 6 else 'out (c),0'
                if y == 6:
                    ins.undoc = True
            elif z == 2:
                t = '%s hl,%s' % ('sbc' if q == 0 else 'adc', RP[pp])
            elif z == 3:
                if q == 0:
                    t = 'ld (%s),%s' % (nn_(), RP[pp])
                    ins.nn_kind = 'mem'
                else:
                    t = 'ld %s,(%s)' % (RP[pp], nn_())
                    ins.nn_kind = 'mem'
            elif z == 4:
                t = 'neg'
                if y:
                    ins.undoc = True
            elif z == 5:
                t = 'reti' if y == 1 else 'retn'
                ins.flow = 'ret'
            elif z == 6:
                t = 'im %s' % IM[y]
            else:
                t = ['ld i,a', 'ld r,a', 'ld a,i', 'ld a,r', 'rrd', 'rld', None, None][y]
        elif x == 2 and z <= 3 and y >= 4:
            t = BLI[(y, z)]
        if t is None:
            t = 'defb 0EDh,%s' % ('%03Xh' % op2)
            ins.undoc = True
    elif x == 0:
        if z == 0:
            if y == 0:
                t = 'nop'
            elif y == 1:
                t = "ex af,af'"
            elif y == 2:
                t = 'djnz ' + e_()
                ins.flow = 'cjump'
            elif y == 3:
                t = 'jr ' + e_()
                ins.flow = 'jump'
            else:
                t = 'jr %s,%s' % (CC[y - 4], e_())
                ins.flow = 'cjump'
            if ins.e is not None:
                ins.target = ins.e
        elif z == 1:
            if q == 0:
                t = 'ld %s,%s' % (rp_(pp), nn_())
                ins.nn_kind = 'imm'
            else:
                t = 'add %s,%s' % (rp_(2), rp_(pp))
        elif z == 2:
            if q == 0:
                t = ['ld (bc),a', 'ld (de),a', None, None][pp]
                if pp == 2:
                    t = 'ld (%s),%s' % (nn_(), rp_(2))
                    ins.nn_kind = 'mem'
                elif pp == 3:
                    t = 'ld (%s),a' % nn_()
                    ins.nn_kind = 'mem'
            else:
                t = ['ld a,(bc)', 'ld a,(de)', None, None][pp]
                if pp == 2:
                    t = 'ld %s,(%s)' % (rp_(2), nn_())
                    ins.nn_kind = 'mem'
                elif pp == 3:
                    t = 'ld a,(%s)' % nn_()
                    ins.nn_kind = 'mem'
        elif z == 3:
            t = '%s %s' % ('inc' if q == 0 else 'dec', rp_(pp))
        elif z in (4, 5):
            t = '%s %s' % ('inc' if z == 4 else 'dec', r_(y))
        elif z == 6:
            rr = r_(y)
            t = 'ld %s,%s' % (rr, n_())
        else:
            t = ['rlca', 'rrca', 'rla', 'rra', 'daa', 'cpl', 'scf', 'ccf'][y]
    elif x == 1:
        if y == 6 and z == 6:
            t = 'halt'
        else:
            # with an index prefix, (ix+d) forms keep plain h/l on the other side
            if idx and (y == 6 or z == 6):
                a = r_(y, False) if y == 6 else R[y]
                b = r_(z, False) if z == 6 else R[z]
            else:
                a = r_(y)
                b = r_(z)
            t = 'ld %s,%s' % (a, b)
    elif x == 2:
        t = ALU[y] + r_(z)
    else:
        if z == 0:
            t = 'ret ' + CC[y]
            ins.flow = 'cret'
        elif z == 1:
            if q == 0:
                t = 'pop ' + rp_(pp, RP2)
            else:
                if pp == 0:
                    t = 'ret'
                    ins.flow = 'ret'
                elif pp == 1:
                    t = 'exx'
                elif pp == 2:
                    t = 'jp (%s)' % rp_(2)
                    ins.flow = 'stop'
                else:
                    t = 'ld sp,%s' % rp_(2)
        elif z == 2:
            t = 'jp %s,%s' % (CC[y], nn_())
            ins.nn_kind = 'jump'
            ins.flow = 'cjump'
            ins.target = ins.nn
        elif z == 3:
            if y == 0:
                t = 'jp ' + nn_()
                ins.nn_kind = 'jump'
                ins.flow = 'jump'
                ins.target = ins.nn
            elif y == 2:
                t = 'out (%s),a' % n_()
            elif y == 3:
                t = 'in a,(%s)' % n_()
            elif y == 4:
                t = 'ex (sp),%s' % rp_(2)
            elif y == 5:
                t = 'ex de,hl'
            elif y == 6:
                t = 'di'
            else:
                t = 'ei'
        elif z == 4:
            t = 'call %s,%s' % (CC[y], nn_())
            ins.nn_kind = 'call'
            ins.flow = 'ccall'
            ins.target = ins.nn
        elif z == 5:
            if q == 0:
                t = 'push ' + rp_(pp, RP2)
            else:
                t = 'call ' + nn_()
                ins.nn_kind = 'call'
                ins.flow = 'call'
                ins.target = ins.nn
        elif z == 6:
            t = ALU[y] + n_()
        else:
            t = 'rst %s' % ('%02Xh' % (y * 8) if y * 8 < 0xA0 else '0%02Xh' % (y * 8))
            ins.flow = 'rst'
            ins.target = y * 8
    ins.text = t
    ins.length = (p - addr) + pos
    ins.bytes = [mem[(addr + i) & 0xFFFF] for i in range(ins.length)]
    return ins


if __name__ == '__main__':
    import sys
    mem = open(sys.argv[1], 'rb').read()
    a = int(sys.argv[2], 16)
    end = int(sys.argv[3], 16)
    while a < end:
        i = decode(mem, a)
        print('%04X  %-12s %s' % (a, ' '.join('%02X' % b for b in i.bytes), i.render()))
        a += i.length
