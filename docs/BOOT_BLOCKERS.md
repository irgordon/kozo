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

QEMU smoke command: present and fail-closed on missing ISO generation tooling.

---

# 2. Verified Blocker

Blocker category: `missing_iso_generation_tooling`.

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The previous `missing_bootable_iso_generation` blocker is refined by the v0.3.6 ISO generation command path.

The remaining blocker is `missing_iso_generation_tooling`.

The current `_start` symbol is present in object evidence, Limine has been selected as the initial boot protocol, the boot image skeleton exists, and `scripts/build_boot_image.sh` contains the ISO generation command path.

The blocker remains active because the local environment does not provide the Limine executable, Limine bootloader artifacts, or xorriso executable needed by that path.

Therefore the repository cannot honestly claim QEMU boot execution.

---

# 3. Missing Components

The current boot blocker report must name these missing components:

* Limine executable
* xorriso executable
* Limine bootloader artifacts
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

* documented Limine executable availability
* documented Limine bootloader artifact availability
* documented xorriso executable availability
* a generated bootable ISO at `artifacts/runtime/boot_image/kozo.iso`
* serial marker validation for the booted kernel path
* a QEMU smoke evidence validator

Only after that work passes verification may KOZO claim QEMU boot evidence.
