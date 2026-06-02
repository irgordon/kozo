# KOZO syscall surface

Generated from:

* `contracts/syscall_catalog.v0.json`
* `contracts/syscall_table_contract.v0.json`
* `contracts/syscall_class_contract.v0.json`
* `contracts/kozo_abi_manifest.json`

This document is generated. Do not edit manually.

## Scope

This report summarizes currently governed KOZO syscalls only. It does not declare Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.

## Summary

| Syscall | Constant | ID | Kind | Class | Payload | Return | Mutates payload | Runtime probe |
| --- | ---: | -: | --- | --- | --- | --- | --- | --- |
| nop | K_SYSCALL_NOP | 0 | no_payload | no_payload_status | null | K_OK | no | yes |
| status | K_SYSCALL_STATUS | 2 | no_payload | no_payload_status | null | K_OK | no | yes |
| debug_heartbeat | K_SYSCALL_DEBUG_HEARTBEAT | 1 | payload | payload_mutating_status | heartbeat_payload | K_OK | sequence, timestamp, status_bits | yes |

## Syscalls

### nop

* Constant: `K_SYSCALL_NOP`
* Numeric ID: `0`
* Kind: `no_payload`
* Class: `no_payload_status`
* Payload behavior: null payload, no layout
* Return status: `K_OK`
* Mutates payload: no
* Branch selector: `abi.K_SYSCALL_NOP`
* Runtime probe: present
* Proof validators:

  * `abi_manifest`
  * `protocol_contract_alignment`
  * `syscall_table_contract`
  * `syscall_class_contract`
  * `syscall_table_conformance`
  * `runtime_trap_path`

### status

* Constant: `K_SYSCALL_STATUS`
* Numeric ID: `2`
* Kind: `no_payload`
* Class: `no_payload_status`
* Payload behavior: null payload, no layout
* Return status: `K_OK`
* Mutates payload: no
* Branch selector: `abi.K_SYSCALL_STATUS`
* Runtime probe: present
* Proof validators:

  * `abi_manifest`
  * `protocol_contract_alignment`
  * `syscall_table_contract`
  * `syscall_class_contract`
  * `syscall_table_conformance`
  * `runtime_trap_path`

### debug_heartbeat

* Constant: `K_SYSCALL_DEBUG_HEARTBEAT`
* Numeric ID: `1`
* Kind: `payload`
* Class: `payload_mutating_status`
* Payload behavior: pointer payload, `heartbeat_payload` layout
* Return status: `K_OK`
* Mutates payload: yes (`sequence`, `timestamp`, `status_bits`)
* Branch selector: `abi.K_SYSCALL_DEBUG_HEARTBEAT`
* Runtime probe: present
* Proof validators:

  * `abi_manifest`
  * `protocol_contract_alignment`
  * `layout_parity`
  * `syscall_boundary_contract`
  * `syscall_boundary_conformance`
  * `syscall_table_contract`
  * `syscall_class_contract`
  * `syscall_table_conformance`
  * `runtime_trap_path`
  * `execution_proof`
  * `return_path_proof`

## Syscall classes

* `no_payload_status`: payload argument `null`, payload layout required `no`, request required `no`, response required `no`, payload mutation `forbidden`, return status required `yes`, examples `nop, status`.
* `payload_mutating_status`: payload argument `pointer`, payload layout required `yes`, request required `yes`, response required `yes`, payload mutation `required`, return status required `yes`, examples `debug_heartbeat`.

## Notes

* This report is generated from contracts.
* The catalog summarizes existing governed syscalls and is not the source of truth.
* Runtime behavior is validated by source-level validators.
* No Linux compatibility is claimed.
