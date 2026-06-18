# KOZO Phase Map

Version: 1
Status: Planning
Scope: Release phase sequencing for the path to a scoped KOZO v1.0.0

---

# 1. Purpose

This document defines the release phase sequence from the current governed prototype toward a scoped KOZO v1.0.0 release.

It exists to make release planning explicit, reviewable, and evidence-driven.

---

# 2. Authority

`PHASEMAP.md` owns release phase sequencing.

It does not override:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* checked-in contracts
* schemas
* validators

If this document conflicts with an authoritative governance document, the authoritative document wins.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not define ABI truth, syscall truth, or runtime behavior.

---

# 4. Release Gates

Every release phase must preserve these gates unless a later governance amendment makes a narrower gate explicit:

* `scripts/verify.sh` passes.
* Python unit discovery passes.
* Odin check/build passes through verification.
* Pinned Rust cargo check passes.
* Generated reports are current.
* `artifacts/latest_verify.json` is valid JSON and reports `pass`.
* Branch protection checks are green for release branches.
* Compatibility claims are scoped and accurate.
* Release evidence is present for the phase being released.

---

# 5. Evidence Required

Release review must include:

* `artifacts/latest_verify.json`
* `artifacts/logs/*.log`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`
* checked-in contracts
* checked-in schemas
* `CHANGELOG.md`
* `PHASEMAP.md`
* `ROADMAP.md`
* CI run URLs or statuses when available
* release notes
* known non-goals list

Detailed evidence rules are owned by `docs/RELEASE_EVIDENCE.md`.

---

# 6. Phase Table

| Phase | Name | Purpose | Required Deliverables | Exit Criteria |
| --- | --- | --- | --- | --- |
| `v0.1.0` | Release governance baseline | Define v1.0.0 scope, release evidence requirements, required CI checks, release checklist, README claim cleanup, and generated report review inputs. | `PHASEMAP.md`, `ROADMAP.md`, `docs/RELEASE_EVIDENCE.md`, `docs/RELEASE_CHECKLIST.md`, `docs/REQUIRED_CHECKS.md`, README claim cleanup if needed. | Release checklist and required checks policy are merged, non-goals are preserved, verification passes, generated governance surfaces are refreshed as needed. |
| `v0.2.0` | Runtime execution evidence | Add runtime evidence beyond source-shape proof using the narrowest honest smoke target available. | `docs/RUNTIME_EVIDENCE.md`, runtime smoke command, runtime evidence artifact, validator for runtime evidence, release evidence logs. | Runtime smoke evidence is reproducible, governed, included in release evidence, and clearly states whether it is boot execution or runtime-adjacent object evidence. |
| `v0.3.0` | Security boundary foundation | Convert security model from policy-only to minimal implementation-backed checks. | Pointer/null boundary enforcement evidence, capability/handle placeholder policy or initial implementation, fault containment expectations, negative tests for unsafe boundary cases. | Security boundary claims are backed by implementation evidence and negative tests. |
| `v0.4.0` | ABI and syscall maturity | Stabilize current ABI/syscall governance and define expansion rules. | ABI version policy, syscall expansion checklist, generated binding compatibility expectations, regression evidence for all governed syscalls. | Current syscall surface is frozen unless changed through governed process. |
| `v0.5.0-rc.1` | Release candidate hardening | Freeze release scope and release gates, produce evidence bundle, confirm branch protection, and dry-run release notes. | Release evidence bundle, completed release checklist, current generated reports, changelog/release notes dry run, all required CI checks green. | Release candidate can be reviewed without adding new scope. |
| `v1.0.0` | Scoped production release | Release only the proven, scoped KOZO surface. | Final release evidence bundle, final changelog and release notes, passing required gates, explicit non-goals. | v1.0.0 claims only evidence-backed behavior and preserves all compatibility non-goals. |

---

# 7. v1.0.0 Constraints

`v1.0.0` must remain scoped to proven behavior.

It must not claim:

* Linux compatibility unless separately implemented and proven
* POSIX completeness
* general userspace execution
* process model behavior
* VFS behavior
* scheduler maturity
* ELF loading
* file descriptor behavior
* production readiness beyond the scoped release definition

---

# 8. Release Checklist

Before release:

* Confirm phase exit criteria are satisfied.
* Complete `docs/RELEASE_CHECKLIST.md`.
* Confirm `docs/REQUIRED_CHECKS.md` required checks pass.
* Confirm release gates pass.
* Confirm generated reports are current.
* Confirm release evidence bundle is present.
* Confirm changelog and release notes describe only evidence-backed behavior.
* Confirm compatibility non-goals are present.
* Confirm no generated artifact was manually edited.
* Confirm branch protection checks are green.
