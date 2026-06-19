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

---

# 2. Verified Blocker

Blocker category: `missing_qemu_execution_evidence`.

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.

The remaining blocker is `missing_qemu_execution_evidence`.

The current `_start` symbol is present in object evidence, Limine has been selected as the initial boot protocol, and the boot image skeleton exists.

The blocker remains active because no QEMU smoke execution, serial evidence capture, or QEMU smoke validator exists.

Therefore the repository cannot honestly claim QEMU boot execution.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* QEMU smoke execution
* serial evidence capture
* QEMU smoke validator

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

* a bounded QEMU smoke command
* serial marker validation for the booted kernel path
* a QEMU smoke evidence validator

Only after that work passes verification may KOZO claim QEMU boot evidence.
