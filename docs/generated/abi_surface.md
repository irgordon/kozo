# KOZO ABI surface

Generated from:

* `contracts/kozo_abi_manifest.json`

This document is generated. Do not edit manually.

## Scope

This report summarizes the currently governed KOZO ABI surface. It does not declare a stable public ABI, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.

## Source files

| Source | Path |
| --- | --- |
| Canonical C header | `contracts/kozo_abi.h` |
| Generated Rust binding | `bindings/rust/kozo_abi.rs` |
| Generated Odin binding | `bindings/odin/kozo_abi.odin` |

## Status constants

| Constant | Value |
| --- | --: |
| K_OK | 0 |
| K_INVALID | 1 |
| K_DENIED | 2 |

## Syscall constants

| Constant | Value |
| --- | --: |
| K_SYSCALL_NOP | 0 |
| K_SYSCALL_DEBUG_HEARTBEAT | 1 |
| K_SYSCALL_STATUS | 2 |

## Layouts

### heartbeat_payload

| Field | Width | Offset |
| --- | --: | --: |
| sequence | 8 | 0 |
| timestamp | 8 | 8 |
| status_bits | 4 | 16 |

Struct size: 24
Struct alignment: 8

Names:

* C: `k_heartbeat_payload_t`
* Rust: `HeartbeatPayload`
* Odin: `Heartbeat_Payload`

## Heartbeat sentinels

### Request

| Field | Value |
| --- | --- |
| sequence | `0xCAFEFEED` |
| timestamp | `0` |
| status_bits | `K_INVALID` |

### Response

| Field | Value |
| --- | --- |
| sequence | `0xCAFEFEEE` |
| timestamp | `0xDEADBEEF` |
| status_bits | `K_OK` |

## Notes

* This report is generated from the ABI manifest.
* The ABI manifest, checked-in ABI files, and validators remain authoritative.
* This report is for review and operator readability only.
