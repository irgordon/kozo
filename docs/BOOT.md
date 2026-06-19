# KOZO Boot Baseline

Version: 1
Status: Authoritative
Scope: Current bootability status and boot baseline requirements

---

# 1. Purpose

This document records the current KOZO boot baseline.

The v0.3.0 bootable runtime baseline attempted to determine whether the current kernel output can honestly be booted under QEMU.

The result is blocked.

v0.3.1 selected Limine as the initial x86_64 boot protocol.

v0.3.2 added the boot image skeleton.

v0.3.3 added a bounded QEMU smoke command and attempted the first QEMU serial path.

v0.3.4 added deterministic boot image packaging metadata and confirmed that Limine ISO tooling was still missing.

v0.3.5 added `docs/BOOT_TOOLING.md` to define the Limine and xorriso acquisition path.

v0.3.6 added the ISO generation command path to `scripts/build_boot_image.sh`, but local generation remains blocked because Limine artifacts and xorriso are unavailable.

v0.3.7 added CI installation of pinned Limine tooling and xorriso so full CI can attempt `scripts/build_boot_image.sh` and upload boot image artifacts when produced.

Remaining blocker: `missing_iso_generation_tooling`.

The local blocker is `missing_iso_generation_tooling`.

If CI produces `artifacts/runtime/boot_image/kozo.iso`, the generated blocker report narrows to `missing_qemu_serial_evidence` for that run.

---

# 2. Current Result

Boot feasibility result: blocked.

Blocker category: `missing_iso_generation_tooling`.

The local blocker category is `missing_iso_generation_tooling`.

CI packaged-image blocker category, when the ISO exists: `missing_qemu_serial_evidence`.

Selected boot protocol: Limine.

The current repository has a 64-bit `_start` symbol, an exported `kernel_entry`, early serial initialization, and runtime-adjacent object/symbol smoke evidence.

The boot protocol decision, boot image skeleton, boot tooling acquisition policy, ISO generation command path, and CI ISO tooling install path are complete.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/package_metadata.json`.

The expected ISO path is `artifacts/runtime/boot_image/kozo.iso`.

GitHub Actions full CI installs xorriso, acquires Limine v12.3.3 from a pinned source release, builds Limine, and attempts ISO generation.

The current local tooling does not yet provide the Limine artifacts and xorriso executable required to produce that image, so local verification continues to report blocked packaging metadata.

KOZO does not have QEMU smoke execution or captured serial evidence.

---

# 3. Missing Components

The concrete remaining missing components are:

* local Limine executable
* local xorriso executable
* local Limine bootloader artifacts
* bootable ISO artifact when not produced by CI
* validated QEMU serial smoke execution

Until those exist, KOZO must not claim QEMU boot evidence.

---

# 4. Current Surfaces

The current source surfaces relevant to future boot work are:

* `kernel/arch/x86_64/boot.asm`
* `kernel/main.odin`
* `kernel/arch/x86_64/serial.odin`
* `scripts/runtime_smoke.sh`
* `scripts/build_boot_image.sh`
* `scripts/qemu_smoke.sh`
* `docs/BOOT_TOOLING.md`

`kernel/arch/x86_64/boot.asm` defines `_start`, and `scripts/build_boot_image.sh` links a kernel ELF for the Limine image skeleton.

`kernel/main.odin` exports `kernel_entry`, but no bootable ISO or disk image currently transfers control to it through a proven loader path.

`kernel/arch/x86_64/serial.odin` initializes COM1 serial output after entry, but no QEMU boot path reaches that initialization yet.

---

# 5. Required Next Fix

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The next boot-enabling fix must use the documented CI/local Limine and xorriso tooling path to produce a bootable ISO consistently before QEMU smoke execution, serial evidence capture, and QEMU smoke validation can be claimed.

The existing QEMU smoke command writes blocked output to `artifacts/runtime/qemu_smoke.log` and stops when `artifacts/runtime/boot_image/package_metadata.json` reports missing ISO tooling or when `artifacts/runtime/boot_image/kozo.iso` is missing.

The selected protocol and implementation plan are owned by `docs/BOOT_PROTOCOL.md`.

The boot image skeleton is owned by `docs/BOOT_IMAGE.md`.

---

# 6. Non-Goals

This document does not claim QEMU boot.

This document does not claim hardware syscall/trap execution.

This document does not claim Linux compatibility.

This document does not claim POSIX compatibility.

This document does not claim general userspace execution.

This document does not claim process model behavior.

This document does not claim VFS behavior.

This document does not claim scheduler maturity.

This document does not claim ELF loading.

This document does not claim file descriptor behavior.

This document does not claim production readiness.

---

# 7. Evidence

The current blocker evidence artifact is:

```text
artifacts/runtime/boot_blocker_report.json
```

It is generated by:

```text
scripts/boot_blocker_report.sh
```

It is validated by:

```text
boot_blocker_report
```

The current boot image packaging metadata is:

```text
artifacts/runtime/boot_image/package_metadata.json
```
