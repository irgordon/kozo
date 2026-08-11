# KOZO Fixed User Execution Context Phase Definition

Version: 1
Status: Defined
Implementation: Unauthorized
Scope: Selection and boundary definition for one kernel-owned user execution context

---

# 1. Purpose

Define one fixed, kernel-owned user execution context as KOZO's next product
capability after the accepted host-portability phase.

This document selects and bounds future work. It does not implement the
context, change runtime behavior, or authorize a version or release.

---

# 2. Problem Solved

KOZO can enter Ring 3, complete one fixed request and response transaction,
and return to Ring 0. The code page, data page, stack, selectors, transition
state, and return path are governed separately, but no single kernel-owned
identity binds them into one execution context with an explicit lifecycle.

Without that ownership boundary, repeated user execution, scheduling, or a
process model would have to rely on ambient constants and unrelated state.
That would make authority and cleanup difficult to validate.

A fixed execution context gives the kernel one place to answer:

* which user code and stack may run;
* which fixed transaction belongs to the execution;
* whether entry or return is valid in the current lifecycle state; and
* whether all authority was cleared before normal runtime continues.

The eventual user value is a controlled foundation for longer-lived user
services and applications. This phase does not provide those applications.

---

# 3. Selected Capability

Selected capability: **Fixed User Execution Context**.

The capability is one statically allocated, supervisor-only record that binds
the accepted user mapping, privilege transition, fixed transaction, and Ring 0
return to one opaque kernel-owned identity and one bounded lifecycle.

Exactly one context is in scope. It executes the existing one-shot user status
transaction once and is cleared before the existing Odin continuation.

---

# 4. Why This Capability Is Next

The roadmap has already proven fixed user mappings, a bounded Ring 3
transition, a fixed request and response, Ring 3 response consumption, and a
governed Ring 0 return. The phase map leaves `USERSPACE_PLANNING` as the next
planned boundary and forbids jumping from planning to general user execution.

A fixed execution context uses all accepted prerequisites without requiring a
frame allocator, timer, scheduler, executable loader, or process model. It
also establishes the ownership boundary those later capabilities would need.

Selecting a repeated user session first would hide context identity and
lifecycle inside a larger behavior change. Selecting scheduling or processes
first would require several missing independent subsystems.

---

# 5. Alternatives Considered

| Candidate | Readiness | System value | User value | Scope risk | Decision |
| --- | --- | --- | --- | --- | --- |
| Fixed user execution context | Existing fixed mappings, transition, transaction, and return are sufficient. | Establishes explicit identity, ownership, lifecycle, and cleanup for user execution. | Enables later bounded sessions and service execution. | Low to moderate. | Selected. |
| Bounded repeated user session | The transition can be reused, but no owned execution identity or lifecycle exists. | Proves more than one transaction. | Moves toward persistent services. | Would hide the missing context boundary. | Deferred until the selected capability is proven. |
| Bounded timer interrupt | Descriptor tables exist, but interrupt-controller, timer, and asynchronous state ownership are absent. | Establishes asynchronous kernel events. | Enables later timing and preemption. | Moderate and independent of the immediate user-boundary gap. | Deferred. |
| Fixed physical-frame allocator | Current fixed context requires no dynamic memory. Physical discovery and allocation policy remain absent. | Enables dynamic mappings. | Supports later process and loader work. | High authority and resource-policy expansion. | Deferred until a selected capability requires it. |
| Process, scheduler, or executable loader | Multiple prerequisites are missing. | Provides broader OS behavior. | Direct application value. | Unacceptably bundles identity, memory, execution, and lifecycle policy. | Rejected as the next phase. |

---

# 6. Capability Boundary

## Inputs

The future capability may consume only already governed kernel facts:

* fixed user code, data, and stack geometry;
* validated paging permissions;
* validated GDT, TSS, IDT, selectors, and Ring 0 return stack;
* fixed request, response, and consumption-record geometry;
* the kernel-owned transaction phase; and
* the existing runtime-status snapshot required by the fixed service.

No user-selected pointer, length, mapping, selector, entry point, service ID,
or context identity is accepted.

## Outputs

The capability returns one explicit kernel status indicating either complete
context lifecycle success or a named validation failure. Success requires the
existing fixed transaction to complete and all context-owned state to be
cleared before Odin continuation.

## Authority

