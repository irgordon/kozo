# KOZO Release Checklist

Version: 1
Status: Authoritative
Scope: Release approval checklist for scoped KOZO releases

---

# 1. Purpose

This document defines the checklist used to decide whether a KOZO release is allowed, blocked, or deferred.

It converts release planning into reviewable release gates.

---

# 2. Authority

`docs/RELEASE_CHECKLIST.md` owns release approval checklist requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`
* checked-in contracts
* schemas
* validators

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, validator logic, or generated artifact policy.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not authorize bypassing governance, invariants, compatibility policy, or validation policy.

---

# 4. Blocker Categories

| Priority | Meaning | Release Effect |
| --- | --- | --- |
| P0 | Correctness, security boundary, or release integrity blocker. | Blocks release. |
| P1 | v1.0.0 credibility blocker. | Blocks v1.0.0 release. |
| P2 | Release candidate blocker. | Blocks release candidate promotion unless explicitly waived through governance. |
| P3 | Non-blocking cleanup or polish. | May be deferred when release claims and evidence remain accurate. |

---

# 5. Approval Rules

A release is allowed only when:

* every required checklist item is complete or explicitly marked not applicable with evidence
* every P0 and P1 blocker is resolved
* every P2 blocker is resolved or waived through governance
* release notes describe only evidence-backed behavior
* compatibility non-goals remain explicit
* required checks are green
* release evidence is complete

Emergency bypass of required checks is not allowed by this document.

Maintainer emergency action, if ever needed, must be documented in a release decision record and must not create unsupported compatibility or production-readiness claims.

---

# 6. Repository State

Required checklist:

* Release branch is correct.
* Working tree is clean.
* Release commit is identified.
* Tag candidate is identified.
* `CHANGELOG.md` is current.
* Release notes are present when required by the phase.
* `docs/PHASEMAP.md` and `docs/ROADMAP.md` match the intended release scope.

Evidence references:

* `git status --short --branch`
* `git log --oneline --decorate -n 5`
* `CHANGELOG.md`
* `docs/PHASEMAP.md`
* `docs/ROADMAP.md`

---

# 7. Verification Gates

Required checklist:

* `scripts/verify.sh` passes.
* `artifacts/latest_verify.json` status is `pass`.
* `artifacts/latest_verify.json` failed check count is `0`.
* `artifacts/runtime/runtime_smoke.log` is present.
* `artifacts/runtime/runtime_smoke.metadata.json` is present.
* `artifacts/runtime/boot_blocker_report.json` is present while boot is blocked.
* `artifacts/runtime/boot_image/package_metadata.json` is present while boot image packaging is blocked.
* `runtime_smoke_evidence` passes.
* `runtime_evidence_review` passes.
* `boot_blocker_report` passes while boot is blocked.
* `boot_image_packaging` passes while boot image packaging is blocked.
* `qemu_smoke_evidence` passes when QEMU smoke metadata is generated.
* Runtime evidence review is complete.
* Runtime metadata non-goals are reviewed.
* Full CI uploaded `artifacts/runtime/runtime_smoke.log` when available.
* Full CI uploaded `artifacts/runtime/runtime_smoke.metadata.json` when available.
* Full CI uploaded `artifacts/runtime/boot_blocker_report.json` while boot is blocked.
* `artifacts/runtime/qemu_smoke.log` is reviewed when the QEMU blocker is under direct review.
* `artifacts/runtime/qemu_smoke.stderr.log` is reviewed when the QEMU blocker is under direct review.
* `artifacts/runtime/qemu_smoke.metadata.json` is reviewed when the QEMU blocker is under direct review.
* QEMU smoke metadata outcome may use only a blocker governed by `contracts/runtime_evidence_taxonomy.v0.json`; capability blockers do not authorize a pass or broaden runtime claims.
* QEMU smoke metadata early markers, observed markers, earliest marker, timeout state, and byte counts are reviewed when the QEMU blocker is under direct review.
* QEMU smoke metadata outcome is `pass` before any QEMU boot claim is made.
* Passing QEMU smoke metadata includes `KOZO_RUNTIME_RETURN_OK` as the expected marker.
* Passing QEMU smoke serial output includes the taxonomy-owned sequence through `KOZO_RUNTIME_LOOP_EXIT_OK`, `KOZO_CAPABILITY_DISPATCH_ENTER`, `KOZO_RUNTIME_STATUS_QUERY_OK`, `KOZO_FIRST_CAPABILITY_OK`, and `KOZO_RUNTIME_RETURN_OK` in order.
* `runtime_progression_entry_contract` and `runtime_progression_evidence` pass.
* The kernel ELF report records the progression entry, bootstrap context, static state, and fixed serial bridge symbols.
* Memory evidence review includes the contract-owned region geometry, full zero fill, bounded sentinel probe, restoration, marker order, and unchanged halt path.
* QEMU serial smoke evidence is promoted only from a green CI run with passing metadata and the full ordered marker sequence.
* Passing QEMU serial smoke evidence is reviewed as a narrow smoke claim, not as hardware trap, userspace, subsystem, compatibility, or production-readiness evidence.
* Release is blocked if runtime evidence is overclaimed or missing required non-goals.
* No QEMU or boot claim is made unless separately implemented and proven.
* Python unit tests pass.
* Odin check/build passes through verification.
* Pinned Rust cargo check passes.
* `git diff --check` passes.

Evidence references:

* `artifacts/latest_verify.json`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/logs/odin-check.log`
* `artifacts/logs/odin-build.log`
* `artifacts/logs/cargo-check.log`
* `artifacts/logs/nm-kernel.log`
* `docs/RUNTIME_EVIDENCE.md`
* `docs/RUNTIME_EVIDENCE_REVIEW.md`

