# Building and shipping

What is in the tree, how to build it on a Mac, and how a release is cut.

## Repository layout

| path | what |
|---|---|
| `magiclantern/` | ML source (fork of `magiclantern_simplified`, trimmed to the 6D) — its own git repository |
| `magiclantern/modules/film_sim/` | the module: menu, shelf and darkroom GUI, hook, engine, recipes |
| `magiclantern/modules/film_sim/se/engine/` | vendored Soup Engine: CR2 parse, raw pipeline, look, JPEG codec |
| `magiclantern/modules/film_sim/se/hosttest/` | host harnesses — where changes are checked without the camera |
| `magiclantern/modules/film_lv/` | LiveView display-filter module (grades the preview plane) |
| `build.sh`, `install-sd.sh` | macOS wrappers: build, then copy and verify by hash |
| `docs/img/` | the images in this file |

The module keeps its evidence in
`magiclantern/modules/film_sim/YUV_FINDINGS.md`: every claim about the hook is a
log line or a measured pixel statistic, including the ones that turned out wrong.

## Build environment (macOS)

| component | purpose |
|---|---|
| `arm-none-eabi-gcc` 13.3.1 (Arm GNU Toolchain) | cross compiler with newlib headers |
| `python3` + `docutils` (`rst2html`) | module help strings are rendered at build time |
| GNU make, git, curl | build system |

The Homebrew `arm-none-eabi-gcc` formula ships no newlib headers and fails with
`stdint.h: No such file or directory`; use the Arm GNU Toolchain.

`build.sh` handles the macOS quirks: `ARM_BINPATH`, `READELF`
(`arm-none-eabi-readelf`), GNU-vs-BSD `stat`, and `rst2html` from the toolchain
venv.

## Cutting a release

A tag, one script, and the hashes on the card — see
[release.md](release.md) for the gates a release has to pass.

## Rendering the screens

Every screenshot and both animations in the README come out of the module's own
drawing code, compiled for the desktop. `fsg_fill`/`fsg_text` have two
implementations — `bmp_*` on the camera, an RGB buffer here — and the layout,
the palettes and the spring animation are the same code in both.

```sh
# the shelf and the darkroom
gcc -O1 -Imagiclantern/modules/film_sim \
    magiclantern/modules/film_sim/tools/gui_preview/preview.c \
    magiclantern/modules/film_sim/gui/fsg.c \
    magiclantern/modules/film_sim/gui/fsg_host.c \
    magiclantern/modules/film_sim/gui/fsg_dat.c \
    -o /tmp/fsg_preview -lm
/tmp/fsg_preview tools/florin_filmroll_1.1/FilmRoll-6D-beta11/ML/data/FILMCAN.DAT

# the creator and the WB screens
gcc -O1 -Imagiclantern/modules/film_sim \
    magiclantern/modules/film_sim/tools/gui_preview/creator_preview.c \
    magiclantern/modules/film_sim/gui/fsg.c \
    magiclantern/modules/film_sim/gui/fsg_host.c \
    magiclantern/modules/film_sim/gui/fsg_dat.c \
    magiclantern/modules/film_sim/gui/fsg_creator.c \
    magiclantern/modules/film_sim/gui/fsg_wb.c \
    -o /tmp/fsg_creator -lm
/tmp/fsg_creator edited

python3 magiclantern/modules/film_sim/tools/gui_preview/render.py          # PNGs
python3 magiclantern/modules/film_sim/tools/gui_preview/render.py \
    --gif docs/img/shelf_glide.gif $(ls /tmp/fsg_anim*.ppm | sed 's|/tmp/fsg_||;s|\.ppm||')
python3 magiclantern/modules/film_sim/tools/gui_preview/render.py \
    --gif docs/img/creator_spin.gif $(ls /tmp/fsg_spin*.ppm | sed 's|/tmp/fsg_||;s|\.ppm||')
```

CI compiles both tools and requires the shelf one to print `BAND CHECK PASS`,
which is only true if drawing the strip band alone produces the same pixels as
drawing the whole screen. Without that, an animation frame could show a seam the
full redraw does not.
