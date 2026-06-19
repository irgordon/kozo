# KOZO Generated Artifacts

Version: 1
Status: Authoritative
Scope: Generated-file edit policy, refresh rules, and drift validation

---

# 1. Purpose

This document defines how generated files are treated in KOZO.

Generated artifacts improve reviewability and language interoperability, but they do not replace their sources of truth.

---

# 2. Authority

This document owns generated-file edit policy.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, and `docs/VALIDATION.md`.

It does not own ABI truth, syscall semantics, compatibility claims, or validator implementation details.

---

# 3. Non-Goals

This document does not define ABI constants.

This document does not define syscall behavior.

This document does not make generated reports authoritative.

This document does not claim production readiness.

---

# 4. Artifact Table

| Artifact path | Source of truth | Generator | Validator or drift check | Manual edits allowed | Refresh command |
| --- | --- | --- | --- | --- | --- |
| `artifacts/latest_verify.json` | validators, task state, evidence logs | `scripts/verify.sh` | schema, harness aggregator, evidence validator | No | `scripts/verify.sh` |
| `docs/generated/syscall_surface.md` | syscall catalog, table contract, class contract, ABI manifest | `harness.syscall_surface_report.write_report()` | `syscall_surface_report` | No | `python3 -c 'from harness.syscall_surface_report import write_report; write_report()'` |
| `docs/generated/abi_surface.md` | ABI manifest | `harness.abi_surface_report.write_report()` | `abi_surface_report` | No | `python3 -c 'from harness.abi_surface_report import write_report; write_report()'` |
| `docs/generated/governance_index.md` | checked-in contracts, schemas, validator registry, latest verification artifact, generated reports, and `CHANGELOG.md` | `harness/governance_index_report.py` | `governance_index_report` | No | Regenerate through the governed report renderer and run `scripts/verify.sh` |
| `bindings/rust/kozo_abi.rs` | `contracts/kozo_abi.h` and governed ABI generation flow | ABI binding generator | ABI and layout validators | No | Use the governed ABI generation command |
| `bindings/odin/kozo_abi.odin` | `contracts/kozo_abi.h` and governed ABI generation flow | ABI binding generator | ABI and layout validators | No | Use the governed ABI generation command |

---

# 5. Rules

Generated files must be reproducible.

Generated reports are non-authoritative.

Generated bindings are not manually edited.

If a generated artifact is stale, regenerate it from its source of truth.

If regeneration produces unexpected changes, inspect the source of truth and validator results before committing.

---

# 6. Generated Reports

Generated Markdown reports are review surfaces.

They summarize contracts and manifests for humans.

They do not own ABI truth, syscall truth, compatibility truth, architecture truth, or validation truth.

Stale generated report content must fail validation.

---

# 7. Generated Bindings

Generated Rust and Odin ABI bindings exist for language use.

They must not be edited directly.

If a generated binding is wrong, fix the contract or generator path.

---

# 8. Proof Artifacts

`artifacts/latest_verify.json` records generated verification state.

It should be refreshed only after source and focused tests pass.

Generated proof-state changes should be committed separately from source changes when practical.

---

# 9. Relationship to Other Governance Documents

`CONTRACTS.md` owns source truth.

`VALIDATION.md` owns verification process.

`INVARIANTS.md` owns generated artifact invariants.

`GOVERNANCE.md` owns precedence and conflict resolution.
