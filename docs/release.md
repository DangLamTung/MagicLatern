# Cutting a release

A release is: a tag, one script, and the hashes on the card.

```sh
./ci/release-build.sh          # build, test, package into dist/
git tag v1.2.0 && git push --tags
```

The tag push runs `.github/workflows/release.yml`, which calls the same script
and publishes `dist/` with `gh release create`. Run the script by hand if you
would rather see the output - the workflow exists to make the result
reproducible, not to be the only way.

## What blocks a release

`ci/release-build.sh` stops before packaging if any of these fail:

| gate | why |
|---|---|
| `se/hosttest/run_tests.sh` | the look engine, both recipe writers, and the neutral-ramp and table bounds. Seconds to run. |
| `tools/romfind/selftest.py` | the ROM analysis tool, on synthetic images |
| the import gate in `build.sh` | a module importing a symbol the body does not export loads with "module load error" and no log at all |
| the zip/module comparison | a stale `film_sim.mo` cannot ship inside a new zip |

The ARM build itself is not in CI: `build.sh` needs the Darwin toolchain, BSD
`stat` and `sysctl`, so it runs on a macOS runner. `macos-26` is the image it asks for --
`macos-14` was retired from GitHub-hosted runners and a retired label cancels
the run in one second.

## Reading the hashes

`SHA256SUMS` checks a download. It does **not** tell you two builds agree: the
`.mo` and `autoexec.bin` embed a build time (`2026-11-06 09:15:18 UTC`), so
rebuilding identical source changes three bytes and the hash with them. To
compare two builds, compare commit ids; to check the camera, compare the card
against the build you just installed:

```sh
md5 -q dist/film_sim-6D.116.mo
md5 -q /Volumes/EOS_DIGITAL/ML/modules/film_sim.mo
shasum -a 256 /Volumes/EOS_DIGITAL/autoexec.bin   # vs dist/SHA256SUMS
```

`./install-sd.sh` does this itself and prints `ok matches build/...`.

## What is in the zip, and what is not

`magiclantern-6D.116.zip` contains the modules listed in
`magiclantern/platform/6D.116/modules.included`. `mlwifi` is deliberately not
on that list: it verifies nine WiFi addresses and calls nothing, so a menu item
for it in a release would be a dead end. It ships as a separate `.mo` a user can
copy into `ML/modules` to try it.
