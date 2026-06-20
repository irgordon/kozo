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

v0.3.8 added QEMU serial smoke metadata, the `qemu_smoke_evidence` validator, and a kernel-emitted `KOZO_BOOT_SMOKE_OK` marker for future QEMU serial validation.

v0.3.9 records the CI-observed QEMU timeout path as an exact blocker, adds QEMU stderr log evidence at `artifacts/runtime/qemu_smoke.stderr.log`, and keeps the no-QEMU-boot claim unless the serial log contains `KOZO_BOOT_SMOKE_OK`.

v0.4.0 adds documented Limine serial and verbose diagnostics, early KOZO serial markers, and a reachability taxonomy that distinguishes `limine_not_reached`, `kernel_not_loaded`, `kernel_entry_not_reached`, `serial_not_initialized`, `marker_not_emitted`, and fallback `qemu_timeout`.

v0.4.1 updates the Limine kernel path to match the staged ISO layout and classifies Limine executable-open failures as `kernel_not_loaded`.

v0.4.2 adds deterministic kernel ELF loadability evidence at `artifacts/runtime/kernel_elf_report.json`, validates the staged kernel ELF architecture, entry point, `_start` alignment, program headers, and PT_LOAD segments, and keeps the no-QEMU-boot claim until serial evidence proves execution.

v0.4.4 updates the Limine kernel path to use explicit `boot():` resource semantics and records ISO path visibility metadata so the configured path can be checked against the staged ISO contents.

Remaining blocker: `missing_iso_generation_tooling`.

The local blocker is `missing_iso_generation_tooling`.

If CI produces `artifacts/runtime/boot_image/kozo.iso`, the generated blocker report narrows to `missing_qemu_serial_evidence` for that run.

If `scripts/qemu_smoke.sh` can run against a generated ISO, it writes `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, and `artifacts/runtime/qemu_smoke.metadata.json`. Passing QEMU evidence requires the serial log to contain `KOZO_BOOT_SMOKE_OK`; blocked metadata preserves the no-QEMU-boot claim.

---

# 2. Current Result

Boot feasibility result: blocked.

Blocker category: `missing_iso_generation_tooling`.

The local blocker category is `missing_iso_generation_tooling`.

CI packaged-image blocker category, when the ISO exists: `missing_qemu_serial_evidence`.

CI observed QEMU execution blocker category, when QEMU runs the ISO but no marker is captured before the bounded timeout: `qemu_timeout`.

Latest inspected post-v0.4.3 CI artifact diagnosis: `kernel_not_loaded`. QEMU launched the ISO, Limine was reached, and Limine failed to open the configured kernel executable path before any KOZO marker appeared.

Current v0.4.2 kernel ELF diagnosis: structurally loadable by local ELF inspection. The staged kernel ELF is an x86_64 executable, `_start` matches the ELF entry point, and PT_LOAD segments are present. This does not prove Limine loaded or executed the kernel.

Selected boot protocol: Limine.

The current repository has a 64-bit `_start` symbol, an exported `kernel_entry`, early serial initialization, early KOZO marker strings, and runtime-adjacent object/symbol smoke evidence.

The boot protocol decision, boot image skeleton, boot tooling acquisition policy, ISO generation command path, CI ISO tooling install path, and kernel entry reachability diagnostic path are complete.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/package_metadata.json`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/kernel_elf_report.json`.

`scripts/qemu_smoke.sh` writes `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.log`, and `artifacts/runtime/qemu_smoke.stderr.log`.

The expected ISO path is `artifacts/runtime/boot_image/kozo.iso`.

The configured Limine kernel path is `boot():/boot/kozo/kozo-kernel.elf`, using Limine's boot-resource path semantics for the boot drive partition containing the configuration file.

The normalized ISO path is `boot/kozo/kozo-kernel.elf`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/iso_contents.txt` when an ISO is produced so packaging validation can confirm the configured Limine path is visible in the image.

The ISO generation command includes Rock Ridge and Joliet metadata so the lower-case Limine path remains visible to the loader when ISO tooling is available.

GitHub Actions full CI installs xorriso, acquires Limine v12.3.3 from a pinned source release, builds Limine, and attempts ISO generation.

The current local tooling does not yet provide the Limine artifacts and xorriso executable required to produce that image, so local verification continues to report blocked packaging metadata.

KOZO has QEMU smoke evidence metadata, but local execution currently records `missing_iso_generation_tooling`. A QEMU boot claim remains unavailable unless `qemu_smoke_evidence` validates a passing serial log with `KOZO_BOOT_SMOKE_OK`.

The early marker sequence is:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
KOZO_BOOT_SMOKE_OK
```

---

# 3. Missing Components

The concrete remaining missing components are:

* local Limine executable
* local xorriso executable
* local Limine bootloader artifacts
* bootable ISO artifact when not produced by CI
* validated QEMU serial smoke execution
* a post-v0.4.1 CI QEMU run that proves Limine can load the kernel executable path

Until those exist, KOZO must not claim QEMU boot evidence.

---

# 4. Current Surfaces

The current source surfaces relevant to future boot work are:

* `kernel/arch/x86_64/boot.asm`
* `kernel/main.odin`
* `kernel/arch/x86_64/serial.odin`
* `scripts/runtime_smoke.sh`
* `scripts/build_boot_image.sh`
* `scripts/kernel_elf_report.py`
* `scripts/qemu_smoke.sh`
* `docs/BOOT_TOOLING.md`
* `artifacts/runtime/kernel_elf_report.json`
* `artifacts/runtime/qemu_smoke.metadata.json`
* `artifacts/runtime/qemu_smoke.log`

`kernel/arch/x86_64/boot.asm` defines `_start`, and `scripts/build_boot_image.sh` links a kernel ELF for the Limine image skeleton.

`artifacts/runtime/kernel_elf_report.json` records that the staged kernel ELF has an x86_64 executable format, `_start` entry alignment, and PT_LOAD segments. That report does not prove Limine has loaded the ELF or transferred control to `_start`.

`kernel/main.odin` exports `kernel_entry` and emits `KOZO_BOOT_SMOKE_OK` after serial initialization, but no local bootable ISO transfers control to it through a proven loader path.

`kernel/arch/x86_64/serial.odin` initializes COM1 serial output and owns the boot smoke marker output. That marker is not a QEMU boot claim until captured from QEMU serial output.

`kernel/arch/x86_64/serial.odin` also owns the v0.4.0 early markers. Those markers are diagnostic evidence only; they do not prove hardware trap execution, userspace execution, or subsystem maturity.

---

# 5. Required Next Fix

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The next boot-enabling fix must use the documented CI/local Limine and xorriso tooling path to produce a bootable ISO consistently before QEMU smoke execution, serial evidence capture, and QEMU smoke validation can be claimed.

The existing QEMU smoke command writes blocked or passing metadata to `artifacts/runtime/qemu_smoke.metadata.json` and serial output to `artifacts/runtime/qemu_smoke.log`.

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

The current QEMU smoke metadata is:

```text
artifacts/runtime/qemu_smoke.metadata.json
```

The QEMU smoke evidence validator is:

```text
qemu_smoke_evidence
```

The current kernel ELF loadability report is:

```text
artifacts/runtime/kernel_elf_report.json
```

The kernel ELF loadability validator is:

```text
kernel_loadability
```
