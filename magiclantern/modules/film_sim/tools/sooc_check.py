#!/usr/bin/env python3
"""Does the camera's own JPEG carry the look once, twice, or not at all?

The in-shutter grade is the part of this module that is easiest to get wrong and
hardest to see: a frame graded twice looks "milky", a frame not graded at all
looks flat, and both have been shipped. This compares a straight-out-of-camera
JPEG against the three things it could be -- the raw developed with no look, the
same developed with the stock applied once, and with it applied twice -- and says
which one it is, with numbers.

    python3 magiclantern/modules/film_sim/tools/sooc_check.py \
        --cr2 /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_3110.CR2 \
        --jpg /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_3110.JPG \
        --stock magiclantern/modules/film_sim/films/classicchrome.fs

Why the base recipe and not the stock: only the base is common to all three
hypotheses. Everything is normalised to a common brightness first, because the
camera's exposure and the develop's are not the same question -- what is being
measured is the shape of the look, cast and contrast.

Control, on a capture known to be graded twice (2 Nov 2026, Da Lat):
    IMG_9923 + classicneg.fs -> x2 closest, 10.9 /255 against 15.5 for x1.
See docs/sooc.md for what each outcome means and which log line corroborates it.
"""
import argparse
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.path.join(HERE, "..", "se", "hosttest")
ROOT = os.path.join(HERE, "..", "..", "..", "..")
BASE = os.path.join(ROOT, "samples", "base-neutral.fs")


def window(jpg):
    """Rows the camera did not cover, if it burned bars into the frame."""
    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    px = im.load()

    def dark(y):
        return max(sum(px[x, y]) for x in range(0, w, max(1, w // 48))) < 14

    top = 0
    while top < h and dark(top):
        top += 1
    bot = 0
    while bot < h and dark(h - 1 - bot):
        bot += 1
    if top + bot > h // 2:          # a dark frame, not a letterbox
        return 0, h
    return top, h - bot


def shape(path, box, size, w, h, crop):
    im = Image.open(path).convert("RGB")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    if crop:
        im = im.crop(box)
    im = im.resize(size, Image.LANCZOS)
    px = list(im.getdata())
    avg = sum(sum(p) for p in px) / (3 * len(px)) or 1
    return [tuple(min(255, int(v * 80 / avg)) for v in p) for p in px]


def diff(a, b):
    return sum(abs(p[i] - q[i]) for p, q in zip(a, b) for i in range(3)) / (len(a) * 3)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("%s failed:\n%s%s" % (os.path.basename(cmd[0]), r.stdout, r.stderr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cr2", required=True)
    ap.add_argument("--jpg", required=True)
    ap.add_argument("--stock", required=True)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--keep", default="/tmp", help="where the develops are written")
    a = ap.parse_args()

    jw, jh = Image.open(a.jpg).size
    y0, y1 = window(a.jpg)
    box = (0, y0, jw, y1)

    base = os.path.join(a.keep, "sooc_base.jpg")
    once = os.path.join(a.keep, "sooc_once.jpg")
    twice = os.path.join(a.keep, "sooc_twice.jpg")
    run([os.path.join(HOST, "rawdev"), a.cr2, a.base, base, "2"])
    run([os.path.join(HOST, "grade_jpeg"), base, a.stock, once])
    run([os.path.join(HOST, "grade_jpeg"), once, a.stock, twice])

    size = (160, 60)
    ref = shape(a.jpg, box, size, jw, jh, True)
    got = [("base  (no look)", base), ("x1    (look once)", once),
           ("x2    (look twice)", twice)]
    scores = []
    for label, path in got:
        d = diff(ref, shape(path, box, size, jw, jh, True))
        scores.append((d, label))
    scores.sort()
    print("%s + %s" % (os.path.basename(a.jpg), os.path.basename(a.stock)))
    for d, label in sorted(scores, key=lambda s: s[1]):
        print("  %-18s mean difference from the camera's JPEG %5.1f /255" % (label, d))
    print("  closest: %s" % scores[0][1])


if __name__ == "__main__":
    main()
