# ADR 0001: Boot Protocol Selection

Status: Accepted

Date: 2026-06-19

---

# Context

KOZO currently has runtime-adjacent object and symbol evidence, not QEMU boot evidence.

The v0.3.0 boot baseline identified the active blocker as `missing_boot_protocol_and_image_packaging`.

The current repository has:

* `kernel/arch/x86_64/boot.asm` defining a 64-bit `_start` symbol
* `kernel/main.odin` exporting `kernel_entry`
* `kernel/arch/x86_64/serial.odin` providing early COM1 serial output after entry
* `scripts/runtime_smoke.sh` proving object and symbol evidence

The current repository does not have:

* linker script
* boot protocol
* loader configuration
* boot image packaging
* QEMU serial smoke evidence

---

# Decision

KOZO will use Limine as the initial boot protocol for the x86_64 bootable runtime baseline.

Selected protocol: Limine

Target architecture: x86_64

Initial boot target: QEMU serial smoke

Initial success marker: early serial marker from kernel entry path

Initial image type: minimal bootable image suitable for QEMU

---

# Alternatives Considered

## Limine

Limine is selected because it is practical for a small x86_64 experimental kernel, supports modern x86_64 boot flows, can load higher-half kernels, and avoids writing a custom loader before KOZO has boot evidence.

## Multiboot2

Multiboot2 is viable for some hobby kernels, but KOZO does not currently have a Multiboot2 header, linker script, or boot image path that makes it a better fit than Limine.

## UEFI-first

UEFI-first is deferred because the repository does not currently have UEFI scaffolding. Starting with UEFI would expand boot services and packaging scope before KOZO has a minimal boot smoke.

## Raw custom loader

A raw custom loader is rejected for the initial boot baseline because it would add loader implementation risk before the kernel has a proven bootable image path.

---

# Consequences

The v0.3.0 blocker remains active until the implementation adds:

* linker script
* Limine configuration
* boot image assembly script
* QEMU smoke script
* serial output marker validation

The next phase can focus on a small Limine-based boot image skeleton instead of revisiting boot protocol choice.

---

# Non-Goals

This decision does not claim QEMU boot.

This decision does not claim hardware trap execution.

This decision does not claim Linux compatibility.

This decision does not claim POSIX compatibility.

This decision does not claim userspace execution.

This decision does not claim process model behavior.

This decision does not claim VFS behavior.

This decision does not claim scheduler maturity.

This decision does not claim ELF loading.

This decision does not claim file descriptor behavior.

This decision does not claim production readiness.

---

# Next Implementation Phase

v0.3.2 Boot Image Skeleton

The next implementation phase should add:

* linker script
* Limine config
* minimal ISO or image packaging script
* QEMU invocation script if feasible
* no claim of boot success until serial evidence is captured

---

# Evidence Impact

The existing `boot_blocker_report` remains valid and active.

This decision narrows the future boot implementation path to Limine, but it does not replace `artifacts/runtime/boot_blocker_report.json` and does not create QEMU boot evidence.
