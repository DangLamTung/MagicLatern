# The neutral base the samples are developed with: identity curves, no hue move,
# no split tone, no grain, and the one thing an identity transform lacks -- the
# brightness a camera JPEG's tone curve gives.
#
# Why 1.8: at 0 the develop is darker than the camera's own JPEG of the same
# frame (mean luma 48 against 74 on IMG_9919, 75 against 147 on IMG_9932); at
# 1.8 the two sit within a third of a stop on nine of eleven frames. This is a
# measuring stick, not a look -- nothing shipped uses it as a stock.
NAME      FLAT
EXPOSURE  1.8
CURVE     0,0 255,255
HUE_SAT   100,100,100,100,100,100,100,100,100,100,100,100
HUE_ROT   0,0,0,0,0,0,0,0,0,0,0,0
HUE_LUM   100,100,100,100,100,100,100,100,100,100,100,100
