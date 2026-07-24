# KOZO Contracts

Version: 1
Status: Authoritative
Scope: Contract purpose, contract source paths, and contract authority

---

# 1. Purpose

This document defines what KOZO means by a contract and which files own system boundary truth.

Contracts make implicit boundaries explicit. A boundary is not governed until it is backed by a checked-in contract and validation.

---

# 2. Authority

This document owns contract purpose and contract authority.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, and `docs/ARCHITECTURE.md`.

It does not own coding style, compatibility claims, security policy, generated artifact edit policy, or validator implementation details.

---

# 3. Non-Goals

This document does not define new ABI constants.

This document does not define new syscall behavior.

This document does not make generated reports authoritative.

This document does not claim Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.

---

# 4. What a Contract Is

A contract is a checked-in source of truth for a system boundary.

A contract must define the surface it owns clearly enough for validators, tests, and generated artifacts to compare implementation state against it.

Contracts may be human-readable, machine-readable, or both.

---

# 5. Rules

System boundary behavior must be contract-backed before it is treated as governed.

Generated bindings are outputs, not source truth.

Generated reports are summaries, not source truth.

Validators enforce contracts but do not create contract truth.

Contract changes require focused validation and generated artifact refresh where applicable.

---

# 6. Contract Source Paths

Current contract paths include:

| Contract | Path | Authority |
| --- | --- | --- |
| Canonical ABI header | `contracts/kozo_abi.h` | ABI constants, types, and layout source |
| ABI manifest | `contracts/kozo_abi_manifest.json` | Machine-readable ABI summary checked against ABI truth |
| Syscall boundary contract | `contracts/syscall_boundary_contract.v0.json` | Currently proven syscall call-boundary shape |
| Syscall table contract | `contracts/syscall_table_contract.v0.json` | Currently proven dispatcher table behavior |
| Syscall class contract | `contracts/syscall_class_contract.v0.json` | Semantic syscall class rules |
| Syscall catalog | `contracts/syscall_catalog.v0.json` | Governed syscall summary checked against source contracts |
| Runtime evidence taxonomy | `contracts/runtime_evidence_taxonomy.v0.json` | Governed QEMU smoke marker, outcome, and blocker vocabulary |
| Runtime halt contract | `contracts/runtime_halt_contract.v0.json` | Post-smoke terminal behavior after `KOZO_BOOT_SMOKE_OK` |
| Runtime progression contract | `contracts/runtime_progression_contract.v0.json` | Future halt-to-runtime transition governance |
| Runtime progression entry contract | `contracts/runtime_progression_entry_contract.v0.json` | Internal assembly-to-Odin boundary, bounded initialization, and exact return governance |
| Runtime progression stages contract | `contracts/runtime_progression_stages.v0.json` | Canonical future runtime progression stage model |
| Controlled runtime loop contract | `contracts/controlled_runtime_loop_contract.v0.json` | Bounded Odin loop state, marker, status, evidence, transition, and halt-continuation boundary |
| First governed runtime capability | `contracts/first_governed_runtime_capability.v0.json` | Versioned internal runtime status request, fixed response, dispatch, marker, claim, and halt-continuation boundary |
| Stack initialization evidence contract | `contracts/stack_initialization_evidence_contract.v0.json` | Controlled stack proof boundary and marker evidence |
| Memory initialization evidence contract | `contracts/memory_initialization_evidence_contract.v0.json` | Future memory proof boundary and marker reservation |

---

# 7. ABI Header Authority

`contracts/kozo_abi.h` is the authoritative ABI contract.

Generated Rust and Odin bindings are outputs derived from ABI truth. They are not edited directly and do not override the header or governed manifest.

If bindings drift from the ABI contract, fix the contract or generator path and regenerate through the governed workflow.

---

# 8. ABI Manifest Role

`contracts/kozo_abi_manifest.json` is the machine-readable ABI manifest.

It records currently governed ABI constants, generated binding paths, heartbeat payload layout, and heartbeat request/response sentinels.

The manifest reduces duplicated validator constants, but it does not replace the canonical ABI header.

---

# 9. Syscall Contract Roles

`contracts/syscall_boundary_contract.v0.json` describes the currently proven syscall boundary shape.

