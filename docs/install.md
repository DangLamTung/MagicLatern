# Installing on a new card

Everything below is for a **blank card**. If the card already boots Magic
Lantern, skip to [Updating an existing card](#updating-an-existing-card).

## 1. Format the card in the camera

Menu → **Format card**. Do this in the 6D, not on the computer: the camera
writes the filesystem and the `DCIM` layout its own bootloader expects.

⚠️ Formatting erases the card.

## 2. Copy the release onto it

From `magiclantern-6D.116.zip` (or the release page), copy **to the root of the
card**, next to `DCIM`:

```
autoexec.bin      the ML payload the bootloader runs
ML-SETUP.FIR      the one-time installer
ML/               every module, font, LUT and data file ML needs
```

The card root afterwards looks like:

```
DCIM/
ML/
autoexec.bin
ML-SETUP.FIR
```

## 3. Make the card bootable — once per card

A Canon body only runs `autoexec.bin` if the card's boot sector carries the
`EOS_DEVELOP` and `BOOTDISK` strings. There are two ways; pick one.

**A. On the camera (no extra tools).** With `ML-SETUP.FIR` on the card, run
Menu → **Firmware version → Update**. ML's installer sets the flag, reboots, and
ML comes up. Then remove `ML-SETUP.FIR` from the card so a stray update cannot
re-run it.

**B. On the computer (no firmware update).** With the card in a reader:

```sh
python3 magiclantern/tools/card-flags/edit_card_flags.py /dev/diskN
```

where `/dev/diskN` is the card's **whole disk** (`diskutil list` shows it; pass
the disk, not `diskXs1`). It needs `numpy`: `python3 -m pip install numpy`. The
tool sets `EOS_DEVELOP` + `BOOTDISK` (and `SCRIPT`, which newer bodies ignore).
`MacBoot` (macOS) and `EOSCard` (Windows) do the same thing with a GUI.

## 4. Power on and check

1. Insert the card, switch on. The card LED blinks as ML loads.
2. Press **ERASE** (the trash button) to open the Magic Lantern menu.
3. **Modules → Film Sim** → `Level`. The module is there, and so is its menu.

If the screen stays dark but autofocus works, the card is bootable but
`autoexec.bin` is missing or wrong — remove the battery, fix the file, retry.

## Updating an existing card

The card is already bootable, so only the files move. From a checkout:

```sh
./build.sh 6D.116      # cross-compile ML + the module
./install-sd.sh        # copy to the card, then verify every file by hash
```

`install-sd.sh` never formats: `ML/SETTINGS`, `ML/LOGS` and the four creator
slots survive. From a release zip, unzip over the card root instead — same
result, one step. Then press ERASE → Modules → Film Sim.

## Where things land on the card

| path | what writes it |
|---|---|
| `ML/modules/film_sim.mo` | the module itself |
| `ML/FILM/*.fs` | recipes — the 34 shipped ones, plus any the creator or a Fuji save wrote (`WHEEL..WHEEL4`, `FUJI1..FUJI4`) |
| `ML/FILMS/*.xml` | the catalogue the shelf is built from; a saved look gets `90_<slot>.xml` here |
| `ML/SETTINGS/*` | module config, plus the unattended-run levers (`AUTODEV.TST`, `DEVSET.TXT`, `DEVPHOTO.TXT`, `AUTOSET.TST`) |
| `ML/LOGS/FILMSIM.LOG` | the only place a camera claim can be checked: per-stage timings, which look was applied, what the WB property read back |
| `ML/FILMSIM/LOOK.BIN` | an optional external 3D LUT — see [looks.md](looks.md) |

## Files a release contains

| asset | what it is |
|---|---|
| `magiclantern-6D.116.zip` | the whole card layout: `ML/`, `autoexec.bin`, `ML-SETUP.FIR` |
| `autoexec-6D.116.bin` | the bootloader payload alone |
| `film_sim-6D.116.mo` | the module on its own, for a card that already has ML |
| `mlwifi-6D.116.mo` | WiFi probe — shipped apart on purpose, it verifies addresses and calls nothing |
| `hosttests.log` | the test run that build came from |
| `SHA256SUMS` | every file above |

`SHA256SUMS` checks a download, not reproducibility: the `.mo` embeds its build
time, so two builds of different commits never match. Compare commit ids for
that — see [release.md](release.md).
