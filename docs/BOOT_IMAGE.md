# KOZO Boot Image Skeleton

Version: 1
Status: Authoritative
Scope: Minimal boot image skeleton for the Limine x86_64 boot path

---

# 1. Purpose

This document defines KOZO's current boot image skeleton.

The skeleton provides the minimum linker, Limine configuration, and staging path needed before a future QEMU serial smoke phase can attempt boot execution.

This phase does not prove boot success.

This phase does not prove QEMU execution.

This phase does not prove hardware trap execution.

---

# 2. Authority

`docs/BOOT_IMAGE.md` owns the boot image skeleton requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/BOOT_PROTOCOL.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`

It does not define ABI truth, syscall truth, compatibility claims, userspace execution, or production readiness.

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

# 4. Build Command

Build the boot image skeleton with:

```text
scripts/build_boot_image.sh
```

The script builds a freestanding kernel ELF, stages the Limine configuration, and attempts ISO generation when Limine artifacts and xorriso are available.

GitHub Actions full CI installs xorriso, builds pinned Limine v12.3.3 source tooling, exports `LIMINE_DIR`, `LIMINE`, and `XORRISO`, and runs this script as part of the full verification workflow.

Boot tooling acquisition requirements are defined in:

```text
docs/BOOT_TOOLING.md
```

---

# 5. Output Path

The generated skeleton path is:

```text
artifacts/runtime/boot_image/
```

The staged image root is:

```text
artifacts/runtime/boot_image/image-root/
```

The staged kernel ELF is:

```text
artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
```

The staged Limine configuration is:

```text
artifacts/runtime/boot_image/image-root/boot/limine/limine.conf
```

The build manifest is:

```text
artifacts/runtime/boot_image/manifest.json
```

The boot image packaging metadata is:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The expected ISO path is:

```text
artifacts/runtime/boot_image/kozo.iso
```

---

# 6. Current Limitations

The skeleton is not a boot proof.

The skeleton does not include QEMU execution.

The skeleton does not include serial output capture.

The skeleton does not include a `qemu_smoke` validator.

The package metadata records either successful ISO packaging or `missing_iso_generation_tooling`.

The current local environment does not produce `artifacts/runtime/boot_image/kozo.iso` because the Limine executable, Limine bootloader artifacts, and xorriso executable are unavailable.

CI may produce `artifacts/runtime/boot_image/kozo.iso` when pinned Limine and xorriso tooling are available and the image command succeeds.

---

# 7. Boot Blocker Relationship

The previous `missing_boot_protocol_and_image_packaging` blocker is reduced by this phase because the boot protocol, linker script, Limine configuration, and boot image staging path now exist.

The previous `missing_bootable_iso_generation` blocker is refined by the ISO generation command path.

The remaining local blocker is `missing_iso_generation_tooling`.

QEMU boot may not be claimed until a later phase captures and validates serial output.

---

# 8. Future QEMU Smoke Path

The future QEMU smoke path should:

* provide Limine and xorriso tooling for the ISO generation command
* build a bootable Limine ISO from the staged image root
* boot the image under QEMU
* capture serial output to `artifacts/runtime/qemu_smoke.log`
* validate an early serial marker from the kernel entry path
* add a runtime evidence validator for the QEMU smoke artifact
