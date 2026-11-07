# Is the shot graded once, twice, or not at all?

The in-shutter grade is the easiest part of this module to get wrong and the
hardest to see. Three outcomes, three different-looking JPEGs, and all three
have been shipped at some point:

| what happened | what the file looks like | how it reads in FILMSIM.LOG |
|---|---|---|
| look applied once, inside the shot | the look | `yuvgrade: in-shutter grade ON (capture style Neutral)` and `yuvhook: 1 call(s) (1 still, 0 ssraw), 1 graded` |
| look applied twice — once by the picture style Canon baked, once by the engine | milky: low contrast, cast, colour pulled toward the middle | `N graded` with a capture style that is **not** `0x84` |
| look not applied at all | flat and neutral; the stock in the slot does nothing | `armed rows …` non-zero but `0 graded` |

The middle one was measured on 2 November 2026: the six Đà Lạt frames that were
being used as samples turned out to be graded twice, which is why they looked
washed. `sooc_check.py` is how that was found and how it is re-checked.

## Running it

```sh
python3 magiclantern/modules/film_sim/tools/sooc_check.py \
    --cr2 /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_3110.CR2 \
    --jpg /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_3110.JPG \
    --stock magiclantern/modules/film_sim/films/classicchrome.fs
```

It develops the raw with `samples/base-neutral.fs` (no look), applies the stock
once, applies it again, and compares all three against the camera's JPEG after
normalising brightness — so what is being measured is the shape of the look, not
the exposure. It prints the closest of the three.

The stock has to be the one that was actually in the slot when the frame was
shot: `ML/SETTINGS/film_sim.cfg` has `film.sim.stock = <n>`, and `n` counts
`ML/FILMS/` in order (`28` is `28_CCHR.xml`, Classic Chrome).

## The control

A capture known to be double-graded must come out `x2`, otherwise the test is not
measuring anything:

```
IMG_9923.JPG + classicneg.fs
  base  (no look)    22.7 /255
  x2    (look twice) 10.9 /255
  x1    (look once)  15.5 /255
  closest: x2
```

That frame is from the morning the samples were shot. The current code forces
the capture style to built-in Neutral and skips the PF2 blob while the grade is
armed, so the expectation for a fresh capture is `x1`. A fresh capture that
comes out `base` means the grade is armed but never reaches the file; one that
comes out `x2` means the style was not Neutral after all.

Either way, read `FILMSIM.LOG` from that boot before changing anything: the
`yuvhook: N call(s) … X graded` line and the `capset: picture style 0x?? -> 0x??`
line together say which of the three rows above happened.
