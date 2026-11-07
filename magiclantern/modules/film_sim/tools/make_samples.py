#!/usr/bin/env python3
"""Rebuild samples/dalat from the raw files, in the framing the camera used.

The camera's JPEGs from that morning carry the look that was in the slot, and
it is a milky one: set against the raw develop of the same frame they are half
the chroma and half the brightness range. So the samples are the raw develops
instead (`rawdev`, the level-3 path this module runs), cropped to the window
Canon burned into its own JPEG -- 65:24 was framed at capture -- and resized.

    python3 magiclantern/modules/film_sim/tools/make_samples.py /Volumes/EOS_DIGITAL/DCIM/100CANON

Needs the host harness built (`make -C magiclantern/modules/film_sim/se/hosttest`)
and the raw itself; nothing here downloads anything.
"""
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAWDEV = os.path.join(HERE, "..", "se", "hosttest", "rawdev")
BASE = os.path.join(HERE, "..", "..", "..", "..", "samples", "base-neutral.fs")
OUT = os.path.join(HERE, "..", "..", "..", "..", "samples", "dalat")

PICKS = [("IMG_9919", "01-pine-grove-morning"), ("IMG_9920", "02-hillside-pines"),
         ("IMG_9921", "03-lookout"), ("IMG_9923", "04-backlit-pines"),
         ("IMG_9925", "05-granite-and-moss"), ("IMG_9930", "06-path-through-pines"),
         ("IMG_9931", "07-yellow-flowers"), ("IMG_9932", "08-road-in-haze"),
         ("IMG_9934", "09-ridge-and-valley"), ("IMG_9937", "10-lake-and-tower"),
         ("IMG_9938", "11-lake-wide")]


def window(jpg):
    """The rows Canon left uncovered, read off the JPEG it wrote."""
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
    return top, h - bot, h


def main():
    card = sys.argv[1] if len(sys.argv) > 1 else "/Volumes/EOS_DIGITAL/DCIM/100CANON"
    total = 0
    for frame, name in PICKS:
        y0, y1, jpeg_h = window(os.path.join(card, frame + ".JPG"))
        tmp = "/tmp/se-sample-%s.jpg" % frame
        r = subprocess.run([RAWDEV, os.path.join(card, frame + ".CR2"), BASE, tmp, "2"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("rawdev %s failed:\n%s%s" % (frame, r.stdout, r.stderr))
        im = Image.open(tmp).convert("RGB")
        # the develop is scale 2, so it shares the JPEG's coordinate space
        if im.height != jpeg_h:
            sys.exit("%s: develop is %dx%d, the JPEG is %d rows"
                     % (frame, im.width, im.height, jpeg_h))
        im = im.crop((0, y0, im.width, y1))
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        im.save(os.path.join(OUT, name + ".jpg"), quality=90, subsampling=0,
                optimize=True)
        size = os.path.getsize(os.path.join(OUT, name + ".jpg"))
        total += size
        print("%-26s %-10s %4dx%-4d rows %d..%d  %5.0f KB"
              % (name, frame, im.width, im.height, y0, y1, size / 1024))
    print("total %.1f MB" % (total / 1e6))


if __name__ == "__main__":
    main()