`contracts/syscall_table_contract.v0.json` describes currently proven dispatcher entries and unknown-syscall behavior.

`contracts/syscall_class_contract.v0.json` describes syscall class semantics such as no-payload status syscalls and payload-mutating status syscalls.

Each syscall behavior must match its declared contract and class.

---

# 10. Catalog Role

`contracts/syscall_catalog.v0.json` summarizes governed syscall entries.

The catalog is a review and coordination surface. It does not own ABI values, table semantics, class semantics, runtime behavior, or compatibility claims.

Catalog entries must be validated against the authoritative contracts and source proofs.

---

# 11. Runtime Evidence Taxonomy Contract Role

`contracts/runtime_evidence_taxonomy.v0.json` owns the governed vocabulary for QEMU serial smoke markers, marker order, smoke outcomes, blocker categories, pass condition, blocked condition, and taxonomy-level non-goals.

It centralizes marker and blocker names so scripts, validators, tests, documentation, and generated evidence metadata do not define independent taxonomies.

Generated smoke metadata remains evidence. It does not define taxonomy authority.

This contract does not define runtime behavior, ABI values, syscall behavior, linker behavior, marker emission behavior, compatibility claims, or production readiness.

---

# 12. Runtime Halt Contract Role

`contracts/runtime_halt_contract.v0.json` describes the governed terminal behavior after the assembly boot smoke marker path emits `KOZO_BOOT_SMOKE_OK`.

It requires the post-marker path in `kernel/arch/x86_64/boot.asm` to enter a deterministic halt loop without falling through into unrelated bytes.

It does not define ABI values, syscall behavior, interrupt handling, scheduler behavior, userspace execution, hardware trap execution, or production readiness.

---

# 13. Runtime Progression Contract Role

`contracts/runtime_progression_contract.v0.json` describes governance for the bounded transition from evidence-complete assembly boot code into a separately validated runtime progression path and back to the terminal halt path.

It requires stack initialization evidence, memory initialization evidence, and progression path evidence before the halt loop can be removed, replaced, bypassed, or jumped around. It owns halt-preservation governance, not the canonical stage order.

It owns transition governance, not implementation evidence. It does not define ABI values, define syscall behavior, enable interrupt handling, initialize a scheduler, start userspace execution, or claim compatibility or production readiness.

---

# 14. Runtime Progression Entry Contract Role

`contracts/runtime_progression_entry_contract.v0.json` defines the implemented internal assembly-to-Odin progression boundary.

It defines the System V AMD64 C call convention, fixed bootstrap context, Odin-owned initialization marker path, exact return status, and final assembly continuation. It owns the `MEMORY_INITIALIZATION_EVIDENCE` to `RUNTIME_PROGRESSION_ENTRY` and `RUNTIME_PROGRESSION_ENTRY` to `RUNTIME_INITIALIZATION_EVIDENCE` proof boundaries but does not define canonical stage order.

The contract and source structure do not prove executed Odin code by themselves. Final promotion requires passing QEMU serial evidence for `KOZO_RUNTIME_PROGRESS_ENTRY`, Odin-dependent `KOZO_RUNTIME_INIT_OK`, and `KOZO_RUNTIME_RETURN_OK`. The contract does not replace the runtime halt contract, expose a userspace ABI, enable userspace execution, or claim complete Odin runtime readiness, compatibility, or production readiness.

---

# 15. Runtime Progression Stages Contract Role

`contracts/runtime_progression_stages.v0.json` owns the canonical stage model for future runtime progression.

It defines stage order, stage prerequisites, required evidence, required contracts, required validators, allowed next stages, transition ownership, and forbidden shortcuts from `BOOT_SMOKE` through `USERSPACE_PLANNING`. Evidence contracts own only their destination-stage proof boundaries.

Planning documents may describe the stage model, but they do not define it. If planning text conflicts with this contract, this contract wins and the planning document must be corrected.

This contract does not implement runtime progression, replace the halt loop, initialize memory, execute Odin runtime code, enable interrupts, enable userspace execution, or claim compatibility or production readiness.

---

# 16. Stack Initialization Evidence Contract Role

`contracts/stack_initialization_evidence_contract.v0.json` defines what KOZO must prove before claiming controlled boot stack initialization evidence.

