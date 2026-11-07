# Samples

Scenery, so a look can be judged on something a look is for. Everything here
came from the author's own strip, shot in Đà Lạt: `00-the-strip.png` is the
contact sheet, and the six numbered files are its frames.

| file | what is in it |
|---|---|
| `01-lake-and-church-tower.jpg` | the lake at Xuan Huong, a church tower through pine branches |
| `02-pine-hills.jpg` | hillside pine under a bright sky |
| `03-sun-through-pines.jpg` | sun through the pines, rocks, deep shadow |
| `04-hilltop.jpg` | people on a lookout, pines, distance haze |
| `05-two-figures.jpg` | two figures under a pine on open ground |
| `06-roadside-hedge.jpg` | roadside hedge in low sun |

They are not camera output and no claim is made that they are — they are the
scenes. What the module does with them is `look-sheet.jpg`: six rows, and in
each row the frame with no look first, then Portra, Classic Neg, Velvia and
Tri-X. Every tile in it was written by `se/hosttest/grade_jpeg`, which runs the
same decode → curves → twelve hue knots → split tone → halation → grain the
camera runs; the tiles are only enlarged, so grain and colour can be seen.

Regenerate it — or use any JPEG and any recipes:

```sh
cd magiclantern/modules/film_sim/se/hosttest && make grade_jpeg

./grade_jpeg ../../../../../samples/dalat/04-hilltop.jpg \
             ../../films/portra.fs /tmp/portra.jpg
# prints: out: 237x89, neutral 0.1%, mean 174,161,137
```

`grade_jpeg` reports what it wrote, including the share of neutral pixels, so a
file that came out grey cannot pass for a graded one.

```sh
python3 magiclantern/modules/film_sim/tools/look_sheet.py \
    samples/dalat/look-sheet.jpg --zoom 2 \
    --scene samples/dalat/01-lake-and-church-tower.jpg "01 lake + tower" \
    --scene samples/dalat/04-hilltop.jpg "04 hilltop" \
    --stock magiclantern/modules/film_sim/films/EK100.fs
```

With no `--stock` the sheet uses the four above; its first column is always a
stated identity recipe, so it cannot drift with the stocks.
