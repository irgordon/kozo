# KOZO Security Model

Version: 1
Status: Authoritative
Scope: Capability rules, trust boundaries, pointer exposure, and development-time proof controls

---

# 1. Purpose

This document defines KOZO security boundary rules.

It separates runtime security assumptions from development-time harness governance.

---

# 2. Authority

This document owns capability and trust-boundary rules.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, and `docs/ARCHITECTURE.md`.

It does not define coding style, validator registration mechanics, generated artifact policy, or compatibility claims.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim formal verification.

This document does not define every syscall.

This document does not define validator implementation details.

This document does not claim Linux compatibility.

---

# 4. Capability Model

KOZO is governed as capability-oriented.

Authority should be represented as explicit capability-like values or opaque handles rather than exposed kernel pointers.

A capability must be validated before privileged action.

---

# 5. Rules

Kernel object pointers must not be exposed to userspace.

Userspace pointers are untrusted.

Capability-like authority must be validated at the boundary.

No-payload syscalls must not dereference or mutate payload state.

Payload syscalls must mutate only contract-allowed fields.

Development-time proof validation must not be confused with runtime security enforcement.

The v0.7.45 bootstrap context is an internal same-address-space assembly-to-Odin input. Odin validates its version, size, reserved fields, stack range, and memory range before using it, but this validation does not create a privilege boundary or userspace ABI. The fixed serial bridge accepts no caller-controlled string or length and conveys no authority.

The v0.8.3 fixed user pages are reserved lower-half mappings with effective
user permissions and W^X policy. All loaded kernel leaves and page-table
storage remain supervisor-only. No Ring 3 code executes, so these mappings do
not establish a privilege boundary, process isolation, arbitrary user-pointer
acceptance, or general userspace. Page faults are not recovered.

---

# 6. Opaque Handles

Userspace-visible authority must be opaque.

Userspace must not learn kernel object addresses or layout through handles.

Opaque values must not be accepted as authority without validation.

---

# 7. Pointer Non-Exposure

Kernel object pointers must not be exposed to userspace.

Pointer exposure creates forgery and confused-authority risks.

Kernel memory identity must stay inside kernel authority.

---

# 8. Userspace Pointer Distrust

Userspace pointers are untrusted.

Kernel code must validate pointer and null expectations before dereference or mutation.

Pointer meaning comes from the syscall contract, not from local assumptions.

---

# 9. Syscall Boundary Validation

Syscall handlers must validate:

* syscall selector
* payload/null expectation
* request fields when a payload is present
* capability or authority requirements when privileged action is involved
* allowed mutation fields
* declared return status

Unknown syscalls must fail deterministically.

---

# 10. No-Payload Syscalls

A no-payload syscall uses the contract-defined no-payload argument.

For currently governed no-payload syscalls, that argument is a null payload pointer.

No-payload syscalls must not dereference or mutate payload state.

---

# 11. Payload Syscalls

Payload syscalls must declare payload layout, request expectations, response expectations, invalid behavior, and allowed mutations.

Payload mutation outside declared fields is forbidden.

---

# 12. Harness File-Scope Enforcement

The harness enforces task file scope during development.

File-scope enforcement protects repository integrity. It is not a runtime security mechanism.

---

# 13. Generated Artifact Integrity

Generated artifacts must be reproducible and validated against source truth.

Generated report drift is a governance failure.

Generated artifacts do not create runtime security guarantees by themselves.

---

# 14. Proof Validation as Development-Time Control

Validators, schemas, and verification scripts are development-time controls.

They are not kernel runtime enforcement.

A passing proof means the current repository state satisfies governed checks. It does not prove production readiness.

---

# 15. Relationship to Other Governance Documents

`INVARIANTS.md` owns non-negotiable security truths.

`CONTRACTS.md` owns boundary contract truth.

`VALIDATION.md` owns proof process.

`CODING_STYLE.md` owns how code should express these rules.

`COMPATIBILITY.md` owns compatibility claim limits.

The v0.7.5 controlled runtime loop introduces no new trust boundary or authority. Its state and marker bridges are boot-owned, fixed-size, and accept no userspace or externally controlled input. Successful loop evidence does not establish isolation, concurrency safety, scheduler policy, interrupt safety, userspace execution, or production security.

