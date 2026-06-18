# KOZO Compatibility

Version: 1
Status: Authoritative
Scope: Compatibility claims, non-goals, and evidence requirements

---

# 1. Purpose

This document defines which compatibility claims KOZO may make and which claims are currently forbidden.

Compatibility claims must be scoped, evidence-backed, and current.

---

# 2. Authority

This document owns compatibility claims and non-goals.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, and `docs/ARCHITECTURE.md`.

It does not implement compatibility and does not define coding style, ABI truth, validator mechanics, or generated artifact policy.

---

# 3. Non-Goals

KOZO does not currently claim:

* Linux compatibility
* Linux application support
* POSIX completeness
* general userspace execution support
* a complete process model
* VFS behavior
* file descriptor behavior
* production readiness

---

# 4. Forbidden Broad Claims

The following broad claims are forbidden unless this document is amended with scoped evidence:

* KOZO is Linux compatible.
* KOZO supports Linux applications.
* KOZO is POSIX complete.
* KOZO supports userspace execution.
* KOZO supports a process model.
* KOZO supports VFS behavior.
* KOZO supports file descriptor behavior.
* KOZO is production ready.

---

# 5. Rules

Compatibility claims must be scoped.

Compatibility claims must be evidence-backed.

Generated reports alone are not compatibility evidence.

Verification passing is not production readiness.

Forbidden broad claims must not appear in authoritative docs, generated reports, README text, changelog entries, or release summaries.

---

# 6. Allowed Scoped Claim Format

A compatibility claim must name:

* exact behavior tested
* architecture tested
* source or contract involved
* command or validator used
* evidence artifact
* known limitations
* date or version of validation

Allowed example shape:

```text
KOZO validates the current x86_64 heartbeat/debug syscall boundary through scripts/verify.sh as of vX.Y.Z. This does not imply Linux compatibility, POSIX completeness, or general userspace execution.
```

---

# 7. Evidence Requirements

Compatibility evidence must be reproducible.

Evidence must be tied to checked-in tests, validators, artifacts, or documented manual procedures.

Evidence must not rely on marketing language or generated reports alone.

Verification passing is not production readiness.

---

# 8. Userspace Claims

Do not claim userspace execution unless the claim names the exact userspace path, syscall surface, ABI boundary, and evidence.

Rust userspace services existing in the repository do not prove a general userspace execution environment.

---

# 9. Process, VFS, and File Descriptor Claims

Do not claim process model behavior, VFS behavior, or file descriptor behavior unless each surface has scoped contracts, implementation, tests, validators, and evidence.

---

# 10. Relationship to Other Governance Documents

`GOVERNANCE.md` owns precedence.

`INVARIANTS.md` forbids broad compatibility claims without evidence.

`ARCHITECTURE.md` owns current system structure.

`VALIDATION.md` owns verification evidence rules.

`CHANGELOG.md` may record compatibility-related changes but does not govern them.
