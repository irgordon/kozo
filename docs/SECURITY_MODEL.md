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