---

# 8. Generated Report Gates

Required checklist:

* `docs/generated/governance_index.md` is current.
* `docs/generated/syscall_surface.md` is current.
* `docs/generated/abi_surface.md` is current.
* Generated ABI bindings self-identify as generated files.
* Generated reports state their non-authoritative status.
* Generated artifacts were produced by their governed generator or verification path.

Evidence references:

* `docs/generated/governance_index.md`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `bindings/rust/kozo_abi.rs`
* `bindings/odin/kozo_abi.odin`

---

# 9. Contract Gates

Required checklist:

* ABI manifest is valid.
* Syscall boundary contract is valid.
* Syscall table contract is valid.
* Syscall class contract is valid.
* Syscall catalog is valid.
* Schemas are valid.
* Contract-backed claims match generated reports and release notes.

Evidence references:

* `contracts/kozo_abi_manifest.json`
* `contracts/syscall_boundary_contract.v0.json`
* `contracts/syscall_table_contract.v0.json`
* `contracts/syscall_class_contract.v0.json`
* `contracts/syscall_catalog.v0.json`
* `schemas/`

---

# 10. CI Gates

Required checklist:

* Required GitHub Actions checks pass.
* `ci / full verification` passes.
* `lint / static checks` passes.
* Required target/toolchain setup is confirmed.
* Runtime smoke evidence is generated by `ci / full verification`.
* Boot blocker report is generated by `ci / full verification` while boot is blocked.
* QEMU smoke log and metadata are uploaded by `ci / full verification` when generated.
* Runtime smoke evidence is not required from `lint / static checks` unless lint runs full verification.
* CI evidence is recorded by URL or status when available.

Evidence references:

* GitHub Actions `ci` workflow status.
* GitHub Actions `lint` workflow status.
* `docs/REQUIRED_CHECKS.md`.

---

# 11. Compatibility Gates

Required checklist:

* No broad Linux compatibility claim is present.
* No POSIX completeness claim is present.
* No general userspace execution claim is present unless scoped and evidence-backed.
* No process model, VFS, scheduler, ELF loading, or file descriptor claim is present unless scoped and evidence-backed.
* No production-readiness claim is present outside the scoped release statement.
* Release notes include known non-goals.

Evidence references:

* `docs/COMPATIBILITY.md`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* release notes

---

# 12. Security and Governance Gates

Required checklist:

* Invariants are reviewed.
* Security model is reviewed.
* Generated artifact policy is reviewed.
* Validation policy is reviewed.
* Release evidence bundle is complete.
* Release scope does not conflict with authoritative governance.

Evidence references:

* `docs/INVARIANTS.md`
* `docs/SECURITY_MODEL.md`
* `docs/GENERATED_ARTIFACTS.md`
* `docs/VALIDATION.md`
* `docs/RELEASE_EVIDENCE.md`

---

# 13. Release Evidence Bundle

Required checklist:

* `artifacts/latest_verify.json` is included.
* Verification logs are included.
* Generated reports are included.
* Contracts are included.
* Schemas are included.
* Changelog is included.
* Release notes are included when available.
* CI run references are included when available.
* Runtime smoke evidence is included for v0.2.0 and later.
* Runtime smoke metadata is included for v0.2.1 and later.
* Runtime evidence review is included for v0.2.3 and later.
* CI/runtime evidence policy alignment is included for v0.2.4 and later.
* Boot blocker report is included for v0.3.0 until QEMU boot evidence replaces it.