Ring 0 exclusively creates, mutates, validates, and clears the context.
Context identity is opaque and must not encode or expose a kernel pointer.

## Owned State

The context owns only:

* format version and size;
* one nonzero opaque identity;
* one lifecycle state;
* bindings to the accepted fixed user regions and transition policy;
* a fixed transition budget and observed transition count;
* association with the accepted fixed transaction phase; and
* reserved fields required to remain zero.

Exact field geometry belongs to a future contract.

## State Not Owned

The context does not own page allocation, general page tables, CPU scheduling,
interrupt-controller state, process identifiers, files, devices, persistent
storage, dynamic capabilities, or arbitrary user memory.

## Interfaces

The future top-level path should remain readable as:

```text
initialize fixed context
validate fixed context
begin existing Ring 3 transaction
validate context at each privilege return
complete existing transaction
clear and validate context
continue existing Odin runtime
```

## Trust Boundary

The supervisor-only context is trusted only after validation. User-writable
pages and user-influenced return state remain untrusted at every crossing.
The existing fixed tables, linker geometry, and contract-defined constants are
trusted dependencies only after their existing validators pass.

---

# 7. Explicit Non-Goals

This capability does not provide:

* repeated or persistent Ring 3 sessions;
* multiple contexts, processes, or address spaces;
* scheduling, preemption, timers, or context switching;
* dynamic mappings, frame allocation, heap allocation, or page-fault recovery;
* arbitrary user code, pointers, lengths, entry points, or stacks;
* a general service dispatcher or public syscall ABI;
* authentication, delegation, inter-process communication, or authorization;
* executable loading, filesystems, drivers, networking, Linux, or POSIX;
* hostile-code containment, exception recovery, or production readiness.

---

# 8. Existing Invariants Preserved

The future implementation must preserve:

* governance precedence and contract authority;
* fail-closed validation and success-marker exclusion after failure;
* the accepted ADR 0017 host-portability matrix;
* committed Git blobs as release-input authority;
* separate build-host and runtime-host evidence;
* supervisor-only kernel mappings and user-page W^X policy;
* the existing fixed request, response, and consumption boundary;
* the current internal capability IDs and response geometry;
* the current ABI and syscall surfaces unless separately authorized;
* immutable v1.0.1, v1.0.0, and v1.0.0-rc.1 release records;
* the terminal Ring 0 halt path; and
* the resource-scaling rule that correctness cannot depend on a developer
  workstation's CPU, memory, or storage capacity.

---

# 9. New Capability Invariants

1. Exactly one fixed user execution context exists.
2. The context record is supervisor-only, fixed-size, and statically allocated.
3. Context identity is nonzero, opaque, kernel-created, and never a pointer.
4. User mode cannot create, select, replace, or mutate context authority.
5. The lifecycle advances only through `UNINITIALIZED`, `READY`, `ACTIVE`,
   `RETURNED`, and `CLEARED` in that order.
6. `ACTIVE` covers the complete accepted two-entry transaction; the existing
   transaction phase remains the subordinate request/response state.
7. Entry requires exact context identity, state, geometry, selectors,
   transition budget, and zero reserved fields.
8. Every Ring 0 return revalidates the context and the existing hardware frame.
9. The transition count never exceeds the contract-defined fixed budget.
10. Context bindings cannot expand the current user mappings or permissions.
11. No kernel pointer or physical address becomes user-visible.
12. Success requires verified clearing of context-owned transient state.
13. Invalid or partially initialized context state cannot enter Ring 3.
14. Failure after Ring 3 entry cannot resume normal Odin execution.

---

# 10. Minimum Usable Behavior

The minimum accepted implementation must:

1. Clear one static supervisor-only context record.
2. Populate it from the accepted fixed geometry and policy.
3. Validate every field before the first `iretq`.
4. Move the lifecycle from `READY` to `ACTIVE` exactly once.
5. Associate both accepted `int 0x81` returns with the same context.
6. Enforce the fixed transition budget.
7. Move the lifecycle to `RETURNED` only after complete response consumption.
8. Clear all transient context state and verify `CLEARED` before Odin resumes.
9. Return an explicit success status through the existing Ring 0 continuation.
10. Preserve the existing one-shot runtime-status response and all later
    internal capability behavior.

Future expansion may add repeated sessions, multiple contexts, scheduling, or
dynamic memory only through separate governed phases.

