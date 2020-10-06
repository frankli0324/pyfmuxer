def hexdump(data, length=16):
    filter = ''.join([
        (len(repr(chr(x))) == 3) and chr(x)
        or '.' for x in range(256)
    ])
    lines = []
    digits = 4 if isinstance(data, str) else 2
    for c in range(0, len(data), length):
        chars = data[c:c + length]
        hex = ' '.join(["%0*x" % (digits, (x)) for x in chars])
        printable = ''.join([
            "%s" % (((x) <= 127 and filter[(x)]) or '.')
            for x in chars
        ])
        lines.append("%04x  %-*s  %s\n" % (c, length * 3, hex, printable))
    print(''.join(lines))
