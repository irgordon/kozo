# Fixed User Runtime Status Service

Status: v0.8.7 implemented with local verification and 41-marker QEMU
evidence. The first hosted run completed the runtime sequence but exposed a
GNU/LLVM ELF-report parsing difference; hosted correction acceptance is
pending.

## 1. Scope

v0.8.7 exposes the existing deterministic runtime-status logic through the
accepted one-shot Ring 3 transaction. The controlled Odin loop completes
before KOZO collects the status snapshot or enters Ring 3.

This service is not a public syscall ABI. It accepts no arbitrary pointer,
length, field selection, or service registration.

## 2. Decision

**Decision**

Use request ID `2` at the existing request address
`0x0000400000001000`. Return one fixed 88-byte response at
`0x0000400000001080`.

**Reason**

One shared kernel snapshot keeps the internal capability and fixed user
response consistent while preserving separate response layouts.

**Rejected**

A generic dispatcher, direct copying of the internal capability response, and
assembly-owned status policy were rejected because each would create a second
authority or broaden the boundary.

**Rule**

The request must validate completely before status collection is consumed.
The response must validate completely before copy-out and again after Ring 3
consumption.

## 3. Runtime Order

```text
controlled runtime loop
-> collect_runtime_status
-> fixed Ring 3 request
-> fixed user runtime-status response
-> Ring 3 response validation
-> Ring 0 response and record revalidation
-> internal capability ID 1
-> internal capability ID 2
-> governed runtime return
-> terminal halt
```

The snapshot is collected once after the loop. The fixed user service and
internal capability ID 1 read that same snapshot. Odin clears and verifies the
snapshot before capability ID 2 runs.

## 4. Request Geometry

The request remains 40 bytes:

| Offset | Size | Field | Required value |
| --- | ---: | --- | --- |
| `0x00` | 4 | version | `1` |
| `0x04` | 4 | request ID | `2` |
| `0x08` | 4 | request size | `40` |
| `0x0c` | 4 | response size | `88` |
| `0x10` | 8 | sequence | `1` |
| `0x18` | 8 | payload | `0` |
| `0x20` | 4 | flags | `0` |
| `0x24` | 4 | reserved | `0` |

Request ID `2` belongs only to this fixed boundary. It is not the internal
capability ID and is not a public syscall number.

## 5. Status Snapshot

`runtime_status_snapshot` is a 64-byte, 8-byte-aligned, supervisor-only
object. It contains no pointers:

| Field | Governed value |
| --- | ---: |
| current progression stage | `5` |
| reserved 0 | `0` |
| proven stage mask | `0x3f` |
| boot memory region size | `4096` |
| controlled-loop limit | `3` |
| controlled-loop final count | `3` |
| controlled-loop accumulator | `6` |
| runtime feature mask | `0x7f` |
| reserved 1 | `0` |

The stage and loop values come from the completed Odin runtime state. Planned
stages are not included in the proven mask.

## 6. User Response

The fixed response uses 88 bytes:

| Offset | Size | Field | Required value |
| --- | ---: | --- | --- |
| `0x00` | 4 | version | `1` |
| `0x04` | 4 | request ID | `2` |
| `0x08` | 4 | status | `0` |
| `0x0c` | 4 | response size | `88` |
| `0x10` | 8 | sequence | `1` |
| `0x18` | 4 | current runtime stage | `5` |
| `0x1c` | 4 | reserved 0 | `0` |
| `0x20` | 8 | proven stage mask | `0x3f` |
| `0x28` | 8 | boot memory region size | `4096` |
| `0x30` | 8 | loop iteration limit | `3` |
| `0x38` | 8 | loop final count | `3` |
| `0x40` | 8 | loop final accumulator | `6` |
| `0x48` | 8 | feature mask | `0x7f` |
| `0x50` | 8 | reserved 1 | `0` |

Feature bits are authoritative in
`contracts/fixed_user_runtime_status_service_contract.v0.json`:

| Bit | Proven fixed feature |
| ---: | --- |
| 0 | fixed user mappings |
| 1 | CPU extended state |
| 2 | bounded Ring 3 transition |
| 3 | fixed user request boundary |
| 4 | bounded response consumption |
| 5 | first internal runtime capability |
| 6 | second internal runtime capability |

