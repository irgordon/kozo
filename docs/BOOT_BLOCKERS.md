# KOZO Boot Blockers

Version: 1
Status: Authoritative
Scope: Current blockers preventing an honest QEMU boot claim

---

# 1. Purpose

This document names the concrete blockers found during the v0.3.0 bootable runtime baseline attempt.

The current result is a verified blocker, not a boot success.

Boot protocol decision: complete.

Selected protocol: Limine.

Boot image skeleton: complete.

Boot image package metadata: present.

Boot tooling acquisition policy: present in `docs/BOOT_TOOLING.md`.

CI ISO tooling install path: present.

QEMU smoke command: present and fail-closed on missing ISO generation tooling or missing serial evidence.

QEMU smoke evidence validator: `qemu_smoke_evidence`.

v0.3.9 records the CI-observed `qemu_timeout` state as an exact QEMU smoke blocker when QEMU runs the packaged ISO but the serial log does not contain `KOZO_BOOT_SMOKE_OK` before the bounded timeout.

v0.4.0 narrows that diagnostic model with Limine serial/verbose configuration, early KOZO marker instrumentation, and exact reachability blockers.

v0.4.1 fixes the Limine kernel executable path and tightens QEMU smoke classification so Limine executable-open failures remain `kernel_not_loaded`.

v0.4.2 adds kernel ELF loadability evidence and validation so `kernel_not_loaded` can be separated from malformed ELF, missing PT_LOAD segments, invalid entry point, or linker-output failures.

v0.4.4 fixes the Limine path semantics from a bare `/boot/kozo/kozo-kernel.elf` path to `boot():/boot/kozo/kozo-kernel.elf` and records ISO contents metadata to prove the normalized configured path is present in packaged images.

v0.4.5 classifies Limine's lower-half program-header rejection as `limine_lower_half_phdr` after CI evidence showed Limine could open the configured kernel path but rejected the ELF load layout.

v0.4.7 moves the kernel ELF PT_LOAD virtual addresses to the higher half and preserves low physical load addresses through linker `AT(...)` placement. Local ELF loadability evidence no longer reports `limine_lower_half_phdr`; the next CI QEMU artifact must determine the next observed blocker or marker state.

v0.4.8 adds the `KOZO_EARLY_0_ENTRY` marker directly in `_start` before stack setup and before Odin code, so the next CI QEMU artifact can distinguish entry handoff from later serial initialization.

v0.4.9 adds `KOZO_EARLY_1_SERIAL_INIT_START` and `KOZO_EARLY_2_SERIAL_INIT_OK` directly in `_start`, before stack setup and before Odin code, so the next CI QEMU artifact can distinguish serial initialization from final smoke marker emission.

---

# 2. Verified Blocker

Blocker category: `missing_iso_generation_tooling`.

The local blocker category is `missing_iso_generation_tooling`.

CI packaged-image blocker category, when `artifacts/runtime/boot_image/kozo.iso` exists: `missing_qemu_serial_evidence`.

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The previous `missing_bootable_iso_generation` blocker is refined by the v0.3.6 ISO generation command path.

The remaining blocker is `missing_iso_generation_tooling`.

For this local environment, `missing_iso_generation_tooling` means Limine and xorriso are not available outside CI.

The current `_start` symbol is present in object evidence, Limine has been selected as the initial boot protocol, the boot image skeleton exists, `scripts/build_boot_image.sh` contains the ISO generation command path, and GitHub Actions full CI installs xorriso plus pinned Limine v12.3.3 source tooling before attempting the build.

The blocker remains active for the local environment because it does not provide the Limine executable, Limine bootloader artifacts, or xorriso executable needed by that path.

If CI produces `artifacts/runtime/boot_image/kozo.iso`, `scripts/boot_blocker_report.sh` narrows the generated blocker report to `missing_qemu_serial_evidence`.

If CI then runs `scripts/qemu_smoke.sh` and the kernel marker is still absent at timeout, the generated blocker report narrows further to `qemu_timeout`.

If the run captures no Limine output and no KOZO marker output, the generated blocker report narrows to `limine_not_reached`.

If Limine output appears without kernel load evidence, or if Limine fails to open or load the configured executable, the generated blocker report narrows to `kernel_not_loaded`.

If Limine reports `Lower half PHDRs are not allowed`, QEMU smoke evidence narrows to `limine_lower_half_phdr`.

If `artifacts/runtime/kernel_elf_report.json` detects a structural ELF issue while QEMU reports `kernel_not_loaded` or another kernel-load blocker, the generated blocker report narrows to `invalid_kernel_elf`, `missing_load_segments`, `invalid_kernel_entry`, `linker_output_invalid`, or `limine_lower_half_phdr`.

If kernel load or handoff evidence appears without `KOZO_EARLY_0_ENTRY`, the generated blocker report narrows to `kernel_entry_not_reached`.

If `KOZO_EARLY_0_ENTRY` appears without `KOZO_EARLY_2_SERIAL_INIT_OK`, the generated blocker report narrows to `serial_not_initialized`.

If `KOZO_EARLY_2_SERIAL_INIT_OK` appears without `KOZO_BOOT_SMOKE_OK`, the generated blocker report narrows to `marker_not_emitted`.

