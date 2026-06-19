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

QEMU smoke command: present and fail-closed on missing ISO generation.

---

# 2. Verified Blocker

Blocker category: `missing_bootable_iso_generation`.

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The remaining blocker is `missing_bootable_iso_generation`.

The current `_start` symbol is present in object evidence, Limine has been selected as the initial boot protocol, and the boot image skeleton exists.

The blocker remains active because `scripts/build_boot_image.sh` does not yet implement ISO generation using the documented Limine and xorriso tooling path.

Therefore the repository cannot honestly claim QEMU boot execution.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* ISO generation command integration
* bootable ISO artifact
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

The validator is:

```text
boot_blocker_report
```

---

# 5. Resolution Path

Resolve this blocker by adding:

* bootable Limine ISO or disk packaging
* deterministic ISO generation in `scripts/build_boot_image.sh`
* serial marker validation for the booted kernel path
* a QEMU smoke evidence validator

Only after that work passes verification may KOZO claim QEMU boot evidence.
