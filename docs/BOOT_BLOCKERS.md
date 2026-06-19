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

---

# 2. Verified Blocker

Blocker category: `missing_boot_protocol_and_image_packaging`.

The `missing_boot_protocol_and_image_packaging` blocker remains active.

The current `_start` symbol is present in object evidence, and Limine has been selected as the initial boot protocol.

The blocker remains active because no linker script, loader configuration, boot image packaging, or QEMU smoke execution exists.

Therefore the repository cannot honestly claim QEMU boot execution.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* linker script
* loader configuration
* boot image packaging
* QEMU smoke execution

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

The validator is:

```text
boot_blocker_report
```

---

# 5. Resolution Path

Resolve this blocker by adding:

* a linker script
* Limine loader configuration
* boot image packaging
* a bounded QEMU smoke command
* serial marker validation for the booted kernel path

Only after that work passes verification may KOZO claim QEMU boot evidence.
