# Kodak Kodachrome 64: deep reds, dark blue shadows, rich mids.
#
# Kodachrome's look is mostly its cyan dye: blue is pulled hard (B curve
# 64,56 and 128,118) while red sits 6-8 levels high through the middle.  That
# is the "deep reds, dark blue shadows" everyone describes, and it is a pair of
# curves, not a global temperature.  ROT +8 on red toward orange keeps skin
# from going pink against all that red.
#
VERSION   3
NAME      KODACHROME 64
DESC      DEEP REDS, DARK BLUE SHADOWS, RICH MIDS
WB        DAYLIGHT
CURVE     0,0 40,30 128,132 200,208 255,250
CURVE_R   0,0 64,66 128,136 192,204 255,252
CURVE_G   0,0 128,128 255,250
CURVE_B   0,0 64,56 128,118 192,180 255,240
SAT       112
HUE_SAT    114,115,116,105,94,95,96,99,102,102,102,108
HUE_ROT    8,7,6,-2,-10,-7,-4,-0.5,3,2,1,4.5
HUE_LUM    101,102.5,104,97,90,91,92,89,86,93,100,100.5
SPLIT_SH  -8,-2,10
SPLIT_HI  10,6,-10
HALATION  24 238 10
HAL_TINT  255,80,40
GRAIN     8
GRAIN_SIZE 10

