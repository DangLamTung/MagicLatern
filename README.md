# Magic Lantern (Canon 6D) + real-time film simulation

This folder contains a Magic Lantern (ML) source checkout focused on the
**Canon EOS 6D** (firmware **1.1.6**), a ready-to-use ARM build environment,
and a new `film_sim` module that applies a film look to LiveView in real time.

```
MagicLatern/
├── magiclantern/          # ML source (github.com/reticulatedpines/magiclantern_simplified)
├── toolchain/             # Arm GNU Toolchain 13.3 + python venv with docutils
├── build.sh               # build wrapper for macOS
└── README.md
```

## Build environment

Installed / required:

| component | purpose | location |
|---|---|---|
| `arm-none-eabi-gcc` 13.3.1 (Arm GNU Toolchain) | cross compiler with newlib headers | `toolchain/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin` |
| `python3` + `docutils` (`rst2html`) | generates module help strings | `toolchain/venv/bin` |
| GNU make, git, curl | build system | system |

The Homebrew `arm-none-eabi-gcc` formula does **not** ship newlib headers and
fails with `stdint.h: No such file or directory`; use the Arm GNU Toolchain
as above.

macOS quirks handled by `build.sh`:

- `ARM_BINPATH` – ML assumes the toolchain is in `/usr/bin`.
- `READELF` – ML wants plain `readelf`; the Arm toolchain only provides
  `arm-none-eabi-readelf`.
- `STAT_CMD` – ML uses GNU `stat -c`; macOS uses BSD `stat -f`.
- `rst2html` – module docs are rendered at build time (docutils).

### Build

```sh
./build.sh                # 6D 1.1.6
./build.sh 6D.116 clean   # clean modules first (required after module edits)
./build.sh 5D3.123        # any other supported camera
```

Output: `magiclantern/platform/6D.116/build/magiclantern.zip`

The platform build does not detect module source changes; always build with
`clean` after editing a module (upstream known issue).

### Install on the 6D

1. Unzip `magiclantern.zip` to the root of a card formatted in the camera
   (`ML/` directory + `autoexec.bin`).
2. Make the card bootable (boot flag) with `EOScard` (Windows) or the
   `mlinstall` tool — needed once per card.
3. Insert the card, power on. ML starts alongside Canon firmware; press
   `DISP`/`Q` (or the ML menu button) to open the ML menus.

## Simulation & testing

### Host simulation (runs the real filter code)

`modules/film_sim/tools/sim` compiles the same `fs_core.h` the camera module
uses, feeds it a synthetic 720×480 UYVY frame (the 6D LiveView geometry) and
writes before/after images plus a per-frame timing:

```sh
make -C magiclantern/modules/film_sim/tools/sim run
# images: .../tools/sim/out/{before,00-Neutral,...,06-Tungsten}.png
```

Presets verified this way: neutral is identity, B&W is truly monochrome,
all luma curves are monotonic.  Host timing is ~0.5 ms/frame on an M-series
Mac; the 6D's DIGIC 5+ is much slower, so treat it as a lower bound.

The sim also takes a PPM and an optional strength/grain, which is what the
calibration uses:

```sh
tools/sim/filmsim_sim out frame.ppm 100 0     # strength 100 %, grain off
```

### Colour calibration

`modules/film_sim/tools/calib/calibrate.py` runs a ColorChecker through the
real filter core and reports CIEDE2000 errors:

```sh
python3 magiclantern/modules/film_sim/tools/calib/calibrate.py
# out/CALIBRATION.txt, out/00-chart-reference.png, out/10-*.png
```

It answers three things, measured rather than assumed:

| check | result |
|---|---|
| chroma convention | signed U/V (`int8`, neutral `0x00`) wins at mean ΔE00 0.86; offset binary scores 51.05 |
| filter identity | Neutral, strength 100, grain 0 → **0.00** ΔE00 (bit-exact) |
| film looks | 3.3–6.0 mean ΔE00 per stock; B&W is a true monochrome |

