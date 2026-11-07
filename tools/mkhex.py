"""A binary as Intel HEX: build/fxs4.com -> build/fxs4.hex. Standard library only.

    python tools/mkhex.py build/fxs4.com build/fxs4.hex [--org 0100] [--start 0100]

Data records of 16 bytes from the address --org (hex, the CP/M programs at 0100h), then the end-of-file record with
the start address --start in its address field, as Intel's 8-bit tools wrote it (:00010001FE for 0100h): loaders that
read only the data and the end are not disturbed. The HEX is the usual way to get a program onto a SAPI-1 without a
DPI card (a serial line, the monitor, LOAD of CP/M).
"""
import argparse


def record(addr, rtype, data=b''):
    body = bytes([len(data), addr >> 8 & 255, addr & 255, rtype]) + data
    return ':' + body.hex().upper() + '%02X' % (-sum(body) & 255)


def to_hex(data, org, start):
    lines = [record(org + i, 0, data[i:i + 16]) for i in range(0, len(data), 16)]
    lines.append(record(start, 1))
    return '\r\n'.join(lines) + '\r\n'


def from_hex(text):
    """{address: byte} and the start address of the end record"""
    mem, start = {}, None
    for line in text.split():
        b = bytes.fromhex(line[1:])
        assert line[0] == ':' and sum(b) & 255 == 0 and len(b) == b[0] + 5, line
        addr, rtype = b[1] << 8 | b[2], b[3]
        if rtype == 0:
            for k, v in enumerate(b[4:-1]):
                mem[addr + k] = v
        elif rtype == 1:
            start = addr
    return mem, start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--org', default='0100')
    ap.add_argument('--start', default='0100')
    a = ap.parse_args()
    data = open(a.src, 'rb').read()
    org, start = int(a.org, 16), int(a.start, 16)
    text = to_hex(data, org, start)
    mem, st = from_hex(text)                  # the check: the HEX gives the binary back
    assert st == start and bytes(mem[org + i] for i in range(len(data))) == data and len(mem) == len(data)
    with open(a.out, 'w', newline='') as f:
        f.write(text)
    print('%s: %d bytes from %04Xh, start %04Xh' % (a.out, len(data), org, start))


if __name__ == '__main__':
    main()
