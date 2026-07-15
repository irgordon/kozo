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

v0.4.5 records the next CI-observed Limine blocker: the configured kernel path is opened, but Limine rejects the current lower-half ELF program-header layout with `limine_lower_half_phdr`.

v0.4.7 moves the kernel ELF virtual load layout to the higher half while preserving low physical load addresses in the linker script. Local ELF evidence no longer reports lower-half PT_LOAD segments, but CI QEMU evidence must still prove whether Limine advances beyond the previous `limine_lower_half_phdr` blocker.

v0.4.8 adds an assembly-level `KOZO_EARLY_0_ENTRY` emission path at `_start`, before stack setup and before calling Odin code. Kernel entry remains unclaimed until CI QEMU serial output captures that marker.

v0.4.9 adds assembly-level `KOZO_EARLY_1_SERIAL_INIT_START` and `KOZO_EARLY_2_SERIAL_INIT_OK` emission at `_start`, before stack setup and before calling Odin code. Serial initialization remains unclaimed until CI QEMU serial output captures `KOZO_EARLY_2_SERIAL_INIT_OK`.

v0.5.0 adds assembly-level `KOZO_BOOT_SMOKE_OK` emission at `_start`, immediately after `KOZO_EARLY_2_SERIAL_INIT_OK` and before stack setup or Odin code. Passing QEMU serial smoke evidence remains unclaimed unless QEMU smoke metadata validates passing evidence and captured serial output contains the full ordered marker sequence.

v0.5.4 promotes the CI-proven QEMU serial smoke evidence after CI run `27894312430` captured the full ordered marker sequence and QEMU smoke metadata reported `outcome: pass` with `blocker_category: none`.

v0.6.0 adds a governed runtime halt contract for the immediate post-smoke path. After `_start` emits `KOZO_BOOT_SMOKE_OK`, the assembly path enters a deterministic terminal `cli`/`hlt` loop instead of falling through into unrelated bytes or continuing into ungoverned runtime work.

v0.7.0 implements the governed stack initialization evidence path. `_start` loads `rsp` with the existing static `boot_stack_top`, performs a minimal push/pop stack-use probe, emits `KOZO_STACK_INIT_OK` through the proven assembly COM1 path, and then enters the existing halt loop.

v0.7.1 adds memory initialization evidence planning through `contracts/memory_initialization_evidence_contract.v0.json`. It reserves `KOZO_MEMORY_INIT_OK` as future evidence, but the marker is not emitted and memory initialization remains unimplemented.

No active QEMU serial smoke blocker.

Local generated blocker: `missing_iso_generation_tooling` when Limine and xorriso tooling are unavailable outside CI.

If CI produces `artifacts/runtime/boot_image/kozo.iso`, the generated blocker report narrows to `missing_qemu_serial_evidence` for that run.