The v0.8.0 runtime status capability remains at the same privilege level and in the same kernel address space as its caller. Its request and response validation reduce internal interface drift; they do not create authentication, authorization, isolation, a userspace boundary, or a hardware syscall boundary. The fixed response exposes no general pointers and accepts no variable-length or externally supplied data.

The v0.8.1 CPU feature and state gate is not a security boundary. Enabling x87
and SSE does not provide process isolation, and no exception recovery or
per-task extended-state ownership exists. AVX remains prohibited because
OSXSAVE, XCR0 policy, XSAVE geometry, and save/restore ownership are not
implemented.

The v0.8.2 runtime state transition remains a same-address-space,
kernel-constructed operation. The request is not reachable from userspace and
does not cross an authentication, authorization, privilege, isolation, or
hardware syscall boundary. The capability can mutate only the named
boot-owned state cell from READY/0 to ACTIVE/1. It exposes no arbitrary target
address, dynamic registration, concurrency guarantee, atomic multi-thread
semantics, or persistent state.

---

# 16. Bounded Privilege-Transition Boundary

v0.8.4 proves one fixed CPL3 excursion and return. Ring 0 selects the target,
selectors, RFLAGS, user stack, token address, interrupt vector, return stack,
and CPL0 continuation. The CPL3 stub cannot choose an arbitrary kernel target
or pointer. The handler accepts only the fixed vector path and validates the
hardware-saved CPL3 frame and fixed probe state before continuation.

This boundary is not a process, sandbox, authentication or authorization
system, public syscall surface, arbitrary user-code facility, exception
recovery system, or general interrupt subsystem. The current fixed mappings
do not establish isolation between processes, and the probe does not return to
Ring 3.

---

# 17. Fixed User Request Boundary

v0.8.5 permits one fixed Ring3 request and one fixed Ring0 response in the
existing governed user-data page. Ring0 validates the hardware entry frame,
the complete fixed spans, exact request fields, and fixed backing before
copying data into supervisor-only shadows. The service operates only on those
shadows. The response is copied to the fixed response span, copied back into a
supervisor-only verification shadow, validated, and all boundary buffers are
cleared and checked zero before continuation.

This is not a generic copy-in/copy-out facility, public syscall ABI, arbitrary
pointer interface, persistent user session, process boundary, authentication
or authorization mechanism, sandbox, or isolation proof. The fixed exception
sinks remain fail-closed containment for this bounded probe; they do not
provide exception recovery, complete diagnostics, or safe execution of
arbitrary hostile user code.

# 18. Bounded User Response Consumption

The consumer RIP and RSP are fixed. The response and 48-byte record addresses
are fixed, and no user pointer or length is accepted. A supervisor-owned phase
selects the second handler. Ring 0 revalidates the response independently
before trusting the copied record.

There is no third Ring 3 transition or persistent userspace runtime. The fixed
fault sinks provide fail-closed containment for this probe only; they do not
prove exception recovery, diagnostic completeness, memory isolation against
arbitrary hostile code, or production safety.

# 19. Fixed User Runtime Status Service

Request identity, addresses, lengths, response fields, and feature bits are
fixed. The response exposes no pointer, physical address, stack address, or
page-table address. Ring 3 cannot select fields or service behavior.

The service reports only already proven runtime facts from one kernel-owned
post-loop snapshot. It is not a public syscall ABI, authorization boundary,
general status API, persistent user session, process boundary, sandbox, or
hostile-code safety proof.

# 20. Fixed User Execution Context Governance Boundary

ADR 0018 assigns context authority exclusively to Ring 0. User mode
cannot create, select, mutate, or clear the identity, lifecycle, mappings,
entry address, stack, selectors, return vector, transition budget, transition
count, transaction phase, service identity, return target, or cleanup state.
The identity is an opaque value, not a kernel pointer or PID.

Cleanup removes execution authority. The clear check must prove that identity,
bindings, transition state, and reserved fields are zero while lifecycle is
`CLEARED`. Failure evidence survives in a separate bounded result that cannot
reactivate the context or authorize later execution.

The bounded implementation applies this policy to the existing one-shot
transaction. Every existing return revalidates lifecycle, fixed identity,
bindings, phase, and count before the transaction can progress. A focused
unregistered validator and Linux QEMU evidence prove the implementation
without changing the governed marker taxonomy. This does not create a public
syscall or API, process isolation, repeated sessions, exception recovery, or
containment for arbitrary hostile user code.
