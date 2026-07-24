# KOZO governance index

Generated from repository governance surfaces.

This document is generated. Do not edit manually.

## Scope

This index summarizes active governance, verification, contract, schema, and generated report surfaces.

This index is not authoritative. Checked-in contracts, schemas, validators, generated proof artifacts, and the changelog remain the source of truth.

## Current version

* Version: `v0.7.5`
* Date: `2026-07-23`
* Status: Implemented locally; hosted CI evidence pending.

## Verification status

* Status: `pass`
* Summary code: `OK`
* Total checks: 51
* Failed checks: 0
* Run ID: `verify-20260724T004930Z`
* Generated at: `2026-07-24T00:49:30Z`

## Registered validators

| Order | Validator |
| --: | --- |
| 1 | `schema` |
| 2 | `plan_lifecycle` |
| 3 | `step_scope` |
| 4 | `verification_refs` |
| 5 | `explanation` |
| 6 | `preconditions` |
| 7 | `subagent` |
| 8 | `rust` |
| 9 | `odin` |
| 10 | `abi` |
| 11 | `abi_manifest` |
| 12 | `abi_surface_report` |
| 13 | `syscall_boundary_contract` |
| 14 | `syscall_boundary_conformance` |
| 15 | `syscall_table_contract` |
| 16 | `syscall_class_contract` |
| 17 | `syscall_table_conformance` |
| 18 | `syscall_catalog` |
| 19 | `syscall_surface_report` |
| 20 | `governance_index_report` |
| 21 | `protocol_contract_alignment` |
| 22 | `layout_parity` |
| 23 | `execution_foundation` |
| 24 | `bridge_alignment` |
| 25 | `runtime_trap_path` |
| 26 | `runtime_smoke_evidence` |
| 27 | `runtime_evidence_review` |
| 28 | `runtime_evidence_taxonomy` |
| 29 | `runtime_halt_contract` |
| 30 | `runtime_progression_contract` |
| 31 | `runtime_progression_entry_contract` |
| 32 | `runtime_progression_evidence` |
| 33 | `runtime_progression_stages` |
| 34 | `stack_initialization_evidence_contract` |
| 35 | `stack_initialization_evidence` |
| 36 | `memory_initialization_evidence_contract` |
| 37 | `memory_initialization_evidence` |
| 38 | `controlled_runtime_loop_contract` |
| 39 | `controlled_runtime_loop_evidence` |
| 40 | `boot_blocker_report` |
| 41 | `boot_protocol_decision` |
| 42 | `boot_image_skeleton` |
| 43 | `boot_image_packaging` |
| 44 | `boot_tooling` |
| 45 | `kernel_loadability` |
| 46 | `host_dependency_portability` |
| 47 | `qemu_smoke_evidence` |
| 48 | `return_path_proof` |
| 49 | `execution_proof` |
| 50 | `validator_coverage` |
| 51 | `evidence` |

## Active contracts

| Path | Version | Role |
| --- | --- | --- |
| `contracts/controlled_runtime_loop_contract.v0.json` | `0` | controlled runtime loop contract.v0 |
| `contracts/kozo_abi_manifest.json` | `0` | ABI manifest |
| `contracts/memory_initialization_evidence_contract.v0.json` | `0` | memory initialization evidence contract.v0 |
| `contracts/runtime_evidence_taxonomy.v0.json` | `0` | runtime evidence taxonomy.v0 |
| `contracts/runtime_halt_contract.v0.json` | `0` | runtime halt contract.v0 |
| `contracts/runtime_progression_contract.v0.json` | `0` | runtime progression contract.v0 |
| `contracts/runtime_progression_entry_contract.v0.json` | `0` | runtime progression entry contract.v0 |
| `contracts/runtime_progression_stages.v0.json` | `0` | runtime progression stages.v0 |
| `contracts/stack_initialization_evidence_contract.v0.json` | `0` | stack initialization evidence contract.v0 |
| `contracts/syscall_boundary_contract.v0.json` | `0` | syscall boundary contract |
| `contracts/syscall_catalog.v0.json` | `0` | syscall catalog |
| `contracts/syscall_class_contract.v0.json` | `0` | syscall class contract |
| `contracts/syscall_table_contract.v0.json` | `0` | syscall table contract |

## Schemas

| Path | Title |
| --- | --- |
| `schemas/agent_context.schema.json` | agent_context.schema.json |
| `schemas/controlled_runtime_loop_contract.schema.json` | KOZO controlled runtime loop contract |
| `schemas/kozo_abi_manifest.schema.json` | kozo_abi_manifest.schema.json |
| `schemas/latest_verify.schema.json` | latest_verify.schema.json |
| `schemas/memory_initialization_evidence_contract.schema.json` | KOZO memory initialization evidence contract |
| `schemas/runtime.schema.json` | runtime.schema.json |
| `schemas/runtime_evidence_taxonomy.schema.json` | KOZO runtime evidence taxonomy |
| `schemas/runtime_halt_contract.schema.json` | KOZO runtime halt contract |
| `schemas/runtime_progression_contract.schema.json` | KOZO runtime progression contract |
| `schemas/runtime_progression_entry_contract.schema.json` | KOZO runtime progression entry contract |
| `schemas/runtime_progression_stages.schema.json` | KOZO runtime progression stages contract |
| `schemas/stack_initialization_evidence_contract.schema.json` | KOZO stack initialization evidence contract |
| `schemas/syscall_boundary_contract.schema.json` | syscall_boundary_contract.schema.json |
| `schemas/syscall_catalog.schema.json` | syscall_catalog.schema.json |
| `schemas/syscall_class_contract.schema.json` | syscall_class_contract.schema.json |
| `schemas/syscall_table_contract.schema.json` | syscall_table_contract.schema.json |
| `schemas/todo.schema.json` | todo.schema.json |

## Generated reports

| Path | Authority |
| --- | --- |
| `docs/generated/syscall_surface.md` | non-authoritative |
| `docs/generated/abi_surface.md` | non-authoritative |
| `docs/generated/governance_index.md` | non-authoritative |

## Latest proof artifact

* Path: `artifacts/latest_verify.json`
* Status: `pass`
* Check count: 51
* Failure count: 0

## Non-goals

* no Linux compatibility claim
* no userspace execution claim
* no process model behavior claim
* no VFS behavior claim
* no scheduler behavior claim
* no ELF loading behavior claim
* no file descriptor behavior claim
* no production readiness claim
* generated reports are non-authoritative