All other feature bits must remain zero.

## 7. Validation

Ring 3 compares every response field against fixed contract values. It writes
the existing 48-byte consumption record only after all fields match. The
record digest is the XOR of the eleven response qwords.

The second Ring 0 handler compares the user response with the retained
supervisor shadow, validates every field again, validates the complete
consumption record and digest, then clears all user and supervisor transaction
buffers. Odin separately clears `runtime_status_snapshot` after capability ID
1 consumes it.

## 8. Variables

| Variable | Purpose | Writer | Reader | Cleared |
| --- | --- | --- | --- | --- |
| `runtime_status_snapshot` | Holds proven post-loop runtime values | `collect_runtime_status` | fixed user formatter and capability ID 1 formatter | after both consumers finish |
| `fixed_user_response_shadow` | Holds the validated user response | Ring 0 response builder | copy-out and Ring 0 revalidation | after consumption |
| `fixed_user_consumption_shadow` | Holds the Ring 3 validation record | second Ring 0 handler | record validator | after final validation |
| `fixed_user_transaction_phase` | Selects request or response handling | Ring 0 handlers | Ring 0 handlers | reset before Odin continues |

## 9. Functions

| Function | Plain-language responsibility |
| --- | --- |
| `collect_runtime_status` | Read the runtime values already proven by KOZO |
| `validate_runtime_status_snapshot` | Check that the snapshot is internally consistent |
| `query_runtime_status` | Build and validate the internal capability response |
| `build_internal_runtime_status_response` | Format the unchanged 64-byte internal response |
| `build_fixed_user_runtime_status_response` | Format the fixed 88-byte Ring 3 response |
| `validate_fixed_user_response` | Check every user-response field before copy-out |
| `execute_fixed_user_runtime_status_transaction` | Run the accepted two-stage Ring 3 transaction |

## 10. Evidence Markers

```text
KOZO_USER_REQUEST_COPY_IN_OK
KOZO_USER_RUNTIME_STATUS_SERVICE_ENTER
KOZO_USER_RUNTIME_STATUS_SERVICE_OK
KOZO_USER_RESPONSE_COPY_OUT_OK
KOZO_RING3_RESPONSE_RESUME
KOZO_USER_RESPONSE_CONSUMED_OK
KOZO_FIXED_USER_RESPONSE_OK
KOZO_FIXED_USER_REQUEST_OK
```

Service entry follows complete request validation. Service success follows
snapshot validation, response formatting, and complete Ring 0 response
validation. Copy-out occurs only after service success.

## 11. Failure And Cleanup

Invalid request identity, geometry, payload, snapshot, response field, digest,
phase, frame, or cleanup state suppresses every later success marker and
converges on the existing halt path. Transaction buffers and the status
snapshot must read back as zero before later runtime success.

The fixed fault sinks provide fail-closed containment for this bounded probe.
They do not provide exception recovery, complete diagnostics, or safe
execution of arbitrary hostile code.

## 12. Claim Boundary

This phase proves one fixed post-loop status transaction built from the same
status source as internal capability ID 1. It does not prove a general
dispatcher, public syscall ABI, arbitrary status query, variable-sized
message, persistent Ring 3 execution, process model, scheduler, isolation,
Linux or POSIX compatibility, or production readiness.

## 13. CI Correction

Hosted QEMU completed the full status transaction, but the GNU ELF report did
not recognize the Ring 3 comparison instructions. GNU associated the consumer
start address with the adjacent `user_privilege_probe_end` alias, so
symbol-specific disassembly returned an empty body even though full
disassembly contained all required instructions.

The report now bounds the consumer by the authoritative start and end symbol
addresses. It normalizes known equivalent `cmp`, `cmpl`, and `cmpq` spellings,
checks all 14 contract response offsets, requires the existing comparison
threshold, and proves record-store, `int 0x81`, and `ud2` order.

This correction changes only how equivalent GNU and LLVM instruction text is
read. It does not change runtime code, marker order, response geometry, or
validator policy.

Future ELF evidence must not depend on one `objdump` spelling. Normalize known
equivalent forms first, then apply the same governed evidence checks.
