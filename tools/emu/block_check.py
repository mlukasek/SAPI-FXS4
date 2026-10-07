#!/usr/bin/env python3
"""Look for coloured blocks in the scroller (a wrong palette entry: background of a code not black).

Takes CGA-1V screenshots at random times while the line animation runs and counts the columns of
row 23 whose lines 4-7 (CGA band 6) are almost all non-black: a character never fills them.

  block_check.py [SHOTS]     default 200
"""
import base64, os, random, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sapimcp as sm
import port


def png_rgb(data):
    """PNG (8-bit RGB or RGBA, no interlace) -> (width, height, rows of bytes, bytes per pixel)."""
    pos, idat, w, h, bpp = 8, b'', 0, 0, 3
    while pos < len(data):
        n, typ = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if typ == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
            bpp = {2: 3, 6: 4}[ctype]
        elif typ == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    rows, prev, stride, i = [], bytearray(w * bpp), w * bpp, 0
    for _ in range(h):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return w, h, rows, bpp


def blocks(png):
    w, h, rows, bpp = png_rgb(png)
    sx, sy = w // 320, h // 200
    found = []
    for c in range(1, 31):
        lit = 0
        for line in range(4, 8):
            y = (4 + 184 + line) * sy
            for i in range(8):
                x = (32 + c * 8 + i) * sx
                px = rows[y][x * bpp:x * bpp + 3]
                if max(px) > 40:
                    lit += 1
        if lit >= 30:
            found.append(c)
    return found


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    random.seed(3)
    port.start()
    sm.call('run_for', ms=1000)
    hits = 0
    for k in range(n):
        if random.random() < 0.05:
            sm.call('type_text', text=random.choice('abcdefgh'))
        sm.call('run_for', ms=random.randint(5, 300))
        r = sm.call('screenshot', display='CGA-1V')
        img = [c for c in (r if isinstance(r, list) else [r]) if isinstance(c, dict) and 'data' in c][0]
        png = base64.b64decode(img['data'])
        b = blocks(png)
        if b:
            hits += 1
            if hits <= 5:
                print('shot %d: blocks in columns %s' % (k, b))
                open(os.path.join(port.ROOT, 'build', 'blocks_%d.png' % k), 'wb').write(png)
    print('%d of %d screenshots with blocks' % (hits, n))


if __name__ == '__main__':
    main()
