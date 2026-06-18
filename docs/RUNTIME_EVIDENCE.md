# KOZO Runtime Evidence

Version: 1
Status: Authoritative
Scope: Runtime smoke evidence for the current governed KOZO runtime boundary

---

# 1. Purpose

This document defines KOZO's current runtime smoke evidence path.

The current path is a bounded runtime-adjacent object and symbol smoke check. It proves that the freestanding x86_64 kernel objects and assembly bridge objects can be built together with the current entry, dispatcher, syscall bridge, and serial marker surfaces present in binary evidence.

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

---

# 4. Runtime Evidence Target

The current target is:

```text
runtime-adjacent-object-symbol-smoke
```

The smoke path builds freestanding x86_64 Odin kernel objects, assembles the current x86_64 boot and syscall bridge objects, records `nm` and `strings` evidence, and verifies required entry, dispatcher, bridge, and serial marker surfaces.

This is the narrowest honest evidence target because the repository does not yet include a boot image, linker script, loader configuration, or QEMU boot packaging.

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

---

# 7. Artifact Path

The runtime smoke artifact is:

```text
artifacts/runtime/runtime_smoke.log
```

The artifact is generated evidence. It must be reproduced by the smoke script before it is used in release review.

---

# 8. Validator

The registered validator is:

```text
runtime_smoke_evidence
```

It checks:

* runtime smoke artifact exists
* artifact is non-empty
* runtime metadata is structurally valid
* expected runtime-adjacent markers are present
* failure markers are absent
* release evidence policy references the artifact
* diagnostics name the failed runtime evidence field

---

# 9. What This Evidence Proves

This evidence proves:

* the freestanding x86_64 kernel object build path succeeds
* x86_64 boot and syscall assembly objects can be assembled
* runtime entry and dispatcher symbols are present in binary evidence
* syscall bridge symbols are present in binary evidence
* current serial heartbeat marker strings are present in binary evidence
* the generated runtime smoke artifact is available for release review

---

# 10. What This Evidence Does Not Prove

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

# 11. Known Limitations

The current runtime smoke path is not a boot smoke test.

It is a deterministic runtime-adjacent evidence step until the repository has enough boot packaging to run a bounded emulator smoke path honestly.
