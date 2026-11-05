# What a Fuji recipe actually is, and what this module can honour

A "film simulation recipe" (Fuji X Weekly and the wider X community) is not a
LUT and not a curve: it is a saved bundle of **camera settings** named against
one of the camera's built-in film simulations. Verified against a published
X-Trans IV recipe (X100V-era) rather than from memory.

Fields, in the order Fuji lists them:

| Fuji field | range | this module | how |
|---|---|---|---|
| Film Simulation (base) | Provia, Velvia, Astia, Classic Chrome, Classic Neg, Eterna, Acros, Monochrome, Pro Neg Hi/Std, … | **partial** | a stock's `NAME` is the base; the 34 in `film_table.h` cover the Canon equivalents, not Fuji's list |
| Dynamic Range | DR100 / DR200 / DR400 | **no** | a sensor-level exposure/tone construct. No equivalent on DIGIC via ML |
| Highlight | −2 … +4 | **yes** | `CURVE` (upper half) |
| Shadow | −2 … +4 | **yes** | `CURVE` (lower half) |
| Color | −4 … +4 | **yes** | `SAT` (100 = 0; −4 … +4 maps to roughly 60…200) |
| Noise Reduction | −4 … +4 | **no** | Canon's NR is a camera property in the picture style; not driven yet |
| Sharpening | −4 … +4 | **partial** | `film.sim.sharp` sets Canon's style sharpness at capture; not per recipe |
| Clarity | −5 … +5 | **attempted, reverted** | implemented as a box-mean high-pass and removed when it failed its own test — see below |
| Grain Effect | Off / Weak / Strong × Small / Large | **yes** | `GRAIN` + `GRAIN_SIZE` |
| Color Chrome Effect | Off / Weak / Strong | **yes** (added) | `COLOR_CHROME 0|1|2` |
| Color Chrome Effect Blue | Off / Weak / Strong | **yes** (added) | `FX_BLUE 0|1|2` |
| White Balance | mode + **R and B**, each −9 … +9 | **partial** | the WB screen edits R and B; they are mapped onto `PROP_WBS_GM` / `PROP_WBS_BA` |
| ISO | the recipe's base ISO | **yes** | `film.sim.iso` / stock box speed |
| Exposure Compensation | a shooting hint | **n/a** | a shooting habit, not an image parameter |

## Color Chrome and FX Blue

Both are statements about the *shape* of the chroma response, which is why
neither can be replaced by a saturation number:

* **Color Chrome** deepens colours that are already saturated and leaves dull
  ones alone.
* **FX Blue** is the same statement restricted to blues.

Measured on the host through the real look (`/tmp/chrometest`, 2026-11-05),
chroma of the same pixel before and after:

| pixel | off | weak | strong |
|---|---|---|---|
| muted red (140,100,95) | 33.1 | 34.5 | 36.7 |
| strong red (210,40,35) | 132.0 | 148.6 | 165.1 |
| strong green | 100.6 | 112.8 | 125.6 |
| grey | 0.0 | 0.0 | 0.0 |

and FX Blue, which moves only blues:

| pixel | off | strong |
|---|---|---|
| muted blue | 27.5 | 28.8 |
| strong blue | 143.6 | 161.6 |
| strong red | 132.0 | 132.0 |

The first implementation multiplied raw (B−Y, R−Y) differences by the *scaled*
YCbCr inverse, over-stating the effect by 454/256. It measured as muted colours
gaining more than saturated ones — the opposite of the claim — and was fixed
before any of this was written down.

## Clarity: implemented, measured, reverted

Clarity is the one field that needs a neighbourhood, and the streaming look
does have the machinery: halation already keeps a rolling column sum and a
delay line, so a box mean of luma is nearly free. It went in as

    out = in + clarity * (in - mean(local)) * midtone_weight

and measured, on a flat 8-pixel chequer of 96/136 that must not change level:

| CLARITY | mean level | local contrast |
|---|---|---|
| off | 116.00 | 16.05 |
| −5 | 108.32 | 9.75 |
| +2 | 118.42 | 18.57 |
| +5 | 122.68 | 22.35 |

Local contrast moves the right way and is monotonic, but **the level moves
with it** — +6.7 at CLARITY 5 on a chequer whose mean cannot legitimately
change. Root cause: the ring sums the **input** luma while the effect is
applied to the **graded** row, so the tone curve's own lift is read as
high-pass detail and multiplied by the clarity amount.

The fix is a ring of graded luma, which means grading before the ring is
filled rather than at emit time — a real change to the streaming order, not a
tweak. Per this module's rule (mRAW was removed rather than shipped broken),
it was reverted instead of shipped: `CLARITY` is not in the parser today.

## White balance: Fuji's axes are not Canon's

A recipe quotes "+2 Red & −5 Blue". `PROP_WBS_BA` / `PROP_WBS_GM` speak
Blue/Amber and Green/Magenta. The screen edits **R and B** so a published
recipe can be typed as printed, and converts on the way out:

    Canon B/A = −Fuji Blue        Canon G/M = −Fuji Red

The scale is 1:1 because both are −9…+9. **This is a structural match, not a
measured equivalence** — no Fuji body was available to compare against, so a
transcribed recipe should be treated as approximate.

The shift is an **offset on the stock's own balance**, not a replacement: every
stock in `film_table.h` carries its own blue/amber and green/magenta pair, and
the applied value is `stock + offset`, clamped to ±9.

## What is still missing, in order of how much a recipe needs it

1. **Clarity** — designed, measured, and reverted for the reason above; it
   needs a graded-luma ring before it can be trusted. This is the biggest gap,
   and recipes lean on it heavily for the "not a clean digital image" look.
2. **Noise Reduction** — a camera property, easy to drive once the style blob
   is understood; currently untouched.
3. **Sharpening per recipe** — the module has one global value, not per stock.
4. **DR** — not reproducible on this body; should be documented as such rather
   than faked with a curve.
5. **Fuji's own base simulations** — Canon's picture styles are the substrate,
   so "Classic Chrome" here is a recipe *named* after one, not Fuji's render.
