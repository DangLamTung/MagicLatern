# The 6D's WiFi: what was found, and how far it can go

Investigation notes, 2026-11-06. Everything here is from the firmware on the card,
not from documentation or memory.

## Identity of the images

| image | size | load address | md5 |
|---|---|---|---|
| `ROM0.BIN` | 8,388,608 | `0xF0000000` | `1543b9813c38003d89af666cc07255d7` |
| `ROM1.BIN` | 16,777,216 | `0xF8000000` | `8e16eee40721ab0a07b3e15486434fa9` |
| `RAM4.BIN` | 268,435,456 | unknown | — |

The load addresses come from `platform/6D.116/consts.h`, which is also what
`src/debug.c` dumps from. The same 16 MB of flash is **also mapped at
`0xFF000000`** — 831,900 words inside ROM1 point into that window — so all
disassembly below uses `0xFF000000` as the base.

## Why string search does not work on this firmware

Every WiFi message is a **format string loaded PC-relative** and passed to Canon's
logging routine at `0x67C8`:

```
ff2616f8:  add   r2, pc, #340    @ the format string
ff2616fc:  mov   r1, #3          @ level
ff261700:  mov   r0, #0x45       @ subsystem id
ff261704:  bl    0x67c8          @ log(subsystem, level, fmt)
```

Consequences, all tested:

- no absolute pointer to any WiFi string exists — checked exact and with a −8..+64
  window, under `0xFF000000`, `0xF8000000`, `0xFF0C0000`, `0xF80C0000`
- no `ADR` match either, because the strings are reached through a base register
  or a message table, not a direct `add rd, pc, #imm`
- inverting the RAM dump (any word minus the string offset landing on a 1 MB
  boundary in `0x40000000`–`0xAFFFFFFF`) returns nothing
- 16-bit offset tables: no dense run

So the anchor has to be **code**, not strings. Ghidra was used for that:
`ROM1.BIN` imported as `ARM:LE:32:v5` at `0xFF000000`, full analysis.

## The WiFi functions

299 distinct functions in `0xFF1E0000`–`0xFF270000` log identifiably. The spine:

| address | identity | evidence |
|---|---|---|
| `0xFF261714` | **`NWCOM Init`** — brings up network comms, allocates heap and BSS | `[NWCOM] NWCOM Init`, `pTopHeap`, `BssRegionSize`, `NetSetup Err` |
| `0xFF2616E8` | transmission callback | `[NWCOM] TransmissionChangeCBR(0x%x)` |
| `0xFF261B00` | network status callback | `[NWCOM] NetworkStatusCBR(Status=%d)` |
| `0xFF261F70` | device identity and discovery | `GUID:%x%x…`, `FriendlyName:%s`, `WizardProperty`, `Connect Confirm Judge` |
| `0xFF262358` | transfer order handler | `Nothing Order`, `FTP Transfer Stop Discover`, `FTP Transfer Count Non Zero(%d)` |
| `0xFF261974` | FTP transfer control | `FTP Transfer ReStart`, `From FTP Cancel Time out`, status tuple |
| `0xFF2634B8` | logical connect state | `DisConnectSuccess(0x%x)(Clr=0x%x)`, `ChangeLogicalConnect(0x%x)` |
| `0xFF2638C4` | connection monitoring and reconnect | `BeaconLoss!!`, `C2C ConnectCancel`, `WlanDisconnect -> ReConnect!!` |
| `0xFF266334` | GUI event fan-out | `NWCOM GUIEvent(0x%x)`, `Connect Event`, `DisConnect Event` |

Supporting strings in the same region, all unreferenced by pointer:
`WLAN module SDIO OK!!`, `Wlan Init Err`, `WLAN Biltin Judge (0x%x)`,
`NWCommu/NWCommuTransOrder.c`, `WFT (%#x <= %#x)`, `PROP_WFT_HTTP`.

## How capable is it?

Assessed strictly from what the strings and structure show.

**Present and complete:**

- a full **FTP** client path (start, stop, restart, cancel, timeout, progress)
- **device discovery** with GUID and friendly name — DLNA/UPnP-shaped
- **connection lifecycle**: associate, disconnect, beacon loss, auto-reconnect
- **C2C** (camera-to-camera) send and receive dialogs
- a **GUI event** layer that tells Canon's UI what the network is doing
- **WFT HTTP** — the web/transfer protocol Canon's own software speaks

**Not present, and this matters:**

- no `socket_create` / `socket_send` symbols anywhere in the image, by name
- no exported symbol table at all (`prop_deliver`, `task_create`,
  `take_semaphore` are all absent), so nothing can be resolved by name
- the transport is **Canon's own PTP/FTP stack**, not BSD sockets

**What that means for a module:** ML can only call what `6D_116.sym` exports,
and none of this is exported. Reaching it means calling fixed addresses directly.
That is possible — the addresses are now known — but it is a different kind of
risk from calling a named API: no signatures, no ABI guarantee, and a wrong call
crashes.

## Realistic capability ladder

| rung | what | risk |
|---|---|---|
| 1 | log that a WiFi address is reachable (no call) | none — the module either loads or does not |
| 2 | call `NWCOM Init` and log the return | low — it is documented by its own strings as the bring-up routine |
| 3 | read network status via `0xFF261B00` | medium — argument shape unknown |
| 4 | drive the FTP transfer path to push a file | high — needs the whole call graph |
| 5 | push a `.fs` recipe through it | as 4, plus the card write on the far side |

Rung 4 is what "transfer data like JPG" means. It is not reachable by guessing;
it needs `0xFF262358` (transfer order) and `0xFF261974` (FTP control) disassembled
and their arguments reconstructed.

## Already true today, without any of this

- **Photos out over WiFi**: Canon's own WiFi GUI and app do it. It is in the
  camera and works.
- **Recipes in**: `fs_film_watch_task()` in `film_sim` picks up any `.fs` that
  appears in `ML/FILM` within about six seconds, no reboot. Any transport that can
  write the card — card reader, phone with an SD slot, writable share — is enough.

So the WiFi reversal only removes the card from the recipe step. It does not add
a capability that is entirely missing; it removes a walk to a computer.
