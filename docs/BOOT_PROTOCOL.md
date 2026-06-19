# KOZO Boot Protocol

Version: 1
Status: Authoritative
Scope: Selected boot protocol and minimum implementation plan for the x86_64 bootable runtime baseline

---

# 1. Purpose

This document records the selected boot protocol for KOZO's initial x86_64 bootable runtime baseline.

It defines the minimum implementation plan needed to resolve the v0.3.0 `missing_boot_protocol_and_image_packaging` blocker.

---

# 2. Authority

`docs/BOOT_PROTOCOL.md` owns the selected boot protocol and boot implementation plan.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`

It does not define ABI truth, syscall truth, compatibility claims, userspace behavior, or production readiness.

---

# 3. Non-Goals

This document does not claim QEMU boot.

This document does not claim hardware syscall/trap execution.

This document does not claim Linux compatibility.

This document does not claim POSIX compatibility.

This document does not claim userspace execution.

This document does not claim process model behavior.

This document does not claim VFS behavior.

This document does not claim scheduler maturity.

This document does not claim ELF loading.

This document does not claim file descriptor behavior.

This document does not claim production readiness.

---

# 4. Selected Protocol

Selected protocol: Limine

Target architecture: x86_64

Initial boot target: QEMU serial smoke

Initial success marker: early serial marker from kernel entry path

Initial image type: minimal bootable image suitable for QEMU

Decision record: `docs/decisions/0001-boot-protocol.md`

---

# 5. Why Limine

Limine is the selected initial boot protocol because it keeps the first bootable runtime baseline focused on kernel image layout, loader configuration, image packaging, and serial evidence.

Limine avoids requiring KOZO to implement a raw custom loader before it can prove a booted kernel path.

Limine is a better initial fit than UEFI-first because KOZO does not currently have UEFI scaffolding.

Limine is a better initial fit than Multiboot2 because KOZO does not currently have a Multiboot2 header, linker script, or loader path.

---

# 6. Required Implementation Components

The boot image skeleton now provides:

* linker script
* kernel entry contract
* Limine configuration
* boot image assembly script

The boot blocker remains active until these components exist:

* bootable Limine ISO or disk image
* Limine bootloader artifacts for image installation
* ISO tooling such as `xorriso` or an equivalent image builder
* serial output marker
* runtime evidence validator for QEMU smoke, in a later phase

---

# 7. Required Files For Next Phase

v0.3.2 Boot Image Skeleton added:

* linker script
* Limine config
* minimal boot image staging script
* freestanding kernel ELF link path

The phase does not claim boot success because serial evidence has not been captured.

---

# 8. Boot Blocker Relationship

The v0.3.0 blocker is reduced.

Current blocker: `missing_bootable_iso_generation`

The boot protocol decision resolved the protocol selection part of the blocker.

Remaining blocker components:

* bootable Limine ISO or disk image
* Limine bootloader artifacts for image installation
* ISO tooling such as `xorriso` or an equivalent image builder
* validated QEMU serial smoke execution

Current packaging metadata:

```text
artifacts/runtime/boot_image/package_metadata.json
```

Expected ISO path:

```text
artifacts/runtime/boot_image/kozo.iso
```

---

# 9. QEMU Smoke Target

The intended smoke target is QEMU serial output from the kernel entry path.

The expected evidence path for a future successful phase is:

```text
artifacts/runtime/qemu_smoke.log
```

The expected marker is an early serial marker from the kernel entry path.

---

# 10. Evidence Boundary

Current evidence remains `runtime-adjacent-object-symbol-smoke`.

The boot protocol decision is planning evidence, not boot evidence.

No QEMU boot claim is valid until a boot image is built, run under QEMU, and validated through captured serial output.

---

# 11. Release Claim Boundary

Release notes may claim that KOZO selected Limine as the initial x86_64 boot protocol.

Release notes must not claim QEMU boot, hardware trap execution, compatibility, userspace execution, subsystem maturity, or production readiness from this decision.
