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
* `CHANGELOG.md`
* `PHASEMAP.md`
* `ROADMAP.md`
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

Future runtime smoke phases must add their runtime logs to this list before using them as release evidence.

---

# 7. Required CI Evidence

Release review must record CI run URLs or statuses when available.

Required checks:

* full verification
* Python unit discovery
* Odin check/build
* pinned Rust cargo check
* JSON validation
* generated report drift checks
* whitespace check

Branch protection should require the CI checks that implement these gates.

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

Before release review:

* Run `scripts/verify.sh`.
* Run Python unit discovery.
* Validate `artifacts/latest_verify.json`.
* Validate `tasks/todo.json`.
* Confirm generated reports are current.
* Confirm required CI checks are green.
* Confirm release evidence bundle is present.
* Confirm changelog and release notes are current.
* Confirm compatibility claims are scoped.
* Confirm non-goals are listed.
* Confirm generated artifacts were not manually edited.

---

# 10. Evidence Bundle Structure

A release evidence bundle should contain or reference:

```text
release-evidence/
  latest_verify.json
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
  ci_status.md
  non_goals.md
```

The exact packaging mechanism may be defined by a later release phase.

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
