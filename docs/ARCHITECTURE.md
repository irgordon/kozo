# KOZO Architecture

Version: 1
Status: Authoritative
Scope: System structure, layer responsibilities, and high-level runtime boundaries

---

# 1. Purpose

This document defines KOZO system structure.

It owns the architectural shape of the repository and the responsibility boundaries between runtime layers and development-time validation.

---

# 2. Authority

This document owns architecture structure only.

It is subordinate to `docs/GOVERNANCE.md` and `docs/INVARIANTS.md`.

It does not own coding style, ABI truth, syscall semantics, generated artifact policy, compatibility claims, security boundary details, validation mechanics, or ADR rules.

---

# 3. Non-Goals

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim production readiness.

This document does not define a monolithic or NT-style architecture.

This document does not make diagrams or generated reports authoritative.

---

# 4. Architectural Model

KOZO is currently governed as a capability-oriented microkernel operating system.

The current repository is organized around three primary layers:

1. Odin kernel
2. Rust userspace services
3. Python harness and validation

Runtime authority belongs to runtime implementation and contracts, not to generated reports or the Python harness.

---

# 5. Odin Kernel Layer

Location:

```text
kernel/
```

The Odin kernel owns kernel-side runtime authority.

It is responsible for the currently implemented kernel entry and syscall dispatch surfaces that are backed by contracts and validators.

The kernel must use ABI constants for governed syscall selectors and must follow declared syscall contracts.

The current boot-to-runtime boundary is an internal System V AMD64 C call from `_start` to the exported Odin symbol `runtime_progression_entry`. Assembly supplies a fixed, versioned bootstrap context after controlled stack and memory evidence. Odin validates that context, performs one bounded static-state probe, emits runtime-initialization evidence through a fixed serial bridge, returns an exact status, and yields to the authoritative assembly halt path.

This boundary proves only a bounded language-level call when passing QEMU evidence captures its markers. It is not a userspace ABI, security boundary, allocator, scheduler, interrupt path, dynamic runtime initialization path, or complete Odin runtime.

Security boundary details are owned by `docs/SECURITY_MODEL.md`.

---

# 6. Rust Userspace Services Layer

Location:

```text
userspace/
```

Rust userspace services are kernel clients and service implementations.

They are not kernel authority.

Kernel-facing Rust code must use generated ABI constants and cross governed boundaries through the declared ABI.

The presence of Rust userspace code does not imply general userspace execution support, process model behavior, Linux compatibility, or production readiness.

---

# 7. Python Harness and Validation Layer

Locations:

```text
harness/
scripts/
tests/
schemas/
```

The Python harness validates repository state during development.

The harness is not part of the operating system runtime.

It enforces schemas, validators, generated report drift checks, artifact evidence checks, and task governance.

Harness details are owned by `docs/VALIDATION.md`.

---

# 8. Contracts Boundary

System boundaries must be contract-backed.

Contract files live under:

```text
contracts/
```

The authoritative ABI contract is:

```text
contracts/kozo_abi.h
```

Contract authority and contract roles are owned by `docs/CONTRACTS.md`.

---

# 9. Generated Surfaces

Generated bindings and reports are derived surfaces.

Generated ABI bindings support language use and must not be edited directly.

Generated reports under `docs/generated/` are review surfaces, not sources of truth.

Generated artifact policy is owned by `docs/GENERATED_ARTIFACTS.md`.

---

# 10. Architecture Diagram

`docs/ARCHITECTURE_DIAGRAM.md` is descriptive and non-authoritative.

It may explain the architecture visually, but it must not override this document or any higher-authority governance document.

---

# 11. Related Governance Documents

| Document | Owns |
| --- | --- |
| `docs/GOVERNANCE.md` | precedence, conflicts, amendments |
| `docs/INVARIANTS.md` | non-negotiable technical truths |
| `docs/CONTRACTS.md` | contract authority |
| `docs/CODING_STYLE.md` | code construction rules |
| `docs/VALIDATION.md` | harness and verification process |
| `docs/GENERATED_ARTIFACTS.md` | generated-file policy |
| `docs/COMPATIBILITY.md` | compatibility claims and non-goals |
| `docs/SECURITY_MODEL.md` | capability and trust-boundary rules |
| `docs/ADR_POLICY.md` | decision-record requirements |

---

# 12. Summary

KOZO architecture is currently governed as a capability-oriented microkernel with an Odin kernel, Rust userspace services, and Python validation harness.

The kernel is runtime authority.

Rust userspace is a kernel client layer.

The Python harness is development-time validation only.

Contracts define boundaries.

Generated reports and diagrams explain but do not govern.