If `scripts/qemu_smoke.sh` can run against a generated ISO, it writes `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, `artifacts/runtime/qemu_smoke.metadata.json`, and `artifacts/runtime/qemu_smoke.summary.txt`. Passing QEMU serial smoke evidence requires the serial log to contain the full ordered marker sequence ending in `KOZO_STACK_INIT_OK`; blocked metadata preserves the no-QEMU-boot claim. The summary is non-authoritative reviewer convenience derived from the metadata and logs.

---

# 2. Current Result

Boot feasibility result: QEMU serial smoke evidence proven.

Active release blocker: none for QEMU serial smoke evidence.

Local generated blocker category: `missing_iso_generation_tooling`.

No active QEMU serial smoke blocker.

CI packaged-image blocker category, when the ISO exists: `missing_qemu_serial_evidence`.

CI observed QEMU execution blocker category, when QEMU runs the ISO but no marker is captured before the bounded timeout: `qemu_timeout`.

Latest inspected post-v0.4.3 CI artifact diagnosis: `kernel_not_loaded`. QEMU launched the ISO, Limine was reached, and Limine failed to open the configured kernel executable path before any KOZO marker appeared.

Latest inspected pre-v0.4.5 CI artifact diagnosis: `limine_lower_half_phdr`. QEMU launched the ISO, Limine was reached, Limine opened the configured kernel path, and Limine rejected the kernel ELF with `PANIC: elf: Lower half PHDRs are not allowed` before any KOZO marker appeared.

Latest inspected v0.4.7 CI artifact diagnosis: `kernel_entry_not_reached`. QEMU launched the ISO, Limine loaded the higher-half ELF, and Limine reported `ELF entry point: 0xffffffff80200000`, but no KOZO marker appeared.

Latest inspected v0.4.8 CI artifact diagnosis: `serial_not_initialized`. QEMU launched the ISO, Limine loaded the higher-half ELF, and captured `KOZO_EARLY_0_ENTRY`, but did not capture `KOZO_EARLY_2_SERIAL_INIT_OK` or `KOZO_BOOT_SMOKE_OK`.

Current v0.4.7 kernel ELF diagnosis: structurally parseable by local ELF inspection, with `_start` and all PT_LOAD virtual addresses in the higher half. The staged kernel ELF is an x86_64 executable, `_start` matches the ELF entry point, PT_LOAD segments are present, and physical load addresses remain low through linker `AT(...)` placement. This does not prove Limine loaded or executed the kernel.

Current v0.4.8 entry handoff change: `_start` writes `KOZO_EARLY_0_ENTRY` directly to COM1 before stack setup, before `kernel_entry`, and before any Odin runtime dependency. This does not prove kernel entry until captured in QEMU serial output.

Current v0.4.9 serial initialization change: `_start` writes the entry marker, the serial initialization start marker, performs minimal COM1 initialization in assembly, and writes the serial initialization OK marker before stack setup. This does not prove QEMU boot until `KOZO_BOOT_SMOKE_OK` appears in captured QEMU serial output.

Current v0.5.0 marker emission change: `_start` writes `KOZO_BOOT_SMOKE_OK` through the same assembly COM1 path after `KOZO_EARLY_2_SERIAL_INIT_OK`. This supports only QEMU serial smoke evidence when QEMU smoke validation observes the full ordered marker sequence in captured serial output; it does not prove Odin runtime execution, stack setup, memory initialization, syscall dispatch, hardware trap execution, or broader boot lifecycle behavior.

Latest inspected v0.5.4 CI smoke status: CI run `27894312430` produced passing QEMU smoke metadata and captured `KOZO_EARLY_0_ENTRY`, `KOZO_EARLY_1_SERIAL_INIT_START`, `KOZO_EARLY_2_SERIAL_INIT_OK`, and `KOZO_BOOT_SMOKE_OK` in the serial log.

Current v0.6.0 runtime halt baseline: `contracts/runtime_halt_contract.v0.json` and `runtime_halt_contract` validate that `kernel/arch/x86_64/boot.asm` emits `KOZO_BOOT_SMOKE_OK` before entering a deterministic `cli`/`hlt` loop with no structural fallthrough.

Current runtime progression governance: `contracts/runtime_progression_stages.v0.json` owns the canonical order and allowed transitions, while `contracts/runtime_progression_contract.v0.json` owns halt-preservation requirements. The halt loop remains authoritative until stack initialization evidence, memory initialization evidence, and progression-entry evidence are separately proven. Stack evidence is proven; memory evidence and progression entry remain planned. These contracts do not implement runtime progression.

Current v0.6.3 runtime progression entry design: `contracts/runtime_progression_entry_contract.v0.json` reserves the future `KOZO_RUNTIME_PROGRESS_ENTRY` marker and defines where progression evidence begins. The marker is not emitted, runtime progression is not implemented, and the halt loop remains authoritative until the required stack, memory, runtime, and progression-path evidence exists.

Current v0.6.6 runtime progression stage governance: `contracts/runtime_progression_stages.v0.json` is the authoritative model for the planned progression from `BOOT_SMOKE` to `USERSPACE_PLANNING`. It defines stage ordering, prerequisites, evidence, transition rules, and forbidden shortcuts. It does not implement runtime progression or replace the halt behavior.

Current v0.7.0 stack initialization evidence: `contracts/stack_initialization_evidence_contract.v0.json` defines the controlled boot stack proof. `_start` sets `rsp` to `boot_stack_top`, performs a bounded push/pop probe, emits `KOZO_STACK_INIT_OK`, and then enters the governed halt loop. This proves only controlled stack establishment and marker emission.

Current v0.7.3 memory evidence hardening: `contracts/memory_initialization_evidence_contract.v0.json` defines the future controlled region (`boot_memory_region` through `boot_memory_region_end`), 4096-byte size and alignment, static boot-path ownership, full-region zero fill, bounded sentinel write/read/compare/restore probe, and marker placement before the unchanged halt loop. `KOZO_MEMORY_INIT_OK` remains reserved but not emitted. No memory initialization, physical memory discovery, paging, virtual memory management, allocator behavior, Odin runtime execution, userspace execution, compatibility, or production readiness is proven.

Selected boot protocol: Limine.

The current repository has a 64-bit `_start` symbol, an exported `kernel_entry`, early serial initialization, early KOZO marker strings, and runtime-adjacent object/symbol smoke evidence.

The boot protocol decision, boot image skeleton, boot tooling acquisition policy, ISO generation command path, CI ISO tooling install path, and kernel entry reachability diagnostic path are complete.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/package_metadata.json`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/kernel_elf_report.json`.

`scripts/qemu_smoke.sh` writes `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, and `artifacts/runtime/qemu_smoke.summary.txt`.

