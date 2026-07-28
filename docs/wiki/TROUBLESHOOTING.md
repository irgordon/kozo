# Troubleshooting

Each section separates the symptom, likely cause, checks, and unsafe shortcut.

## QEMU Is Not Found

**What you see:** metadata reports `missing_qemu_tooling`.

**What it usually means:** `KOZO_QEMU_BIN` is unset and
`qemu-system-x86_64` is not discoverable.

**What to check:**

```bash
command -v qemu-system-x86_64
qemu-system-x86_64 --version
```

**What not to do:** do not hardcode one developer-specific path into a script.

## QEMU Produces No Serial Output

**What you see:** the serial log is empty or the run times out before a marker.

**What it usually means:** QEMU did not launch the image, firmware did not reach
Limine, or the kernel stopped before serial entry.

**What to check:**

```bash
wc -c artifacts/runtime/qemu_smoke.log artifacts/runtime/qemu_smoke.stderr.log
cat artifacts/runtime/qemu_smoke.stderr.log
jq '{outcome, blocker_category, qemu_exit_code}' artifacts/runtime/qemu_smoke.metadata.json
```

**What not to do:** do not convert an empty run into pass evidence with a retry.

## Limine Is Not Reached

**What you see:** no Limine text and no KOZO entry marker.

**What it usually means:** the ISO, firmware path, or Limine artifacts are
wrong.

**What to check:**

```bash
ls -lh artifacts/runtime/boot_image/kozo.iso
cat artifacts/runtime/boot_image/iso_contents.txt
cat artifacts/runtime/qemu_smoke.stderr.log
```

**What not to do:** do not debug Odin runtime code before the bootloader path is
proven.

## A Marker Is Missing

**What you see:** the marker list ends before `KOZO_RUNTIME_RETURN_OK`.

**What it usually means:** execution stopped at the boundary after the last
observed marker.

**What to check:**

```bash
jq -r '.observed_markers[]' artifacts/runtime/qemu_smoke.metadata.json
cat artifacts/runtime/qemu_smoke.summary.txt
```

**What not to do:** do not reorder the taxonomy or weaken pass criteria.

## ELF Reports Differ on macOS and Linux

**What you see:** labels or instruction spelling differ between GNU and LLVM
tools.

**What it usually means:** the tools printed equivalent binary data
differently.

**What to check:**

```bash
aarch64-elf-readelf -h -l -S -s artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
nm -n artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
objdump -d artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
```

**What not to do:** do not lower required instruction or symbol evidence to
hide a formatting difference.

## A Generated Report Is Stale

**What you see:** a drift validator reports that checked-in output differs from
the renderer.

**What it usually means:** an authoritative input changed without a governed
refresh.

**What to check:**

```bash
git status --short
scripts/verify.sh
git diff -- docs/generated artifacts
```

**What not to do:** do not edit the generated report manually.

## The Governance Index Fails

**What you see:** `governance_index_report` reports stale content.

**What it usually means:** contracts, schemas, validators, tasks, or version
state changed.

**What to check:**

```bash
python3 -c 'from harness.governance_index_report import write_report; write_report()'
python3 -m unittest tests/test_governance_index_report.py
```

**What not to do:** do not delete the validator or hand-edit the index.

## cargo-deny Fails

**What you see:** an advisory, ban, source, or license check fails.

**What it usually means:** package metadata or dependency policy does not match
`deny.toml`.

**What to check:**

```bash
cargo deny --manifest-path userspace/core_service/Cargo.toml check licenses
cargo deny --manifest-path userspace/core_service/Cargo.toml check
```

**What not to do:** do not add a crate exception merely to make the command
green.

## Taplo Crashes on macOS

**What you see:** Taplo exits with a `system-configuration` or NULL-object
panic.

**What it usually means:** the local Taplo build failed while reading macOS
network configuration, not that the TOML is valid or invalid.

**What to check:**

```bash
taplo fmt --check .
taplo check
```

**What not to do:** do not report Taplo success after a panic. Record the
tooling limitation and rely on the governed checks that actually ran.

## A Documented Command No Longer Works

**What you see:** a command fails even though the guide describes it as current.

**What it usually means:** tooling or repository behavior changed without a
documentation update.

**What to check:**

```bash
git log -1 --oneline
git status --short --branch
```

**What not to do:** do not replace the command with an untested workaround.
Open a focused documentation or tooling correction.
