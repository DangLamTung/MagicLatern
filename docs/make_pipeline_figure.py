#!/usr/bin/env python3
"""Draw the capture + LiveView pipeline figure.

Mermaid cannot lay this out: `direction LR` inside a subgraph is ignored, and
an edge that crosses a subgraph boundary drags the whole graph into one row.
Two lanes plus two summary boxes need coordinates, so this draws them.

    python3 docs/make_pipeline_figure.py docs/img/capture-pipeline.png

Everything on it is a fact from the sources: the addresses, sizes and the two
measured costs (copy 11 ms, grade 89 ms) come from ML/LOGS/FILMSIM.LOG on the
6D; the "mean 36.7 levels apart" comes from se/hosttest/bench_grade.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1020
BG = (255, 255, 255)
BOX = (240, 240, 240)
EDGE = (40, 40, 40)
TXT = (25, 25, 25)
MUTED = (90, 90, 90)
SHOT_BG = (250, 240, 250)
SHOT_LINE = (190, 150, 190)
LIVE_BG = (238, 248, 248)
LIVE_LINE = (140, 190, 190)
NOTE_BG = (247, 247, 247)
NOTE_LINE = (200, 200, 200)

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_I = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


def font(size, italic=False):
    for p in ((FONT_I if italic else FONT), FONT):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def badge(d, cx, cy, n, r=14):
    """The stage number, drawn: Arial has no circled digits and PIL renders
    them as empty boxes."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255), outline=EDGE, width=2)
    f = font(16)
    t = str(n)
    tw = d.textbbox((0, 0), t, font=f)[2]
    th = d.textbbox((0, 0), t, font=f)[3]
    d.text((cx - tw / 2, cy - th / 2 - 2), t, font=f, fill=TXT)


def box(d, x, y, w, h, lines, fill=BOX, outline=EDGE, size=17, num=None):
    d.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=fill, outline=outline, width=2)
    if num:
        badge(d, x + 26, y + 24, num)
    f = font(size)
    heights = [d.textbbox((0, 0), ln, font=f)[3] for ln in lines]
    gap = 4
    total = sum(heights) + gap * (len(lines) - 1)
    ty = y + (h - total) / 2
    for ln, lh in zip(lines, heights):
        tw = d.textbbox((0, 0), ln, font=f)[2]
        d.text((x + (w - tw) / 2, ty), ln, font=f, fill=TXT)
        ty += lh + gap


