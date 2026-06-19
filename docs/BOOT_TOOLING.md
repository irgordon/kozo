# KOZO Boot Tooling

Version: 1
Status: Authoritative
Scope: Tooling acquisition requirements for the Limine x86_64 ISO path

---

# 1. Purpose

This document defines the tooling required to turn the current Limine boot image skeleton into a bootable ISO.

It records the acquisition path for Limine and ISO generation tooling.

This document does not claim that KOZO currently produces a bootable ISO in every environment.

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

Limine tooling for CI is pinned to:

```text
v12.3.3
```

The pinned source tarball checksum is:

```text
9e97c9fedc714daa5d7fd2b66a32d85df6bcbf3452657fd26bebad7c8b423009
```

xorriso must be version-recorded before KOZO claims reproducible ISO generation.

The CI path installs xorriso from the GitHub Actions Ubuntu package repository and records the tool version in CI output.

Local development environments may use the same Limine release, a platform package, or another reviewed source build, but release evidence must record the exact tool versions used.

---

# 6. Installation Methods

Local development path:

```text
Install Limine from the platform package manager or from a pinned upstream release.
Install xorriso from the platform package manager.
Confirm limine or limine-deploy is on PATH.
Confirm xorriso is on PATH.
Optionally set LIMINE_DIR, LIMINE_INSTALL, LIMINE, or XORRISO for explicit tool paths.
Run scripts/build_boot_image.sh.
```

CI installation path:

```text
Install xorriso through apt.
Download Limine v12.3.3 from the upstream GitHub release source tarball.
Verify the Limine tarball with SHA256 before extraction.
Build Limine from source in the CI workspace.
Export LIMINE_DIR, LIMINE, and XORRISO for scripts/build_boot_image.sh.
Run scripts/build_boot_image.sh.
```

CI installs the ISO tooling and attempts `scripts/build_boot_image.sh`.

CI may produce `artifacts/runtime/boot_image/kozo.iso` when the pinned toolchain and image command succeed.

If ISO generation fails, CI must fail closed or produce blocker metadata without making a boot claim.

---

# 7. Tool Provenance

Boot tooling must be reproducible.

Tooling source must be documented before it is used as release evidence.

Opaque vendored binaries are discouraged.

The CI path acquires Limine from a pinned upstream source release and builds it during the workflow.

The CI path does not commit or vendor Limine binaries.

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

* `limine`, `limine-deploy`, or the explicit `LIMINE` path must resolve to an executable
* `xorriso` or the explicit `XORRISO` path must resolve to an executable
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

CI now follows this path as a required full-verification step, but QEMU smoke evidence remains a later phase.

---

# 10. Boot Blocker Relationship

The current blocker is:

```text
missing_iso_generation_tooling
```

The previous `missing_limine_iso_tooling` blocker is resolved at the policy level by this document.

The previous `missing_bootable_iso_generation` blocker is refined by the v0.3.6 ISO generation command path.

KOZO may produce this artifact in CI when the pinned Limine source build and xorriso path succeed:

```text
artifacts/runtime/boot_image/kozo.iso
```

The local environment may still report `missing_iso_generation_tooling` until it provides the documented Limine executable, Limine bootloader artifacts, and xorriso executable.

The next release phase must use the produced ISO, when available, to attempt QEMU serial smoke evidence before any QEMU boot claim is made.