---

# 11. Failure Behavior

| Failure | Required behavior |
| --- | --- |
| Invalid input or geometry | Reject before Ring 3 entry and emit no later success evidence. |
| Invalid lifecycle or transaction state | Return a fixed error before entry, or converge on the existing terminal fault path after entry. |
| Identity mismatch | Reject; never substitute another context or infer identity from an address. |
| Transition-budget exhaustion | Reject before another privilege transition. |
| Missing dependency | Fail build or validation; do not bypass the dependency. |
| Partial initialization | Clear what can be cleared, validate cleanup, and do not enter Ring 3. |
| Unexpected Ring 3 return | Use the existing fail-closed fault/return containment and do not enter Odin. |
| Corrupted active context | Emit no completion success and converge on terminal halt. |
| Cleanup failure | Return no context success and do not continue normal runtime. |
| Timeout | No internal wait is allowed; the existing bounded QEMU timeout remains evidence policy, not capability success. |

Static allocation means dynamic resource exhaustion is not part of the minimum
path. A busy or already-active context is an invalid state and fails closed.

---

# 12. Security and Trust Boundary

The design follows deny-by-default Zero Trust and defense-in-depth (DiD)
rules:

* identity and authority are explicit rather than inferred from an address;
* Ring 0 owns all authority-bearing state;
* every privilege crossing validates both the execution context and the
  existing hardware frame;
* user-writable data remains untrusted even when it contains an expected value;
* context validation does not replace mapping, frame, transaction, or response
  validation; and
* cleanup removes stale authority before the kernel continues.

The fixed exception sinks remain fail-closed containment for this bounded
path. They do not establish exception recovery, diagnostic completeness, or
safe execution of arbitrary hostile user code.

---

# 13. Resource Implications

## CPU

The minimum path requires no additional CPU, core, timer, or instruction-set
feature. It adds a bounded number of state transitions and comparisons around
the existing transaction.

## RAM

One small static supervisor-only record is expected. No heap, frame allocator,
additional user page, or dynamic page-table page is allowed.

## Storage

No persistent state or new runtime storage is required. Source, tests, and
proof may increase repository and release-bundle size modestly.

No numeric guest minimum is defined by this phase. Implementation validation
must measure context size, kernel ELF growth, stack impact, and bounded QEMU
runtime. More host or guest resources must not change correctness.

---

# 14. Host-Build Implications

The accepted ADR 0017 matrix remains required:

| Host | Build requirement | Runtime requirement | Required evidence level |
| --- | --- | --- | --- |
| Linux / `ubuntu-24.04` | Build and all context contracts, tests, source checks, and ELF tooling pass. | Governed QEMU execution required. | `VALIDATED_RUNTIME` |
| Windows / `windows-2025` Git Bash | Build and all portable context contracts and tests pass. Host-path and tool-output differences remain normalized at governed boundaries. | `NOT_EXECUTED` | `VALIDATED_BUILD` |
| macOS / `macos-15` | Build and all portable context contracts and tests pass without Homebrew-path assumptions. | `NOT_EXECUTED` | `VALIDATED_BUILD` |

No new external build dependency is expected. If implementation requires one,
the authorization task must define acquisition, versioning, and all three host
paths before code is accepted.

---

# 15. Runtime-Host Implications

Linux remains the only required runtime-validation host. The selected
capability is x86-64 guest behavior and does not require Windows or macOS QEMU
claims.

Windows and macOS runtime status remains `NOT_EXECUTED`. Build success must not
be reported as guest-runtime success.

---

# 16. Testing Requirements

Future implementation requires focused evidence for:

* contract and schema validity;
* context initialization and exact field validation;
* every allowed lifecycle transition;
* every forbidden skipped, repeated, or backward transition;
* opaque identity mismatch and pointer-like identity rejection;
* fixed geometry, selector, reserved-field, and transition-budget failures;
* association with both existing Ring 3 returns;
* cleanup and zero-state validation;
* unchanged user response and internal capability behavior;
* fail-closed behavior after partial initialization and active-state failure;
* source and ELF ordering around `iretq`, both `int 0x81` entries, return, and
  halt;
* all three pinned build hosts; and
* Linux QEMU execution through the complete existing marker sequence.

Every new logic branch requires focused positive or negative evidence.

---

