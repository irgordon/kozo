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
* `CHANGELOG.md`
* `PHASEMAP.md`
* `ROADMAP.md`
* `docs/RELEASE_CHECKLIST.md`
* `docs/REQUIRED_CHECKS.md`
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

Future runtime smoke phases must add their runtime logs to this list before using them as release evidence.

---

# 7. Required CI Evidence

Release review must record CI run URLs or statuses when available.

Required check policy is owned by `docs/REQUIRED_CHECKS.md`.

The minimum release evidence must record:

* full verification status
* lint/static-check status
* required target/toolchain setup
* CI run URL or status when available

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
  ci_status.md
  non_goals.md
```

This is the minimum directory or archive shape for release review.

The exact packaging command may be defined by a later release phase.

---

# 11. Release Blocker Categories

| Priority | Meaning |
| --- | --- |
| P0 | Correctness, security boundary, or release integrity blocker. |
| P1 | v1.0.0 credibility blocker. |
| P2 | Release candidate blocker. |
| P3 | Non-blocking cleanup or polish. |

P0 and P1 issues block v1.0.0 release.

P2 issues block release candidate promotion unless explicitly waived through governance.

P3 issues may be deferred when they do not weaken release claims or evidence.
