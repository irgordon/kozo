# KOZO Runtime Evidence

Version: 1
Status: Authoritative
Scope: Runtime smoke evidence for the current governed KOZO runtime boundary

---

# 1. Purpose

This document defines KOZO's current runtime smoke evidence path.

The current path is a bounded runtime-adjacent object and symbol smoke check. It proves that the freestanding x86_64 kernel objects and assembly bridge objects can be built together with the current entry, dispatcher, syscall bridge, and serial marker surfaces present in binary evidence.

The v0.3.0 boot baseline attempted to move beyond runtime-adjacent evidence. It is currently blocked by `missing_boot_protocol_and_image_packaging`.

v0.3.1 selected Limine as the planned x86_64 boot protocol, but QEMU smoke is planned and not yet proven.

v0.3.2 added a boot image skeleton, but QEMU smoke is still planned and not yet proven.

v0.3.3 added a bounded QEMU smoke command, but it currently fails closed because no bootable Limine ISO or disk image is produced.

v0.3.4 added boot image package metadata at `artifacts/runtime/boot_image/package_metadata.json`, recording the packaging blocker.

v0.3.5 added `docs/BOOT_TOOLING.md` to define the Limine and xorriso acquisition path.

v0.3.6 added the ISO generation command path, but local ISO generation is blocked by missing Limine artifacts and xorriso tooling.

v0.3.7 added full-CI installation of pinned Limine source tooling and xorriso so CI can attempt ISO generation and upload boot image artifacts.

Current boot blocker: `missing_iso_generation_tooling`.

---

# 2. Authority

This document owns runtime smoke evidence requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, or production-readiness claims.

---

# 3. Non-Goals

This evidence does not prove Linux compatibility.

This evidence does not prove POSIX compatibility.

This evidence does not prove general userspace execution.

This evidence does not prove a process model.

This evidence does not prove VFS behavior.

This evidence does not prove scheduler maturity.

This evidence does not prove ELF loading.

This evidence does not prove file descriptor behavior.

This evidence does not prove production readiness.

This evidence does not prove QEMU boot execution, hardware syscall execution, interrupt handling, or privilege transition behavior.

The current boot blocker report also does not prove QEMU boot.

The boot protocol decision also does not prove QEMU boot.

The boot image skeleton also does not prove QEMU boot.

---

# 4. Runtime Evidence Target

The current target is:

```text
runtime-adjacent-object-symbol-smoke
```

The smoke path builds freestanding x86_64 Odin kernel objects, assembles the current x86_64 boot and syscall bridge objects, records `nm` and `strings` evidence, and verifies required entry, dispatcher, bridge, and serial marker surfaces.

This remains the narrowest passing runtime evidence target until `artifacts/runtime/boot_image/kozo.iso` is generated and then booted with validated serial output.

---

# 5. Required Tools

Required tools:

* `odin`
* `nasm`
* `nm`
* `strings`
* `grep`
* `find`

No network access is required.

---

# 6. Evidence Command

Generate runtime smoke evidence with:

```bash
scripts/runtime_smoke.sh
```

Full verification runs this command through `scripts/verify.sh`.

Full CI runs `scripts/verify.sh`, so runtime smoke evidence is required in full CI through the full-verification path.

The lint workflow does not run runtime smoke evidence unless it is changed to run full verification.

---

# 7. Artifact Path

The runtime smoke artifact is:

```text
artifacts/runtime/runtime_smoke.log
```

The runtime smoke metadata artifact is:

```text
artifacts/runtime/runtime_smoke.metadata.json
```

The boot blocker artifact is:

```text
artifacts/runtime/boot_blocker_report.json
```

The QEMU smoke log path is:

```text
artifacts/runtime/qemu_smoke.log
```

The boot image package metadata path is:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The expected boot image path is:

```text
artifacts/runtime/boot_image/kozo.iso
```

The boot tooling policy path is:

```text
docs/BOOT_TOOLING.md
```

The QEMU smoke log is currently blocker evidence only. It is not passing QEMU serial smoke evidence.

The selected boot protocol is documented in:

```text
docs/BOOT_PROTOCOL.md
docs/decisions/0001-boot-protocol.md
```

The boot image skeleton is documented in:

```text
docs/BOOT_IMAGE.md
```

The log is generated evidence. It must be reproduced by the smoke script before it is used in release review.

The metadata is deterministic generated evidence. It identifies the evidence type, source log, generator, validator, positive claims, and explicit non-goals.

Full CI should upload both runtime smoke artifacts when full verification runs.