The expected ISO path is `artifacts/runtime/boot_image/kozo.iso`.

The configured Limine kernel path is `boot():/boot/kozo/kozo-kernel.elf`, using Limine's boot-resource path semantics for the boot drive partition containing the configuration file.

The normalized ISO path is `boot/kozo/kozo-kernel.elf`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/iso_contents.txt` when an ISO is produced so packaging validation can confirm the configured Limine path is visible in the image.

The ISO generation command includes Rock Ridge and Joliet metadata so the lower-case Limine path remains visible to the loader when ISO tooling is available.

GitHub Actions full CI installs xorriso, acquires Limine v12.3.3 from a pinned source release, builds Limine, and attempts ISO generation.

The current local tooling does not yet provide the Limine artifacts and xorriso executable required to produce that image, so local verification continues to report blocked packaging metadata.

KOZO has CI-proven QEMU serial smoke evidence. Local execution may still record `missing_iso_generation_tooling` when Limine and xorriso are unavailable outside CI.

The early marker sequence is:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
KOZO_BOOT_SMOKE_OK
KOZO_STACK_INIT_OK
```

---

# 3. Missing Components

The concrete remaining local-only missing components are:

* local Limine executable
* local xorriso executable
* local Limine bootloader artifacts
* bootable ISO artifact when not produced by CI
Validated QEMU serial smoke execution is no longer missing in CI evidence.

This still does not authorize a broad QEMU boot, hardware trap, compatibility, userspace, subsystem, or production-readiness claim.

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
* `artifacts/runtime/qemu_smoke.summary.txt`

`kernel/arch/x86_64/boot.asm` defines `_start`, and `scripts/build_boot_image.sh` links a kernel ELF for the Limine image skeleton.

`artifacts/runtime/kernel_elf_report.json` records that the staged kernel ELF has an x86_64 executable format, `_start` entry alignment, PT_LOAD segments, PT_LOAD virtual and physical addresses, higher-half layout summary, and the current load-layout blocker. That report does not prove Limine has loaded the ELF or transferred control to `_start`.

`kernel/arch/x86_64/boot.asm` emits `KOZO_BOOT_SMOKE_OK` after assembly-level serial initialization, establishes the controlled boot stack, and emits `KOZO_STACK_INIT_OK`. `kernel/main.odin` also keeps a later boot smoke marker path after Odin serial initialization. Passing QEMU serial smoke evidence requires the captured serial log to contain the expected marker sequence.

After the assembly-level `KOZO_STACK_INIT_OK` emission, `kernel/arch/x86_64/boot.asm` enters the governed terminal halt loop. That source-level terminal behavior is validated by `runtime_halt_contract` and does not prove hardware halt instruction semantics, interrupt handling, scheduler behavior, general stack readiness, Odin runtime execution, memory initialization, syscall dispatch, or production readiness.

`kernel/arch/x86_64/serial.odin` initializes COM1 serial output for the later Odin path. The v0.5.0 smoke marker is owned by the assembly entry path and is not Odin runtime, stack, memory, syscall, or hardware-trap evidence.

`kernel/arch/x86_64/serial.odin` also owns the v0.4.0 early markers. Those markers are diagnostic evidence only; they do not prove hardware trap execution, userspace execution, or subsystem maturity.

---

# 5. Required Next Fix

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The QEMU serial smoke and stack evidence paths are proven in CI. The next runtime phase may implement only the hardened static memory evidence boundary while preserving the existing halt path afterward.

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
