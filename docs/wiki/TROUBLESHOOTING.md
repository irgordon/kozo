# Troubleshooting

Use the last trustworthy result. Do not weaken a validator, replace a checksum,
or classify a missing marker as success.

## QEMU Command Not Found

**Symptom:** the script reports `missing_qemu_tooling`.

**Likely cause:** `qemu-system-x86_64` is outside `PATH` and
`KOZO_QEMU_BIN` is unset.

**Safe check:**

```bash
command -v qemu-system-x86_64
```

**Expected result:** an executable path. Set `KOZO_QEMU_BIN` to that path when
running the script.

**Stop when:** no suitable x86-64 QEMU executable is installed. Do not hardcode
one developer's path into repository policy.

## QEMU Exits With 124

**Symptom:** the bounded smoke command exits with status `124`.

**Likely cause:** KOZO reached its terminal halt loop and the smoke timeout
stopped QEMU, or execution stalled before success.

**Safe check:**

```bash
cat artifacts/runtime/qemu_smoke.summary.txt
jq '{outcome, observed_markers}' artifacts/runtime/qemu_smoke.metadata.json
```

**Expected result:** `Outcome: pass`, 41 ordered markers, and final marker
`KOZO_RUNTIME_RETURN_OK`.

**Stop when:** the final marker is missing, the marker order differs, or the
summary reports a blocker. Exit `124` alone never proves success.

## No Serial Output

**Symptom:** the serial log has zero bytes or contains firmware output but no
KOZO marker.

**Likely cause:** QEMU did not launch the ISO, firmware did not reach Limine, or
the kernel stopped before serial initialization.

**Safe check:**

```bash
wc -c artifacts/runtime/qemu_smoke.log artifacts/runtime/qemu_smoke.stderr.log
cat artifacts/runtime/qemu_smoke.stderr.log
jq '{outcome, qemu_exit_code}' artifacts/runtime/qemu_smoke.metadata.json
```

**Expected result:** nonzero serial output and an exact blocker when the run
cannot pass.

**Stop when:** the serial log remains empty. Preserve stderr and do not convert
an automatic retry into silent pass evidence.

## Final Marker Is Missing

**Symptom:** markers stop before `KOZO_RUNTIME_RETURN_OK`.

**Likely cause:** the stage after the last observed marker failed.

**Safe check:**

```bash
jq -r '.observed_markers[]' artifacts/runtime/qemu_smoke.metadata.json
cat artifacts/runtime/qemu_smoke.summary.txt
```

**Expected result:** the summary names the last trusted marker and a
mechanically distinguishable blocker.

**Stop when:** a required marker is absent or duplicated. Do not reorder the
taxonomy or relax pass criteria.

## Limine Tree Is Incomplete

**Symptom:** the boot-image script cannot find Limine binaries, BIOS stages, or
UEFI files.

**Likely cause:** the pinned Limine tree was not built or `LIMINE_DIR` and
`LIMINE` refer to different installations.

**Safe check:**

```bash
test -x "$LIMINE"
test -f "$LIMINE_DIR/limine-bios.sys"
test -f "$LIMINE_DIR/limine-bios-cd.bin"
test -f "$LIMINE_DIR/limine-uefi-cd.bin"
```

**Expected result:** all four checks succeed for the pinned version described
in [Boot Tooling](../BOOT_TOOLING.md).

**Stop when:** any required file is absent. Rebuild the pinned tree instead of
copying files from an unknown Limine version.

## xorriso Prints Portability Warnings

**Symptom:** xorriso warns about EFI directory visibility, active partitions,
or hybrid-media compatibility.

**Likely cause:** the image builder is describing platform-specific boot-media
details. A warning is not automatically an ISO failure.

**Safe check:**

```bash
scripts/build_boot_image.sh
scripts/qemu_smoke.sh
```

**Expected result:** the ISO is nonzero, Limine packaging completes, and the
governed QEMU result passes.

**Stop when:** xorriso exits nonzero, the ISO is missing, or QEMU fails. Record
warnings accurately; do not suppress them to make logs quiet.

## `ld.lld` and `lld` Are Confused

**Symptom:** setup instructions appear satisfied, but the linker command is not
found.

**Likely cause:** the LLVM package is installed while the executable name
`ld.lld` is outside `PATH`; `lld` is a project/tool family name, not the linker
command used here.

**Safe check:**

```bash
command -v ld.lld
ld.lld --version
```

**Expected result:** an executable `ld.lld`.

**Stop when:** only an unrelated `lld` command exists. Do not substitute a
different linker without validating the build policy.

## Current Odin Leaves a `.o` Object Behind

