# KOZO Invariants

Version: 1
Status: Authoritative
Scope: Non-negotiable technical truths that must remain valid across architecture, contracts, code, validation, and generated artifacts

---

# 1. Purpose

This document defines what must always remain true in KOZO.

Invariants are not preferences.

An invariant protects a system property that must not be broken by architecture changes, code changes, generated artifacts, validators, or documentation updates.

If an implementation cannot satisfy an invariant, the implementation must change or an explicit governance amendment must be made.

---

# 2. Authority

This document is subordinate to `docs/GOVERNANCE.md` and higher than architecture, contracts, coding style, validation details, generated artifact policy, compatibility policy, and diagrams.

If this document conflicts with `docs/GOVERNANCE.md`, governance wins.

If another document conflicts with this document, this document wins.

---

# 3. Non-Goals

This document does not explain every implementation detail.

This document does not define coding style.

This document does not define generated report format.

This document does not define every syscall.

This document does not define every validator.

This document does not define compatibility promises.

This document only defines what must remain true.

---

# 4. Runtime Authority Invariants

## 4.1 Kernel authority remains in the kernel

Kernel authority must remain inside the Odin kernel.

Userspace services may request kernel action only through explicit kernel interfaces.

Userspace services must not bypass kernel authority through shared mutable state, raw kernel pointers, or undocumented side channels.

---

## 4.2 Harness code is not runtime code

The Python harness is not part of the operating system runtime.

Harness code may validate, generate, summarize, and verify repository state.

Harness code must not be treated as kernel behavior.

Harness success does not prove production readiness.

---

## 4.3 Userspace services are not kernel authority

Rust userspace services may implement system services, runtime probes, or higher-level components.

Rust userspace code does not gain kernel authority by existing in the repository.

Kernel-facing Rust code must communicate through the KOZO ABI contract.

---

## 4.4 Kernel object pointers must not be exposed to userspace

Kernel object pointers must never be exposed as userspace authority.

Userspace must receive opaque identifiers, handles, or capability-like values.

Pointer forgery must not become an authority path.

---

## 4.5 Internal capabilities do not imply isolation

A same-address-space kernel capability may organize internal runtime behavior only within its explicit contract.

Its existence must not be described as a userspace boundary, privilege separation, authentication, sandboxing, process isolation, or hardware syscall enforcement.

---

# 5. Contract Invariants

## 5.1 System boundaries must be contract-backed

Every system boundary must be described by an explicit contract before it is treated as governed.

Examples:

* ABI boundary
* syscall boundary
* syscall table
* syscall class
* syscall catalog
* generated report surface

Undocumented behavior is not governed behavior.

---

## 5.2 The ABI contract owns ABI truth

ABI truth must come from checked-in ABI contracts and their governed manifests.

Generated bindings summarize ABI truth for language use.

Generated bindings must not become the source of ABI truth.

---

## 5.3 Generated bindings must not be edited directly

Generated ABI bindings must not be manually edited.

If a generated binding is wrong, fix the contract or generator.

Manual binding edits create ABI drift.

---

## 5.4 Generated reports are non-authoritative

Generated reports are review surfaces.

They do not own ABI truth, syscall truth, compatibility truth, architecture truth, or validation truth.

Examples:

* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`

Generated reports must be validated against their sources.

---

## 5.5 Catalogs summarize, but do not own, behavior

Catalogs provide a compact view of governed surfaces.

A catalog must be checked against authoritative contracts.

A catalog must not override ABI contracts, syscall contracts, class contracts, source code, or validators.

---

# 6. Syscall Invariants

## 6.1 Syscall selectors must use ABI constants

Syscall selectors in source code must use generated ABI constants.

Hardcoded syscall numeric values are forbidden in live syscall paths.

Good:

```odin
case abi.K_SYSCALL_STATUS:
```

Bad:

```odin
case 2:
```

---

## 6.2 Syscall behavior must match declared class

A syscall entry must obey its declared semantic class.

A `no_payload_status` syscall must not use a payload.

A `payload_mutating_status` syscall must use a declared payload layout and mutate only allowed fields.

Class drift is a contract violation.

---

## 6.3 No-payload syscalls must not mutate payload

A no-payload syscall must not mutate payload state.

A no-payload syscall must not require a payload layout.

A no-payload syscall must not depend on heartbeat payload sentinels.

---

## 6.4 Payload-mutating syscalls must declare mutation

A payload-mutating syscall must declare:

* payload layout
* request expectations
* response expectations
* allowed mutation fields
* invalid request behavior
* success return behavior

Mutation outside the declared fields is forbidden.

---

## 6.5 Unknown syscalls must fail deterministically

Unknown or unsupported syscall IDs must produce deterministic failure behavior.

The default path must not accidentally execute a handled branch.

The default path must not mutate payload state unless explicitly governed by a contract.

---

# 7. Memory and Pointer Invariants

## 7.1 Userspace pointers are untrusted

Every userspace pointer is untrusted.

Kernel code must validate pointer expectations before use.

A null pointer may be valid only when the syscall contract explicitly allows it.

---

## 7.2 Pointer expectations must match syscall class

A no-payload syscall must receive the contract-defined no-payload argument.

A payload syscall must receive the contract-defined payload pointer.

Kernel code must not infer pointer meaning outside the contract.

---

## 7.3 Kernel memory ownership must be explicit

Kernel memory ownership must be visible.

Hidden ownership transfer is forbidden.

Hidden allocation in boundary paths is forbidden unless an authoritative document explicitly permits it.

---

# 8. Capability and Security Invariants

## 8.1 Capabilities are opaque to userspace

Capabilities must not expose kernel object identity or kernel memory layout.

Userspace must not be able to forge authority by constructing raw values.

---

## 8.2 Capability validation occurs at the boundary

A syscall boundary must validate authority before privileged operation.

Capability checks must not be deferred past the point where unsafe action has already occurred.

---

## 8.3 Harness file-scope enforcement protects repository integrity

The harness must enforce scoped changes where task state declares allowed files.

A task must not silently modify unrelated files.

Step-scope enforcement prevents accidental governance drift.

---

# 9. Validation Invariants

## 9.1 Verification must fail closed

Verification must fail when required evidence is missing.

Verification must not silently pass because a tool, source file, generated artifact, or proof input is unavailable.

---

## 9.2 Validators must be deterministic

Validators must produce deterministic results for the same repository state.

Validators must not depend on network access.

Validators must not depend on hidden environment state.

Validators must not depend on wall-clock time unless time is passed as explicit input.

---

## 9.3 Registered validators require focused tests

Every registered validator must have a focused test file.

A validator without focused tests must not be registered.

---

## 9.4 Registered validators require marker-level negative coverage

Every registered validator must declare negative coverage markers.

Each marker must map to a behavioral negative test.

A negative-looking test name is not enough.

The test must invoke the validator or approved harness path and assert failure behavior.

---

## 9.5 Validators must name failed contract fields

Validator diagnostics must identify the failed field, rule, or surface.

Generic failure diagnostics are not acceptable for governed proof.

Good:

```json
{
  "reason": "missing_syscall_constant",
  "contract_field": "constants.syscalls.K_SYSCALL_STATUS"
}
```

Bad:

```json
{
  "reason": "invalid"
}
```

---

# 10. Generated Artifact Invariants

## 10.1 Generated artifacts must be reproducible

Generated artifacts must be reproducible from checked-in source truth.

A generated artifact that cannot be reproduced must not be trusted.

---

## 10.2 Generated artifacts must declare or imply their source

Every generated artifact must have a known source of truth.

Examples:

* `artifacts/latest_verify.json` comes from `scripts/verify.sh` and the harness aggregator.
* `docs/generated/syscall_surface.md` comes from syscall contracts and catalog.
* `docs/generated/abi_surface.md` comes from the ABI manifest.

---

## 10.3 Generated report drift must fail validation

If a generated report differs from deterministic renderer output, verification must fail.

Manual edits to generated reports must not pass validation.

---

# 11. Documentation Invariants

## 11.1 Diagrams are descriptive

Diagrams explain structure.

Diagrams do not define authority.

A diagram must not override governance documents, invariants, architecture, contracts, validators, or generated artifacts.

---

## 11.2 Changelog records changes but does not govern

`CHANGELOG.md` records completed changes.

It does not define system authority.

If the changelog conflicts with governance, governance wins.

---

## 11.3 README is introductory

`README.md` introduces the project.

It must not override governance, invariants, architecture, contracts, or validators.

---

# 12. Compatibility Invariants

## 12.1 No broad compatibility claim without evidence

KOZO must not claim broad compatibility without scoped evidence.

Forbidden claims include:

* KOZO is Linux compatible
* KOZO supports Linux applications
* KOZO is POSIX complete
* KOZO supports userspace execution
* KOZO supports a process model
* KOZO supports VFS behavior
* KOZO supports file descriptor behavior

A compatibility claim must name the exact behavior tested.

---

## 12.2 Verification is not production readiness

Passing verification does not make KOZO production ready.

Production readiness requires separate governance, threat analysis, testing, operational policy, and support model.

---

# 13. Coding and Review Invariants

## 13.1 Code must prefer explicit structure over cleverness

KOZO code must be inspectable.

Cleverness that hides authority, mutation, allocation, or failure behavior is not allowed.

---

## 13.2 Runtime behavior must not be hidden in generated reports

Generated reports may describe runtime behavior.

They must not define it.

Runtime behavior must be defined by contracts and implementation.

---

## 13.3 Tests must prove failure behavior

Tests must prove that invalid states fail.

A success-only test is not sufficient for governed behavior.

---

# 14. Amendment Rules

Changing an invariant is a governance-level event.

An invariant change requires:

* clear rationale
* review of affected governance documents
* review of affected contracts
* review of affected validators
* test updates
* changelog entry
* ADR when architecture, security, compatibility, or contract authority changes

Do not bypass an invariant by adding a lower-authority exception.

---

# 15. Relationship to Other Governance Documents

`GOVERNANCE.md` owns precedence and amendment process.

`ARCHITECTURE.md` explains system structure within these invariants.

`CONTRACTS.md` defines governed boundary sources within these invariants.

`CODING_STYLE.md` defines code construction within these invariants.

`VALIDATION.md` defines proof process within these invariants.

Generated reports, diagrams, changelog entries, and README text must not override these invariants.

---

# 16. Summary

KOZO must remain contract-backed, deterministic, capability-oriented, and validation-governed.

Kernel authority stays in the kernel.

Harness code stays out of runtime authority.

Generated reports stay non-authoritative.

Generated bindings stay generated.

Syscall behavior stays classed, contracted, and validated.

Validators stay covered by behavioral negative tests.

Compatibility claims stay scoped and evidence-backed.