It defines `KOZO_STACK_INIT_OK` as the stack evidence marker, records the controlled static boot stack source fields, defines prerequisites, evidence requirements, proof boundaries, assumptions enabled by stack evidence, assumptions that remain invalid, and non-goals.

The marker is emitted by current runtime code after `rsp` is loaded from `boot_stack_top` and a minimal stack-use probe runs. It must still be captured from runtime code through a governed evidence path before generated evidence can claim a passing sequence.

This contract does not allocate memory dynamically, execute Odin runtime code, replace the halt loop, enable interrupts, add userspace execution, prove general stack readiness, or claim compatibility or production readiness.

---

# 17. Memory Initialization Evidence Contract Role

`contracts/memory_initialization_evidence_contract.v0.json` defines what KOZO must prove before claiming controlled memory initialization evidence.

It defines `KOZO_MEMORY_INIT_OK` and the exact implemented proof boundary: a 4096-byte, 4096-byte-aligned static `.bss` region owned by the x86_64 boot memory evidence path; full-region zero fill; a bounded 64-bit sentinel write/read/compare/restore probe; and marker emission only after initialization and probe success and before the halt loop.

The contract owns the destination-stage proof boundary. `contracts/runtime_progression_stages.v0.json` remains the sole authority for stage order and transitions. The schema and validators make the implemented source boundary and captured marker evidence mechanically checkable.

The marker is emitted by current assembly only after the governed zero fill and probe succeed. This contract does not prove physical memory discovery, paging, virtual memory management, allocator behavior, heap allocation, Odin runtime execution, halt replacement, interrupts, scheduler behavior, userspace execution, compatibility, or production readiness.

---

# 18. Generated Reports

Generated reports are summaries.

Examples:

* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`

Generated reports do not own contract truth. If a generated report conflicts with a contract, the contract wins and the report must be regenerated.

---

# 18. Validators as Proof Mechanisms

Validators prove that checked-in source, contracts, generated artifacts, and task state agree.

Validators do not create contract truth. They enforce it.

When a validator finds missing source, missing evidence, stale generated reports, or contract drift, it must fail closed.

---

# 19. Contract Change Requirements

A contract change requires:

* a clear statement of the changed boundary
* focused tests for positive and negative paths
* validator updates when proof behavior changes
* generated artifact refresh when generated outputs depend on the contract
* changelog update
* ADR when architecture, ABI model, syscall boundary semantics, security assumptions, or document authority changes

---

# 19. Relationship to Other Governance Documents

`GOVERNANCE.md` owns document precedence.

`INVARIANTS.md` owns non-negotiable truths.

`ARCHITECTURE.md` owns system structure.

`VALIDATION.md` owns harness rules.

`GENERATED_ARTIFACTS.md` owns generated-file edit policy.

`ADR_POLICY.md` owns decision-record requirements.

---

# 20. Controlled Runtime Loop Contract Role

`contracts/controlled_runtime_loop_contract.v0.json` owns the `RUNTIME_INITIALIZATION_EVIDENCE` to `CONTROLLED_RUNTIME_LOOP` proof boundary. It fixes the loop at three iterations, defines the static volatile state layout and final values, governs loop markers and internal statuses, requires linked ELF symbols plus a retained binary backward edge, and preserves the runtime halt contract after exact success.

The contract does not authorize a scheduler, interrupts, allocation, userspace, process, VFS, file descriptor, compatibility, or production behavior.

---

# 21. First Governed Runtime Capability Role

`contracts/first_governed_runtime_capability.v0.json` owns the `CONTROLLED_RUNTIME_LOOP` to `FIRST_GOVERNED_RUNTIME_CAPABILITY` proof boundary. It defines capability ID 1 (`RUNTIME_STATUS_QUERY`), request version 1 with a 16-byte/4-byte-aligned layout, response version 1 with a 64-byte/8-byte-aligned layout, exact status values, validation requirements, marker ownership, and terminal continuation.

The response reports the last accepted baseline, stage 5 with mask `0x3f`, plus the governed 4096-byte memory-region size and executed loop values 3, 3, and 6. It does not report the capability stage as already proven. The contract creates no public ABI, userspace access, privilege separation, hardware syscall entry, scheduler, process, allocation, compatibility, or production claim.