For v0.5.0 and later, passing QEMU smoke evidence requires this full ordered marker sequence:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
KOZO_BOOT_SMOKE_OK
```

Even then, QEMU boot evidence remains blocked until serial output is captured and validated.

`scripts/qemu_smoke.sh` writes `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.log`, and `artifacts/runtime/qemu_smoke.stderr.log`. The expected kernel-emitted serial marker is `KOZO_BOOT_SMOKE_OK`.

Therefore the repository cannot honestly claim QEMU boot execution.

The latest inspected v0.4.0 CI artifact reached Limine and failed to open `boot:///boot/kozo/kozo-kernel.elf`, so its evidence-backed diagnostic blocker is `kernel_not_loaded`.

The v0.4.4 Limine config uses `boot():/boot/kozo/kozo-kernel.elf`, which explicitly names the boot drive partition containing the Limine configuration file.

The normalized configured path is `boot/kozo/kozo-kernel.elf`, and packaged image metadata records whether that path appears in `artifacts/runtime/boot_image/iso_contents.txt`.

The v0.4.2 kernel ELF report records the staged kernel ELF as an x86_64 executable with `_start` matching the ELF entry point and PT_LOAD segments present. This does not prove Limine loaded or executed the kernel.

The latest inspected pre-v0.4.5 CI artifact reached Limine, opened `boot():/boot/kozo/kozo-kernel.elf`, and failed with `PANIC: elf: Lower half PHDRs are not allowed`. The current evidence-backed load-layout blocker is `limine_lower_half_phdr`; kernel entry has not been reached.

The v0.4.7 local kernel ELF report records `_start` at `0xffffffff80200000`, PT_LOAD virtual addresses starting at `0xffffffff80200000`, low physical load addresses starting at `0x200000`, and `load_layout_blocker` as `none`. This does not prove Limine loaded or entered the kernel; it only clears the local lower-half PHDR evidence.

The latest inspected v0.4.7 CI artifact loaded the higher-half ELF and reported `ELF entry point: 0xffffffff80200000`, but no KOZO marker appeared. The evidence-backed blocker for that artifact is `kernel_entry_not_reached`.

The v0.4.8 entry handoff path emits `KOZO_EARLY_0_ENTRY` from assembly before stack setup. If CI captures that marker without `KOZO_EARLY_2_SERIAL_INIT_OK`, the blocker must narrow to `serial_not_initialized`; until that marker is captured, kernel entry remains unclaimed.

The latest inspected v0.4.8 CI artifact captured `KOZO_EARLY_0_ENTRY` and narrowed the blocker to `serial_not_initialized`. Kernel entry handoff is proven for that artifact, but serial initialization remains unproven because `KOZO_EARLY_2_SERIAL_INIT_OK` is absent.

The v0.4.9 early serial path emits `KOZO_EARLY_1_SERIAL_INIT_START` and `KOZO_EARLY_2_SERIAL_INIT_OK` from assembly before stack setup. If CI captures `KOZO_EARLY_2_SERIAL_INIT_OK` without `KOZO_BOOT_SMOKE_OK`, the blocker must narrow to `marker_not_emitted`; until the OK marker is captured, serial initialization remains unclaimed.

The v0.5.0 boot smoke path emits `KOZO_BOOT_SMOKE_OK` from assembly immediately after the serial initialization OK marker. This clears `marker_not_emitted` only when QEMU smoke validation captures the full ordered marker sequence.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* local Limine executable
* local xorriso executable
* local Limine bootloader artifacts
* bootable ISO artifact when not produced by CI
* validated QEMU serial smoke execution

---

# 4. Blocker Evidence

The blocker report is generated at:

```text
artifacts/runtime/boot_blocker_report.json
```

The generator is:

```text
scripts/boot_blocker_report.sh
```

The QEMU blocker review command is:

```text
scripts/qemu_smoke.sh
```

The QEMU smoke metadata is:

```text
artifacts/runtime/qemu_smoke.metadata.json
```

The QEMU smoke serial log is:

```text
artifacts/runtime/qemu_smoke.log
```

The QEMU smoke stderr log is:

```text
artifacts/runtime/qemu_smoke.stderr.log
```

The packaging metadata is:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The tooling acquisition policy is:

```text
docs/BOOT_TOOLING.md
```

The expected ISO path is:

```text
artifacts/runtime/boot_image/kozo.iso
```

The kernel ELF loadability report is:

```text
artifacts/runtime/kernel_elf_report.json
```

The kernel ELF report generator is:

```text
scripts/kernel_elf_report.py
```

The kernel ELF loadability validator is:

```text
kernel_loadability
```

The ISO contents report is:

```text
artifacts/runtime/boot_image/iso_contents.txt
```

The validator is:

```text
boot_blocker_report
```

---

# 5. Resolution Path

Resolve the local tooling part of this blocker by adding:

* documented Limine executable availability
* documented Limine bootloader artifact availability
* documented xorriso executable availability
* a generated bootable ISO at `artifacts/runtime/boot_image/kozo.iso`

Resolve the runtime evidence part of this blocker by adding:

* serial marker validation for the booted kernel path
* passing `qemu_smoke_evidence` over a QEMU serial log containing `KOZO_BOOT_SMOKE_OK`

If CI still reports `kernel_not_loaded` after v0.4.2, inspect Limine ISO filesystem visibility, Limine ELF loading diagnostics, and generated ISO contents before investigating serial initialization.

Only after that work passes verification may KOZO claim QEMU boot evidence.
