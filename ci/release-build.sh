#!/bin/sh
#
# Build the 6D firmware, prove the artefacts, and write them to dist/.
#
#   ./ci/release-build.sh                     # toolchain already in toolchain/
#   DOWNLOAD_TOOLCHAIN=1 ./ci/release-build.sh # fetch it first (CI)
#
# env:
#   MODULE_REPO  where the module tree comes from (default: this repo's own
#                GitHub module repo)
#   MODULE_REF   branch, tag or sha to build (default: dev)
#
# The point of doing it in a script rather than inline in the workflow is that
# the same steps run on a Mac, so a red release job can be reproduced locally
# instead of guessed at.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

MODULE_REPO=${MODULE_REPO:-https://github.com/DangLamTung/MagicLatern-ML.git}
MODULE_REF=${MODULE_REF:-dev}
# GitHub's macOS runners are arm64 or x86_64 depending on the image.
case $(uname -m) in
  arm64|aarch64) TC_ARCH=darwin-arm64 ;;
  *)             TC_ARCH=darwin-x86_64 ;;
esac
TOOLCHAIN_DIR="arm-gnu-toolchain-13.3.rel1-$TC_ARCH-arm-none-eabi"
TOOLCHAIN_URL="https://developer.arm.com/-/media/Files/downloads/gnu/13.3.rel1/binrel/$TOOLCHAIN_DIR.tar.xz"
CAM=${CAM:-6D.116}
DIST="$ROOT/dist"

say() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------- toolchain
if [ ! -x "toolchain/$TOOLCHAIN_DIR/bin/arm-none-eabi-gcc" ]; then
    if [ "${DOWNLOAD_TOOLCHAIN:-0}" != "1" ]; then
        echo "no ARM toolchain in toolchain/$TOOLCHAIN_DIR" >&2
        echo "re-run with DOWNLOAD_TOOLCHAIN=1, or extract it there yourself" >&2
        exit 1
    fi
    say "downloading the ARM toolchain (128 MB)"
    mkdir -p toolchain
    curl -fL --retry 3 -o "/tmp/$TOOLCHAIN_DIR.tar.xz" "$TOOLCHAIN_URL"
    tar -xJf "/tmp/$TOOLCHAIN_DIR.tar.xz" -C toolchain
    rm -f "/tmp/$TOOLCHAIN_DIR.tar.xz"
fi
say "toolchain: $(toolchain/$TOOLCHAIN_DIR/bin/arm-none-eabi-gcc -dumpversion)"

# ---------------------------------------------------------------------- venv
# build.sh refuses to run without docutils (it makes the user guide).
if [ ! -x toolchain/venv/bin/rst2html ]; then
    say "creating the docutils venv"
    python3 -m venv toolchain/venv
    toolchain/venv/bin/pip install -q --upgrade pip
    toolchain/venv/bin/pip install -q docutils
fi

# -------------------------------------------------------------------- module
if [ ! -d magiclantern/.git ] && [ ! -f magiclantern/Makefile.globals ]; then
    say "cloning $MODULE_REF from $MODULE_REPO"
    rm -rf magiclantern
    git clone -q "$MODULE_REPO" magiclantern
    git -C magiclantern checkout -q "$MODULE_REF"
fi
say "module tree: $(git -C magiclantern rev-parse --short HEAD 2>/dev/null || echo 'not a git checkout')"

# --------------------------------------------------------------------- tests
# A release that was never tested is not a release. The host tests cover the
# look engine and every recipe writer, and they take seconds.
say "host tests"
( cd magiclantern/modules/film_sim/se/hosttest && ./run_tests.sh ) | tee /tmp/fs_hosttests.log
grep -q "ALL HOST TESTS PASSED" /tmp/fs_hosttests.log || {
    echo "host tests did not pass; refusing to package" >&2; exit 1; }

say "romfind unit tests"
( cd magiclantern/modules/film_sim/tools/romfind && ./selftest.py )

# --------------------------------------------------------------------- build
# "clean" because the platform build does not notice module source changes on
# its own, and a release is exactly the moment that mistake is unrecoverable.
say "build $CAM"
# Not `./build.sh | tee`: sh has no pipefail, so the pipe would report tee's
# status and a failed build would be blamed on the import gate below.
if ! ./build.sh "$CAM" clean > /tmp/fs_build.log 2>&1; then
    tail -n 40 /tmp/fs_build.log >&2
    echo "build failed" >&2
    exit 1
fi
tail -n 8 /tmp/fs_build.log

# A module that imports a symbol the body does not export loads with "module
# load error" and no log at all. build.sh fails on it, but say it out loud so
# the log shows the gate ran.
grep -q "every import resolves" /tmp/fs_build.log || {
    echo "the module import gate did not report success" >&2; exit 1; }

# ------------------------------------------------------------------- package
ZIP="magiclantern/platform/$CAM/build/magiclantern.zip"
BIN="magiclantern/platform/$CAM/build/autoexec.bin"
MOD="magiclantern/platform/$CAM/build/modules/film_sim.mo"
for f in "$ZIP" "$BIN" "$MOD"; do
    [ -s "$f" ] || { echo "missing artefact: $f" >&2; exit 1; }
done

# The zip must contain the module the tests just covered, not a stale copy.
say "verify the zip carries the built module"
rm -rf /tmp/fs_zipcheck && mkdir -p /tmp/fs_zipcheck
unzip -qo "$ZIP" ML/modules/film_sim.mo -d /tmp/fs_zipcheck
same=$(cmp -s /tmp/fs_zipcheck/ML/modules/film_sim.mo "$MOD" && echo yes || echo no)
[ "$same" = yes ] || { echo "the zip holds a different film_sim.mo than the build" >&2; exit 1; }

rm -rf "$DIST" && mkdir -p "$DIST"
cp "$ZIP" "$DIST/magiclantern-$CAM.zip"
cp "$BIN" "$DIST/autoexec-$CAM.bin"
cp "$MOD" "$DIST/film_sim-$CAM.mo"
[ -f "magiclantern/modules/mlwifi/build/mlwifi.mo" ] && \
    cp "magiclantern/modules/mlwifi/build/mlwifi.mo" "$DIST/mlwifi-$CAM.mo" || true
cp /tmp/fs_hosttests.log "$DIST/hosttests.log"

cat > "$DIST/RELEASE-NOTES.md" <<NOTES
Built from MagicLatern-ML \`$(git -C magiclantern rev-parse --short HEAD 2>/dev/null || echo unknown)\`
($MODULE_REF). The host tests and the ROM-tool unit tests passed before anything
was packaged; the log is in \`hosttests.log\`.

| asset | what it is |
|---|---|
| magiclantern-$CAM.zip | the ML tree to copy onto the card, film_sim included |
| autoexec-$CAM.bin | the bootloader payload alone, if that is all you replaced |
| film_sim-$CAM.mo | the module on its own |
| mlwifi-$CAM.mo | WiFi probe, shipped apart on purpose: it is not in the zip because it only verifies nine addresses and calls nothing yet |
| hosttests.log | the test run this build came from |
| SHA256SUMS | every file above |

A .mo hash identifies one build, not a tree: the module embeds its build time
(`2026-11-06 09:15:18 UTC` and three differing bytes is the whole delta between
two builds of the same source). Use SHA256SUMS to check a download, not to
decide whether two builds agree -- compare commit ids for that, and compare the
card against the build you just installed.
NOTES

say "checksums"
( cd "$DIST" && { shasum -a 256 ./* 2>/dev/null || sha256sum ./*; } ) | tee "$DIST/SHA256SUMS"

say "done: $DIST"
