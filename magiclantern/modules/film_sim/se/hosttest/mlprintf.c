/*
 * mlprintf - a stand-in for Canon's vsnprintf, which is not ISO C.
 *
 * Three things have now shipped broken because macOS printf is correct and the
 * camera's is not:
 *
 *   "%.8s"   ->  ".8s"    a save wrote ML/FILM/.8s.fs and nothing could open it
 *   "%.11s"  ->  ".11s"   an XML carried <code>.11s</code>
 *   "%-9s"   ->  "-9s"    a recipe lost all three HUE_ lines: the parser did not
 *                         know a key called "-9s", so a saved look kept only its
 *                         curve
 *
 * The camera's formatter handles %d %u %x %s %c, the '+' and '0' flags, and a
 * width. It does not handle a precision or the '-' flag: it emits the specifier
 * text instead. Every one of those facts came off a card, not from a manual --
 * FILMSIM.LOG prints "date 2026-11-06 09:15:18" (%02d works) and addresses as
 * "0x1ee17800" (%08x works), while the files above carry the literal tails.
 *
 * This file exists so the host tests can run the writers through the camera's
 * behaviour instead of the host's. It defines snprintf/vsnprintf itself, which
 * takes precedence over libc for every call in the test binary -- but only if
 * _FORTIFY_SOURCE is off, because macOS's <stdio.h> otherwise rewrites the
 * call into __builtin___vsnprintf_chk, which no symbol can intercept (that is
 * exactly how a first attempt at this file silently tested nothing).
 *
 * Build with:
 *
 *     -D_FORTIFY_SOURCE=0 mlprintf.c creatorwrite.c ...
 *
 * A specifier the camera cannot parse then fails the round-trip test here, on a
 * Mac, instead of on the camera with a silently wrong picture.
 */
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

typedef struct {
    char  *out;
    size_t cap;
    size_t len;
} mlbuf;

static void putc_ml(mlbuf *b, char c)
{
    if (b->len + 1 < b->cap)
        b->out[b->len] = c;
    b->len++;
}

static void puts_ml(mlbuf *b, const char *s, int len)
{
    int i;
    for (i = 0; i < len; i++)
        putc_ml(b, s[i]);
}

static void emit_number(mlbuf *b, unsigned long v, int base, int upper,
                        int width, int zero, int neg, int plus)
{
    char tmp[32];
    int n = 0;
    const char *digits = upper ? "0123456789ABCDEF" : "0123456789abcdef";

    do {
        tmp[n++] = digits[v % (unsigned)base];
        v /= (unsigned)base;
    } while (v);

    if (neg || plus)
        width--;                       /* the sign is part of the field  */
    while (n < width) {
        tmp[n++] = zero ? '0' : ' ';
        if (!zero) break;              /* right alignment handled below   */
    }
    if (neg)      putc_ml(b, '-');
    else if (plus) putc_ml(b, '+');
    while (n-- > 0)
        putc_ml(b, tmp[n]);
}

static int vsnprintf_ml(char *buf, size_t cap, const char *fmt, va_list ap)
{
    mlbuf b;
    b.out = buf; b.cap = cap; b.len = 0;

    for (; *fmt; fmt++) {
        int zero = 0, plus = 0, width = 0, done = 0;

        if (*fmt != '%') { putc_ml(&b, *fmt); continue; }
        fmt++;

        /* The camera reads '+' and '0' and a width, then wants a conversion. */
        for (;; fmt++) {
            if (*fmt == '+') plus = 1;
            else if (*fmt == '0') zero = 1;
            else if (*fmt >= '1' && *fmt <= '9') {
                while (*fmt >= '0' && *fmt <= '9') width = width * 10 + (*fmt++ - '0');
                fmt--;
            } else break;
        }

        switch (*fmt) {
        case 'd': case 'i': {
            long v = va_arg(ap, int);
            if (v < 0) emit_number(&b, (unsigned long)(-v), 10, 0, width, zero, 1, 0);
            else       emit_number(&b, (unsigned long)v, 10, 0, width, zero, 0, plus);
            done = 1;
            break;
        }
        case 'u':
            emit_number(&b, va_arg(ap, unsigned), 10, 0, width, zero, 0, 0);
            done = 1;
            break;
        case 'x':
            emit_number(&b, va_arg(ap, unsigned), 16, 0, width, zero, 0, 0);
            done = 1;
            break;
        case 'X':
            emit_number(&b, va_arg(ap, unsigned), 16, 1, width, zero, 0, 0);
            done = 1;
            break;
        case 's': {
            const char *s = va_arg(ap, const char *);
            int n = s ? (int)strlen(s) : 0;
            puts_ml(&b, s ? s : "(null)", n);
            done = 1;
            break;
        }
        case 'c':
            putc_ml(&b, (char)va_arg(ap, int));
            done = 1;
            break;
        case '%':
            putc_ml(&b, '%');
            done = 1;
            break;
        default:
            break;
        }
        if (!done) {
            /*
             * A precision (".") or the '-' flag lands here. The camera does not
             * swallow them: it prints the tail of the specifier as text, which
             * is the bug this file is here to catch. Reproduce that exactly.
             */
            putc_ml(&b, *fmt);
        }
    }

    if (b.cap) {
        size_t end = b.len < b.cap - 1 ? b.len : b.cap - 1;
        b.out[end] = 0;
    }
    return (int)b.len;
}

/* The real names, so every call in the program lands here. */
int vsnprintf(char *buf, size_t cap, const char *fmt, va_list ap)
{
    return vsnprintf_ml(buf, cap, fmt, ap);
}

int snprintf(char *buf, size_t cap, const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsnprintf_ml(buf, cap, fmt, ap);
    va_end(ap);
    return n;
}
