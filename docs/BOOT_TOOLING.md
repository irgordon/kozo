# KOZO Boot Tooling

Version: 1
Status: Authoritative
Scope: Tooling acquisition requirements for the Limine x86_64 ISO path

---

# 1. Purpose

This document defines the tooling required to turn the current Limine boot image skeleton into a bootable ISO.

It records the acquisition path for Limine and ISO generation tooling.

This document does not claim that KOZO currently produces a bootable ISO in this environment.

---

# 2. Authority

`docs/BOOT_TOOLING.md` owns boot tooling acquisition requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/BOOT_PROTOCOL.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`

It does not define ABI truth, syscall truth, runtime behavior, compatibility claims, userspace execution, or production readiness.

---

# 3. Non-Goals

This document does not claim QEMU boot.

This document does not claim serial output success.

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

# 4. Required Tooling

The bootable ISO path requires:

* Limine
* xorriso
* standard shell utilities already used by `scripts/build_boot_image.sh`

Limine purpose:

* provides the selected boot protocol implementation
* provides bootloader installation artifacts for the ISO image
* owns the future `limine-deploy` or equivalent bootloader installation step

xorriso purpose:

* creates the ISO image from `artifacts/runtime/boot_image/image-root/`
* provides El Torito-compatible ISO image generation for the future QEMU path

---

# 5. Required Versions

Limine must be version-pinned before KOZO claims reproducible ISO generation.

xorriso must be version-recorded before KOZO claims reproducible ISO generation.

This phase does not pin a Limine release because Limine is not vendored and no ISO generation command is implemented yet.

The next ISO generation phase must either:

* pin an externally installed Limine package version, or
* pin a source release and build or acquire Limine artifacts through a documented reproducible process

---

# 6. Installation Methods

Local development path:

```text
Install Limine from the platform package manager or from a pinned upstream release.
Install xorriso from the platform package manager.
Confirm limine or limine-deploy is on PATH.
Confirm xorriso is on PATH.
Run scripts/build_boot_image.sh.
```

CI installation path:

```text
Install xorriso through apt.
Install Limine through a pinned package or pinned source release.
Verify limine or limine-deploy is available before ISO generation.
Verify xorriso is available before ISO generation.
Run scripts/build_boot_image.sh.
```

CI does not currently install Limine or xorriso because QEMU boot evidence is not yet required in CI.

---

# 7. Tool Provenance

Boot tooling must be reproducible.

Tooling source must be documented before it is used as release evidence.

Opaque vendored binaries are discouraged.

If vendoring ever becomes necessary, the repository must record:

* upstream source
* version
* license
* checksum
* refresh procedure
* validator ownership

---

# 8. Tool Verification

Before a future ISO generation phase may claim packaging success:

* `limine` or `limine-deploy` must be found on PATH
* `xorriso` must be found on PATH
* tool versions must be logged or recorded
* `scripts/build_boot_image.sh` must fail closed when required tooling is unavailable
* `artifacts/runtime/boot_image/kozo.iso` must exist before ISO packaging can be marked complete

---

# 9. Future ISO Generation Path

The future ISO generation path should:

1. build the kernel ELF
2. stage `boot/limine.conf`
3. stage Limine bootloader artifacts
4. run `xorriso` to create `artifacts/runtime/boot_image/kozo.iso`
5. install or finalize the Limine bootloader state
6. update `artifacts/runtime/boot_image/package_metadata.json`
7. leave QEMU boot validation to `scripts/qemu_smoke.sh`

---

# 10. Boot Blocker Relationship

The current blocker is:

```text
missing_iso_generation_tooling
```

The previous `missing_limine_iso_tooling` blocker is resolved at the policy level by this document.

The previous `missing_bootable_iso_generation` blocker is refined by the v0.3.6 ISO generation command path.

KOZO still does not produce:

```text
artifacts/runtime/boot_image/kozo.iso
```

The next required fix is to provide the documented Limine executable, Limine bootloader artifacts, and xorriso executable so the ISO generation command can produce `artifacts/runtime/boot_image/kozo.iso`.
