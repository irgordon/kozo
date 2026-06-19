# KOZO governance index

Generated from repository governance surfaces.

This document is generated. Do not edit manually.

## Scope

This index summarizes active governance, verification, contract, schema, and generated report surfaces.

This index is not authoritative. Checked-in contracts, schemas, validators, generated proof artifacts, and the changelog remain the source of truth.

## Current version

* Version: `v0.3.1`
* Date: `2026-06-19`
* Status: Boot protocol selection.

## Verification status

* Status: `pass`
* Summary code: `OK`
* Total checks: 33
* Failed checks: 0
* Run ID: `verify-20260619T023004Z`
* Generated at: `2026-06-19T02:30:04Z`

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
| 28 | `boot_blocker_report` |
| 29 | `boot_protocol_decision` |
| 30 | `return_path_proof` |
| 31 | `execution_proof` |
| 32 | `validator_coverage` |
| 33 | `evidence` |

## Active contracts

| Path | Version | Role |
| --- | --- | --- |
| `contracts/kozo_abi_manifest.json` | `0` | ABI manifest |
| `contracts/syscall_boundary_contract.v0.json` | `0` | syscall boundary contract |
| `contracts/syscall_catalog.v0.json` | `0` | syscall catalog |
| `contracts/syscall_class_contract.v0.json` | `0` | syscall class contract |
| `contracts/syscall_table_contract.v0.json` | `0` | syscall table contract |

## Schemas

| Path | Title |
| --- | --- |
| `schemas/agent_context.schema.json` | agent_context.schema.json |
| `schemas/kozo_abi_manifest.schema.json` | kozo_abi_manifest.schema.json |
| `schemas/latest_verify.schema.json` | latest_verify.schema.json |
| `schemas/runtime.schema.json` | runtime.schema.json |
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
* Check count: 33
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
