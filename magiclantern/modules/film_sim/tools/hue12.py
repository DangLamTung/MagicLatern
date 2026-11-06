#!/usr/bin/env python3
"""Expand a .fs recipe's hue controls from 6 knots to 12.

The engine stores 12 hue sectors and expands a 6-value line on load by putting
the written value on every 60-degree knot and the average of its two neighbours
between them (parse_hue_vec in se/engine/stock.c):

    even i  ->  v[i]
    odd  i  ->  (v[i] + v[i+1]) / 2, wrapping

Because that expansion is exact in float and a .5 midpoint is exact in binary,
writing the 12 values out by hand changes nothing downstream: the stock parses
to the same twelve floats, and the render is byte-identical. That is the whole
point of this tool -- the 12 wedges the Colour Creator writes and the 12 knots a
stock uses are now the same thing, without re-grading a single recipe by eye.

    tools/hue12.py files/*.fs            # rewrite in place
    tools/hue12.py --check films/*.fs    # report only, exit 1 if any are 6
"""
import sys

KEYS = ("HUE_SAT", "HUE_ROT", "HUE_LUM")


def expand(vals):
    """6 values -> 12, exactly as parse_hue_vec() does."""
    out = []
    for i, v in enumerate(vals):
        out.append(v)
        out.append((v + vals[(i + 1) % len(vals)]) / 2.0)
    return out


def fmt(x):
    i = int(x)
    return str(i) if x == i else ("%.1f" % x)


def convert_line(line):
    """Return (new_line, changed). Only a 6-value hue line is touched."""
    s = line.strip()
    if not s or s.startswith("#"):
        return line, False
    parts = s.split(None, 1)
    if len(parts) != 2 or parts[0] not in KEYS:
        return line, False
    raw = parts[1].replace(",", " ").split()
    try:
        vals = [float(t) for t in raw]
    except ValueError:
        return line, False
    if len(vals) != 6:
        return line, False
    new = "%-10s %s\n" % (parts[0], ",".join(fmt(v) for v in expand(vals)))
    return new, True


def main(argv):
    check = False
    files = []
    for a in argv[1:]:
        if a == "--check":
            check = True
        elif a.startswith("-"):
            sys.exit("unknown option: " + a)
        else:
            files.append(a)
    if not files:
        sys.exit(__doc__)

    total = changed = 0
    for path in files:
        with open(path) as f:
            lines = f.readlines()
        out, hit = [], 0
        for line in lines:
            new, ch = convert_line(line)
            out.append(new)
            hit += 1 if ch else 0
        if hit:
            total += 1
            changed += hit
            if not check:
                with open(path, "w") as f:
                    f.writelines(out)
        print("%-28s %s" % (path.split("/")[-1],
                            "%d line(s) 6->12" % hit if hit else "already 12"))
    print("\n%d file(s), %d line(s) %s" % (total, changed,
                                           "would change" if check else "changed"))
    if check and total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
