# Fetching recipes over WiFi — plan, not built

Goal: pick a film simulation or a colour recipe on a phone, push it to the
camera, shoot. This document is the plan; **no part of it is implemented.**

## Correction: this body DOES have WiFi

An earlier version of this document said the 6D has no WiFi of its own. That
is wrong, and the camera's own firmware dump on the card says so. `strings` on
`ML/LOGS/ROM1.BIN`:

```
[NWCOM] Wlan Init Err
[NWCOM] NWCOM WLAN Biltin Judge (0x%x)
[NWCOM] WIFI_SETTING OFF
PROP_WIFI_SETTING (%d)
[FA_NW] FA_ChkWlan : %lx %lx
GuiPropertyData PROP_WFT_HTTP (%x)<-(%x)
SetHTTPUserName1<%s>
ComDLNAResizeSem
WlanMgr/WlanMgr.c  NWCommu/NWCommuTransOrder.c  NWMgr/NetworkSetting.c
Lan/DlgLnWirelessConnected.c  LanWizard/LnWizUtility.c
```

So the body carries WlanMgr, NWCommu, the LAN dialogs, DLNA and the WFT HTTP
server. Canon's WiFi is present; it is Canon's firmware that drives it.

## What ML can and cannot do with it on this body

| | state |
|---|---|
| Call Canon's WiFi stack from ML | **not today.** `platform/6D.116/build/6D_116.sym` has no `wlan_connect`, no `socket_create/send/recv` -- the symbols `modules/yolo` uses exist on 200D-class bodies, not here. `yolo.mo` is shipped in the build but cannot resolve those imports on this table |
| Add them | possible but large: they have to be found by disassembling the firmware (`ROM0.BIN`/`ROM1.BIN` are on the card) and added to the .sym. Legitimate work on your own firmware, zero guarantee it lands |
| Put files where Canon's app can see them | **works today.** Anything in `DCIM/nnnCANON/` is what the app lists and sends |

## Raw over WiFi

The transport is file-level over `DCIM`, and `.CR2` files sit in the same
folders as `.JPG`, so nothing in the firmware prevents moving a raw file. What
limits it is Canon's app and firmware policy, and **that is not verified** --
canon.com was not reachable from here and no authoritative statement was read.
The check costs two minutes on the camera: connect the app, open the file list,
see whether a `.CR2` is offered.

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

## Plan, in order

### 1. Make a developed look reachable by the app (small, now)

Develop writes `IMG_nnnn_F.JPG`. `_F` is not a DCF name, so the camera's own
list -- and therefore the app's -- has no reason to show it. Give Develop an
option to write the DCF-legal `IMG_nnnn.JPG` that pairs with the CR2, which is
what "Replace Camera JPEG" already half does.

### 2. Recipe push (small, now)

Already works if the phone writes the card: `ML/FILM/*.fs` is read at boot.
The only gap is noticing a change without a reboot. `fs_watch_task` plus a host
test that drops files into a temp directory and asserts the loaded set follows
makes the camera side genuinely ready for a phone, and it is testable here
without a WiFi card.

### 3. Our own server on the camera (large, optional)

Add `wlan_connect` + the `socket_*` family to `6D_116.sym` from the firmware
dump, then do what `modules/yolo` does on its bodies: a small HTTP server in a
module, so a phone can pull developed JPEGs, push `.fs` recipes and read the log
without Canon's app. The only route to an app of our own, and the only one with
real risk.

### 4. Decide the app question first

- **Canon's app + files** -- no app to write, limited to what Canon lists.
- **Our server + a web page** -- needs 3.
- **SD relay** -- works today, no code, no app.

## What I would build first

`fs_watch_task` plus a host test that drops files into a temp directory and
asserts the loaded set follows — that makes the camera side genuinely ready for
a phone, and it is testable here without a WiFi card. Everything above it is
somebody else's transport.