The chroma result matches `imgconv.c`, where U/V are clamped to `-128..127`
and handed to `UYVY_PACK` (which only masks) — on DIGIC 4/5 the LiveView
buffers hold two's-complement chroma, not offset binary.  Getting that wrong
turns a neutral patch into a 51 ΔE00 colour error.

`clip` and `max dh` in the report are the guard rails for tuning: a clipped
patch means colour is thrown away, and a large hue rotation on skin/foliage
(a "memory colour") is the shift people actually notice.

### QEMU (qemu-eos)

`qemu-eos` is installed at `toolchain/qemu-eos/bin/qemu-system-arm` (built
from `toolchain/qemu-src/qemu-4.2.1`, ML model patches vendored in
`qemu/vendor/`) and exposes a **Canon EOS 6D** machine (`-M 6D`), but two
things are needed to use it:

1. **Flash dumps from your own 6D.** qemu-eos emulates the CPU, EDMAC, MPU,
   SD/CF, display and DryOS timers, but it has no firmware to run.  The 6D
   model loads `6D/116/ROM0.BIN` (8 MB), `6D/116/ROM1.BIN` (16 MB) and
   optionally `SFDATA.BIN` (8 MB serial-flash data; zero-filled if absent).
   They are not distributable — they come from the camera.
2. **A QEMU that can run on Apple Silicon.** QEMU 4.2.1 predates arm64 macOS
   and allocates an RWX JIT buffer, which macOS refuses.  This tree is
   configured with `--enable-tcg-interpreter` plus a one-line patch in
   `accel/tcg/translate-all.c` so the code buffer is RW/R (TCI only stores
   bytecode there), and built with VNC for the display.

```sh
./qemu/install-qemu-eos.sh   # build/install the emulator (idempotent)
./qemu/qemu-eos list         # models: 6D, 5D3, 60D, 700D, ...
./qemu/qemu-eos emu 6D 116 --ml 6D.116   # boot with ML on the card
open vnc://localhost:5900    # the emulated camera LCD

./qemu/run-6d.sh --build     # 6D shortcut: rebuild ML in QEMU mode + boot
```

The screen is QEMU compositing the camera's two VRAM planes for real
(`framebuffer_update_display_bmp_yuv()`): the 8-bit bitmap plane carries the
Canon/ML UI, the UYVY plane carries LiveView.

What QEMU **can** verify today (measured 2026-10-30, 6D 1.1.6): the firmware
runs — card init, MPU spells, DMA, `menu_init()` — and with a bootable card it
prints `Now jump to AUTOEXEC.BIN!!` and enters ML's `copy_and_restart`, so the
bootloader and relocation work.

What it **cannot** verify yet: ML's own task and modules.  After `init_task` is
hooked the guest stalls within ~20 ms of guest time — the vCPU parks in a Canon
cache-maintenance sequence (`0xFF32D908`, interrupts masked) waiting for an
interrupt the emulator never delivers.  No `ML/LOGS/FILMSIM.LOG` is written, so
no module behaviour (menus, property writes, PF2 conversion) can be observed.
Do not assume the module runs under QEMU until that stall is fixed.

The card must be **bootable**: `EOS_DEVELOP` at `0x2B` and `BOOTDISK` at `0x40`
of the partition boot sector for FAT16, `0x47`/`0x5C` for FAT32.  Corrupting
those offsets (or writing the FAT32 pair onto a FAT16 card) silently stops the
boot after two card reads.

What it **cannot** verify: the film look.  The sensor is not emulated, no
frames are produced for `YUV422_LV_BUFFER_*`, so the display filter has no
pixels to work on (QEMU-EOS' EDMAC is "not fully implemented" and copies RAM
around instead of generating images).  That is why the host simulation above
exists.

Use `./build.sh 6D.116 clean` after a QEMU-mode build: `CONFIG_QEMU=y`
binaries are not safe on real hardware.

## How Magic Lantern works