Full CI should also upload the boot blocker report while v0.3.0 remains blocked.

Full CI should upload boot image package metadata and `artifacts/runtime/boot_image/kozo.iso` when ISO generation succeeds.

---

# 8. Packaging

Runtime evidence is generated under:

```text
artifacts/runtime/
```

The boot blocker report is generated under the same directory.

For release review, package or copy it under:

```text
artifacts/release/runtime/
  runtime_smoke.log
  runtime_smoke.metadata.json
```

`artifacts/runtime/runtime_smoke.log` is the live generated output.

`artifacts/release/runtime/runtime_smoke.log` is the release bundle copy.

Do not treat the release bundle copy as source truth. Regenerate the live artifact with `scripts/runtime_smoke.sh` when reviewing or refreshing evidence.

---

# 9. Review Instructions

Before release review:

* Run `scripts/runtime_smoke.sh`.
* Run `scripts/boot_blocker_report.sh` while v0.3.0 remains blocked.
* Run `scripts/qemu_smoke.sh` only when reviewing the current QEMU blocker directly; it is expected to fail closed until bootable image packaging exists.
* Confirm `artifacts/runtime/runtime_smoke.log` exists and is non-empty.
* Confirm `artifacts/runtime/runtime_smoke.metadata.json` is valid JSON.
* Confirm `artifacts/runtime/boot_blocker_report.json` is valid JSON while boot is blocked.
* Confirm metadata `evidence_type` is `runtime-adjacent-object-symbol-smoke`.
* Confirm metadata positive claims match the current smoke target.
* Confirm metadata non-goals still include QEMU boot, hardware trap execution, Linux compatibility, userspace execution, process model, VFS behavior, scheduler maturity, ELF loading, file descriptor behavior, and production readiness.
* Confirm `runtime_smoke_evidence` passes.
* Copy or archive the log and metadata into the release evidence bundle.
* Copy or archive the boot blocker report into the release evidence bundle while boot is blocked.

---

# 10. Retention Policy

The latest live runtime smoke log and metadata live under `artifacts/runtime/`.

Release bundle copies live under `artifacts/release/runtime/` when a release evidence bundle is assembled.

Transient object files created while generating evidence must be cleaned by `scripts/runtime_smoke.sh`.

Historical release evidence may be retained outside the live artifacts directory by release tooling or GitHub release assets.

---

# 11. Invalidating Changes

Runtime evidence is invalidated by:

* changes to `kernel/`
* changes to `kernel/arch/`
* changes to the ABI bindings used by the kernel
* changes to `scripts/runtime_smoke.sh`
* changes to `docs/RUNTIME_EVIDENCE.md`
* changes to `harness/validators_impl/runtime_smoke_evidence.py`
* changes to `scripts/boot_blocker_report.sh`
* changes to `scripts/qemu_smoke.sh`
* changes to `harness/validators_impl/boot_blocker_report.py`
* stale, missing, malformed, or failed runtime smoke artifacts
* stale, missing, malformed, or failed boot blocker artifacts while boot is blocked

When invalidated, regenerate evidence and rerun full verification.

---

# 12. Validator

The registered validator is:

```text
runtime_smoke_evidence
```

It checks:

* runtime smoke artifact exists
* runtime smoke metadata exists
* runtime smoke metadata is valid JSON
* runtime smoke metadata fields match the governed evidence target
* runtime smoke metadata declares required positive claims
* runtime smoke metadata declares required non-goals
* artifact is non-empty
* runtime metadata is structurally valid
* expected runtime-adjacent markers are present
* failure markers are absent
* release evidence policy references the artifact
* release evidence policy references the metadata
* diagnostics name the failed runtime evidence field

---

# 13. What This Evidence Proves

This evidence proves:

* the freestanding x86_64 kernel object build path succeeds
* x86_64 boot and syscall assembly objects can be assembled
* runtime entry and dispatcher symbols are present in binary evidence
* syscall bridge symbols are present in binary evidence
* current serial heartbeat marker strings are present in binary evidence
* the generated runtime smoke artifact is available for release review

---

# 14. What This Evidence Does Not Prove

This evidence does not prove:

* QEMU boot
* hardware syscall or interrupt transition
* privilege transition
* Rust userspace execution in a kernel-managed process
* scheduler behavior
* memory isolation
* production readiness

Those surfaces require later phase work.

---

# 15. Known Limitations

The current runtime smoke path is not a boot smoke test.

It is a deterministic runtime-adjacent evidence step until the repository has enough boot packaging to run a bounded emulator smoke path honestly.
