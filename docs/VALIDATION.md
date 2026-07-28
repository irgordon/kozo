# KOZO Validation

Version: 1
Status: Authoritative
Scope: Harness, validator, verification, evidence, and proof-state rules

---

# 1. Purpose

This document defines how KOZO verifies repository state.

Validation proves that source files, contracts, generated artifacts, task state, schemas, and evidence agree for the current development state.

---

# 2. Authority

This document owns harness and verification process rules.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, and `docs/CONTRACTS.md`.

It does not own ABI truth, syscall semantics, runtime architecture, coding style, compatibility claims, or generated-file edit policy.

---

# 3. Non-Goals

Validation passing is not production readiness.

The harness is not runtime code.

This document does not define kernel behavior.

This document does not make generated artifacts authoritative.

This document does not claim Linux compatibility.

---

# 4. Verification Entry Point

`scripts/verify.sh` is the full verification entry point.

It runs the governed validation pipeline, refreshes proof evidence, and writes `artifacts/latest_verify.json`.

Focused tests should run before full verification when source or validator behavior changes.

---

# 5. Rules

The harness is not runtime.

Verification passing is not production readiness.

Validators must be deterministic.

Validators must fail closed.

Missing proof input must fail unless explicitly governed.

Generated proof state must be refreshed only after focused source checks pass.

---

# 6. Latest Verification Artifact

`artifacts/latest_verify.json` is generated proof state.

It records the most recent full verification result.

It is authoritative only as generated evidence for the current tree after `scripts/verify.sh` reproduces it.

It does not override source files, contracts, validators, or governance documents.

---

# 7. Validator Registry

`harness/registry.py` owns canonical validator names, subsystems, status labels, artifact version, and validator order.

`harness/validators.py` must register validators in canonical order.

Registry order is part of the proof surface. A validator must not be inserted casually or outside the governed order.

---

# 8. Validator Registration Requirements

A registered validator must have:

* canonical name
* canonical subsystem
* deterministic behavior
* focused test file
* behavioral negative-path coverage
* marker-level negative coverage metadata
* diagnostics that identify failed fields or surfaces

Missing proof input must fail unless a higher-authority document explicitly governs a scoped exception.

---

# 9. Coverage Governance

Validator coverage governance requires every registered validator to have focused tests.

Coverage-depth governance requires declared negative markers to map to concrete test functions.

A valid negative test must invoke the validator or approved harness path, provide bad input or bad source state, assert failure behavior, and check diagnostic quality where practical.

Negative-looking function names are not enough.

---

# 10. Generated Report Drift Validation

Generated reports must match deterministic renderer output.

If a generated report is stale, manually edited, or missing required source-derived content, validation must fail.

Current generated report validators include:

* `syscall_surface_report`
* `abi_surface_report`

Current runtime evidence and runtime contract validators include:

* `runtime_smoke_evidence`
* `qemu_smoke_evidence`
* `runtime_evidence_taxonomy`
* `runtime_halt_contract`
* `runtime_progression_contract`
* `runtime_progression_entry_contract`
* `runtime_progression_stages`
* `stack_initialization_evidence_contract`
* `stack_initialization_evidence`
* `memory_initialization_evidence_contract`
* `memory_initialization_evidence`
* `runtime_progression_evidence`
* `controlled_runtime_loop_contract`
* `controlled_runtime_loop_evidence`
* `first_governed_runtime_capability`
* `first_governed_runtime_capability_evidence`
* `runtime_state_transition_capability`
* `runtime_state_transition_capability_evidence`
* `fixed_user_mapping_foundation`
* `fixed_user_mapping_foundation_evidence`
* `bounded_privilege_transition_probe_contract`
* `bounded_privilege_transition_probe_evidence`
* `fixed_user_request_boundary_contract`
* `fixed_user_request_boundary_evidence`

`runtime_progression_stages` performs graph-level validation. It rejects direct and indirect cycles, duplicate identifiers and names, unknown references, forward prerequisites, proven stages with unproven mandatory prerequisites, backward or skipped transitions, unknown contract or validator authorities, and transitions with missing or multiple owners. The traversal is deterministic and contract order remains authoritative.

`memory_initialization_evidence_contract` validates the implemented memory proof specification. `memory_initialization_evidence` separately validates assembly region geometry, exact full-region zero fill, bounded 64-bit probe and restoration order, marker placement, terminal halt structure, and passing QEMU metadata/log alignment or an allowed local tooling blocker.

`runtime_progression_entry_contract` validates the internal calling convention, fixed bootstrap context, bounded Odin operation, marker ownership, exact return boundary, and preserved halt authority. `runtime_progression_evidence` separately validates source ordering, linked symbols, stage status, QEMU metadata/log agreement, and the terminal halt continuation. Only passing QEMU evidence can promote the implemented runtime stages to proven.

`controlled_runtime_loop_contract` validates the three-iteration state model, deterministic accumulator, marker order, exact statuses, transition ownership, and terminal continuation. `controlled_runtime_loop_evidence` separately validates volatile source operations, failure-before-success ordering, fixed marker bridges, linked symbols, retained ELF backward branch, terminal comparison, stage status, QEMU metadata/log agreement, and the unchanged halt path. Hosted QEMU evidence is required before `CONTROLLED_RUNTIME_LOOP` becomes proven.

`first_governed_runtime_capability` validates capability identity, fixed request and response geometry, stage-mask meaning, status values, marker boundaries, transition ownership, claim limits, and halt continuation. `first_governed_runtime_capability_evidence` separately validates top-down source ordering, request and response defense, explicit dispatch, response population and validation, success-marker exclusion from failure paths, fixed bridges, linked symbols and call edge, stage state, and QEMU metadata/log agreement. Hosted QEMU evidence is required before `FIRST_GOVERNED_RUNTIME_CAPABILITY` becomes proven.