def arrow(d, pts, label=None, dashed=False, lw=2):
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        if dashed:
            # manual dashes: PIL has no dashed stroke
            n = max(1, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 // 12))
            for k in range(n):
                a = k / n
                b = (k + 0.5) / n
                d.line([x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                        x1 + (x2 - x1) * b, y1 + (y2 - y1) * b], fill=MUTED, width=lw)
        else:
            d.line([x1, y1, x2, y2], fill=EDGE, width=lw)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = 8
    if abs(x2 - x1) >= abs(y2 - y1):
        s = 1 if x2 > x1 else -1
        tri = [(x2, y2), (x2 - s * 14, y2 - ang), (x2 - s * 14, y2 + ang)]
    else:
        s = 1 if y2 > y1 else -1
        tri = [(x2, y2), (x2 - ang, y2 - s * 14), (x2 + ang, y2 - s * 14)]
    d.polygon(tri, fill=EDGE if not dashed else MUTED)
    if label:
        f = font(16, italic=True)
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        tw = d.textbbox((0, 0), label, font=f)[2]
        if abs(x2 - x1) >= abs(y2 - y1):
            d.text((mx - tw / 2, my - 26), label, font=f, fill=TXT)
        else:
            d.text((mx + 12, my - 10), label, font=f, fill=TXT)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/img/capture-pipeline.png"
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    BW, BH = 210, 150

    # ---------------------------------------------------------------- row A
    d.rounded_rectangle([30, 20, W - 60, 200], radius=6, fill=SHOT_BG,
                        outline=SHOT_LINE, width=2)
    d.text((44, 26), "ONE SHOT — the seam the module owns runs inside Canon's own call",
           font=font(17), fill=TXT)

    ax = [50, 330, 610, 890]
    rowA = [
        ["shutter", "release"],
        ["sensor", "readout", "raw frame", "in DRAM"],
        ["raw development", "black level", "white balance", "picture style", "demosaic"],
        ["YUV 4:2:2", "frame complete", "0x4c394000", "5472x3648", "stride 10944", "39 923 712 B"],
    ]
    for i, (x, lines) in enumerate(zip(ax, rowA)):
        box(d, x, 56, BW, BH, lines, num=i + 1)
    for x in ax[:-1]:
        arrow(d, [(x + BW, 131), (x + 280, 131)])

    # ---------------------------------------------------------------- row B
    # the foothold panel
    d.rounded_rectangle([50, 240, 1230, 470], radius=6, fill=(252, 250, 235),
                        outline=(200, 180, 120), width=2)
    d.text((64, 246), "the module's only foothold — it runs inside Canon's own call",
           font=font(17), fill=TXT)

    box(d, 70, 280, 300, 160,
        ["the seam — entry of", "0xFF16E930", "sssCompleteSsrawToYuv",
         "word 0xE92D41FC"], fill=(210, 245, 210), outline=(60, 120, 60), num=5)
    box(d, 470, 280, 300, 160,
        ["grade in place", "cached alias 0xc394000", "D-cache clean", "about 2 s"],
        fill=(210, 245, 210), outline=(60, 120, 60), num=6)
    arrow(d, [(370, 360), (470, 360)])
    d.text((374, 330), "r1 = 0x4c394000", font=font(15, italic=True), fill=TXT)

    # ④ down to ⑤, along the outside of the panel so it crosses no label,
    # then in through ⑤'s left edge
    arrow(d, [(995, 206), (995, 224), (36, 224), (36, 360), (70, 360)])
    d.text((1005, 212), "then the seam, and Canon compressing what the seam left behind",
           font=font(16, italic=True), fill=TXT)

    box(d, 850, 280, 300, 160,
        ["Canon continues", "0xFF3442DC", "sdfExecuteYuvToJpegPath",
         "also patched:", "reports, grades nothing"], num=7)
    arrow(d, [(770, 360), (850, 360)], "return to Canon")

    box(d, 1270, 280, 300, 160,
        ["hardware JPEG encoder", "DMA-reads", "0x4c394000"], num=8)
    arrow(d, [(1150, 360), (1270, 360)])

    box(d, 1640, 240, 330, 110,
        ["IMG_xxxx.JPG", "5472x3648, one encode", "a B&W recipe gives sat 0.0"], num=9)
    box(d, 1640, 380, 330, 110,
        ["the CR2's embedded preview:", "same encoder, same buffer"], num=9)
    arrow(d, [(1570, 330), (1600, 330), (1600, 295), (1640, 295)])
    arrow(d, [(1570, 390), (1600, 390), (1600, 435), (1640, 435)])

    # ---------------------------------------------------------------- row C
    d.rounded_rectangle([30, 500, W - 60, 730], radius=6, fill=LIVE_BG,
                        outline=LIVE_LINE, width=2)
    d.text((44, 506), "EVERY LIVEVIEW FRAME — ML's display filter, not Canon's encoder call",
           font=font(17), fill=TXT)

    lx = [50, 400, 750, 1100, 1450]
    rowC = [
        ["Canon's LiveView plane", "720x480 UYVY", "691 200 B",
         "cached alias 0x1F227800"],
        ["CBR_DISPLAY_FILTER", "fs_display_filter", "per frame, gated by", "film.sim.fps"],
        ["fs_process_frame", "copy whole plane", "→ fs_snap", "11 ms — coherence,",
         "not cache"],
        ["fs_core_process_rows", "grade 89 ms", "+ aspect bars"],
        ["display_filter_mark_written", "ML flips", "YUV422_LV_BUFFER", "_DISPLAY_ADDR to",
         "display_filter_buffer"],
    ]
    for i, (x, lines) in enumerate(zip(lx, rowC)):
        box(d, x, 536, 300, 170, lines, num=10 + i)
    for x in lx[:-1]:
        arrow(d, [(x + 300, 621), (x + 350, 621)])
    box(d, 1800, 566, 150, 110, ["panel"], size=18)
    arrow(d, [(1750, 621), (1800, 621)])

    # ---------------------------------------------------------------- summary
    shared = [
        "ALREADY SHARED",
        "",
        "aspect-bar geometry —",
        "fs_core_aspect_bars()",
        "signed-chroma UYVY words",
        "the D-cache alias rule",
        "fs_sync() gates both",
    ]
    differ = [
        "NOT SHARED — two grade engines",
        "",
        "LiveView: fs_lut_t from fs_presets[]",
        "10 presets, no per-hue table, ~1.5 KB",
        "Shot: se_yuvtbl baked from the .fs recipe",
        "3080 B, 32x32 hue cells",
        "one frame, both engines:",
        "mean 36.7 levels apart, 83% of",
        "samples over 8 levels",
    ]
    box(d, 60, 780, 760, 210, shared, fill=NOTE_BG, outline=NOTE_LINE, size=17)
    box(d, 900, 780, 900, 210, differ, fill=NOTE_BG, outline=NOTE_LINE, size=17)

    # both lanes feed the comparison: one dashed bus down the right margin,
    # along y=772, then a drop into each box. Nothing is crossed.
    BUS = W - 28
    arrow(d, [(W - 60, 200), (BUS, 200)], dashed=True)
    arrow(d, [(W - 60, 730), (BUS, 730)], dashed=True)
    d.line([BUS, 200, BUS, 772], fill=MUTED, width=2)
    d.line([BUS, 772, 480, 772], fill=MUTED, width=2)
    arrow(d, [(480, 772), (480, 790)], dashed=True)
    arrow(d, [(1250, 772), (1250, 790)], dashed=True)

    img.save(out)
    print("wrote %s  %dx%d" % (out, W, H))


if __name__ == "__main__":
    main()
