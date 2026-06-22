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