**Symptom:** release-bundle validation reports `Odin did not emit the
requested object`, but a file with the same name and an added `.o` suffix
exists.

**Likely cause:** Odin `dev-2026-08` changed a suffixless `-out` request to
produce `<name>.o`. The v1.0.0 object helper recognizes the prior output forms
but not this one. This is tracked as `KOZO-TRIAGE-001`.

**Safe check:**

```bash
odin version
find artifacts -maxdepth 1 -name 'kernel-build-check*' -print
```

**Expected result:** the affected toolchain reports `dev-2026-08`, the exact
requested path is absent, and `artifacts/kernel-build-check.o` exists.

**Supported workaround:** use the accepted Odin `dev-2026-07` toolchain for
the v1.0.0 source and release-bundle path until the bounded patch is accepted.

**Stop when:** the exact requested object is absent. Do not rename the file,
weaken the release validator, or treat the failed bundle as accepted proof.

## Cargo Reports Generated-ABI Warnings

**Symptom:** `cargo check` succeeds but prints naming or dead-code warnings from
generated ABI bindings.

**Likely cause:** generated names preserve the canonical ABI rather than Rust
style.

**Safe check:**

```bash
cargo check --manifest-path userspace/core_service/Cargo.toml
cargo deny --manifest-path userspace/core_service/Cargo.toml check
```

**Expected result:** both commands pass; existing warnings remain visible and
do not conceal an error.

**Stop when:** either command fails or a new warning indicates behavior drift.
Do not hand-edit generated bindings.

## GNU and LLVM Disassembly Differ

**Symptom:** symbol labels or equivalent instruction spellings differ between
hosts.

**Likely cause:** GNU and LLVM tools format the same x86-64 binary differently.

**Safe check:**

```bash
aarch64-elf-readelf -h -l -S -s artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
nm -n artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
objdump -d artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
```

**Expected result:** ELF64 x86-64 metadata and equivalent required symbols and
instructions. The AArch64-prefixed tool is used only for ELF metadata.

**Stop when:** required structure or instructions are absent. Do not lower
evidence counts to hide formatting differences.

## Checksum Mismatch

**Symptom:** `shasum -a 256 -c SHA256SUMS` reports `FAILED`.

**Likely cause:** an incomplete, corrupted, or wrong-version download.

**Safe check:** confirm all files came from the same
[v1.0.0 release](https://github.com/irgordon/kozo/releases/tag/v1.0.0), then run
the checksum command again.

**Expected result:** every listed file reports `OK`.

**Stop when:** any mismatch remains. Delete the suspect download, download it
again, and do not run it until validation succeeds.

## Wrong Release Version

**Symptom:** asset names or metadata mention `v1.0.0-rc.1` instead of `v1.0.0`,
or the expected final archive is absent.

**Likely cause:** assets were downloaded from the historical prerelease.

**Safe check:**

```bash
jq '{version, display_version, commit}' release_metadata.json
```

**Expected result:** version `1.0.0`, display version `v1.0.0`, and commit
`1586089415a98a11d2024d606ce6301f568b7d6e`.

**Stop when:** metadata identifies another release. Do not combine files from
different release pages.

## A Local Rebuild Is Mistaken for the Hosted ISO

**Symptom:** a local ISO boots, but the result is being used to claim that the
downloaded release works.

**Likely cause:** `KOZO_BOOT_ISO` points to
`artifacts/runtime/boot_image/kozo.iso` instead of the downloaded file.

**Safe check:**

```bash
jq '.boot_image' artifacts/runtime/qemu_smoke.metadata.json
```

**Expected result:** the recorded path is the intended downloaded ISO during a
release-artifact test.

**Stop when:** the path names a local rebuild. Re-run against the hosted ISO;
do not substitute one evidence source for the other.

## A Generated Report Is Stale

**Symptom:** a drift validator reports that checked-in output differs from the
renderer.

**Likely cause:** an authoritative input changed without a governed refresh.

**Safe check:**

```bash
git status --short
scripts/verify.sh
git diff -- docs/generated artifacts
```

**Expected result:** generated changes are explained by current authoritative
inputs and pass the drift validator.

**Stop when:** the reason for the generated change is unknown. Never edit the
report manually.

## A Documented Command No Longer Works

**Symptom:** a current guide command fails in a clean checkout.

**Likely cause:** tooling or repository behavior changed without a
documentation update.

**Safe check:**

```bash
git log -1 --oneline
git status --short --branch
```

**Expected result:** the checkout and guide refer to the same branch or tag.

**Stop when:** an untested workaround would change governance or evidence.
Open a focused documentation or tooling correction instead.
