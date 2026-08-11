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

Before Odin entry, v0.8.3 replaces the inherited bootloader mapping root with
one KOZO-owned, fixed four-level hierarchy. A supervisor-only higher-half
kernel subtree preserves the loaded image and active stack. A separate
lower-half subtree maps one user RX code page and two user RW-NX pages for data
and a future stack. Construction, effective-permission walking, CR3 activation
and readback, and bounded survival remain assembly-owned. `docs/PAGING.md` and
`contracts/fixed_user_mapping_foundation.v0.json` own the detailed boundary.
No lower-privilege execution occurs.

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

The v0.7.5 controlled runtime loop is a bounded internal Odin operation inside the existing boot-owned address space. It uses static volatile state, fixed no-input marker bridges, exact internal statuses, and the existing assembly return-to-halt continuation. It is not a scheduler, event loop, userspace execution path, allocator, interrupt path, or production runtime.

The v0.8.0 first governed capability extends that same internal path as `runtime_progression_entry` → `controlled_runtime_loop` → `execute_first_governed_capability` → `dispatch_runtime_capability` → `query_runtime_status` → validated response → governed return. It accepts one fixed versioned request, dispatches one numeric identifier, reports only the accepted stage 0 through 5 baseline, and returns an exact status. It is a same-address-space kernel boundary, not a userspace, privilege, authentication, isolation, or hardware syscall boundary.

Before that Odin path, v0.8.1 extends the assembly bootstrap sequence as
memory evidence → CPUID feature validation → CR0/CR4 read-modify-write and
readback → x87/MXCSR initialization → bounded SSE2 survival probe → Odin entry.
This establishes the boot CPU state required by the allowed early Odin
instruction class. It does not establish AVX/XSAVE, per-task state ownership,
context switching, exception recovery, or complete CPU initialization.

v0.8.2 extends the accepted internal Odin path as controlled runtime loop →
runtime status query → bounded runtime state transition → governed return →
terminal halt. One direct dispatcher routes capability ID 1 to the unchanged
status query and capability ID 2 to one boot-owned READY/0-to-ACTIVE/1 state
transition. The second capability validates fixed request/response geometry,
performs volatile mutation and readback, and validates its response before
success. It does not create dynamic registration, arbitrary memory mutation,
userspace access, concurrency, authorization, privilege separation, or a
general state-machine subsystem.

---

# 13. Bounded Privilege Transition

v0.8.4 inserts one assembly-owned privilege probe between fixed mapping
survival and Odin runtime entry. A fixed GDT, TSS, and IDT establish one
`iretq` path to `user_privilege_probe_start` and one DPL3 `int 0x81` return
gate. The return gate switches through TSS.RSP0 to a dedicated
supervisor-only stack, validates the hardware-saved CPL3 frame and probe state,
and restores one fixed CPL0 continuation.

The path is layered as boot coordination, descriptor/table validation,
fixed-entry execution, return-frame validation, and terminal convergence. It
does not introduce a process model, general userspace, a public syscall ABI,
general interrupt handling, return to Ring 3, or isolation. Detailed authority
lives in `contracts/bounded_privilege_transition_probe_contract.v0.json` and
`docs/PRIVILEGE_TRANSITION.md`.

---

# 14. Fixed User Request Boundary

v0.8.5 extends the single fixed CPL3 excursion without adding a second
transition mechanism. The linked Ring3 stub writes one exact 40-byte request
inside the accepted user RW-NX page and invokes the existing `int 0x81` gate.
The Ring0 handler validates the hardware frame and both complete fixed spans,
copies into supervisor-only shadows, executes one deterministic service,
copies one exact 48-byte response back, validates readback, clears every
transaction buffer, and resumes only `privilege_ring0_continuation`.

This remains assembly-owned boot-probe behavior. It is not a public syscall
ABI, arbitrary user-pointer boundary, general copy framework, persistent
userspace runtime, process model, scheduler, isolation boundary, compatibility
claim, or production runtime. Authority lives in
`contracts/fixed_user_request_boundary_contract.v0.json`; detailed geometry and
evidence are described in `docs/USER_REQUEST_BOUNDARY.md`.

# 15. Bounded User Response Consumption

v0.8.6 extends the fixed transaction without adding a general dispatch path:

```text
fixed Ring 3 request
-> fixed Ring 0 service and response copy-out
-> sanitized iretq to fixed Ring 3 response consumer
-> complete response validation and fixed 48-byte record
-> second int 0x81
-> Ring 0 response revalidation and record acceptance
-> fixed Ring 0 continuation
-> Odin runtime
```

The kernel-owned phase selects exactly two handlers. Consumer RIP, RSP,
response address, record address, and lengths are fixed. No dynamic message,
arbitrary pointer, third Ring 3 transition, or persistent userspace runtime is
introduced.

# 16. Runtime-Ordered User Status Service

v0.8.7 moves the accepted one-shot Ring 3 transaction into the Odin runtime
sequence after the controlled loop. Odin collects one validated 64-byte
post-loop snapshot. The assembly transaction formats the fixed 88-byte user
response from that snapshot, and internal capability ID 1 formats its
unchanged response from the same source.

The fixed transaction returns to Odin before capabilities 1 and 2 execute.
The assembly halt loop remains the only terminal runtime state. The path adds
no general dispatcher, public syscall ABI, arbitrary pointer, persistent
userspace runtime, process model, or scheduler.

# 17. Defined Fixed User Execution Context Boundary

ADR 0018 defines, but does not implement, one future supervisor-owned context
around the accepted one-shot Ring 3 transaction. The context binds the current
fixed code, data, stack, entry, selectors, return vector, request identity, and
transaction phase to one opaque non-pointer identity.

The planned top-level path is context initialization and validation, `READY`,
activation immediately before the existing Ring 3 entry, `ACTIVE`, both
existing `int 0x81` returns, completed-transaction validation, `RETURNED`, one
result commit, authority clearing, verified `CLEARED`, and the unchanged Odin
continuation. The transition budget is two because those are the only two
returns in the accepted transaction.

The context and its result are separate internal kernel records. The context
owns mutable execution authority; the result records bounded outcome evidence
without identity or reusable authority. This boundary is not present in the
runtime yet and does not create a process, scheduler entity, public ABI,
repeated session, or hostile-code containment boundary.
