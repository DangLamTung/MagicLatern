#!/usr/bin/env python3
"""Contact sheet of the module's own develop output over a set of scenes.

Every tile is a real JPEG written by `se/hosttest/grade_jpeg`, which runs the
same decode -> curves -> hue axes -> split tone -> halation -> grain the camera
runs. Nothing here is drawn, upscaled from a mockup, or otherwise invented; the
tiles are only enlarged so the grain and colour can be seen.

    python3 magiclantern/modules/film_sim/tools/look_sheet.py \
        samples/dalat/look-sheet.jpg --zoom 2 \
        --scene samples/dalat/04-hilltop.jpg "04 hilltop" \
        --scene samples/dalat/06-roadside-hedge.jpg "06 roadside hedge"

The first column of every row is the scene with no look, so the difference is
the look and not the framing.
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
GRADE = os.path.join(HERE, "..", "se", "hosttest", "grade_jpeg")
FILMS = os.path.join(HERE, "..", "films")
# Identity recipe: sat 100, no grain, no tone move, no hue rotation. Written
# here rather than borrowed so the "flat" column cannot drift with a stock.
FLAT = """#FLAT
NAME      FLAT
CURVE     0,0 255,255
HUE_SAT   100,100,100,100,100,100,100,100,100,100,100,100
HUE_ROT   0,0,0,0,0,0,0,0,0,0,0,0
HUE_LUM   100,100,100,100,100,100,100,100,100,100,100,100
"""


def prepare(scene, width, tmp):
    """Downscale the scene first when a sheet has to stay a sane size.

    grade_jpeg decodes at half size, so a tile is half the source; a 2736-wide
    frame would make each tile 1368 wide and a six-row sheet 8 MB. The sample
    files keep their resolution -- only the sheet's input is reduced.
    """
    if not width:
        return scene
    im = Image.open(scene).convert("RGB")
    if im.width <= width:
        return scene
    out = os.path.join(tmp, "src-" + os.path.basename(scene))
    im.resize((width, round(im.height * width / im.width)), Image.LANCZOS).save(
        out, quality=95, subsampling=0)
    return out


def develop(scene, stock, out):
    if not os.path.exists(out):
        r = subprocess.run([GRADE, scene, stock, out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("grade_jpeg failed for %s + %s:\n%s%s"
                     % (scene, stock, r.stdout, r.stderr))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--scene", nargs=2, action="append", required=True,
                    metavar=("PATH", "LABEL"))
    ap.add_argument("--stock", action="append", default=None,
                    help="recipe path; default the four used in the docs")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--width", type=int, default=0,
                    help="downscale each scene to this width before grading")
    a = ap.parse_args()

    stocks = a.stock or [os.path.join(FILMS, n) for n in
                         ("portra.fs", "classicneg.fs", "velvia.fs", "TRI-X.fs")]
    tmp = tempfile.mkdtemp()
    flat = os.path.join(tmp, "FLAT.fs")
    with open(flat, "w") as f:
        f.write(FLAT)
    columns = [("no look", flat)] + [(os.path.splitext(os.path.basename(s))[0], s)
                                     for s in stocks]

    tiles = []
    for path, label in a.scene:
        row = []
        src = prepare(path, a.width, tmp)
        for i, (_, stock) in enumerate(columns):
            out = os.path.join(tmp, "%s-%d.jpg" % (label, i))
            row.append((label, Image.open(develop(src, stock, out)).convert("RGB")))
        tiles.append(row)

    hdr = 18
    gut = 10 + max(len(lbl) for _, lbl in a.scene) * 6
    tw, th = tiles[0][0][1].size
    tw *= a.zoom
    th *= a.zoom
    sheet = Image.new("RGB", (gut + tw * len(columns), hdr + th * len(tiles)),
                      (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, (label, _) in enumerate(columns):
        d.text((gut + i * tw + 4, 4), label.upper(), fill=(235, 235, 235))
    for r, row in enumerate(tiles):
        d.text((4, hdr + r * th + 4), row[0][0].upper(), fill=(235, 235, 235))
        for c, (_, im) in enumerate(row):
            sheet.paste(im.resize((tw, th), Image.LANCZOS),
                        (gut + c * tw, hdr + r * th))
    if a.out.lower().endswith((".jpg", ".jpeg")):
        # A sheet of JPEG tiles: re-encoding at 95 costs nothing visible and a
        # sixth of the bytes a PNG of the same sheet takes.
        sheet.save(a.out, quality=95, subsampling=0)
    else:
        sheet.save(a.out)
    print("%s: %dx%d, %d scenes x %d columns"
          % (a.out, sheet.width, sheet.height, len(tiles), len(columns)))


if __name__ == "__main__":
    main()
