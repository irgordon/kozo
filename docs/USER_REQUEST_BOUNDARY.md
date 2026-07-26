# Fixed User Request Boundary

Version: 0
Status: Implemented and locally evidenced; hosted CI pending

# 1. Authority

`contracts/fixed_user_request_boundary_contract.v0.json` owns this boundary.
This document is descriptive. Generated ELF and QEMU reports are evidence, not
authority.

# 2. Scope

v0.8.5 extends the fixed v0.8.4 CPL3 probe with one exact request and response
transaction. The fixed Ring3 stub constructs the request, invokes the existing
`int 0x81` gate, and never resumes. Ring0 validates the saved hardware frame
before accessing the shared page, copies the complete request to
supervisor-only storage, executes one deterministic service, copies one exact
response back, validates the readback, clears all transaction buffers, and
resumes the existing fixed Ring0 continuation.

# 3. Geometry

Both shared spans remain inside the accepted user RW-NX data page.

| Object | Address or symbol | Size | Alignment | Owner |
| --- | --- | ---: | ---: | --- |
| Request | `0x0000400000001000` | 40 | 8 | Fixed Ring3 probe |
| Response | `0x0000400000001080` | 48 | 8 | Ring0 boundary |
| Request shadow | `fixed_user_request_shadow` | 40 | 8 | Ring0 |
| Response shadow | `fixed_user_response_shadow` | 48 | 8 | Ring0 |
| Readback buffer | `fixed_user_response_verify` | 48 | 8 | Ring0 |

The request contains version, request identifier, request and response sizes,
sequence, payload, flags, and reserved fields. The response contains version,
request identifier, status, response size, sequence, echoed payload, observed
user and kernel CPL values, and a deterministic response token.

# 4. Validation Order

The Ring0 handler performs:

```text
saved CPL3 frame validation
complete fixed-span and RW-NX backing validation
exact 40-byte copy-in
every-field request validation
fixed service execution using supervisor shadows only
every-field response validation
exact 48-byte copy-out
exact response readback and validation
shared and supervisor buffer clearing
zero readback
fixed Ring0 continuation
```

The service computes only
`response_token = request.payload XOR 0xa5a55a5ac3c33c3c`. It accepts no
caller-selected identifier, pointer, length, function, or continuation.

# 5. Evidence

The governed boundary is:

```text
KOZO_RING3_ENTER
KOZO_USER_REQUEST_COPY_IN_OK
KOZO_USER_REQUEST_SERVICE_OK
KOZO_USER_RESPONSE_COPY_OUT_OK
KOZO_FIXED_USER_REQUEST_OK
KOZO_RING3_PROBE_OK
KOZO_RING0_RETURN_OK
KOZO_RUNTIME_PROGRESS_ENTRY
```

The four request-boundary markers are emitted in Ring0 only after their
corresponding validation completes. `KOZO_RING3_PROBE_OK` remains the enclosing
proof of validated CPL3 execution; Ring3 is not granted serial I/O.

# 6. Failure Behavior

Invalid range, copy, request, service, response, readback, clearing, or
continuation state returns a nonzero fixed status. `_start` suppresses later
success markers and converges on `boot_terminal_halt`. The fixed fault sinks
remain fail-closed containment for this probe; they do not provide exception
recovery, diagnostic completeness, or safe execution of arbitrary hostile
user code.

# 7. Claim Boundary

This phase proves one exact boot-time request and response transaction crossed
the already proven fixed CPL3/Ring0 boundary and that the complete transaction
was validated and cleared before the existing continuation.

It does not prove a general syscall ABI, arbitrary user-pointer handling,
general `copy_from_user` or `copy_to_user`, return to Ring3, persistent
userspace, processes, scheduling, isolation, Linux or POSIX compatibility, or
production readiness.
