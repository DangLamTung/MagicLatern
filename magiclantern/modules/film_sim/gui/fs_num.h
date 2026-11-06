/*
 * fs_num.h - numbers formatted without trust in Canon's vsnprintf.
 *
 * The firmware's vsnprintf has no precision support. It does not reject
 * "%.8s", it prints the tail as text: a save that asked for
 * "ML/FILM/%.8s.fs" wrote a file called ".8s.fs", and "ML/FILMS/90_%.8s.xml"
 * with <code>%.11s</code> inside it. Both were found on a real card, and the
 * camera's own FILMSIM.LOG says it out loud:
 *
 *   creator: wrote ML/FILM/.8s.fs (371 bytes, 12 wedges)
 *   look: registered LOOK as ML/FILMS/90_.8s.xml
 *
 * Zero-padded width ("%02d") is not trusted either: it is the same kind of
 * length/flag parsing, and a wrong guess puts "R06d" on the card instead of
 * "R000123". So anything that has to be padded is padded here, by hand, and
 * the module's sources are checked for both specifier shapes by
 * se/hosttest/fmtchk.c.
 */
#ifndef FS_NUM_H_INCLUDED
#define FS_NUM_H_INCLUDED

#include <stddef.h>

/*
 * Write `value` into `out` with at least `width` characters, zero filled.
 * Never writes more than ``cap - 1`` characters plus the terminator.
 * A negative value keeps its sign in front of the padding: -7 at width 3 is
 * "-07", not "0-7".
 */
static void fs_pad_num(char *out, size_t cap, int value, int width)
{
  char rev[12];
  unsigned v;
  size_t i = 0;
  int n = 0, neg;

  if (!out || cap < 2)
    return;

  neg = value < 0;
  v = neg ? (unsigned)(-(value + 1)) + 1u : (unsigned)value; /* no UB on INT_MIN */

  do {
    rev[n++] = (char)('0' + (v % 10u));
    v /= 10u;
  } while (v && n < (int)sizeof rev);

  if (neg && i < cap - 1)
    out[i++] = '-';
  while ((int)i < width && i < cap - 1)
    out[i++] = '0';
  while (n > 0 && i < cap - 1)
    out[i++] = rev[--n];
  out[i] = 0;
}

#endif