- `autoexec.bin` is a normal ARM binary that DryOS loads from the card root
  when the card is flagged bootable. ML is **not** modified Canon firmware;
  it is a separate program that hooks into the running firmware.
- Hooks:
  - **Task hooks** (`CONFIG_NEW_DRYOS_TASK_HOOKS`, `src/task_utils.c`,
    `src/state-object.c`) – ML code runs inside Canon tasks.
  - **Property handlers** (`PROP_HANDLER`) – react to ISO/shutter/LV state
    changes via Canon’s property system.
  - **Binary patches / reloc** (`src/patch*.c`, `src/reloc.c`) – redirect
    single Canon functions to ML implementations when no hook exists.
- **LiveView pipeline**: Canon’s EDMAC writes YUV422 frames (720×480, UYVY,
  pitch 1440) into `YUV422_LV_BUFFER_1/2/3`. ML’s overlay task draws the
  bitmap UI on top, and “display filters” can point
  `YUV422_LV_BUFFER_DISPLAY_ADDR` at an ML-owned buffer instead. That is the
  hook used by focus peaking, defishing, MLV raw preview and this film
  simulation.
- **Raw capture**: ML reconfigures the sensor readout and EDMAC to write
  14-bit raw frames into memory, bypassing Canon’s JPEG/H.264 encoder; the
  `mlv_lite`/`mlv_rec` modules wrap those frames into MLV (video) and
  `raw.c`/`chdk-dng.c` write DNG (stills).
- **Modules** live in `ML/MODULES/*.mo`: position-independent ARMv5TE
  code, partially linked, loaded by ML’s built-in TCC loader. Unresolved
  symbols are bound at load time against ML’s export table and the camera
  firmware, so a module can refuse to load on an unsupported body.

6D specifics: DIGIC 5+, full frame, LV buffers at `0x5F227800`, `0x5F637800`,
`0x5EE17800`, display-buffer pointer at `0x7550C + 0xA4`, and
`CONFIG_CAN_REDIRECT_DISPLAY_BUFFER_EASILY` — the simplest display-filter
flavour, so the film simulation works without per-camera hacks.

## Real-time film simulation

Menu: **Display → Film Sim** (module `ML/modules/film_sim.mo`).

- Per-frame pipeline on the UYVY LiveView buffer: filmic tone curve →
  hue matrix → per-luma saturation (with highlight desaturation) →
  split toning → grain.
- Presets: Neutral, Warm Negative, Cool Negative, Vivid Slide, Cinema,
  B&W Classic, Tungsten; adjustable strength, grain and frame rate.
- Preview only. Canon JPEG/H.264 and raw files are untouched; for captures
  export a matching LUT and apply it in post:

```sh
python3 magiclantern/modules/film_sim/tools/filmsim_lut.py \
        -p warm_negative -s 80 -n 33 -o warm_negative.cube
```

The LUT mirrors the module’s integer math (verified with
`--self-test`), so raw stills and MLV footage can be graded to match what
the 6D showed in LiveView.

### 6D caveats

- Only one display filter runs at a time. `mlv_lite` claims it when Raw
  video preview is not “Auto/LiveView”; focus peaking as display filter and
  defishing preview also take precedence. Set `Movie → RAW video → Preview`
  to `Auto` (plain LiveView) to see the film look while recording MLV.
- Display filters are disabled with an HDMI monitor connected and in
  x5/x10 zoom.
- 720×480 × ~30 fps of fixed-point work is cheap on DIGIC 5+, but lower the
  `Frame rate` entry if you stack many overlays.
- For JPEG shooting the camera’s own pipeline is used, so the look cannot be
  baked into the JPEG. ML’s Picture Style sliders (contrast/saturation/color
  tone) are the only native capture-side knobs; use the LUT for everything
  else.

## Contributing upstream

`magiclantern/LLM_POLICY.md` requires disclosing LLM involvement and does not
accept large amounts of LLM-generated code. Keep module changes small,
reviewed and understood before sending a patch/PR to
https://github.com/reticulatedpines/magiclantern_simplified.