# 17. Existing Governed Baseline

Implementation must retain every currently passing check. The accepted
baseline is:

* Python: 1,136 tests;
* governed verification: 67 checks, 0 failures;
* QEMU: pass;
* blocker: none;
* runtime markers: 41 ordered; and
* final marker: `KOZO_RUNTIME_RETURN_OK`.

New focused tests and validators may raise counts. They may not remove or
weaken existing coverage to preserve a number.

---

# 18. Marker and Evidence Impact

No marker change is required.

The existing `KOZO_RING3_ENTER`, fixed transaction markers,
`KOZO_RING0_RETURN_OK`, later capability markers, and final runtime marker can
bound the context lifecycle. A new contract and evidence validator must prove
that context initialization, transitions, return validation, and cleanup
dominate those existing success points in source and ELF control flow.

The 41-marker taxonomy remains unchanged by both this selection task and the
minimum future implementation. Any later design that needs new markers or
changes marker meaning requires separate authorization.

---

# 19. Hosted Acceptance Evidence

Future implementation acceptance requires:

* CI success and lint success;
* the pinned Linux, Windows, and macOS build contracts passing;
* all 67 existing verification checks still passing plus the new context
  contract and evidence checks;
* Linux QEMU pass, blocker none, all 41 markers ordered, and final
  `KOZO_RUNTIME_RETURN_OK`;
* context contract, schema, source, ELF, lifecycle, cleanup, and failure
  evidence passing;
* the existing paging, privilege, request, response, status-service,
  capability, and halt validators passing unchanged;
* `latest_verify.json` valid and aggregate serialization tested; and
* no new macOS or Windows runtime claim.

---

# 20. Release Impact Classification

Current published release: `v1.0.1`.

Likely eventual release class: minor.

Reason: the capability would add a new runtime ownership and lifecycle
boundary without repairing a released defect.

Version assignment is deferred to separate authorization. This definition
does not authorize `v1.1.0`, any patch release, or publication.

---

# 21. Prerequisites

Before implementation changes architecture or security authority:

1. Adopt an ADR for fixed execution-context identity, ownership, lifecycle,
   and its relationship to the existing transaction phase.
2. Authorize a fixed execution-context contract, schema, validators, focused
   tests, and ELF evidence.
3. Update the runtime progression stage authority so the planned
   `USERSPACE_PLANNING` boundary can name this capability without implying
   general userspace execution.

These are governance and evidence prerequisites, not independent product
capabilities. They may be included at the start of one separately authorized
implementation task, in governance-first order.

No marker-taxonomy change, new external dependency, resource study, or prior
runtime capability is required.

---

# 22. Governance Review

| Authority | Result | Rationale |
| --- | --- | --- |
| `docs/ROADMAP.md` | Consistent | The selection advances the proven fixed user boundary without claiming deferred general userspace. |
| `docs/PHASEMAP.md` | Consistent with prerequisite | The next planned stage is userspace planning; its contract authority must be updated before implementation. |
| `docs/GOVERNANCE.md` | Consistent | This task changes planning state only and leaves higher authority unchanged. |
| `docs/INVARIANTS.md` | Consistent | Fail-closed, security, portability, runtime, and release invariants remain intact. |
| `docs/VALIDATION.md` | Consistent with prerequisite | Future behavior requires contract, source, ELF, negative, and runtime evidence. |
| `docs/COMPATIBILITY.md` | Consistent | No general userspace, process, or host-runtime claim is added. |
| `docs/ARCHITECTURE.md` | ADR required before implementation | A new runtime ownership record must be adopted before architecture text changes. |
| `docs/SECURITY_MODEL.md` | ADR required before implementation | Explicit context identity and lifecycle add authority checks at the existing privilege boundary. |
| ADR 0017 | Consistent | All three build hosts remain required and runtime evidence stays separate. |

Governance-conflict classification: `ADR_REQUIRED` before implementation.
The phase definition itself is not blocked because the ADR is not an
independent product capability.

---

# 23. Authorization Boundary

Phase 0 Host Portability: accepted.

Selected capability: Fixed User Execution Context.

Phase definition: complete.

Implementation authorized: false.

Version change authorized: false.

Release authorized: false.

Current release: `v1.0.1`.

Next action: a separate explicit implementation-authorization task using this
definition as authority and completing the governance prerequisites before
runtime mutation.
