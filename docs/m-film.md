# What M-Film has that this module does not

[M-Film](https://github.com/HNGSeries/M-Film) is the nearest sibling of this
project: a Magic Lantern module that turns a Canon body into a film camera —
a shelf of stocks, a roll counter, a darkroom — and it lists the **6D.116 as
`working`**. This is a review of their repository as of 2026-11-04, what was
taken from it, and what is still worth taking.

Everything below was read from their sources, not from their README's claims.
Where a number is ours, it was measured here and the command is given.

---

## 1. Taken: their film catalogue

### What was done

Their catalogue is 72 stocks: 9 described by a model in `ml-dev/films/films.py`,
and 63 whose colour comes from the
[Film-Luts](https://github.com/YahiaAngelo/Film-Luts) collection by Yahia
Angelo — **MIT licensed**, fetched at build time, not committed to their repo.

[`tools/mfilm_import.py`](../magiclantern/modules/film_sim/tools/mfilm_import.py)
imports it. Per stock it writes three things:

| file | what it is |
|---|---|
| `ML/FILMS/NN_<CODE>.xml` | the stock definition; `<lut>` points at the next line |
| `ML/FILMSIM/LUT/<CODE>.BIN` | a packed 17³ LUT baked from the MIT `.cube` (29,486 bytes) |
| `ML/FILM/<CODE>.fs` | the look: **grain and halation only** — colour is the LUT's |

The split is theirs: *"the colour from the LUT, the rest (scanner exposure,
halation, grain, softness) from the kind and speed"*. The recipe is therefore
flat (`SAT 100`, no curve), because our develop applies the LUT after the
camera→sRGB conversion and before the look, which is the order those LUTs
expect — they take ordinary sRGB pictures.

### Two code changes were needed

1. **A stock can carry its own LUT.** `<lut>` in the XML was parsed, saved and
   round-tripped but never read; the develop used one global
   `ML/FILMSIM/LOOK.BIN`. `fs_sync()` in [`film_sim.c`](../magiclantern/modules/film_sim/film_sim.c)
   now uses the selected stock's own path when that file exists, and falls back
   to the global one. A stock's LUT is part of its definition, so it is not
   behind `film.sim.lut` — those recipes are flat and would come out grey.
2. **`MAX_DYNAMIC_FILMS` 64 → 96**, because the card now holds 84 stocks and
   the loader drops the extras silently past the limit (~29 KB of module BSS).

### A bug the import made reachable

`fs_sync()`'s change signature packed the stock index into **6 bits**
(`stock & 0x3F`). With 33 stocks that was invisible; with 84, stock 64 has the
same signature as stock 0, so selecting it changed nothing — the LiveView look
kept using stock 0's preset. The field is now 7 bits. Found by reviewing the
change against its callers, not by running it.

### Measured

```
python3 tools/mfilm_import.py --all-missing --out /Volumes/EOS_DIGITAL
  52 stocks imported            (65 catalogue entries not already on the card)
rm ML/FILMS/75_panfplus.xml     (one duplicate: we ship "Pan F Plus 50")
  -> 84 stocks: 33 tuned here + 51 imported
```

Each import is developed once on the host with the camera's own code
(`se_cam_test photo.CR2 recipe.fs out.jpg 5 - 100 100 lut.BIN`), because a
recipe that bakes to an identity look or an all-black frame is a failed
import:

| stock | mean luma | chroma sd | |
|---|---|---|---|
| APX 25 | 123.7 | 0.26 | monochrome, as it should be |
| Delta 3200 | 116.7 | 0.35 | monochrome |
| Sensia 100 | 121.7 | 4.76 | colour |
| Vista 200 | 105.3 | 6.68 | colour |
| Vision 2393 | 114.1 | 5.52 | colour |

Grain and halation are a **fit**, not their numbers: their model works in
scene-linear stops against its own tone curve, so copying a value across
would be a made-up claim. The mapping is printed per stock and can be argued
with. Their own note says the same about their values: *"Every number here is
an artistic starting point, not measured data."*

### Not verified

The import is verified as far as the host goes. Nothing here has been run on
the camera: the per-stock `<lut>` lookup, the 84-stock shelf, and
`MAX_DYNAMIC_FILMS = 96` all need one boot with a card that has these files.

---

## 2. The animation — theirs against ours, measured

Their shelf is a spring, not an ease. `fos_ui.c`:

```c
int spring_step(struct spring *s, float target, int dt, float hz, float zeta)
```

— a damped oscillator integrated in 8 ms sub-steps, which *settles* (returns
0) rather than asymptote. Their carousel is one scalar; everything else is
derived from the distance to it (`fos_shelf.c`, `pose_of()`):

```
x = 360 + sign(d) * (n*192 + f*122) * spread
scale = 1 - n*0.27 - f*0.17
light = 1 - n*0.42 - f*0.30
rot   = d * 0.085          /* turns to face the middle */
reflect = 64 * clamp(1.25 - |d|)
```

No per-item tween exists to get out of step with the others.

Ours (`fs_shelf_animate()` in `film_sim.c`) is `step = d/3` on a 70 ms clock.
Re-implementing their `spring_step` line for line and running both:

| | settle | frames | biggest single-frame jump |
|---|---|---|---|
| their spring, 2.1 Hz ζ 0.86 at 28 ms | **560 ms** | 20 | **0.152** shelf |
| ours, 1 shelf | 1050 ms | 15 | 0.332 shelf |
| ours, 3 shelves | 1260 ms | 18 | **1.000 shelf** |

At three stocks away our first frame teleports a whole shelf width, then
crawls — 100 px in one 70 ms step. That is the difference being seen.

Two more things behind it:

- **Only the moving band is redrawn and presented.** `ui_damage(y0,y1)`
  accumulates dirty rows; `shelf_draw()` restores that band from a cached
  background (`ui_bg`) and redraws the sprites; `fos_port_present(px_row, w,
  y0, y1)` sends only those rows to the panel.
- **It degrades instead of stuttering.** `frame_stats()` measures
  draw+present per second: over 50 ms average drops `fos_can_quality`, under
  26 ms for three seconds raises it. Simpler canisters, not a slower shelf.

Their loop targets 28 ms (~35 fps) and always leaves the camera 1–10 ms
(`frame_rest`), so Canon's own tasks keep running.

---

## 3. The renderer: why their screens can have gradients

Our `gui/fsg.h` says only fixed palette constants may be drawn, with an exact
`ml_color()` mapping — "no gradients, no blends". M-Film shows that limit is
self-imposed, not the panel's:

> **254 entries** (index 0 and 255 stay Canon's) shared across **10 tonal
> ramps** — warm grey, steel, amber, red, orange, crimson, green, violet,
> blue, film base — each ramp running near-black → hue → light tint. Every
> colour is "a ramp and a level along it", so shading, gradients, fades and
> anti-aliasing are all level changes, and a **4×4 ordered dither**
> (`fos_bayer[y&3][x&3]`) supplies four bits of sub-level between neighbouring
> entries:

```c
int p = (((lv * ramp_mul[ramp] >> 16) + fos_bayer[y & 3][x & 3]) >> 4;
```

That one idea is what the canisters' cylinder shading, the spotlight, the
contact shadows and the reflections are made of. Their canister art is a
label painted once into a wrap-around texture, then *"each column of the
drawing folds its shading into a gain and an offset per ramp, and a label
pixel costs a lookup, a multiply and a dither"* (`fos_film.c`).

It is also how their contact sheet and darkroom show a photograph: each print
carries **its own 240-colour palette** built from the frame with error
diffusion.

---

## 4. Their tooling, worth copying

| tool | what it gives us |
|---|---|
| `sim/tools/mkcr2.c` (+ `checkcr2.py`, `devtest.c`) | synthesise a CR2 of any sensor size, then check the decoder sample by sample. This is the missing piece for our **mRAW** work: we have one camera file and no way to make a fixture. |
| `sim/tools/armcount.py` | qemu-arm `-d in_asm,exec` → ARM instructions per function *and per source line*. "The camera has no profiler; this gives the instruction budget of the same code compiled for ARMv5TE." This is how the `fs_pack_px` non-inlining should have been found. |
| `sim/bench.c` | time one shelf frame on the PC through the same `shelf_update()/shelf_draw()` the camera runs, with a stubbed port layer. |
| `sim/scenes/*.txt` | scripted screens: `150 wr` = at 150 ms, wheel right. Every preview PNG in their repo is generated from these, so a GUI change that moves the layout is caught. We have no such regression. |
| fonts and film data on the card | `ML/DATA/FOSFONT.BIN`, `FOSFILMS.BIN` — kept out of the binary because boot size is their binding constraint. |
| `--module` build | `autoexec.bin` carries only three hooks that forward to the module: **~180 KB less at boot**. |

Also worth reading, not copying: `films/lut.py` handles the **input colour
space** of a LUT (LogC3, S-Log3, Cineon, Rec.709, sRGB, linear), chosen by
filename. Our `cube2bin.py` assumes sRGB; most film LUTs are made for LogC3
or S-Log3, so a `.cube` from that world applied to an sRGB image is wrong.
That gap is worth closing.

---

## 5. Memory: they run the 6D at 848 KB

`ml-dev/MEMORY.md` and `ml-dev/cameras.txt` survey what each camera can give
Magic Lantern at boot. For the 6D:

```
6D.116   working   868096   (848K)   Works since 0.1.2 (#17, #22)
```

`boot-d45-am.c` fixes ML's slice, so their fork raised it there. 868,096 bytes
is pool start `0x520000` against `RESTARTSTART 0x44C100`; Canon keeps 8.19 MB.
**We take 592 KB (`0x4E0000`, 605,952 bytes) and Canon keeps 8.36 MB** — i.e.
the same body has been run with 256 KB more reserved than we use, and shipped.

Their 6D builds are 740,864 bytes at boot. Ours is a module loaded from the
pool, so the constraint is not identical, but the ceiling is far higher than
we assumed.

---

## 6. Where we are ahead — do not import these

- **Full-resolution develop.** Their in-camera print is 720 × 480 (0.35 MP);
  full size is a separate closed-source desktop program. Our develop writes
  5472-wide JPEGs and is verified byte-identical host-vs-camera.
- **Text recipes.** `.fs` files are editable on the card; theirs are
  `films.py` → generated C tables → `FOSFILMS.BIN`.
- **The 2D table path.** Baked luma/chroma/hue tables applied to a UYVY frame
  in the shot have no equivalent there; they run the full float model per
  pixel.

---

## 7. Licensing

- M-Film camera side: **GPL-2.0**, same tree as ours. Reading it is fine; the
  code we took (the stock catalogue and the kind/speed heuristics) is
  re-derived here, not copied.
- Film-Luts: **MIT**, by Yahia Angelo. Their `.cube` files are not in the
  M-Film repository and are not in ours either — `mfilm_import.py` fetches
  them into `tools/.cache/` at import time and bakes the `.BIN` locally.
  Attribution is in the tool's header.
- Film and brand names are descriptive; nothing is endorsed by Kodak,
  Fujifilm, Ilford, Agfa or CineStill.

---

## 8. Reproduce

```sh
# host tools
make -C magiclantern/modules/film_sim/se/hosttest

# what is on the card against what they publish
python3 magiclantern/modules/film_sim/tools/mfilm_import.py --list --out /Volumes/EOS_DIGITAL

# import anything missing, and develop one photo with each new stock
python3 magiclantern/modules/film_sim/tools/mfilm_import.py --all-missing \
        --out /Volumes/EOS_DIGITAL \
        --verify /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_9937.CR2

./build.sh && ./install-sd.sh      # module, then verify labels + md5 on the card
```
