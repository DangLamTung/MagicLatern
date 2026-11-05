# Fetching recipes over WiFi — plan, not built

Goal: pick a film simulation or a colour recipe on a phone, push it to the
camera, shoot. This document is the plan; **no part of it is implemented.**

## What decides whether it is possible at all

The 6D has an SD card slot and no WiFi of its own. Two routes exist, and only
one of them works on this body:

| route | verdict |
|---|---|
| **SD-card relay** — phone writes to the card, camera reads it | **works today, no code needed.** The camera already reads `ML/FILM/*.fs` and `ML/SETTINGS/*.TXT` at boot. A phone with a card reader, or the camera in mass-storage mode, is a "sync" already |
| **WiFi on the body** | **not on the 6D.** Canon's WiFi on this generation is a separate WFT/eye-fi accessory or an SD card with WiFi built in. ML cannot add a radio |
| **SD card with WiFi (Eye-Fi / Toshiba FlashAir / Transcend Wi-Fi)** | **the realistic route.** These present an HTTP server on the card's own network. The camera reads the files it writes; the phone PUTs them |

So the honest shape of the feature is: **the camera side is already done** —
it reads recipes from the card. What is missing is a *transport* that writes
those files, and that transport lives in the card or the phone, not in ML.

## Plan

### 1. Camera side (small, buildable now)

Nothing new is needed to *consume* a recipe: `.fs` files under `ML/FILM/` are
already scanned, grouped and shown on the shelf, and a file can also be
selected at boot from `ML/SETTINGS/DEVSET.TXT`.

The one gap is **noticing a change without a reboot**. Today the shelf reloads
after a Develop and after a Save. A file dropped by a phone while the camera
sits idle would not appear until the next reload. Fix: a `fs_watch_task` that
stats the directory every few seconds and calls `fs_load_films_xml()` when the
count or the newest mtime moves. That is the whole camera-side feature, and it
is measurable on the host by watching a temp directory.

### 2. Card side (no ML code)

A WiFi SD card runs its own filesystem server. The phone app does an HTTP PUT of
`ML/FILM/<NAME>.fs`. Nothing to implement in ML; it is a card purchase.

### 3. Phone side (real work, but not here)

A PWA that:
* holds the Fuji field set from `docs/fuji-recipe-fields.md`,
* renders the same 12-wedge wheel and the same WB grid (the same drawing code
  could be compiled to WASM, since `gui/fsg.c` only uses `fsg_fill`/`fsg_text`),
* writes `.fs` text — `gui/fs_fuji.c` and `gui/fsg_creator.c` already contain
  the two formatters, so the format is fixed by the camera, not by the app,
* optionally pulls a shared recipe list.

### 4. What "fetch from the internet" would actually mean

The camera cannot. The *phone* can, and then relays to the card. So a "browse
Fuji X Weekly" feature is a phone feature; the camera's contract is only "watch
`ML/FILM/` and load what is there".

## Hazards, in the order they would bite

1. **A file written while the module is reading it.** `FIO_ReadFile` of a
   half-written `.fs` yields a parse that fails on `NAME` and the stock is
   skipped. The watcher must write-then-rename, or read only after two
   identical stat results — the same rule `fs_auto_task` already uses for new
   frames ("stable across two 2.5 s polls").
2. **Card filesystem caching.** The camera's FAT driver caches directory
   entries. A watcher must re-`FIO_OpenDir` each poll rather than trust a
   cached handle, and the log must print what it saw.
3. **Power.** A WiFi card draws continuously; on an idle camera that is the
   difference between a battery lasting hours and minutes. The watcher should
   poll at seconds, not continuously, and only while the module's screen is up
   or the camera is awake.
4. **No authentication.** These cards often serve an open AP. Any recipe
   dropped there is trusted and will be shot — the module already refuses a
   stock with no `NAME`, which is the only sanity check worth having.

## What I would build first

`fs_watch_task` plus a host test that drops files into a temp directory and
asserts the loaded set follows — that makes the camera side genuinely ready for
a phone, and it is testable here without a WiFi card. Everything above it is
somebody else's transport.