The release evidence bundle shape is owned by `docs/RELEASE_EVIDENCE.md`.

For v0.7.5 and later, confirm the controlled runtime loop contract and evidence validators pass, the ELF report records the linked loop symbols and backward branch, hosted QEMU evidence contains the ordered loop markers, exact return evidence follows loop exit, and the halt contract still passes. Do not promote the loop stage from local source or ELF evidence alone.

For v0.8.0 and later, confirm the first capability contract and evidence validators pass, request and response validation remain explicit, the ELF report records dispatcher/handler/bridge symbols and the progression call edge, hosted QEMU evidence contains all three capability markers before runtime return, and failure paths cannot emit success markers. Do not promote the capability from local source or ELF evidence alone.

For v0.8.1 and later, confirm the CPU extended-state contract and evidence
validators pass, the ELF report records CPU-state symbols and required
instructions, no governed AVX/YMM/ZMM/`xsetbv` use exists, hosted QEMU contains
the three CPU-state markers before runtime progression, the full capability
suffix remains present, and the terminal halt contract still passes.

For v0.8.2 and later, confirm both state-transition validators pass, capability
ID 1 behavior remains unchanged, ELF evidence records the state cell, direct
ID 2 route, handler, accessors, and fixed bridges, and hosted QEMU contains the
ordered update-entry, update-success, second-capability, return, and halt
evidence. Reject any release evidence that implies arbitrary memory writes,
concurrency, userspace access, authorization, persistence, or isolation.

For v0.8.3 and later, confirm both fixed user-mapping validators pass; ELF
evidence records seven aligned table pages and three aligned backing pages;
effective U/S propagates across PML4E/PDPTE/PDE/PTE; kernel leaves remain
supervisor-only; code is RX and data/stack are RW-NX; CR3 readback matches;
QEMU captures all five mapping markers before runtime entry; and the existing
capability, return, and halt evidence remains present. Do not infer Ring 3 or
isolation from Ring 0 survival probes.

---

# 14. Release Decision

Every release review must record one decision:

* release allowed
* release blocked
* release deferred

The decision record must include:

* release candidate version
* release commit
* tag candidate
* checklist result
* blocker category, if any
* required follow-up
* reviewer or maintainer approval

Release decision records may be stored in release notes, issue trackers, or a later governed release record file.

---

# 15. v0.8.4 Privilege-Transition Gate

For v0.8.4 and later, confirm:

* both bounded privilege-transition validators pass;
* the accepted fixed user-mapping validators remain green;
* ELF evidence records fixed GDT, TSS, IDT, stack, user-target, return-handler, continuation, `iretq`, and `int 0x81` paths;
* hosted QEMU captures all five privilege markers between mapping survival and Odin entry;
* the complete capability suffix and terminal halt remain present;
* no known failure path emits Ring3-probe, Ring0-return, or runtime-return success.

Reject any release claim that treats this fixed boot-time probe as general
userspace, process isolation, public syscall handling, exception recovery, or
production readiness.

---

# 16. v0.8.5 Fixed User Request Boundary Gate

For v0.8.5 and later, confirm:

* `fixed_user_request_boundary_contract` and
  `fixed_user_request_boundary_evidence` pass;
* ELF evidence records exact request, response, and verification-shadow
  geometry and the ordered handler call chain;
* hosted QEMU captures all four fixed-boundary markers between Ring3 entry and
  the existing Ring3-probe marker;
* request and response spans remain fixed within the governed user data page;
* all boundary buffers are cleared and verified zero before continuation;
* the accepted privilege, capability, runtime-return, and halt evidence remains
  green.

Reject any release claim that generalizes this transaction into arbitrary
user pointers, a public syscall ABI, persistent userspace, process isolation,
hostile-code safety, compatibility, or production readiness.

# 17. v0.8.6 Bounded User Response Consumption Gate

Confirm:

* v0.8.5 remains accepted;
* both response-consumption validators pass;
* QEMU reports `pass`, blocker `none`, and all 40 markers exactly once;
* the three new markers occur between response copy-out and fixed-request
  completion;
* ELF evidence proves fixed phase/shadow geometry, two entries, response
  revalidation, exact record copy, clearing, and the fixed continuation;
* no later success marker exists on a failed response path;
* existing paging, privilege, CPU-state, capability, return, and halt evidence
  remains green;
* no persistent Ring 3 runtime, general syscall ABI, arbitrary pointer,
  process, compatibility, or production claim was added.
