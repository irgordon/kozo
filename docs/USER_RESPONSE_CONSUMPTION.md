# Bounded User Response Consumption

Status: v0.8.6 implemented and validated locally; hosted CI acceptance pending.

Authority: `contracts/bounded_user_response_consumption_contract.v0.json`.

# 1. Purpose

v0.8.6 extends the accepted fixed user-request boundary with one sanitized
return to a fixed Ring 3 response consumer. The consumer validates the exact
kernel response, writes one fixed consumption record, and invokes the existing
`int 0x81` gate a second time. This remains one boot-time transaction.

# 2. Accepted Prerequisites

The implementation depends on the hosted-accepted fixed user mappings,
bounded privilege transition, and v0.8.5 fixed request boundary. The governed
page layout, selectors, TSS.RSP0, interrupt gate, and terminal halt remain
unchanged.

# 3. Two-Stage Transaction

```text
REQUEST_PENDING
-> first int 0x81
-> fixed request service and response copy-out
-> RESPONSE_READY
-> sanitized iretq to fixed response consumer
-> response validation and fixed record creation
-> second int 0x81
-> Ring 0 response and record validation
-> CONSUMED
-> fixed Ring 0 continuation
-> REQUEST_PENDING
```

The phase is a supervisor-only 8-byte cell. Ring 3 receives no phase pointer
and cannot select a handler.

# 4. Fixed Resume Boundary

The second Ring 3 RIP is `user_response_consumer_start`. The RSP is the fixed
accepted `USER_INITIAL_RSP`. Ring 0 constructs a fresh `iretq` frame with the
fixed user selectors and sanitized RFLAGS `0x2`. The consumer validates CPL3,
the exact stack value, stack push/pop survival, and every response field.

# 5. Consumption Record

The consumer writes exactly 48 bytes at
`0x0000400000001100` (`USER_PROBE_DATA_VA + 0x100`):

| Offset | Size | Field | Required value |
| --- | ---: | --- | --- |
| `0x00` | 4 | version | `1` |
| `0x04` | 4 | record ID | `1` |
| `0x08` | 4 | record size | `48` |
| `0x0c` | 4 | validation status | `0` |
| `0x10` | 8 | sequence | accepted response sequence |
| `0x18` | 8 | echoed payload | accepted response payload |
| `0x20` | 8 | response token | accepted response token |
| `0x28` | 8 | reserved | `0` |

The address and length are fixed. No user pointer or length crosses the gate.
The record does not overlap the request, response, code, stack, or supervisor
storage.

# 6. Second Ring 0 Handler

The phase selects the second handler. It validates the saved CPL3 frame,
fixed RIP, fixed RSP, selectors, RFLAGS, current CPL0, and TSS.RSP0 stack
bounds. It then revalidates the fixed response mapping and all six response
qwords, copies six qwords into `fixed_user_consumption_shadow`, and validates
every record field.

# 7. Clearing and Continuation

After validation, Ring 0 clears the user response, user record, response
shadow, consumption shadow, and response verification storage. Zero readback
must pass before the phase becomes `CONSUMED`. The fixed Ring 0 continuation
revalidates CPL0, selectors, kernel stack, phase, and zeroed buffers, then
resets the phase to `REQUEST_PENDING` before the existing Odin path.

# 8. Evidence

The governed boundary is:

```text
KOZO_USER_RESPONSE_COPY_OUT_OK
KOZO_RING3_RESPONSE_RESUME
KOZO_USER_RESPONSE_CONSUMED_OK
KOZO_FIXED_USER_RESPONSE_OK
KOZO_FIXED_USER_REQUEST_OK
KOZO_RING3_PROBE_OK
KOZO_RING0_RETURN_OK
KOZO_RUNTIME_PROGRESS_ENTRY
```

ELF evidence requires the fixed phase and shadow geometry, two `iretq` sites,
two `int 0x81` sites, response comparisons, fixed record stores and copy,
clearing operations, fixed continuation, and prohibited-instruction scan.
QEMU evidence must contain the complete 40-marker sequence exactly once.

# 9. Failure Behavior

Invalid phase, resume frame, span, response content, record copy, record
content, clearing, or continuation returns a nonzero fixed status. No later
transaction or runtime success marker is emitted. The existing boot caller
converges on the terminal halt.

# 10. Claim Boundary

This phase proves one fixed response was consumed by one fixed CPL3
continuation and validated again by one fixed Ring 0 handler. It does not
prove persistent Ring 3 execution, multiple request loops, a general syscall
ABI, arbitrary pointers or messages, process isolation, hostile-code safety,
scheduling, compatibility, or production readiness.

# 11. Future Work

A later implementation may expose one existing deterministic kernel status
service through this same fixed boundary. That work must retain fixed geometry
and must not infer a general syscall ABI from this one-shot proof.
