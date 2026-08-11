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

Host build claims require the corresponding governed GitHub Actions runner.

Linux hosted QEMU remains the authoritative guest-runtime proof. Local macOS development is one validation environment and does not create a compatibility claim by itself.

No build or verification script may depend on user-specific absolute paths.

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

Host portability evidence proves only that declared tools and controlled paths can build or verify the scoped repository surface. It does not prove Linux compatibility, POSIX completeness, general userspace execution, or production readiness.

---

# 8. Host Evidence Ladder

Every claimed development host uses one explicit status:

| Status | Meaning |
| --- | --- |
| `NOT_EXECUTED` | No governed hosted contract has run. |
| `DESIGNED` | No intentional blocker is known, but hosted evidence is absent. |
| `VALIDATED_BUILD` | The required hosted build/tooling contract passed. |
| `VALIDATED_RUNTIME` | The build/tooling contract and the separate guest-runtime contract passed. |
| `UNSUPPORTED` | The host is outside the declared contract or has a known blocking incompatibility. |

Claim promotion is one-way and evidence-backed:

```text
DESIGNED
    -> required hosted build evidence -> VALIDATED_BUILD
    -> actual governed runtime evidence -> VALIDATED_RUNTIME
```

No inference is allowed between levels. In particular, a passing Windows build
job does not prove Windows QEMU or guest-runtime behavior. Terms such as
"supported," "portable," or unqualified "validated" must name the exact
status and evidence.

The Phase 0 required build hosts are Linux `ubuntu-24.04`, Windows
`windows-2025`, and macOS `macos-15`. Current hosted evidence is recorded in
`docs/portability/HOST_MATRIX.md`:

| Host | Current status | Build evidence | Runtime evidence |
| --- | --- | --- | --- |
| Linux | `VALIDATED_RUNTIME` | `PASS` in portability run `31458972010` | `PASS` in CI run `31458972015` |
| Windows | `VALIDATED_BUILD` | Required job and aggregate release-input identity gate `PASS` in run `31458972010` | `NOT_EXECUTED` |
| macOS | `VALIDATED_BUILD` | `PASS` in portability run `31458972010` | `NOT_EXECUTED` |

Windows now satisfies `VALIDATED_BUILD` because its per-host contract and the
required distributed path/size/SHA-256 gate both passed. The correction uses
committed blob authority, narrow LF checkout policy, and byte-exact staging;
it does not normalize invalid inputs downstream. Windows runtime remains
`NOT_EXECUTED`, so this status does not claim Windows QEMU behavior.

---

# 9. Userspace Claims

Do not claim userspace execution unless the claim names the exact userspace path, syscall surface, ABI boundary, and evidence.

Rust userspace services existing in the repository do not prove a general userspace execution environment.

---

# 10. Process, VFS, and File Descriptor Claims

Do not claim process model behavior, VFS behavior, or file descriptor behavior unless each surface has scoped contracts, implementation, tests, validators, and evidence.

---

# 11. Relationship to Other Governance Documents

`GOVERNANCE.md` owns precedence.

`INVARIANTS.md` forbids broad compatibility claims without evidence.

`ARCHITECTURE.md` owns current system structure.

`VALIDATION.md` owns verification evidence rules.

`CHANGELOG.md` may record compatibility-related changes but does not govern them.
