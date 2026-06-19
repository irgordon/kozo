# KOZO Release Evidence

Version: 1
Status: Authoritative
Scope: Required evidence for KOZO release review

---

# 1. Purpose

This document defines the evidence required before a KOZO release may be reviewed.

Release evidence must make claims reproducible, scoped, and auditable.

---

# 2. Authority

This document owns release evidence requirements.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, and `docs/COMPATIBILITY.md`.

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, or validator implementation mechanics.

`docs/RELEASE_CHECKLIST.md` owns release approval checklist requirements.

`docs/REQUIRED_CHECKS.md` owns required CI/check policy.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not make generated reports authoritative.

---

# 4. Required Release Artifacts

Every release review must include:

* `artifacts/latest_verify.json`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/runtime/boot_blocker_report.json`
* `docs/BOOT_PROTOCOL.md`
* `docs/decisions/0001-boot-protocol.md`
* `CHANGELOG.md`
* `PHASEMAP.md`
* `ROADMAP.md`
* `docs/RELEASE_CHECKLIST.md`
* `docs/REQUIRED_CHECKS.md`
* `docs/RUNTIME_EVIDENCE_REVIEW.md`
* release notes
* known non-goals list
* checked-in contracts
* checked-in schemas

`artifacts/latest_verify.json` must be valid JSON and must report `pass`.

---

# 5. Required Generated Reports

Every release review must include current generated reports:

* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`

Generated reports are review surfaces. They do not own contract, compatibility, architecture, or runtime truth.

---

# 6. Required Logs

Release review must include verification logs when generated:

* `artifacts/logs/odin-check.log`
* `artifacts/logs/odin-build.log`
* `artifacts/logs/cargo-check.log`
* `artifacts/logs/nm-kernel.log`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/runtime/boot_blocker_report.json`

Future runtime smoke phases must add their runtime logs to this list before using them as release evidence.

Runtime evidence review is required for release review and is governed by `docs/RUNTIME_EVIDENCE_REVIEW.md`.

The boot blocker report is required while v0.3.0 remains blocked and is governed by `docs/BOOT.md`, `docs/BOOT_BLOCKERS.md`, `scripts/boot_blocker_report.sh`, and `boot_blocker_report`.

The current boot blocker category is `missing_boot_protocol_and_image_packaging`.

The boot protocol decision is release context only. It does not require QEMU evidence and does not create a QEMU boot claim.

---

# 7. Required CI Evidence

Release review must record CI run URLs or statuses when available.

Required check policy is owned by `docs/REQUIRED_CHECKS.md`.

The minimum release evidence must record:

* full verification status
* lint/static-check status
* required target/toolchain setup
* runtime smoke log and metadata artifact availability from full CI when available
* boot blocker report artifact availability from full CI while boot is blocked
* CI run URL or status when available

Full CI runs `scripts/verify.sh`, so runtime smoke evidence is required there through full verification and should be uploaded as CI artifacts.

Full CI also runs the boot blocker report generator through `scripts/verify.sh` while boot remains blocked, and should upload `artifacts/runtime/boot_blocker_report.json`.

The lint workflow is static-check only. It does not own runtime smoke evidence unless it is changed to run full verification.

---

# 8. Required Changelog and Release Notes

`CHANGELOG.md` must include the release version and must identify:

* added behavior
* changed behavior
* generated artifact changes
* validator or governance changes
* explicit non-goals

Release notes must describe only behavior backed by release evidence.

Release notes must not introduce compatibility or production-readiness claims that are not backed by authoritative documents and evidence.

---

# 9. Release Checklist

Release checklist authority is owned by `docs/RELEASE_CHECKLIST.md`.

Before release review, the checklist must confirm:

* repository state
* verification gates
* generated report gates
* contract gates
* CI gates
* compatibility gates
* security and governance gates
* release evidence bundle completeness
* release decision

---

# 10. Evidence Bundle Structure

A release evidence bundle should contain or reference:

```text
release-evidence/
  README.md
  latest_verify.json
  runtime/
    runtime_smoke.log
    runtime_smoke.metadata.json
    boot_blocker_report.json
  logs/
    odin-check.log
    odin-build.log
    cargo-check.log
    nm-kernel.log
  reports/
    syscall_surface.md
    abi_surface.md
    governance_index.md
  contracts/
  schemas/
  changelog.md
  release_notes.md
  phase_map.md
  roadmap.md
  release_checklist.md
  required_checks.md
  runtime_evidence_review.md
  ci_status.md
  non_goals.md
```

This is the minimum directory or archive shape for release review.

Runtime evidence is generated under `artifacts/runtime/`.

Release packaging should copy the runtime log and metadata to `artifacts/release/runtime/` when assembling a release evidence bundle.

The exact packaging command may be defined by a later release phase.

---

# 11. Retention Guidance

Keep the latest generated runtime evidence under `artifacts/runtime/` for local review.

Keep release-reviewed runtime evidence under `artifacts/release/runtime/` or an equivalent release archive.

Do not rely on stale runtime evidence after runtime, ABI binding, smoke script, or runtime evidence validator changes.

---

# 12. Release Blocker Categories

| Priority | Meaning |
| --- | --- |
| P0 | Correctness, security boundary, or release integrity blocker. |
| P1 | v1.0.0 credibility blocker. |
| P2 | Release candidate blocker. |
| P3 | Non-blocking cleanup or polish. |

P0 and P1 issues block v1.0.0 release.

P2 issues block release candidate promotion unless explicitly waived through governance.

P3 issues may be deferred when they do not weaken release claims or evidence.