`runtime_state_transition_capability` validates capability ID 2, fixed request,
response, and state geometry, the sole READY/0-to-ACTIVE/1 transition, status
stability, volatile-readback and rollback policy, marker ownership, claims, and
halt authority. `runtime_state_transition_capability_evidence` separately
validates explicit state initialization, overflow-safe request geometry,
direct dispatcher routing, volatile mutation/readback, response validation,
fixed bridges, focused ELF symbols and call edges, full QEMU marker order, and
the existing return-to-halt continuation. Hosted QEMU evidence is required for
phase acceptance.

`fixed_user_mapping_foundation` validates the authoritative fixed paging
geometry and permission policy. `fixed_user_mapping_foundation_evidence`
separately validates source ordering, table clearing, upper-level U/S, NX and
W^X, CR3 readback, fixed software walking, survival probes, ELF symbols and
geometry, absence of privilege-transition instructions, and full QEMU marker
agreement.

---

# 11. Evidence and Logs

Evidence files must resolve on disk when declared.

Current evidence outputs include:

* `artifacts/logs/odin-check.log`
* `artifacts/logs/odin-build.log`
* `artifacts/logs/cargo-check.log`
* `artifacts/logs/nm-kernel.log`

Missing evidence must fail closed unless explicitly governed.

---

# 12. Artifact Refresh Rules

Generated proof state changes must be reviewed separately from source changes when practical.

Normal flow:

1. Apply source, document, contract, or validator changes.
2. Run focused checks.
3. Commit source changes.
4. Run `scripts/verify.sh`.
5. Inspect generated artifact diffs.
6. Commit generated proof-state refresh separately if changed.

---

# 13. Fail-Closed Behavior

Validators must fail closed.

They must not pass because:

* a file is missing
* a tool did not run
* source text could not be loaded
* a generated report was absent
* a proof input was unavailable
* a diagnostic could not be produced

---

# 14. Determinism

Validators must be deterministic for the same repository state.

Validators must not depend on network access, hidden environment state, random ordering, or wall-clock time unless that value is explicit input.

---

# 15. Relationship to Other Governance Documents

`CONTRACTS.md` owns contract authority.

`GENERATED_ARTIFACTS.md` owns generated-file edit policy.

`CODING_STYLE.md` owns validator code shape.

`INVARIANTS.md` owns validation invariants.

`GOVERNANCE.md` owns conflict resolution.

---

# 16. CPU Extended-State Validation

`cpu_extended_state_initialization_contract` validates the authoritative
feature, control-register, x87, MXCSR, SIMD, marker, failure, and non-goal
policy. `cpu_extended_state_initialization_evidence` then validates source
ordering, ELF symbols and instructions, bounded probe geometry, AVX
prohibition, QEMU marker evidence, and halt convergence.

Source strings or generated reports alone cannot promote the runtime claim.
Hosted QEMU and verification evidence are required for phase acceptance.

---

# 17. Bounded Privilege-Transition Validation

`bounded_privilege_transition_probe_contract` validates contract/schema
geometry, fixed selectors, entry and return mechanisms, marker order, failure
statuses, claim boundary, and non-goals.

`bounded_privilege_transition_probe_evidence` validates source sequencing,
fixed mapping prerequisites, descriptor and stack ownership, linked symbols,
`iretq` and `int 0x81` paths, saved-frame/token checks, fixed continuation,
fault-to-halt convergence, QEMU metadata/log agreement, the unchanged Odin
capability suffix, and terminal halt preservation.

Marker strings alone are insufficient. Final acceptance requires hosted QEMU
evidence that the full ordered sequence executed.

---

# 18. Fixed User Request Boundary Validation

`fixed_user_request_boundary_contract` validates the exact 40-byte request,
48-byte response, fixed user spans, supervisor shadows, deterministic service,
copy sequence, clearing, marker order, statuses, and non-goals.

`fixed_user_request_boundary_evidence` separately validates Ring3 request
construction, frame and complete-span defense, exact copy-in/service/copy-out
and readback order, buffer zeroing, linked geometry, QEMU agreement, fixed
continuation, and failure exclusion.

Marker strings alone are insufficient. Final acceptance requires hosted QEMU
evidence that the complete boundary sequence executed while the accepted
privilege, capability, runtime-return, and halt validators remained green.

# 19. Bounded User Response Consumption Validation

The contract validator owns exact phase values, response and record geometry,
resume-frame policy, response checks, second-frame checks, record copy and
validation, clearing, phase reset, markers, statuses, and claim boundaries.

The evidence validator separately checks assembly order, linker assertions,
ELF symbols and operations, two transition and entry sites, QEMU metadata/log
agreement, exact marker multiplicity, failure exclusions, and terminal halt
convergence. Every diagnostic includes `reason` and `contract_field`.

# 20. Fixed User Runtime Status Validation

`fixed_user_runtime_status_service_contract` validates request ID `2`, request
and response geometry, snapshot fields, seven feature bits, service order,
digest policy, cleanup, markers, failures, claim boundary, and non-goals.

`fixed_user_runtime_status_service_evidence` validates one shared Odin
collector, the unchanged internal response, post-loop transaction order,
complete assembly formatting and validation, linked snapshot/shadow geometry,
Ring 3 comparisons, Ring 0 revalidation, XOR digest, cleanup, 41-marker
metadata/log agreement, failure exclusion, and halt preservation. Every
failure reports `reason` and `contract_field`.
