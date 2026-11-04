#!/usr/bin/env python3
"""Draw what a custom look does, and how it travels.

Two looks are shown: FILM SIM / Classic Chrome (the Fujifilm-style one this
project already ships) and a new Olympus-style recipe, films/olympus_natural.fs.
Neither picture on the page is an invention: both are sampled out of the .cube
that fs2cube exports from the recipe itself, so the swatches are the engine's
own answer for that input colour.

    make -C magiclantern/modules/film_sim/se/hosttest fs2cube
    python3 docs/make_look_figure.py film_eval/looks.png
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, "magiclantern", "modules", "film_sim", "tools")
FILMS = os.path.join(REPO, "magiclantern", "modules", "film_sim", "films")
FS2CUBE = os.path.join(REPO, "magiclantern", "modules", "film_sim", "se",
                       "hosttest", "fs2cube")

sys.path.insert(0, TOOLS)
import cube2bin

BG = (250, 250, 250)
INK = (28, 28, 30)
MUTED = (110, 110, 115)
LINE = (205, 205, 208)
CARD = (255, 255, 255)

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

LOOKS = [
    ("Fujifilm-style", "Classic Chrome", "classicchrome.fs", "1.82"),
    ("Olympus-style", "Natural (authored)", "olympus_natural.fs", "3.77"),
]

PATCHES = [
    ("skin, lit",      (235, 190, 170)),
    ("skin, mid",      (205, 155, 130)),
    ("skin, shadow",   (150, 105,  85)),
    ("sky",            (135, 175, 215)),
    ("foliage",        ( 85, 120,  60)),
    ("grass",          (120, 150,  70)),
    ("brick",          (170, 105,  85)),
    ("concrete",       (170, 170, 165)),
    ("asphalt",        ( 90,  90,  95)),
    ("sunset",         (235, 150,  90)),
    ("flower",         (200,  90, 140)),
    ("deep shadow",    ( 35,  35,  45)),
    ("white",          (245, 245, 240)),
    ("black",          ( 15,  15,  15)),
]


def font(size, bold=False):
    path = FONT_B if bold else FONT
    for p in (path, FONT):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


class Cube:
    def __init__(self, path):
        self.size, self.dmin, self.dmax, self.vals = cube2bin.parse_cube(path)

    def __call__(self, rgb):
        v = cube2bin.sample(self.size, self.dmin, self.dmax, self.vals,
                            rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        return tuple(int(round(min(1.0, max(0.0, c)) * 255)) for c in v)


def export(recipe):
    cube = os.path.join("/tmp", os.path.basename(recipe) + ".cube")
    if not os.path.exists(cube) or os.path.getmtime(cube) < os.path.getmtime(recipe):
        if not os.path.exists(FS2CUBE):
            raise SystemExit("build fs2cube first: make -C %s fs2cube"
                             % os.path.dirname(FS2CUBE))
        subprocess.run([FS2CUBE, recipe, cube, "33"], check=True,
                       stdout=subprocess.DEVNULL)
    return cube


def text_w(d, s, f):
    return d.textbbox((0, 0), s, font=f)[2]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "film_eval", "looks.png")
    cubes = []
    for _a, _b, fname, _r in LOOKS:
        cube = export(os.path.join(FILMS, fname))
        cubes.append(Cube(cube))
        print("%s -> %s (%d^3)" % (fname, cube, cubes[-1].size))

    W = 1500
    pad = 48
    row_h = 54
    rows = len(PATCHES)
    grid_h = rows * row_h
    ramp_h = 150
    pipe_h = 190
    H = pad + 60 + pipe_h + 40 + 30 + grid_h + 30 + ramp_h + pad

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = font(34, True)
    f_sub = font(17)
    f_lbl = font(15)
    f_box = font(16)
    f_small = font(13)

    d.text((pad, pad - 8), "A custom look: recipe and cube, one colour",
           font=f_title, fill=INK)
    d.text((pad, pad + 32),
           "Both columns are sampled from the .cube that fs2cube exports from the recipe — "
           "the swatches are the engine's own answer, not a mock-up.",
           font=f_sub, fill=MUTED)

    # ------------------------------------------------------------- pipeline
    y0 = pad + 78
    bw, bh, gap = 250, 96, 46
    stages = [
        ("recipe .fs", ["colour, curves,", "6 hue axes, grain", "~1 KB, text"]),
        ("fs2cube", ["runs the engine", "over a 33³ lattice"]),
        ("look.cube", ["standard .cube", "Resolve / Lightroom", "~780 KB text"]),
        ("cube2bin", ["resample + pack"]),
        ("LOOK.BIN", ["17³ packed", "29 KB", "what the camera reads"]),
    ]
    x = pad
    for i, (title, lines) in enumerate(stages):
        fill = (238, 244, 252) if i in (0, 4) else CARD
        d.rounded_rectangle([x, y0, x + bw, y0 + bh], radius=6, fill=fill,
                            outline=LINE, width=2)
        tw = text_w(d, title, f_box)
        d.text((x + (bw - tw) / 2, y0 + 10), title, font=f_box, fill=INK)
        yy = y0 + 34
        for ln in lines:
            lw = text_w(d, ln, f_small)
            d.text((x + (bw - lw) / 2, yy), ln, font=f_small, fill=MUTED)
            yy += 17
        if i < len(stages) - 1:
            ay = y0 + bh / 2
            d.line([x + bw, ay, x + bw + gap - 10, ay], fill=MUTED, width=2)
            d.polygon([(x + bw + gap - 10, ay), (x + bw + gap - 22, ay - 6),
                       (x + bw + gap - 22, ay + 6)], fill=MUTED)
            d.text((x + bw + 6, ay - 22), "→" if False else "", font=f_small, fill=MUTED)
        x += bw + gap

    # the shutter path, below the pipeline
    note_y = y0 + bh + 12
    d.text((pad, note_y),
           "The same .fs also bakes the 2D tables the shutter path grades with — "
           "a cube cannot be read there, so the recipe is the source of both.",
           font=f_small, fill=MUTED)
    d.text((pad, note_y + 20),
           "Round trip, checked on a 17³ lattice through the engine (lutchk): "
           "recipe vs cube + flat look = mean " + LOOKS[0][3] + " levels (Classic Chrome), "
           + LOOKS[1][3] + " (Olympus).",
           font=f_small, fill=MUTED)

    # ------------------------------------------------------------- swatches
    gw = (W - pad * 2 - 190) // 3
    y = y0 + pipe_h + 46
    heads = ["source", LOOKS[0][0] + " · " + LOOKS[0][1], LOOKS[1][0] + " · " + LOOKS[1][1]]
    d.text((pad, y - 26), "the same colours through each look", font=font(18, True), fill=INK)
    for i, h in enumerate(heads):
        d.text((pad + 190 + i * (gw + 8), y - 24), h, font=f_lbl, fill=MUTED)

    for r, (name, rgb) in enumerate(PATCHES):
        yy = y + r * row_h
        d.text((pad, yy + 16), name, font=f_lbl, fill=INK)
        d.rectangle([pad + 190, yy + 4, pad + 190 + gw, yy + row_h - 10], fill=rgb,
                    outline=LINE)
        for i, cube in enumerate(cubes):
            c = cube(rgb)
            xx = pad + 190 + (i + 1) * (gw + 8)
            d.rectangle([xx, yy + 4, xx + gw, yy + row_h - 10], fill=c, outline=LINE)
            if r == 0:
                d.text((xx + 6, yy + row_h - 10), "%d,%d,%d" % c, font=f_small,
                       fill=(0, 0, 0) if sum(c) > 380 else (255, 255, 255))

    # ---------------------------------------------------------------- ramps
    y = y + rows * row_h + 34
    d.text((pad, y - 24), "tone, and chroma at 128: the neutral axis and a saturated one",
           font=font(18, True), fill=INK)
    steps = 48
    ramp_w = (W - pad * 2 - 190) // 3
    for band in range(2):
        yy = y + band * 58
        for i in range(steps):
            v = int(round(i * 255 / (steps - 1)))
            src = (v, v, v) if band == 0 else (
                max(0, min(255, 128 + int(0.55 * (v - 128)))),
                max(0, min(255, 128 - int(0.30 * (v - 128)))),
                max(0, min(255, 128 - int(0.75 * (v - 128)))),
            )
            for j, cube in enumerate([None] + cubes):
                xx = pad + 190 + j * (ramp_w + 8) + i * ramp_w // steps
                ww = (i + 1) * ramp_w // steps - i * ramp_w // steps
                col = src if j == 0 else cube(src)
                d.rectangle([xx, yy + 6, xx + ww, yy + 38], fill=col)

    img.save(out)
    print("wrote %s  %dx%d" % (out, W, H))


if __name__ == "__main__":
    main()
