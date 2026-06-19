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

QEMU smoke command: present and fail-closed on missing bootable image packaging.

---

# 2. Verified Blocker

Blocker category: `missing_bootable_iso_packaging`.

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.

The previous `missing_qemu_execution_evidence` blocker is refined.

The remaining blocker is `missing_bootable_iso_packaging`.

The current `_start` symbol is present in object evidence, Limine has been selected as the initial boot protocol, and the boot image skeleton exists.

The blocker remains active because the repository does not yet produce a bootable Limine ISO or disk image for QEMU.

Therefore the repository cannot honestly claim QEMU boot execution.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* bootable Limine ISO or disk image
* Limine bootloader artifacts for image installation
* ISO tooling such as `xorriso` or an equivalent image builder
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

The validator is:

```text
boot_blocker_report
```

---

# 5. Resolution Path

Resolve this blocker by adding:

* bootable Limine ISO or disk packaging
* Limine bootloader artifact installation
* deterministic image tooling such as `xorriso` or an equivalent image builder
* serial marker validation for the booted kernel path
* a QEMU smoke evidence validator

Only after that work passes verification may KOZO claim QEMU boot evidence.
